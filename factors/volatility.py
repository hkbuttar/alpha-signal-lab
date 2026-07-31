"""Low-volatility factor.

Rationale: lower-volatility names have historically delivered better
risk-adjusted returns than CAPM would predict (the "low-volatility anomaly").
Used here both as a standalone signal and, separately, as an input to
risk-layer position sizing (risk/sizing.py) — the two uses are independent so
a low-vol name can be favored by this factor while still being sized down if
it's a large portfolio-level risk contributor.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from factors._util import melt_scores, pivot_field

name = "volatility"

WINDOW_DAYS = 60
MIN_PERIODS = 20
TRADING_DAYS_PER_YEAR = 252


def compute(prices: pd.DataFrame, news: pd.DataFrame | None = None) -> pd.DataFrame:
    """Inverse cross-sectional rank of trailing 60-day annualized realized vol.

    Args:
        prices: Long-format OHLCV panel.
        news: Unused, present for interface compatibility.

    Returns:
        Long-format [date, ticker, score] where higher score means lower
        realized volatility. NaN until WINDOW_DAYS of history exist.
    """
    close = pivot_field(prices, "close")
    daily_return = close.pct_change()
    realized_vol = daily_return.rolling(WINDOW_DAYS, min_periods=MIN_PERIODS).std() * np.sqrt(
        TRADING_DAYS_PER_YEAR
    )
    # ascending=False gives rank 1 to the highest-vol name, so the lowest-vol
    # name ends up with the largest rank number, i.e. the highest score.
    score = realized_vol.rank(axis=1, ascending=False, na_option="keep")
    return melt_scores(score)
