"""Hard portfolio-level exposure limits.

Applied unconditionally after risk/sizing.py's vol-targeted weights, as a
backstop against the sizing heuristic under- or over-estimating risk. Order of
enforcement matters: per-name first (bounds any single position), then
per-sector (bounds sector concentration), then gross (bounds total leverage) -
each step operates on the output of the previous one.
"""

from __future__ import annotations

import pandas as pd

MAX_GROSS_EXPOSURE = 1.5
MAX_NAME_EXPOSURE = 0.05
MAX_SECTOR_EXPOSURE = 0.25


def apply_limits(
    weights: pd.Series,
    sector_map: dict[str, str],
    max_gross: float = MAX_GROSS_EXPOSURE,
    max_name: float = MAX_NAME_EXPOSURE,
    max_sector: float = MAX_SECTOR_EXPOSURE,
) -> pd.Series:
    """Clip target weights to per-name, per-sector, and gross exposure limits.

    Args:
        weights: Target weights indexed by ticker, positive for longs,
            negative for shorts.
        sector_map: Ticker to sector name mapping (config.universe.TICKER_SECTOR).
        max_gross: Max total gross exposure (sum of |weight|).
        max_name: Max absolute weight for any single name.
        max_sector: Max absolute net exposure for any single sector.

    Returns:
        Adjusted weights, same index as input.
    """
    if weights.empty:
        return weights

    clipped = weights.clip(lower=-max_name, upper=max_name)

    sectors = pd.Series({ticker: sector_map.get(ticker, "Unknown") for ticker in clipped.index})
    sector_exposure = clipped.groupby(sectors).sum()
    for sector, exposure in sector_exposure.items():
        if abs(exposure) > max_sector:
            scale = max_sector / abs(exposure)
            in_sector = sectors[sectors == sector].index
            clipped.loc[in_sector] *= scale

    gross = clipped.abs().sum()
    if gross > max_gross:
        clipped *= max_gross / gross

    return clipped
