"""FastAPI backend for the React dashboard (deployed on Render).

Thin HTTP wrapper, not a second data layer: every endpoint here just JSON-
shapes data already computed by live/storage.py, backtest/results_io.py,
backtest/metrics.py, and risk/. If the underlying logic ever needs to change,
change it there, not here, so the Streamlit dashboard (dashboard/app.py) and
this API never drift apart on what a "rolling Sharpe" or "sector exposure"
actually means.

Run locally: uvicorn backend.main:app --reload
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backtest import results_io
from config.universe import TICKER_SECTOR
from live import storage
from risk.kill_switch import running_drawdown
from risk.var import historical_var, parametric_var

ROLLING_WINDOW_DAYS = 21
TRADING_DAYS_PER_YEAR = 252
MIN_RISK_HISTORY_DAYS = 5

app = FastAPI(title="Alpha Signal Lab API")

_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    # Defaults wide open for initial setup; tighten to the real Vercel URL via
    # ALLOWED_ORIGINS once deployed (comma-separated if there's more than one).
    allow_origins=["*"] if _allowed_origins == "*" else _allowed_origins.split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _snapshots_df() -> pd.DataFrame:
    """Live portfolio snapshots, or an empty frame if Postgres isn't reachable yet."""
    try:
        conn = storage.get_connection()
    except KeyError:
        return pd.DataFrame()
    try:
        return storage.read_snapshots(conn)
    finally:
        conn.close()


@app.get("/api/snapshots")
def get_snapshots() -> dict:
    df = _snapshots_df()
    if df.empty:
        return {"snapshots": []}
    return {
        "snapshots": [
            {"date": str(row["date"]), "equity": row["equity"], "cash": row["cash"]}
            for _, row in df.iterrows()
        ]
    }


@app.get("/api/positions/latest")
def get_latest_positions() -> dict:
    df = _snapshots_df()
    if df.empty:
        return {"date": None, "positions": [], "sector_exposure": []}

    latest = df.iloc[-1]
    positions = latest["positions_json"] or {}
    position_rows = [
        {"ticker": ticker, "shares": shares, "sector": TICKER_SECTOR.get(ticker, "Unknown")}
        for ticker, shares in positions.items()
    ]

    sector_totals: dict[str, float] = {}
    for row in position_rows:
        sector_totals[row["sector"]] = sector_totals.get(row["sector"], 0.0) + row["shares"]

    return {
        "date": str(latest["date"]),
        "positions": position_rows,
        "sector_exposure": [{"sector": s, "shares": v} for s, v in sector_totals.items()],
    }


@app.get("/api/backtest/runs")
def get_backtest_runs() -> dict:
    return {"runs": results_io.list_runs(), "sample_metrics": results_io.load_sample_metrics()}


@app.get("/api/backtest/{run_id}")
def get_backtest_run(run_id: str) -> dict:
    if run_id not in results_io.list_runs():
        raise HTTPException(status_code=404, detail=f"Unknown backtest run: {run_id}")

    equity, metrics = results_io.load_run(run_id)
    return {
        "equity": [{"date": str(date), "equity": value} for date, value in equity.items()],
        "metrics": metrics,
    }


@app.get("/api/risk/rolling")
def get_rolling_risk() -> dict:
    df = _snapshots_df()
    empty = {
        "dates": [],
        "rolling_sharpe": [],
        "drawdown": [],
        "historical_var": None,
        "parametric_var": None,
    }
    if df.empty:
        return empty

    equity = df.set_index("date")["equity"]
    # Keep NaN (don't dropna) so `returns` stays index-aligned with `equity` for zipping below.
    returns = equity.pct_change()
    if returns.notna().sum() < MIN_RISK_HISTORY_DAYS:
        return empty

    drawdown = running_drawdown(equity)
    rolling_sharpe = (
        returns.rolling(ROLLING_WINDOW_DAYS).mean()
        / returns.rolling(ROLLING_WINDOW_DAYS).std()
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    )

    return {
        "dates": [str(d) for d in equity.index],
        "rolling_sharpe": [None if pd.isna(v) else v for v in rolling_sharpe],
        "drawdown": [None if pd.isna(v) else v for v in drawdown],
        "historical_var": round(historical_var(returns.dropna()), 4),
        "parametric_var": round(parametric_var(returns.dropna()), 4),
    }
