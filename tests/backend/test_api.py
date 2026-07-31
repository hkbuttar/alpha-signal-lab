"""FastAPI backend tests. No real Postgres: `_snapshots_df` (the single
chokepoint every endpoint uses to reach live/storage.py) and results_io are
monkeypatched, keeping this suite network/database-free like the rest of the
project's tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import main
from backtest import results_io

client = TestClient(main.app)


def _snapshots(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_snapshots_empty_when_no_data(monkeypatch):
    monkeypatch.setattr(main, "_snapshots_df", lambda: pd.DataFrame())
    resp = client.get("/api/snapshots")
    assert resp.status_code == 200
    assert resp.json() == {"snapshots": []}


def test_snapshots_returns_records(monkeypatch):
    df = _snapshots(
        [
            {"date": "2024-01-02", "equity": 1_000_000.0, "cash": 500_000.0, "positions_json": {}},
            {"date": "2024-01-03", "equity": 1_010_000.0, "cash": 490_000.0, "positions_json": {}},
        ]
    )
    monkeypatch.setattr(main, "_snapshots_df", lambda: df)
    resp = client.get("/api/snapshots")
    body = resp.json()
    assert len(body["snapshots"]) == 2
    assert body["snapshots"][0] == {"date": "2024-01-02", "equity": 1_000_000.0, "cash": 500_000.0}


def test_positions_latest_empty_when_no_data(monkeypatch):
    monkeypatch.setattr(main, "_snapshots_df", lambda: pd.DataFrame())
    resp = client.get("/api/positions/latest")
    assert resp.json() == {"date": None, "positions": [], "sector_exposure": []}


def test_positions_latest_aggregates_by_sector(monkeypatch):
    df = _snapshots(
        [
            {
                "date": "2024-01-02",
                "equity": 1_000_000.0,
                "cash": 500_000.0,
                "positions_json": {"AAPL": 10.0, "MSFT": 5.0, "JPM": -3.0},
            }
        ]
    )
    monkeypatch.setattr(main, "_snapshots_df", lambda: df)
    resp = client.get("/api/positions/latest")
    body = resp.json()

    assert body["date"] == "2024-01-02"
    assert {p["ticker"] for p in body["positions"]} == {"AAPL", "MSFT", "JPM"}

    tech = next(s for s in body["sector_exposure"] if s["sector"] == "Technology")
    assert tech["shares"] == pytest.approx(15.0)
    financials = next(s for s in body["sector_exposure"] if s["sector"] == "Financials")
    assert financials["shares"] == pytest.approx(-3.0)


def test_backtest_runs_lists_available_runs(monkeypatch):
    monkeypatch.setattr(results_io, "list_runs", lambda: ["run-a", "run-b"])
    monkeypatch.setattr(results_io, "load_sample_metrics", lambda: {"cagr": 0.05})
    resp = client.get("/api/backtest/runs")
    assert resp.json() == {"runs": ["run-a", "run-b"], "sample_metrics": {"cagr": 0.05}}


def test_backtest_run_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(results_io, "list_runs", lambda: [])
    resp = client.get("/api/backtest/does-not-exist")
    assert resp.status_code == 404


def test_backtest_run_found_returns_equity_and_metrics(monkeypatch):
    equity = pd.Series([100.0, 110.0], index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    metrics = {"cagr": 0.1, "sharpe_ratio": 1.2}
    monkeypatch.setattr(results_io, "list_runs", lambda: ["run-a"])
    monkeypatch.setattr(results_io, "load_run", lambda run_name: (equity, metrics))

    resp = client.get("/api/backtest/run-a")
    body = resp.json()
    assert body["metrics"] == metrics
    assert len(body["equity"]) == 2
    assert body["equity"][0]["equity"] == 100.0


def test_rolling_risk_empty_below_min_history(monkeypatch):
    df = _snapshots(
        [
            {"date": d, "equity": 1_000_000.0, "cash": 0.0, "positions_json": {}}
            for d in ["2024-01-02", "2024-01-03"]
        ]
    )
    monkeypatch.setattr(main, "_snapshots_df", lambda: df)
    resp = client.get("/api/risk/rolling")
    assert resp.json() == {
        "dates": [],
        "rolling_sharpe": [],
        "drawdown": [],
        "historical_var": None,
        "parametric_var": None,
    }


def test_rolling_risk_arrays_stay_aligned(monkeypatch):
    dates = pd.bdate_range("2024-01-02", periods=30).strftime("%Y-%m-%d")
    rng = np.random.default_rng(0)
    equity = 1_000_000.0 * np.cumprod(1 + rng.normal(0, 0.01, len(dates)))
    df = _snapshots(
        [
            {"date": d, "equity": e, "cash": 0.0, "positions_json": {}}
            for d, e in zip(dates, equity, strict=True)
        ]
    )
    monkeypatch.setattr(main, "_snapshots_df", lambda: df)

    resp = client.get("/api/risk/rolling")
    body = resp.json()

    assert len(body["dates"]) == len(body["rolling_sharpe"]) == len(body["drawdown"]) == len(dates)
    assert body["historical_var"] is not None
    assert body["parametric_var"] is not None
