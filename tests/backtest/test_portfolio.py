from backtest.portfolio import Portfolio


def test_apply_fill_updates_cash_and_positions():
    portfolio = Portfolio(starting_cash=10_000.0)
    portfolio.apply_fill("AAA", 10, 100.0, commission=1.0)

    assert portfolio.positions["AAA"] == 10
    assert portfolio.cash == 10_000.0 - 1_000.0 - 1.0


def test_position_removed_when_it_nets_to_zero():
    portfolio = Portfolio(starting_cash=10_000.0)
    portfolio.apply_fill("AAA", 10, 100.0, commission=0.0)
    portfolio.apply_fill("AAA", -10, 100.0, commission=0.0)

    assert "AAA" not in portfolio.positions


def test_mark_to_market_computes_equity_and_records_history():
    portfolio = Portfolio(starting_cash=10_000.0)
    portfolio.apply_fill("AAA", 10, 100.0, commission=0.0)

    equity = portfolio.mark_to_market("2024-01-02", {"AAA": 110.0})

    assert equity == 10_000.0 - 1_000.0 + 1_100.0
    assert portfolio.equity_series().iloc[0] == equity
    assert portfolio.position_history().iloc[0]["ticker"] == "AAA"


def test_flatten_orders_negates_current_positions():
    portfolio = Portfolio(starting_cash=10_000.0)
    portfolio.apply_fill("AAA", 10, 100.0, commission=0.0)
    portfolio.apply_fill("BBB", -5, 50.0, commission=0.0)

    orders = portfolio.flatten_orders()
    assert orders == {"AAA": -10, "BBB": 5}
