"""Short-horizon mean-reversion factor.

Rationale: over short horizons, extreme price moves partially reverse,
particularly in the absence of new fundamental information. Scored so that a
large recent negative move gets a high score (expected to bounce back).
"""

from __future__ import annotations

import pandas as pd

from factors._util import melt_scores, pivot_field

name = "mean_reversion"

RETURN_WINDOW_DAYS = 5
ROLLING_WINDOW_DAYS = 60
MIN_PERIODS = 20


def compute(prices: pd.DataFrame, news: pd.DataFrame | None = None) -> pd.DataFrame:
    """Z-score of the trailing 5-day return vs its trailing 60-day mean/std, negated.

    Args:
        prices: Long-format OHLCV panel.
        news: Unused, present for interface compatibility.

    Returns:
        Long-format [date, ticker, score]. NaN until ROLLING_WINDOW_DAYS of
        history exist for a ticker.
    """
    close = pivot_field(prices, "close")
    short_return = close.pct_change(RETURN_WINDOW_DAYS)
    rolling_mean = short_return.rolling(ROLLING_WINDOW_DAYS, min_periods=MIN_PERIODS).mean()
    rolling_std = short_return.rolling(ROLLING_WINDOW_DAYS, min_periods=MIN_PERIODS).std()
    zscore = (short_return - rolling_mean) / rolling_std.replace(0, pd.NA)
    score = -zscore
    return melt_scores(score)
