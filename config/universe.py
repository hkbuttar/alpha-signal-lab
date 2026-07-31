"""Single source of truth for the tradable equity universe and sector map.

Universe is ~50 liquid US large-caps across four sectors (Technology, Healthcare,
Financials, Energy). This is the current constituent list only; no delisted or
acquired names are included, so survivorship bias is present (see README
Limitations & Assumptions).
"""

from __future__ import annotations

SECTOR_TICKERS: dict[str, list[str]] = {
    "Technology": [
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "META",
        "AVGO",
        "ORCL",
        "CRM",
        "ADBE",
        "CSCO",
        "AMD",
        "INTC",
        "TXN",
    ],
    "Healthcare": [
        "JNJ",
        "UNH",
        "LLY",
        "PFE",
        "MRK",
        "ABBV",
        "TMO",
        "ABT",
        "DHR",
        "BMY",
        "AMGN",
        "GILD",
    ],
    "Financials": [
        "JPM",
        "BAC",
        "WFC",
        "GS",
        "MS",
        "C",
        "SCHW",
        "AXP",
        "BLK",
        "SPGI",
        "PNC",
        "USB",
        "TFC",
    ],
    "Energy": [
        "XOM",
        "CVX",
        "COP",
        "SLB",
        "EOG",
        "MPC",
        "PSX",
        "VLO",
        "OXY",
        "WMB",
        "KMI",
        "DVN",
    ],
}

TICKER_SECTOR: dict[str, str] = {
    ticker: sector for sector, tickers in SECTOR_TICKERS.items() for ticker in tickers
}

UNIVERSE: list[str] = sorted(TICKER_SECTOR)
