import pandas as pd

from data import news


def test_fetch_newsapi_returns_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    result = news._fetch_newsapi("AAA", "2022-01-01", "2022-01-10")
    assert result.empty
    assert list(result.columns) == news.NEWS_COLUMNS


def test_load_news_caches_between_calls(monkeypatch, tmp_path):
    monkeypatch.setattr(news, "CACHE_DIR", tmp_path)
    calls = {"count": 0}

    def fake_fetch(ticker, start, end):
        calls["count"] += 1
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp(start),
                    "ticker": ticker,
                    "headline": "Test headline",
                    "source": "newsapi",
                }
            ]
        )

    monkeypatch.setattr(news, "_fetch_newsapi", fake_fetch)

    first = news.load_news(["AAA"], "2022-01-01", "2022-01-10", source="newsapi")
    second = news.load_news(["AAA"], "2022-01-01", "2022-01-10", source="newsapi")

    assert calls["count"] == 1  # second call served entirely from cache
    assert len(first) == 1
    assert len(second) == 1
