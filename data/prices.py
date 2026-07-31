"""Daily OHLCV price loading with local parquet caching.

Two sources are supported:

- ``yfinance`` (default): no API key required, used for research notebooks and
  backtests since it is the fastest to iterate with.
- ``alpaca``: Alpaca Market Data API, used for the live paper-trading pipeline so
  the same account covers both data and order execution.

All data is returned in long format (one row per ticker per day) and cached to
parquet under ``data/cache/prices/`` so repeated calls for an overlapping date
range do not re-hit the network.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent / "cache" / "prices"

PRICE_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume"]


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker}.parquet"


def _read_cache(ticker: str) -> pd.DataFrame | None:
    path = _cache_path(ticker)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def _write_cache(ticker: str, df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.sort_values("date").drop_duplicates("date").to_parquet(_cache_path(ticker), index=False)


def _merge_cache(ticker: str, fresh: pd.DataFrame) -> pd.DataFrame:
    cached = _read_cache(ticker)
    combined = fresh if cached is None else pd.concat([cached, fresh], ignore_index=True)
    combined = combined.sort_values("date").drop_duplicates("date", keep="last")
    _write_cache(ticker, combined)
    return combined


def _empty_price_frame() -> pd.DataFrame:
    # An empty pd.DataFrame(columns=...) defaults every column to object dtype,
    # which silently upcasts a whole concatenated "date" column to object the
    # moment one ticker (e.g. a delisted/renamed symbol) fails to download and
    # falls back to this. Give "date" its real dtype so concat can't do that.
    empty = pd.DataFrame(columns=PRICE_COLUMNS)
    empty["date"] = pd.to_datetime(empty["date"])
    return empty


def _download_yfinance(ticker: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if raw.empty:
        return _empty_price_frame()
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns=str.lower).reset_index()
    raw = raw.rename(columns={"Date": "date"})
    raw["date"] = pd.to_datetime(raw["date"]).dt.normalize()
    raw["ticker"] = ticker
    return raw[PRICE_COLUMNS]


def _download_alpaca(ticker: str, start: str, end: str) -> pd.DataFrame:
    from alpaca.data.enums import DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(
        os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"]
    )
    request = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        feed=DataFeed.IEX,
    )
    bars = client.get_stock_bars(request).df.reset_index()
    if bars.empty:
        return _empty_price_frame()
    bars["date"] = pd.to_datetime(bars["timestamp"]).dt.normalize()
    bars["ticker"] = ticker
    return bars.rename(columns={"symbol": "ticker"})[PRICE_COLUMNS]


def load_prices(
    tickers: list[str],
    start: str,
    end: str,
    source: str = "yfinance",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Load daily OHLCV bars for a list of tickers over [start, end).

    Args:
        tickers: Ticker symbols to load.
        start: Start date, inclusive, as an ISO string (e.g. "2020-01-01").
        end: End date, exclusive, as an ISO string.
        source: "yfinance" or "alpaca".
        use_cache: Whether to read/write the local parquet cache.

    Returns:
        Long-format DataFrame with columns
        [date, ticker, open, high, low, close, volume], sorted by date then ticker.
    """
    downloader = {"yfinance": _download_yfinance, "alpaca": _download_alpaca}[source]

    frames = []
    for ticker in tickers:
        cached = _read_cache(ticker) if use_cache else None
        needs_fetch = True
        if cached is not None and not cached.empty:
            cached_start, cached_end = cached["date"].min(), cached["date"].max()
            if cached_start <= pd.Timestamp(start) and cached_end >= pd.Timestamp(
                end
            ) - pd.Timedelta(days=1):
                needs_fetch = False

        if needs_fetch:
            fresh = downloader(ticker, start, end)
            merged = _merge_cache(ticker, fresh) if use_cache else fresh
        else:
            merged = cached

        window = merged[
            (merged["date"] >= pd.Timestamp(start)) & (merged["date"] < pd.Timestamp(end))
        ]
        frames.append(window)

    if not frames:
        return _empty_price_frame()
    result = (
        pd.concat(frames, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)
    )
    result["date"] = pd.to_datetime(result["date"])
    return result
