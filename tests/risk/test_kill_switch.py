import pandas as pd

from risk.kill_switch import KillSwitch, running_drawdown


def test_triggers_at_threshold_drawdown():
    switch = KillSwitch(max_drawdown=0.15)
    assert switch.check(100.0) is False
    assert switch.check(90.0) is False  # 10% drawdown, below threshold
    assert switch.check(84.0) is True  # 16% drawdown, breaches threshold


def test_stays_triggered_even_if_equity_recovers():
    switch = KillSwitch(max_drawdown=0.15)
    switch.check(100.0)
    switch.check(80.0)  # triggers
    assert switch.check(100.0) is True  # does not silently re-arm


def test_reset_clears_triggered_state():
    switch = KillSwitch(max_drawdown=0.15)
    switch.check(100.0)
    switch.check(80.0)
    switch.reset()
    assert switch.triggered is False
    assert switch.check(100.0) is False


def test_peak_tracks_new_highs():
    switch = KillSwitch(max_drawdown=0.15)
    switch.check(100.0)
    switch.check(120.0)
    assert switch.check(105.0) is False  # 12.5% off the new peak of 120, below threshold


def test_running_drawdown_matches_peak_formula():
    equity = pd.Series([100.0, 110.0, 90.0, 95.0])
    drawdown = running_drawdown(equity)
    assert list(drawdown) == [0.0, 0.0, 1 - 90.0 / 110.0, 1 - 95.0 / 110.0]
