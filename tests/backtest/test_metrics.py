import pandas as pd
import pytest

from backtest import metrics


def test_cagr_of_doubling_over_one_year():
    # cagr() treats len(equity)/252 as elapsed years, so use a full year of
    # daily doubling growth for a meaningful check.
    dates = pd.bdate_range("2022-01-03", periods=252)
    growth = pd.Series([100.0 * (2 ** (i / 251)) for i in range(252)], index=dates)
    assert metrics.cagr(growth) == pytest.approx(1.0, rel=0.01)


def test_max_drawdown_matches_known_trough():
    equity = pd.Series([100.0, 120.0, 90.0, 110.0])
    assert metrics.max_drawdown(equity) == pytest.approx(1 - 90.0 / 120.0)


def test_win_rate_counts_positive_days():
    returns = pd.Series([0.01, -0.01, 0.02, 0.0, -0.005])
    assert metrics.win_rate(returns) == pytest.approx(2 / 5)


def test_sharpe_is_nan_for_zero_vol_returns():
    returns = pd.Series([0.001] * 20)
    assert metrics.sharpe_ratio(returns) != metrics.sharpe_ratio(returns)  # nan


def test_avg_holding_period_averages_contiguous_runs():
    dates = pd.bdate_range("2022-01-03", periods=6)
    history = pd.DataFrame(
        {
            "date": list(dates[:3]) + list(dates[4:6]),
            "ticker": ["AAA"] * 3 + ["AAA"] * 2,
            "shares": [10, 10, 10, 10, 10],
        }
    )
    # AAA held for 3 consecutive days, then a fully-flat portfolio day (date
    # index 3, absent from history entirely), then held for 2 more days.
    # Without passing the full calendar, day 3 never appears in the reshaped
    # date axis and the two runs would wrongly merge into one run of 5.
    assert metrics.avg_holding_period(history, all_dates=dates) == pytest.approx((3 + 2) / 2)


def test_avg_holding_period_without_calendar_merges_across_fully_flat_days():
    dates = pd.bdate_range("2022-01-03", periods=6)
    history = pd.DataFrame(
        {
            "date": list(dates[:3]) + list(dates[4:6]),
            "ticker": ["AAA"] * 3 + ["AAA"] * 2,
            "shares": [10, 10, 10, 10, 10],
        }
    )
    # Documented limitation: without all_dates, a fully-flat day that no
    # ticker logged a row for is invisible to the reshape, so the runs merge.
    assert metrics.avg_holding_period(history) == pytest.approx(5.0)
