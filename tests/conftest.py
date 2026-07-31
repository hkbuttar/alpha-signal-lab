"""Shared synthetic-data fixtures. No test in this suite hits the network -
price/news panels are generated in-memory and any external client (yfinance,
Alpaca, OpenAI) is monkeypatched where relevant.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _make_price_panel(tickers: list[str], n_days: int, start: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=n_days)

    rows = []
    for i, ticker in enumerate(tickers):
        price = 100.0 + i * 10
        # give each ticker a distinct vol regime so volatility.py has something to rank
        vol = 0.005 + 0.01 * (i / max(1, len(tickers) - 1))
        for date in dates:
            price *= 1 + rng.normal(0, vol)
            open_price = price * (1 + rng.normal(0, 0.001))
            volume = 1_000_000 + i * 50_000
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": open_price,
                    "high": max(open_price, price) * 1.001,
                    "low": min(open_price, price) * 0.999,
                    "close": price,
                    "volume": volume,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def price_panel_factory():
    def _factory(tickers=None, n_days=320, start="2022-01-03", seed=0):
        tickers = tickers or ["AAA", "BBB", "CCC", "DDD", "EEE"]
        return _make_price_panel(tickers, n_days, start, seed)

    return _factory


@pytest.fixture
def price_panel(price_panel_factory):
    return price_panel_factory()
