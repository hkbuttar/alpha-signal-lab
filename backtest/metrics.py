"""Backtest performance metrics: CAGR, Sharpe, Sortino, drawdown, win rate, holding period."""

from __future__ import annotations

import numpy as np
import pandas as pd

from risk.kill_switch import running_drawdown

TRADING_DAYS_PER_YEAR = 252
ZERO_VOL_EPSILON = (
    1e-9  # below this, treat std as zero rather than risk a divide-by-near-zero blowup
)


def cagr(equity: pd.Series) -> float:
    """Compound annual growth rate over the equity curve's full span."""
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return float("nan")
    years = len(equity) / TRADING_DAYS_PER_YEAR
    return (
        float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) if years > 0 else float("nan")
    )


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Annualized Sharpe ratio of daily returns."""
    excess = returns.dropna() - risk_free / TRADING_DAYS_PER_YEAR
    if excess.empty or excess.std() < ZERO_VOL_EPSILON:
        return float("nan")
    return float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def sortino_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Annualized Sortino ratio (downside-deviation-only Sharpe) of daily returns."""
    excess = returns.dropna() - risk_free / TRADING_DAYS_PER_YEAR
    downside = excess[excess < 0]
    if downside.empty or downside.std() < ZERO_VOL_EPSILON:
        return float("nan")
    return float(excess.mean() / downside.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough drawdown over the equity curve."""
    if equity.empty:
        return float("nan")
    return float(running_drawdown(equity).max())


def win_rate(returns: pd.Series) -> float:
    """Fraction of trading days with a positive return."""
    clean = returns.dropna()
    if clean.empty:
        return float("nan")
    return float((clean > 0).mean())


def avg_holding_period(position_history: pd.DataFrame, all_dates: pd.Index | None = None) -> float:
    """Average length, in trading days, of a continuous non-zero position in a name.

    Args:
        position_history: Long-format [date, ticker, shares]. Portfolio only
            logs a row for tickers it actually holds, so a day where the
            entire book is flat (e.g. before the first rebalance, or after a
            kill-switch flatten) simply has no rows at all that day.
        all_dates: The full trading calendar the backtest ran over (e.g. the
            equity curve's index, which has an entry every day regardless of
            positions). Without this, a fully-flat day wouldn't appear in the
            reshaped date axis at all and would silently merge the holding
            runs on either side of it into one.
    """
    if position_history.empty:
        return float("nan")

    wide = position_history.pivot_table(
        index="date", columns="ticker", values="shares", fill_value=0.0
    )
    if all_dates is not None:
        wide = wide.reindex(pd.Index(all_dates).union(wide.index), fill_value=0.0)
    spans = []
    for ticker in wide.columns:
        held = wide[ticker] != 0
        run_id = (held != held.shift()).cumsum()
        for _, group in held[held].groupby(run_id[held]):
            spans.append(len(group))

    return float(np.mean(spans)) if spans else float("nan")


def compute_metrics(equity: pd.Series, position_history: pd.DataFrame) -> dict[str, float]:
    """Full metrics table for a backtest run, matching the README Results section."""
    returns = equity.pct_change()
    return {
        "cagr": cagr(equity),
        "sharpe_ratio": sharpe_ratio(returns),
        "sortino_ratio": sortino_ratio(returns),
        "max_drawdown": max_drawdown(equity),
        "win_rate": win_rate(returns),
        "avg_holding_period_days": avg_holding_period(position_history, all_dates=equity.index),
    }
