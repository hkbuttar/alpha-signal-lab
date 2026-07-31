"""Drawdown kill-switch.

If realized drawdown from the running equity peak exceeds ``max_drawdown``,
the strategy should flatten all positions and halt new order generation until
manually reviewed. This is treated as the single most important safety
control in the system: a good signal with no downside control is not a
fundable strategy.

This module is intentionally minimal. It has no knowledge of order execution
or portfolio construction; it only tracks equity and reports a boolean. Both
backtest/engine.py and live/scheduler.py own the responsibility of actually
flattening positions when ``check`` returns True.
"""

from __future__ import annotations

import pandas as pd

DEFAULT_MAX_DRAWDOWN = 0.15


class KillSwitch:
    """Stateful, streaming drawdown monitor for use in a day-by-day loop."""

    def __init__(self, max_drawdown: float = DEFAULT_MAX_DRAWDOWN) -> None:
        self.max_drawdown = max_drawdown
        self._peak_equity: float | None = None
        self.triggered = False

    def check(self, equity: float) -> bool:
        """Update with the latest equity value and report kill-switch state.

        Args:
            equity: Current total portfolio equity (positions + cash).

        Returns:
            True if drawdown from the running peak is at or beyond
            ``max_drawdown``. Once triggered, stays triggered until ``reset``
            is called explicitly (a kill-switch should not silently
            re-arm itself just because equity ticked back up).
        """
        if self._peak_equity is None or equity > self._peak_equity:
            self._peak_equity = equity

        drawdown = 0.0 if not self._peak_equity else 1 - equity / self._peak_equity
        if drawdown >= self.max_drawdown:
            self.triggered = True
        return self.triggered

    def reset(self) -> None:
        """Manually re-arm the kill-switch after review."""
        self._peak_equity = None
        self.triggered = False


def running_drawdown(equity_curve: pd.Series) -> pd.Series:
    """Vectorized drawdown-from-peak series, for reporting/backtesting analysis."""
    peak = equity_curve.cummax()
    return 1 - equity_curve / peak
