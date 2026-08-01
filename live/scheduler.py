"""Daily live paper-trading job.

Run once per trading day (scheduled via .github/workflows/paper-trading.yml):
pull the latest Alpaca price/news data, recompute the composite signal, size
and risk-limit a target book against the account's actual current equity, and
submit the resulting orders. Every step is logged to SQLite (live/storage.py)
so the dashboard and backtest-vs-live reconciliation have a full record.

The kill-switch is checked against the account's actual equity *before* any
new orders are generated - if it fires, the run flattens existing positions
and submits nothing else, exactly like the backtest engine's halt behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from config.universe import TICKER_SECTOR, UNIVERSE
from data.news import load_news
from data.prices import load_prices
from factors import mean_reversion, momentum, sentiment, volatility
from factors.composite import combine_factors, select_deciles
from live import storage
from live.alpaca_client import AlpacaClient
from risk.kill_switch import KillSwitch
from risk.limits import apply_limits
from risk.sizing import size_portfolio

HISTORY_WINDOW_DAYS = 450
DECILE_FRACTION = 0.1
MIN_CROSS_SECTION_BREADTH = 10
TARGET_VOL = 0.10
KILL_SWITCH_DRAWDOWN = 0.15


def run_daily() -> None:
    conn = storage.get_connection()
    client = AlpacaClient()

    today = datetime.now(UTC).date()
    start = (pd.Timestamp(today) - pd.Timedelta(days=HISTORY_WINDOW_DAYS)).strftime("%Y-%m-%d")
    end = (pd.Timestamp(today) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    prices = load_prices(UNIVERSE, start, end, source="alpaca")
    news = load_news(UNIVERSE, start, end, source="alpaca")

    if prices.empty:
        print("No price data returned for today; skipping run.")
        return

    factor_scores = {
        momentum.name: momentum.compute(prices),
        mean_reversion.name: mean_reversion.compute(prices),
        volatility.name: volatility.compute(prices),
        sentiment.name: sentiment.compute(prices, news),
    }
    composite = combine_factors(factor_scores, prices)

    latest_date = prices["date"].max()
    day_scores = (
        composite[composite["date"] == latest_date].set_index("ticker")["composite_score"].dropna()
    )

    account = client.get_account()
    equity = account["equity"]

    kill_switch = KillSwitch(KILL_SWITCH_DRAWDOWN)
    triggered = kill_switch.check(equity)

    current_positions = client.get_positions()
    submitted_at = datetime.now(UTC).isoformat()

    if triggered:
        print(f"Kill switch triggered (equity={equity:.2f}); flattening all positions.")
        for ticker, shares in current_positions.items():
            result = client.submit_order(ticker, -shares)
            storage.log_order(conn, str(latest_date), ticker, -shares, submitted_at)
            print(result)
        storage.log_snapshot(conn, str(latest_date), equity, account["cash"], {})
        return

    longs, shorts = select_deciles(
        day_scores, decile_frac=DECILE_FRACTION, min_breadth=MIN_CROSS_SECTION_BREADTH
    )

    close_wide = prices.pivot(index="date", columns="ticker", values="close")
    returns_wide = close_wide.pct_change()

    target_shares = pd.Series(dtype=float)
    if longs or shorts:
        raw_weights = size_portfolio(longs, shorts, returns_wide, target_vol=TARGET_VOL)
        target_weights = apply_limits(raw_weights, TICKER_SECTOR)
        target_shares = (target_weights * equity / close_wide.loc[latest_date]).dropna()
        # Alpaca rejects fractional orders that open or hold a short position, so
        # short-side targets must land on a whole share count; longs can stay fractional.
        short_in_target = target_shares.index.intersection(shorts)
        target_shares.loc[short_in_target] = target_shares.loc[short_in_target].round()

    current_shares = pd.Series(current_positions, dtype=float)
    all_tickers = target_shares.index.union(current_shares.index)
    deltas = target_shares.reindex(all_tickers, fill_value=0.0) - current_shares.reindex(
        all_tickers, fill_value=0.0
    )

    for ticker, shares in deltas[deltas.abs() > 1e-6].items():
        result = client.submit_order(ticker, shares)
        storage.log_order(conn, str(latest_date), ticker, shares, submitted_at)
        print(result)

    storage.log_snapshot(conn, str(latest_date), equity, account["cash"], current_positions)


if __name__ == "__main__":
    run_daily()
