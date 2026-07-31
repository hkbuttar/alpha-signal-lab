"""12-1 month momentum factor.

Rationale: assets that have outperformed over the recent past tend to continue
outperforming over intermediate horizons. The most recent month is skipped
because short-term returns tend to partially reverse (see mean_reversion.py),
so including it would have the momentum and mean-reversion factors fighting
over the same window.
"""

from __future__ import annotations

import pandas as pd

from factors._util import melt_scores, pivot_field

name = "momentum"

LOOKBACK_DAYS = 252
SKIP_DAYS = 21


def compute(prices: pd.DataFrame, news: pd.DataFrame | None = None) -> pd.DataFrame:
    """12-1 month momentum: return from t-252 to t-21, per ticker per day.

    Args:
        prices: Long-format OHLCV panel.
        news: Unused, present for interface compatibility.

    Returns:
        Long-format [date, ticker, score]. NaN until LOOKBACK_DAYS of history
        exist for a ticker.
    """
    close = pivot_field(prices, "close")
    lagged = close.shift(SKIP_DAYS)
    base = close.shift(LOOKBACK_DAYS)
    score = (lagged / base) - 1
    return melt_scores(score)
