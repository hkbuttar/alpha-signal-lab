"""Small shared helpers for pivoting between long and wide panel shapes.

Not part of the public Factor interface; just avoids repeating the same
long-to-wide reshape in every factor module.
"""

from __future__ import annotations

import pandas as pd


def pivot_field(prices: pd.DataFrame, field: str = "close") -> pd.DataFrame:
    """Reshape a long-format price panel into a wide date x ticker matrix."""
    return prices.pivot(index="date", columns="ticker", values=field).sort_index()


def melt_scores(wide: pd.DataFrame) -> pd.DataFrame:
    """Reshape a wide date x ticker score matrix back to long [date, ticker, score]."""
    long = wide.reset_index().melt(id_vars="date", var_name="ticker", value_name="score")
    return long.sort_values(["date", "ticker"]).reset_index(drop=True)


def cross_sectional_zscore(wide: pd.DataFrame) -> pd.DataFrame:
    """Z-score each row (day) across tickers, ignoring NaNs."""
    mean = wide.mean(axis=1, skipna=True)
    std = wide.std(axis=1, skipna=True)
    return wide.sub(mean, axis=0).div(std.replace(0, pd.NA), axis=0)
