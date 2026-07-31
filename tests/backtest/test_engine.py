"""End-to-end backtest engine test on a fabricated price panel.

No network access: data.prices.load_prices / data.news.load_news are
monkeypatched inside backtest.engine so this exercises the full event loop
(factor computation -> composite -> sizing -> limits -> fills -> portfolio)
without ever hitting yfinance/NewsAPI. This doubles as the functional proof
that `python -m backtest.engine` works, for environments without network
access to Yahoo Finance.
"""

from __future__ import annotations

import pandas as pd

from backtest import engine
from data.news import NEWS_COLUMNS


def _install_fake_loaders(monkeypatch, panel: pd.DataFrame) -> None:
    def fake_load_prices(tickers, start, end, source="yfinance", use_cache=True):
        window = panel[(panel["date"] >= pd.Timestamp(start)) & (panel["date"] < pd.Timestamp(end))]
        return window[window["ticker"].isin(tickers)].reset_index(drop=True)

    def fake_load_news(tickers, start, end, source="newsapi", use_cache=True):
        return pd.DataFrame(columns=NEWS_COLUMNS)

    monkeypatch.setattr(engine, "load_prices", fake_load_prices)
    monkeypatch.setattr(engine, "load_news", fake_load_news)


def test_end_to_end_backtest_runs_and_produces_metrics(monkeypatch, price_panel_factory):
    tickers = [f"T{i}" for i in range(12)]
    panel = price_panel_factory(tickers=tickers, n_days=500, start="2020-01-02", seed=11)
    _install_fake_loaders(monkeypatch, panel)

    dates = sorted(panel["date"].unique())
    start, end = dates[320].strftime("%Y-%m-%d"), dates[340].strftime("%Y-%m-%d")

    result = engine.run_backtest(start=start, end=end, rebalance="weekly", universe=tickers)

    equity_curve = result["equity_curve"]
    trading_dates_in_window = [d for d in dates if pd.Timestamp(start) <= d < pd.Timestamp(end)]

    assert len(equity_curve) == len(trading_dates_in_window)
    assert equity_curve.notna().all()
    assert set(result["metrics"]) == {
        "cagr",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "win_rate",
        "avg_holding_period_days",
    }
    assert isinstance(result["kill_switch_triggered"], bool)


def test_thin_universe_below_min_breadth_never_trades(monkeypatch, price_panel_factory):
    tickers = [f"T{i}" for i in range(5)]  # below MIN_CROSS_SECTION_BREADTH
    panel = price_panel_factory(tickers=tickers, n_days=500, start="2020-01-02", seed=12)
    _install_fake_loaders(monkeypatch, panel)

    dates = sorted(panel["date"].unique())
    start, end = dates[320].strftime("%Y-%m-%d"), dates[330].strftime("%Y-%m-%d")

    result = engine.run_backtest(
        start=start, end=end, rebalance="weekly", universe=tickers, starting_cash=1_000_000.0
    )

    assert (result["equity_curve"] == 1_000_000.0).all()
