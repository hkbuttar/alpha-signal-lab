"""Volatility-targeted position sizing.

Within each side (long/short) of the selected names, weight is inversely
proportional to trailing realized volatility, so a single volatile name
doesn't dominate that side's risk. The combined book is then scaled so its
estimated volatility matches ``target_vol``.

The portfolio-vol estimate used for that scaling assumes zero cross-name
correlation (a simplification, not a real covariance estimate) purely to get
a leverage scalar; it is a sizing heuristic, not a risk limit. Hard caps on
gross/name/sector exposure are enforced separately and unconditionally by
risk/limits.py regardless of what this module outputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VOL_WINDOW_DAYS = 60
MIN_VOL_PERIODS = 20
TRADING_DAYS_PER_YEAR = 252


def trailing_realized_vol(returns: pd.DataFrame, tickers: list[str]) -> pd.Series:
    """Trailing annualized realized vol as of the last row of ``returns``.

    Args:
        returns: Wide date x ticker daily return matrix, containing only dates
            up to and including the sizing date (point-in-time).
        tickers: Tickers to compute vol for.

    Returns:
        Series indexed by ticker.
    """
    window = returns[tickers].tail(VOL_WINDOW_DAYS)
    vol = window.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    vol[window.count() < MIN_VOL_PERIODS] = np.nan
    return vol


def _inverse_vol_weights(tickers: list[str], returns: pd.DataFrame) -> pd.Series:
    if not tickers:
        return pd.Series(dtype=float)
    vol = trailing_realized_vol(returns, tickers).replace(0, np.nan)
    inv_vol = (1 / vol).fillna(0)
    total = inv_vol.sum()
    if total == 0:
        return pd.Series(1.0 / len(tickers), index=tickers)
    return inv_vol / total


def size_portfolio(
    long_tickers: list[str],
    short_tickers: list[str],
    returns: pd.DataFrame,
    target_vol: float = 0.10,
    base_gross: float = 1.0,
) -> pd.Series:
    """Produce target portfolio weights for a long/short selection.

    Args:
        long_tickers: Tickers to hold long.
        short_tickers: Tickers to hold short.
        returns: Wide date x ticker daily return matrix, point-in-time (only
            rows up to and including the sizing date).
        target_vol: Annualized portfolio volatility target used to scale
            overall leverage.
        base_gross: Gross exposure (long + |short|) before vol-target scaling,
            split evenly between the two sides.

    Returns:
        Series of target weights indexed by ticker, positive for longs,
        negative for shorts. Not yet clipped to risk/limits.py caps.
    """
    long_weights = _inverse_vol_weights(long_tickers, returns) * (base_gross / 2)
    short_weights = _inverse_vol_weights(short_tickers, returns) * -(base_gross / 2)
    weights = pd.concat([long_weights, short_weights])

    if weights.empty:
        return weights

    vol = trailing_realized_vol(returns, list(weights.index)).fillna(0)
    portfolio_vol_estimate = float(np.sqrt(((weights * vol) ** 2).sum()))
    scale = target_vol / portfolio_vol_estimate if portfolio_vol_estimate > 0 else 1.0
    return weights * scale
