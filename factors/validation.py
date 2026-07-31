"""Factor validation utilities: IC, IC decay, and turnover.

Each factor is evaluated independently before being trusted in the composite,
using these three diagnostics. Reused by both factors/composite.py (to derive
IC-based combination weights) and notebooks/research.ipynb (to report them).
"""

from __future__ import annotations

import pandas as pd

from factors._util import pivot_field

MIN_CROSS_SECTION = 5


def _pivot_scores(scores: pd.DataFrame) -> pd.DataFrame:
    return scores.pivot(index="date", columns="ticker", values="score").sort_index()


def information_coefficient(
    scores: pd.DataFrame, prices: pd.DataFrame, horizon: int = 5
) -> pd.Series:
    """Daily cross-sectional rank correlation between factor score and forward return.

    Args:
        scores: Long-format [date, ticker, score].
        prices: Long-format OHLCV panel used to compute forward returns.
        horizon: Forward return horizon in trading days.

    Returns:
        Series of IC values indexed by date. A date is only included if at
        least MIN_CROSS_SECTION tickers have both a score and a forward return
        (skipped rather than treated as IC=0, to avoid diluting the average
        with uninformative days).
    """
    score_wide = _pivot_scores(scores)
    close = pivot_field(prices, "close")
    forward_return = close.shift(-horizon) / close - 1

    common_dates = score_wide.index.intersection(forward_return.index)
    ic_by_date = {}
    for date in common_dates:
        s = score_wide.loc[date]
        r = forward_return.loc[date]
        valid = s.notna() & r.notna()
        if valid.sum() >= MIN_CROSS_SECTION:
            ic_by_date[date] = (
                s[valid].astype(float).corr(r[valid].astype(float), method="spearman")
            )

    return pd.Series(ic_by_date, dtype=float).sort_index()


def ic_decay(
    scores: pd.DataFrame, prices: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 10, 21, 63)
) -> pd.Series:
    """Mean IC at each forward horizon, showing how quickly predictive power fades."""
    return pd.Series(
        {h: information_coefficient(scores, prices, horizon=h).mean() for h in horizons}
    )


def turnover(scores: pd.DataFrame, top_frac: float = 0.1) -> pd.Series:
    """Day-over-day churn in the top-``top_frac`` ranked names.

    High turnover implies higher transaction costs to actually capture the
    signal, since the strategy would need to trade in and out of names
    frequently just to stay aligned with the ranking.

    Returns:
        Series indexed by date, values in [0, 1] (fraction of the top set that
        changed from the prior day).
    """
    score_wide = _pivot_scores(scores)

    def top_set(row: pd.Series) -> set[str]:
        valid = row.dropna()
        n = max(1, int(len(valid) * top_frac))
        return set(valid.nlargest(n).index)

    membership = score_wide.apply(top_set, axis=1)

    turnover_by_date = {}
    prev: set[str] | None = None
    for date, members in membership.items():
        if prev:
            turnover_by_date[date] = len(members.symmetric_difference(prev)) / (2 * len(prev))
        prev = members

    return pd.Series(turnover_by_date, dtype=float).sort_index()
