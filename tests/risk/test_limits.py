import pandas as pd
import pytest

from risk.limits import apply_limits

SECTOR_MAP = {"A": "Tech", "B": "Tech", "C": "Tech", "D": "Energy"}


def test_name_exposure_is_clipped():
    weights = pd.Series({"A": 0.20, "D": -0.01})
    clipped = apply_limits(weights, SECTOR_MAP, max_gross=10, max_name=0.05, max_sector=10)
    assert clipped["A"] == pytest.approx(0.05)


def test_sector_exposure_is_scaled_down_proportionally():
    weights = pd.Series({"A": 0.10, "B": 0.10, "C": 0.10, "D": 0.01})
    clipped = apply_limits(weights, SECTOR_MAP, max_gross=10, max_name=10, max_sector=0.15)
    tech_exposure = clipped[["A", "B", "C"]].sum()
    assert tech_exposure == pytest.approx(0.15)
    # relative weighting within the sector is preserved
    assert clipped["A"] == pytest.approx(clipped["B"])


def test_gross_exposure_is_scaled_down_to_cap():
    weights = pd.Series({"A": 0.5, "D": -0.5})
    clipped = apply_limits(weights, SECTOR_MAP, max_gross=0.5, max_name=10, max_sector=10)
    assert clipped.abs().sum() == pytest.approx(0.5)


def test_within_limits_weights_are_unchanged():
    weights = pd.Series({"A": 0.02, "D": -0.01})
    clipped = apply_limits(weights, SECTOR_MAP)
    pd.testing.assert_series_equal(clipped, weights)


def test_empty_weights_returns_empty():
    assert apply_limits(pd.Series(dtype=float), SECTOR_MAP).empty
