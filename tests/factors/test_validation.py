import pandas as pd

from factors import validation


def _perfect_signal_panel():
    dates = pd.bdate_range("2022-01-03", periods=30)
    tickers = ["A", "B", "C", "D", "E"]
    drifts = {"A": 0.001, "B": 0.002, "C": 0.003, "D": 0.004, "E": 0.005}

    price_rows, score_rows = [], []
    for ticker in tickers:
        price = 100.0
        for date in dates:
            price_rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 1_000_000,
                }
            )
            score_rows.append({"date": date, "ticker": ticker, "score": drifts[ticker]})
            price *= 1 + drifts[ticker]

    return pd.DataFrame(price_rows), pd.DataFrame(score_rows)


def test_information_coefficient_is_near_perfect_for_a_perfect_signal():
    prices, scores = _perfect_signal_panel()
    ic = validation.information_coefficient(scores, prices, horizon=5)
    assert not ic.empty
    assert (ic > 0.999).all()


def test_ic_decay_returns_a_value_per_horizon():
    prices, scores = _perfect_signal_panel()
    decay = validation.ic_decay(scores, prices, horizons=(1, 5, 10))
    assert list(decay.index) == [1, 5, 10]
    assert decay.notna().all()


def test_turnover_full_churn_when_top_name_flips():
    dates = pd.bdate_range("2022-01-03", periods=2)
    day1 = {"A": 4, "B": 3, "C": 2, "D": 1}
    day2 = {"A": 1, "B": 2, "C": 3, "D": 4}

    rows = [{"date": dates[0], "ticker": t, "score": s} for t, s in day1.items()]
    rows += [{"date": dates[1], "ticker": t, "score": s} for t, s in day2.items()]
    scores = pd.DataFrame(rows)

    churn = validation.turnover(scores, top_frac=0.25)
    assert churn.loc[dates[1]] == 1.0
