"""Portfolio Value at Risk, computed both historically and parametrically.

Both are reported daily alongside the dashboard's rolling risk view. Historical
VaR makes no distributional assumption but needs enough return history to be
stable; parametric VaR is stable with less data but assumes normally
distributed returns, which understates tail risk. Reporting both is
deliberate, so a large gap between them is itself a signal that the return
distribution is unusually skewed or fat-tailed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

DEFAULT_CONFIDENCE = 0.95


def historical_var(returns: pd.Series, confidence: float = DEFAULT_CONFIDENCE) -> float:
    """Empirical VaR: the loss at the given confidence's percentile of realized returns.

    Args:
        returns: Daily portfolio returns.
        confidence: Confidence level, e.g. 0.95 for 95% VaR.

    Returns:
        Positive float representing the loss magnitude (e.g. 0.03 == a 3% loss).
    """
    if returns.empty:
        return float("nan")
    percentile = (1 - confidence) * 100
    return float(-np.percentile(returns.dropna(), percentile))


def parametric_var(returns: pd.Series, confidence: float = DEFAULT_CONFIDENCE) -> float:
    """Variance-covariance VaR assuming normally distributed daily returns.

    Args:
        returns: Daily portfolio returns.
        confidence: Confidence level, e.g. 0.95 for 95% VaR.

    Returns:
        Positive float representing the loss magnitude.
    """
    clean = returns.dropna()
    if clean.empty:
        return float("nan")
    mean, std = clean.mean(), clean.std()
    z = norm.ppf(1 - confidence)
    return float(-(mean + z * std))
