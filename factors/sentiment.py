"""LLM news sentiment factor.

Rationale: news sentiment may capture information not yet reflected in price,
particularly for lower-coverage names.

Method: each headline is scored independently by GPT-4o-mini on a [-1, +1]
polarity scale (prompted to return only a number, no explanation), then
aggregated to a daily per-ticker mean. Per-headline scores are cached to
parquet keyed by a hash of the headline text, since the same headline should
never need to be re-scored (and re-scoring would just burn API spend).

Coverage caveat: this factor is only as good as the news panel it's given. The
NewsAPI free tier (data/news.py) only covers roughly the last month, so for
most of a multi-year backtest window this factor will legitimately have no
headlines to score and will return NaN rather than a fabricated neutral score.
composite.py handles that by renormalizing weights across whatever factors do
have a score for a given ticker/day.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pandas as pd

name = "sentiment"

CACHE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "cache" / "sentiment" / "scores.parquet"
)

SENTIMENT_PROMPT = (
    "Score the sentiment of this financial news headline toward the company it "
    "concerns, on a scale from -1 (very negative) to +1 (very positive), with 0 "
    "being neutral. Respond with only the number, nothing else.\n\nHeadline: {headline}"
)


def _headline_hash(headline: str) -> str:
    return hashlib.sha256(headline.encode("utf-8")).hexdigest()


def _load_cache() -> pd.DataFrame:
    if CACHE_PATH.exists():
        return pd.read_parquet(CACHE_PATH)
    return pd.DataFrame(columns=["headline_hash", "score"])


def _save_cache(cache: pd.DataFrame) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache.drop_duplicates("headline_hash", keep="last").to_parquet(CACHE_PATH, index=False)


def score_headline(headline: str, client=None) -> float | None:
    """Score a single headline with GPT-4o-mini, returning a float in [-1, 1].

    Returns None if no LLM_API_KEY is configured or the call fails, so callers
    can distinguish "not scored" from a genuine neutral 0.0.
    """
    if client is None:
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            return None
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": SENTIMENT_PROMPT.format(headline=headline)}],
            temperature=0,
            max_tokens=5,
        )
        return max(-1.0, min(1.0, float(response.choices[0].message.content.strip())))
    except (ValueError, KeyError, IndexError, AttributeError):
        return None


def score_headlines(headlines: list[str], client=None) -> dict[str, float]:
    """Score a batch of headlines, reusing the on-disk cache where possible."""
    cache = _load_cache()
    cached_scores = dict(zip(cache["headline_hash"], cache["score"], strict=True))

    results: dict[str, float] = {}
    new_rows = []
    for headline in headlines:
        h = _headline_hash(headline)
        if h in cached_scores:
            results[headline] = cached_scores[h]
            continue
        score = score_headline(headline, client=client)
        if score is not None:
            results[headline] = score
            new_rows.append({"headline_hash": h, "score": score})

    if new_rows:
        _save_cache(pd.concat([cache, pd.DataFrame(new_rows)], ignore_index=True))

    return results


def compute(prices: pd.DataFrame, news: pd.DataFrame | None = None) -> pd.DataFrame:
    """Daily per-ticker mean sentiment score.

    Args:
        prices: Long-format OHLCV panel, used only to define the full
            date/ticker grid the output should align to.
        news: Long-format headline panel [date, ticker, headline, source].

    Returns:
        Long-format [date, ticker, score], reindexed to every (date, ticker)
        pair present in ``prices``. NaN wherever there is no news coverage.
    """
    grid = prices[["date", "ticker"]].drop_duplicates()

    if news is None or news.empty:
        return grid.assign(score=pd.NA)

    scores = score_headlines(news["headline"].tolist())
    scored = news.assign(score=news["headline"].map(scores))
    daily = (
        scored.dropna(subset=["score"]).groupby(["date", "ticker"], as_index=False)["score"].mean()
    )

    merged = grid.merge(daily, on=["date", "ticker"], how="left")
    return merged
