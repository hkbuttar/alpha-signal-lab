import numpy as np
import pandas as pd
import pytest

from risk.sizing import size_portfolio


def _returns(seed: int = 0, n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n)
    return pd.DataFrame(
        {"LOW": rng.normal(0, 0.005, n), "HIGH": rng.normal(0, 0.02, n)}, index=dates
    )


def test_lower_vol_name_gets_larger_weight_within_a_side():
    weights = size_portfolio(["LOW", "HIGH"], [], _returns(), target_vol=0.10)
    assert weights["LOW"] > weights["HIGH"] > 0


def test_short_side_weights_are_negative():
    weights = size_portfolio([], ["LOW", "HIGH"], _returns(), target_vol=0.10)
    assert (weights < 0).all()


def test_higher_target_vol_increases_gross_exposure():
    low_target = size_portfolio(["LOW", "HIGH"], [], _returns(), target_vol=0.05)
    high_target = size_portfolio(["LOW", "HIGH"], [], _returns(), target_vol=0.20)
    assert high_target.abs().sum() > low_target.abs().sum()


def test_empty_selection_returns_empty_series():
    weights = size_portfolio([], [], _returns(), target_vol=0.10)
    assert weights.empty


def test_zero_vol_names_fall_back_to_equal_weight():
    dates = pd.bdate_range("2022-01-03", periods=30)
    flat_returns = pd.DataFrame({"A": [0.0] * 30, "B": [0.0] * 30}, index=dates)
    weights = size_portfolio(["A", "B"], [], flat_returns, target_vol=0.10)
    assert weights["A"] == pytest.approx(weights["B"])
