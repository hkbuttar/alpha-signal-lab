import pytest

from backtest import fills


def test_slippage_zero_when_adv_unknown():
    assert fills.slippage_bps(1_000, adv_shares=0) == 0.0


def test_slippage_scales_linearly_with_participation():
    small = fills.slippage_bps(100, adv_shares=10_000)
    large = fills.slippage_bps(1_000, adv_shares=10_000)
    assert large == pytest.approx(small * 10)


def test_commission_proportional_to_notional():
    assert fills.commission(10_000) == pytest.approx(10_000 * fills.COMMISSION_BPS / 10_000)


def test_buy_fills_above_open_sell_fills_below():
    buy_price, _ = fills.compute_fill(order_shares=1_000, next_open=100.0, adv_shares=10_000)
    sell_price, _ = fills.compute_fill(order_shares=-1_000, next_open=100.0, adv_shares=10_000)

    assert buy_price > 100.0
    assert sell_price < 100.0
    assert buy_price - 100.0 == pytest.approx(100.0 - sell_price)


def test_zero_order_has_no_slippage_or_commission():
    price, fee = fills.compute_fill(order_shares=0, next_open=100.0, adv_shares=10_000)
    assert price == 100.0
    assert fee == 0.0
