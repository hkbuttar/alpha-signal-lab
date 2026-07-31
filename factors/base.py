"""Shared interface that every factor implements.

A factor is any callable that takes a point-in-time price panel (and optionally a
news panel) and returns a cross-sectional score per ticker per day. Composite
combination and backtest wiring only depend on this shape, so new factors can be
dropped in without touching any other module.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

SCORE_COLUMNS = ["date", "ticker", "score"]


class Factor(Protocol):
    """Protocol every factor module's ``compute`` function satisfies."""

    name: str

    def compute(self, prices: pd.DataFrame, news: pd.DataFrame | None = None) -> pd.DataFrame:
        """Compute a cross-sectional score per ticker per day.

        Args:
            prices: Long-format OHLCV panel, columns
                [date, ticker, open, high, low, close, volume].
            news: Optional long-format headline panel, columns
                [date, ticker, headline, source]. Only used by factors that need it.

        Returns:
            Long-format DataFrame with columns [date, ticker, score]. ``score``
            may be NaN for a ticker/day where the factor has no opinion (e.g. not
            enough lookback history, or no news coverage); NaN is preserved
            rather than filled, since silently zero-filling would misrepresent a
            missing signal as a neutral one.
        """
        ...
