"""Thin wrapper over Alpaca's TradingClient for paper-trading order execution.

CLAUDE.md boundary file: this places real (paper) orders. Any change to order
logic, sizing, or execution triggers needs a human review before merging, even
though it's paper money. Keep it a thin, auditable wrapper rather than adding
strategy logic here - order sizing and risk decisions belong in
backtest/engine.py, risk/, and live/scheduler.py, not here.
"""

from __future__ import annotations

import os

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

ORDER_EPSILON = 1e-6


class AlpacaClient:
    """Paper-trading-only client. Refuses to run against a live-money endpoint."""

    def __init__(
        self, api_key: str | None = None, secret_key: str | None = None, base_url: str | None = None
    ) -> None:
        api_key = api_key or os.environ["ALPACA_API_KEY"]
        secret_key = secret_key or os.environ["ALPACA_SECRET_KEY"]
        base_url = base_url or os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

        if "paper-api" not in base_url:
            raise RuntimeError(
                f"ALPACA_BASE_URL ({base_url}) does not look like a paper-trading endpoint; "
                "refusing to initialize a client that could place live orders."
            )

        self._client = TradingClient(api_key, secret_key, paper=True, url_override=base_url)

    def get_account(self) -> dict:
        account = self._client.get_account()
        return {"equity": float(account.equity), "cash": float(account.cash)}

    def get_positions(self) -> dict[str, float]:
        """Current positions, ticker -> signed share quantity (negative for shorts)."""
        positions = self._client.get_all_positions()
        return {p.symbol: float(p.qty) for p in positions}

    def submit_order(self, ticker: str, shares: float) -> dict:
        """Submit a market order for a signed share delta (positive = buy, negative = sell)."""
        if abs(shares) < ORDER_EPSILON:
            return {"ticker": ticker, "shares": 0.0, "status": "skipped"}

        request = MarketOrderRequest(
            symbol=ticker,
            qty=abs(shares),
            side=OrderSide.BUY if shares > 0 else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = self._client.submit_order(request)
        return {
            "ticker": ticker,
            "shares": shares,
            "order_id": str(order.id),
            "status": order.status,
        }
