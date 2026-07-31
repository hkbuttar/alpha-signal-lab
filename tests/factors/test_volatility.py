from factors import volatility


def test_lowest_vol_ticker_gets_highest_score(price_panel_factory):
    # price_panel_factory gives ticker i an increasing vol regime, so the
    # first ticker (index 0) is the lowest-vol name.
    tickers = ["LOW", "MID", "HIGH"]
    panel = price_panel_factory(tickers=tickers, n_days=150, seed=2)

    scores = volatility.compute(panel)
    last_date = sorted(scores["date"].unique())[-1]
    day_scores = scores[scores["date"] == last_date].set_index("ticker")["score"]

    assert day_scores["LOW"] > day_scores["HIGH"]


def test_nan_before_window_available(price_panel):
    scores = volatility.compute(price_panel)
    early_date = sorted(scores["date"].unique())[0]
    assert scores[scores["date"] == early_date]["score"].isna().all()
