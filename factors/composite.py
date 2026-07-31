"""Combine individual factor scores into a single composite score and rank.

Method:
1. Each factor's raw score is cross-sectionally z-scored per day (so factors on
   different scales, e.g. a return ratio vs a rank, are comparable).
2. Factors are blended with trailing-IC-derived weights: on each refit date,
   each factor's weight is its mean 5-day-forward Information Coefficient over
   the preceding ``ic_lookback`` trading days (clipped at zero, since a factor
   with no observed positive predictive power in-window shouldn't get active
   negative weight). Weights are held constant between refit dates. This is
   the "walk-forward" part of the signal combination: the weight used on any
   given day was derived entirely from data available before that day.
3. Per ticker/day, only factors with a non-NaN z-score are blended, with
   weights renormalized across the available subset (e.g. when sentiment has
   no news coverage for a name, momentum/mean-reversion/volatility absorb its
   weight for that row rather than the composite silently going to zero).

If every factor has non-positive trailing IC at a refit date (e.g. very early
in a backtest, or in a genuinely low-signal regime), weights fall back to
equal weighting for that period rather than being undefined.
"""

from __future__ import annotations

import pandas as pd

from factors._util import cross_sectional_zscore, melt_scores
from factors.validation import information_coefficient

IC_LOOKBACK_DAYS = 126
IC_HORIZON_DAYS = 5
REFIT_FREQ = "MS"  # first trading day on/after the start of each calendar month


def _pivot_scores(scores: pd.DataFrame) -> pd.DataFrame:
    return scores.pivot(index="date", columns="ticker", values="score").sort_index()


def _refit_dates(trading_dates: pd.DatetimeIndex, refit_freq: str) -> pd.DatetimeIndex:
    calendar = pd.Series(trading_dates, index=trading_dates)
    first_per_period = calendar.groupby(pd.Grouper(freq=refit_freq)).first().dropna()
    return pd.DatetimeIndex(first_per_period.values)


def _trailing_weights(
    factor_scores: dict[str, pd.DataFrame],
    prices: pd.DataFrame,
    refit_date: pd.Timestamp,
    ic_lookback: int,
) -> dict[str, float]:
    window_start = refit_date - pd.Timedelta(
        days=int(ic_lookback * 1.6)
    )  # calendar buffer for weekends/holidays
    ics = {}
    for factor_name, scores in factor_scores.items():
        windowed = scores[(scores["date"] >= window_start) & (scores["date"] < refit_date)]
        if windowed.empty:
            ics[factor_name] = 0.0
            continue
        ic_series = information_coefficient(windowed, prices, horizon=IC_HORIZON_DAYS)
        ics[factor_name] = (
            0.0 if ic_series.empty else max(0.0, float(ic_series.tail(ic_lookback).mean()))
        )

    total = sum(ics.values())
    if total <= 0:
        n = len(factor_scores)
        return dict.fromkeys(factor_scores, 1.0 / n)
    return {name: ic / total for name, ic in ics.items()}


def combine_factors(
    factor_scores: dict[str, pd.DataFrame],
    prices: pd.DataFrame,
    ic_lookback: int = IC_LOOKBACK_DAYS,
    refit_freq: str = REFIT_FREQ,
) -> pd.DataFrame:
    """Blend factor scores into a composite score and daily cross-sectional rank.

    Args:
        factor_scores: Mapping of factor name to its long-format [date, ticker,
            score] output.
        prices: Long-format OHLCV panel, used to derive the trading calendar
            and forward returns for IC weighting.
        ic_lookback: Trailing trading-day window used to estimate each
            factor's IC ahead of a refit.
        refit_freq: Pandas offset alias for how often weights are recomputed.

    Returns:
        Long-format DataFrame [date, ticker, composite_score, rank], where
        rank 1 is the highest composite_score that day (best long candidate)
        and the highest rank number is the best short candidate.
    """
    trading_dates = pd.DatetimeIndex(sorted(prices["date"].unique()), name="date")
    refit_dates = _refit_dates(trading_dates, refit_freq)

    zscored = {
        name: cross_sectional_zscore(_pivot_scores(df)) for name, df in factor_scores.items()
    }

    weights_by_refit = {
        refit_date: _trailing_weights(factor_scores, prices, refit_date, ic_lookback)
        for refit_date in refit_dates
    }

    composite = pd.DataFrame(
        index=trading_dates, columns=sorted({t for z in zscored.values() for t in z.columns})
    )
    active_weights = dict.fromkeys(factor_scores, 1.0 / len(factor_scores))

    for date in trading_dates:
        if date in weights_by_refit:
            active_weights = weights_by_refit[date]

        row_scores = pd.DataFrame(
            {
                name: z.loc[date] if date in z.index else pd.Series(dtype=float)
                for name, z in zscored.items()
            }
        )
        available_weight = row_scores.notna().mul(pd.Series(active_weights), axis=1)
        weight_sum = available_weight.sum(axis=1)
        normalized = available_weight.div(weight_sum.replace(0, pd.NA), axis=0)
        composite.loc[date] = (row_scores.fillna(0) * normalized).sum(axis=1, min_count=1)

    composite = composite.astype(float)
    long_composite = melt_scores(composite).rename(columns={"score": "composite_score"})
    long_composite["rank"] = long_composite.groupby("date")["composite_score"].rank(
        ascending=False, method="first"
    )
    return long_composite


def select_deciles(
    day_scores: pd.Series, decile_frac: float = 0.1, min_breadth: int = 10
) -> tuple[list[str], list[str]]:
    """Select the top/bottom decile tickers from a single day's composite scores.

    Shared by backtest/engine.py and live/scheduler.py so both pick long/short
    candidates the same way.

    Args:
        day_scores: Composite scores for one day, indexed by ticker, with NaN
            rows already dropped.
        decile_frac: Fraction of the cross-section to take on each side.
        min_breadth: Minimum number of scored names required to trust the
            ranking; below this, returns empty selections rather than trading
            on a too-thin cross-section.

    Returns:
        (long_tickers, short_tickers)
    """
    if len(day_scores) < min_breadth:
        return [], []
    n = max(1, int(len(day_scores) * decile_frac))
    return day_scores.nlargest(n).index.tolist(), day_scores.nsmallest(n).index.tolist()
