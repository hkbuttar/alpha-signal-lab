from types import SimpleNamespace

import pandas as pd

from factors import sentiment


def _fake_client(text: str = "0.5"):
    calls = {"count": 0}

    def create(**kwargs):
        calls["count"] += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), calls


def test_score_headline_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert sentiment.score_headline("Company beats earnings") is None


def test_score_headline_parses_client_response():
    client, calls = _fake_client("0.5")
    assert sentiment.score_headline("Company beats earnings", client=client) == 0.5
    assert calls["count"] == 1


def test_score_headline_clips_out_of_range_values():
    client, _ = _fake_client("3.7")
    assert sentiment.score_headline("Wildly positive news", client=client) == 1.0


def test_score_headlines_caches_across_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(sentiment, "CACHE_PATH", tmp_path / "scores.parquet")
    client, calls = _fake_client("0.2")

    first = sentiment.score_headlines(["Headline A", "Headline B"], client=client)
    assert calls["count"] == 2
    assert first == {"Headline A": 0.2, "Headline B": 0.2}

    second = sentiment.score_headlines(["Headline A"], client=client)
    assert calls["count"] == 2  # no new calls, served from cache
    assert second == {"Headline A": 0.2}


def test_compute_returns_nan_grid_when_no_news(price_panel):
    scores = sentiment.compute(price_panel, news=None)
    assert set(scores.columns) == {"date", "ticker", "score"}
    assert len(scores) == price_panel[["date", "ticker"]].drop_duplicates().shape[0]
    assert scores["score"].isna().all()


def test_compute_aggregates_daily_mean(monkeypatch, price_panel):
    monkeypatch.setattr(
        sentiment, "score_headlines", lambda headlines, client=None: {"h1": 1.0, "h2": -0.5}
    )

    ticker = price_panel["ticker"].iloc[0]
    date = price_panel["date"].iloc[0]
    news = pd.DataFrame(
        [
            {"date": date, "ticker": ticker, "headline": "h1", "source": "test"},
            {"date": date, "ticker": ticker, "headline": "h2", "source": "test"},
        ]
    )

    scores = sentiment.compute(price_panel, news=news)
    row = scores[(scores["date"] == date) & (scores["ticker"] == ticker)]
    assert row["score"].iloc[0] == 0.25
