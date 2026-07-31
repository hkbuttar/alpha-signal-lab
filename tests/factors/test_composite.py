import pandas as pd

from factors import mean_reversion, momentum, volatility
from factors._util import cross_sectional_zscore
from factors.composite import combine_factors, select_deciles


def test_missing_factor_falls_back_to_available_factors(price_panel_factory):
    panel = price_panel_factory(
        tickers=["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"], n_days=280, seed=7
    )
    f1 = momentum.compute(panel)
    f2 = mean_reversion.compute(panel).copy()

    # Force one otherwise-valid (date, ticker) cell to be missing in f2, as
    # would happen for a name with no news coverage that day.
    valid_f2 = f2.dropna(subset=["score"])
    gap_date, gap_ticker = valid_f2.iloc[-1][["date", "ticker"]]
    f2.loc[(f2["date"] == gap_date) & (f2["ticker"] == gap_ticker), "score"] = pd.NA

    composite = combine_factors({"momentum": f1, "mean_reversion": f2}, panel)

    f1_wide = f1.pivot(index="date", columns="ticker", values="score")
    f1_zscore = cross_sectional_zscore(f1_wide).loc[gap_date, gap_ticker]

    composite_row = composite[(composite["date"] == gap_date) & (composite["ticker"] == gap_ticker)]
    assert composite_row["composite_score"].iloc[0] == f1_zscore


def test_rank_matches_composite_score_ordering(price_panel_factory):
    panel = price_panel_factory(n_days=220, seed=3)
    factor_scores = {"momentum": momentum.compute(panel), "volatility": volatility.compute(panel)}
    composite = combine_factors(factor_scores, panel)

    last_date = sorted(composite["date"].unique())[-1]
    day = composite[composite["date"] == last_date].dropna(subset=["composite_score"])
    ordered = day.sort_values("composite_score", ascending=False)
    assert list(ordered["rank"]) == list(range(1, len(day) + 1))


def test_select_deciles_respects_min_breadth():
    scores = pd.Series([5, 4, 3, 2, 1], index=["A", "B", "C", "D", "E"])
    longs, shorts = select_deciles(scores, decile_frac=0.2, min_breadth=10)
    assert longs == []
    assert shorts == []


def test_select_deciles_picks_extremes():
    scores = pd.Series(range(10), index=[f"T{i}" for i in range(10)])
    longs, shorts = select_deciles(scores, decile_frac=0.2, min_breadth=5)
    assert set(longs) == {"T9", "T8"}
    assert set(shorts) == {"T0", "T1"}
