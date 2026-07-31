"""Fill simulation: next-day-open execution, commission, and slippage.

Orders decided using information through day t are never filled at day t's
close; they're filled at day t+1's open, since acting on the same bar the
signal was computed from is a common source of look-ahead bias in vectorized
backtests. Slippage is modeled as a linear function of participation rate
(order size relative to average daily volume), since a large order in a
low-liquidity name should cost more to execute than the same order in a
heavily traded one.
"""

from __future__ import annotations

COMMISSION_BPS = 5.0
IMPACT_BPS_AT_FULL_PARTICIPATION = 50.0
ADV_WINDOW_DAYS = 21


def slippage_bps(order_shares: float, adv_shares: float) -> float:
    """Linear market-impact slippage in bps.

    Args:
        order_shares: Signed order size in shares (sign doesn't matter here).
        adv_shares: Trailing average daily volume in shares.

    Returns:
        Slippage in bps, scaling linearly with participation rate
        (|order| / ADV). Zero if ADV is unknown or non-positive.
    """
    if adv_shares <= 0:
        return 0.0
    participation = abs(order_shares) / adv_shares
    return IMPACT_BPS_AT_FULL_PARTICIPATION * participation


def commission(notional: float) -> float:
    """Flat commission cost in dollars for a trade of the given notional."""
    return abs(notional) * COMMISSION_BPS / 10_000


def compute_fill(order_shares: float, next_open: float, adv_shares: float) -> tuple[float, float]:
    """Simulate a fill for an order, given the next bar's open price.

    Args:
        order_shares: Signed order size (positive = buy, negative = sell).
        next_open: Next trading day's open price.
        adv_shares: Trailing average daily volume in shares, for slippage.

    Returns:
        (fill_price, commission_cost). Buys fill above the quoted open,
        sells fill below it, both by the modeled slippage.
    """
    if order_shares == 0:
        return next_open, 0.0

    slip = slippage_bps(order_shares, adv_shares) / 10_000
    direction = 1 if order_shares > 0 else -1
    fill_price = next_open * (1 + direction * slip)
    fee = commission(order_shares * fill_price)
    return fill_price, fee
