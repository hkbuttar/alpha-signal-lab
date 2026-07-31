"""Event-driven backtest engine.

Steps through trading days chronologically rather than vectorizing over the
whole date range at once, so the strategy only ever acts on information that
would have been available at that point in time:

    for each trading day:
        1. fill any orders decided on the previous day, at today's open
        2. mark the portfolio to market at today's close
        3. check the drawdown kill-switch
        4. on rebalance days (and only if the kill-switch hasn't fired),
           recompute the composite ranking, select the long/short deciles,
           size and risk-limit the target book, and queue orders for
           tomorrow's open

Run as: python -m backtest.engine --start 2020-01-01 --end 2025-01-01
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from backtest import fills
from backtest import metrics as backtest_metrics
from backtest.portfolio import Portfolio
from config.universe import TICKER_SECTOR, UNIVERSE
from data.news import load_news
from data.prices import load_prices
from factors import mean_reversion, momentum, sentiment, volatility
from factors.composite import combine_factors, select_deciles
from risk.kill_switch import KillSwitch
from risk.limits import apply_limits
from risk.sizing import size_portfolio

RESULTS_DIR = Path(__file__).resolve().parent / "results"

HISTORY_BUFFER_DAYS = 450  # calendar days of lookback before `start`, for factor warmup
DECILE_FRACTION = 0.1
MIN_CROSS_SECTION_BREADTH = 10  # minimum non-NaN names before deciles are trusted
ORDER_EPSILON = 1e-6


def _rebalance_dates(trading_dates: pd.DatetimeIndex, freq: str) -> set[pd.Timestamp]:
    trading_dates = pd.DatetimeIndex(trading_dates)
    if freq == "daily":
        return set(trading_dates)
    if freq == "weekly":
        series = pd.Series(trading_dates, index=trading_dates)
        firsts = series.groupby(trading_dates.to_period("W")).first()
        return set(firsts.values)
    raise ValueError(f"Unknown rebalance frequency: {freq}")


def run_backtest(
    start: str,
    end: str,
    rebalance: str = "weekly",
    starting_cash: float = 1_000_000.0,
    universe: list[str] | None = None,
    price_source: str = "yfinance",
    news_source: str = "newsapi",
    target_vol: float = 0.10,
    kill_switch_drawdown: float = 0.15,
) -> dict:
    """Run the full event-driven backtest over [start, end).

    Returns:
        Dict with "equity_curve" (pd.Series), "metrics" (dict), and
        "kill_switch_triggered" (bool).
    """
    tickers = universe or UNIVERSE
    load_start = (pd.Timestamp(start) - pd.Timedelta(days=HISTORY_BUFFER_DAYS)).strftime("%Y-%m-%d")

    prices = load_prices(tickers, load_start, end, source=price_source)
    news = load_news(tickers, load_start, end, source=news_source)

    factor_scores = {
        momentum.name: momentum.compute(prices),
        mean_reversion.name: mean_reversion.compute(prices),
        volatility.name: volatility.compute(prices),
        sentiment.name: sentiment.compute(prices, news),
    }
    composite = combine_factors(factor_scores, prices)
    composite_wide = composite.pivot(index="date", columns="ticker", values="composite_score")

    close_wide = prices.pivot(index="date", columns="ticker", values="close")
    open_wide = prices.pivot(index="date", columns="ticker", values="open")
    adv_wide = (
        prices.pivot(index="date", columns="ticker", values="volume")
        .rolling(fills.ADV_WINDOW_DAYS, min_periods=5)
        .mean()
    )
    returns_wide = close_wide.pct_change()

    trading_dates = close_wide.index[
        (close_wide.index >= pd.Timestamp(start)) & (close_wide.index < pd.Timestamp(end))
    ]
    rebalance_dates = _rebalance_dates(trading_dates, rebalance)

    portfolio = Portfolio(starting_cash)
    kill_switch = KillSwitch(kill_switch_drawdown)
    halted = False
    pending_orders: dict[str, float] = {}

    for date in trading_dates:
        if pending_orders:
            today_open = open_wide.loc[date]
            today_adv = adv_wide.loc[date]
            for ticker, shares_delta in pending_orders.items():
                next_open = today_open.get(ticker)
                if pd.isna(next_open):
                    continue
                adv = today_adv.get(ticker, 0.0)
                fill_price, fee = fills.compute_fill(
                    shares_delta, next_open, adv if pd.notna(adv) else 0.0
                )
                portfolio.apply_fill(ticker, shares_delta, fill_price, fee)
            pending_orders = {}

        equity = portfolio.mark_to_market(date, close_wide.loc[date].to_dict())

        if not halted and kill_switch.check(equity):
            halted = True
            pending_orders = portfolio.flatten_orders()
            continue
        if halted:
            continue

        if date in rebalance_dates and date in composite_wide.index:
            day_scores = composite_wide.loc[date].dropna()
            longs, shorts = select_deciles(
                day_scores, decile_frac=DECILE_FRACTION, min_breadth=MIN_CROSS_SECTION_BREADTH
            )
            if longs or shorts:
                trailing_returns = returns_wide.loc[:date]
                raw_weights = size_portfolio(longs, shorts, trailing_returns, target_vol=target_vol)
                target_weights = apply_limits(raw_weights, TICKER_SECTOR)

                target_shares = (target_weights * equity / close_wide.loc[date]).dropna()
                current_shares = pd.Series(portfolio.positions, dtype=float)
                all_tickers = target_shares.index.union(current_shares.index)
                deltas = target_shares.reindex(
                    all_tickers, fill_value=0.0
                ) - current_shares.reindex(all_tickers, fill_value=0.0)
                pending_orders = deltas[deltas.abs() > ORDER_EPSILON].to_dict()

    equity_series = portfolio.equity_series()
    metrics = backtest_metrics.compute_metrics(equity_series, portfolio.position_history())

    return {
        "equity_curve": equity_series,
        "metrics": metrics,
        "kill_switch_triggered": kill_switch.triggered,
    }


def _save_run(result: dict, start: str, end: str, rebalance: str) -> Path:
    run_dir = RESULTS_DIR / "runs" / f"{start}_{end}_{rebalance}"
    run_dir.mkdir(parents=True, exist_ok=True)
    result["equity_curve"].rename("equity").to_csv(run_dir / "equity_curve.csv")
    with open(run_dir / "metrics.json", "w") as f:
        json.dump(
            {**result["metrics"], "kill_switch_triggered": result["kill_switch_triggered"]},
            f,
            indent=2,
        )
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the event-driven factor backtest.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2020-01-01")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-01-01")
    parser.add_argument("--rebalance", choices=["daily", "weekly"], default="weekly")
    parser.add_argument("--starting-cash", type=float, default=1_000_000.0)
    parser.add_argument("--price-source", choices=["yfinance", "alpaca"], default="yfinance")
    parser.add_argument("--news-source", choices=["newsapi", "alpaca"], default="newsapi")
    args = parser.parse_args()

    result = run_backtest(
        start=args.start,
        end=args.end,
        rebalance=args.rebalance,
        starting_cash=args.starting_cash,
        price_source=args.price_source,
        news_source=args.news_source,
    )

    run_dir = _save_run(result, args.start, args.end, args.rebalance)

    print(f"Backtest {args.start} -> {args.end} ({args.rebalance} rebalance)")
    print(f"Kill switch triggered: {result['kill_switch_triggered']}")
    for key, value in result["metrics"].items():
        print(f"  {key}: {value:.4f}" if value == value else f"  {key}: nan")
    print(f"Saved results to {run_dir}")


if __name__ == "__main__":
    main()
