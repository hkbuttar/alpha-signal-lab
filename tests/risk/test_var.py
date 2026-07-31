import numpy as np
import pandas as pd
import pytest

from risk.var import historical_var, parametric_var


def test_historical_var_matches_percentile_definition():
    returns = pd.Series(np.linspace(-0.05, 0.05, 101))  # uniform, easy percentile math
    var95 = historical_var(returns, confidence=0.95)
    assert var95 == pytest.approx(-np.percentile(returns, 5))


def test_parametric_var_is_positive_for_typical_returns():
    rng = np.random.default_rng(0)
    returns = pd.Series(rng.normal(0.0005, 0.01, 500))
    assert parametric_var(returns) > 0


def test_higher_confidence_gives_larger_var():
    rng = np.random.default_rng(1)
    returns = pd.Series(rng.normal(0.0, 0.01, 500))
    var95 = historical_var(returns, confidence=0.95)
    var99 = historical_var(returns, confidence=0.99)
    assert var99 > var95


def test_empty_returns_yield_nan():
    empty = pd.Series(dtype=float)
    assert historical_var(empty) != historical_var(empty)  # nan != nan
    assert parametric_var(empty) != parametric_var(empty)
