import pytest

from factors import momentum


def test_score_matches_manual_calculation(price_panel):
    scores = momentum.compute(price_panel)
    close = price_panel.pivot(index="date", columns="ticker", values="close")

    date = close.index[-1]
    ticker = close.columns[0]
    expected = (
        close[ticker].iloc[-1 - momentum.SKIP_DAYS]
        / close[ticker].iloc[-1 - momentum.LOOKBACK_DAYS]
        - 1
    )

    actual = scores[(scores["date"] == date) & (scores["ticker"] == ticker)]["score"].iloc[0]
    assert actual == pytest.approx(expected, rel=1e-9)


def test_nan_before_lookback_available(price_panel):
    scores = momentum.compute(price_panel)
    early_date = sorted(scores["date"].unique())[0]
    early_scores = scores[scores["date"] == early_date]
    assert early_scores["score"].isna().all()


def test_output_shape_matches_input_grid(price_panel):
    scores = momentum.compute(price_panel)
    assert set(scores.columns) == {"date", "ticker", "score"}
    assert len(scores) == price_panel[["date", "ticker"]].drop_duplicates().shape[0]
