"""Daily news headline loading with local parquet caching.

Two sources are supported:

- ``newsapi``: NewsAPI.org free developer tier. Important limitation: the free
  tier only serves articles from roughly the last month, so it cannot backfill
  headlines for a multi-year backtest window. It is primarily useful for the
  live paper-trading loop.
- ``alpaca``: Alpaca's bundled Benzinga-sourced news feed, which has much deeper
  history and is the better source when historical sentiment coverage matters.

Both return long format (one row per headline) and are cached to parquet under
``data/cache/news/``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).resolve().parent / "cache" / "news"

NEWS_COLUMNS = ["date", "ticker", "headline", "source"]


def _empty_news_frame() -> pd.DataFrame:
    # See data/prices.py's _empty_price_frame for why "date" needs a real
    # dtype here: an untyped empty frame defaults to object dtype, which
    # upcasts a whole concatenated "date" column to object the moment one
    # ticker has zero headlines.
    empty = pd.DataFrame(columns=NEWS_COLUMNS)
    empty["date"] = pd.to_datetime(empty["date"])
    return empty


def _cache_path(ticker: str, source: str) -> Path:
    return CACHE_DIR / f"{ticker}_{source}.parquet"


def _read_cache(ticker: str, source: str) -> pd.DataFrame | None:
    path = _cache_path(ticker, source)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def _write_cache(ticker: str, source: str, df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.sort_values("date").drop_duplicates(["date", "headline"]).to_parquet(
        _cache_path(ticker, source), index=False
    )


def _fetch_newsapi(ticker: str, start: str, end: str) -> pd.DataFrame:
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return _empty_news_frame()

    resp = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": ticker,
            "from": start,
            "to": end,
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": api_key,
        },
        timeout=10,
    )
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    if not articles:
        return _empty_news_frame()

    rows = [
        {
            "date": pd.to_datetime(a["publishedAt"]).normalize(),
            "ticker": ticker,
            "headline": a["title"],
            "source": "newsapi",
        }
        for a in articles
    ]
    return pd.DataFrame(rows, columns=NEWS_COLUMNS)


def _fetch_alpaca(ticker: str, start: str, end: str) -> pd.DataFrame:
    from alpaca.data.historical.news import NewsClient
    from alpaca.data.requests import NewsRequest

    client = NewsClient(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"])
    request = NewsRequest(symbols=ticker, start=start, end=end)
    news = client.get_news(request)
    articles = getattr(news, "news", [])
    if not articles:
        return _empty_news_frame()

    rows = [
        {
            "date": pd.to_datetime(a.created_at).normalize(),
            "ticker": ticker,
            "headline": a.headline,
            "source": "alpaca",
        }
        for a in articles
    ]
    return pd.DataFrame(rows, columns=NEWS_COLUMNS)


def load_news(
    tickers: list[str],
    start: str,
    end: str,
    source: str = "newsapi",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Load daily headlines for a list of tickers over [start, end).

    Args:
        tickers: Ticker symbols to load.
        start: Start date, inclusive, as an ISO string.
        end: End date, exclusive, as an ISO string.
        source: "newsapi" or "alpaca".
        use_cache: Whether to read/write the local parquet cache.

    Returns:
        Long-format DataFrame with columns [date, ticker, headline, source].
        Empty (not missing) for ticker/date combinations with no coverage,
        which is expected for most of a multi-year backtest window when
        source="newsapi" (see module docstring).
    """
    fetcher = {"newsapi": _fetch_newsapi, "alpaca": _fetch_alpaca}[source]

    frames = []
    for ticker in tickers:
        cached = _read_cache(ticker, source) if use_cache else None
        if cached is None:
            merged = fetcher(ticker, start, end)
            if use_cache:
                _write_cache(ticker, source, merged)
        else:
            merged = cached
        window = merged[
            (merged["date"] >= pd.Timestamp(start)) & (merged["date"] < pd.Timestamp(end))
        ]
        frames.append(window)

    if not frames:
        return _empty_news_frame()
    result = (
        pd.concat(frames, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)
    )
    result["date"] = pd.to_datetime(result["date"])
    return result
