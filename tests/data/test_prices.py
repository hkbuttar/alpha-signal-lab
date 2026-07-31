import pandas as pd

from data import prices


def _fake_downloader(calls):
    def _download(ticker, start, end):
        calls["count"] += 1
        dates = pd.bdate_range(start, end)
        return pd.DataFrame(
            {
                "date": dates,
                "ticker": ticker,
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 100,
            }
        )[prices.PRICE_COLUMNS]

    return _download


def test_load_prices_returns_expected_columns(monkeypatch, tmp_path):
    monkeypatch.setattr(prices, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(prices, "_download_yfinance", _fake_downloader({"count": 0}))

    result = prices.load_prices(["AAA"], "2022-01-03", "2022-01-10", source="yfinance")

    assert list(result.columns) == prices.PRICE_COLUMNS
    assert (result["date"] >= pd.Timestamp("2022-01-03")).all()
    assert (result["date"] < pd.Timestamp("2022-01-10")).all()


def test_second_call_within_cached_range_skips_redownload(monkeypatch, tmp_path):
    monkeypatch.setattr(prices, "CACHE_DIR", tmp_path)
    calls = {"count": 0}
    monkeypatch.setattr(prices, "_download_yfinance", _fake_downloader(calls))

    prices.load_prices(["AAA"], "2022-01-03", "2022-01-14", source="yfinance")
    assert calls["count"] == 1

    prices.load_prices(["AAA"], "2022-01-04", "2022-01-08", source="yfinance")
    assert calls["count"] == 1  # fully covered by the cache written above


def test_disabling_cache_always_redownloads(monkeypatch, tmp_path):
    monkeypatch.setattr(prices, "CACHE_DIR", tmp_path)
    calls = {"count": 0}
    monkeypatch.setattr(prices, "_download_yfinance", _fake_downloader(calls))

    prices.load_prices(["AAA"], "2022-01-03", "2022-01-10", source="yfinance", use_cache=False)
    prices.load_prices(["AAA"], "2022-01-03", "2022-01-10", source="yfinance", use_cache=False)
    assert calls["count"] == 2
