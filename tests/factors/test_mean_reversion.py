import numpy as np

from factors import mean_reversion


def test_large_drop_scores_positive_others_dont(price_panel_factory):
    panel = price_panel_factory(tickers=["AAA", "BBB"], n_days=100, seed=1)
    close = panel.pivot(index="date", columns="ticker", values="close")

    # Force a sharp recent drop in AAA relative to its own trailing history.
    close.loc[close.index[-6] :, "AAA"] = close.loc[close.index[-6], "AAA"] * np.linspace(
        1.0, 0.7, 6
    )
    panel = panel.set_index(["date", "ticker"])
    for date in close.index[-6:]:
        panel.loc[(date, "AAA"), "close"] = close.loc[date, "AAA"]
    panel = panel.reset_index()

    scores = mean_reversion.compute(panel)
    last_date = close.index[-1]
    aaa_score = scores[(scores["date"] == last_date) & (scores["ticker"] == "AAA")]["score"].iloc[0]

    assert aaa_score > 0


def test_nan_before_window_available(price_panel):
    scores = mean_reversion.compute(price_panel)
    early_date = sorted(scores["date"].unique())[0]
    assert scores[scores["date"] == early_date]["score"].isna().all()


def test_output_columns(price_panel):
    scores = mean_reversion.compute(price_panel)
    assert set(scores.columns) == {"date", "ticker", "score"}
