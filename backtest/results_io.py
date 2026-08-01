"""Shared helpers for listing/loading committed backtest runs.

Used by both dashboard/app.py (Streamlit) and backend/main.py (FastAPI, behind
the React dashboard) so the two presentation layers don't each reimplement
the same "read equity_curve.csv + metrics.json off disk" logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RUNS_DIR = RESULTS_DIR / "runs"
SAMPLE_METRICS_PATH = RESULTS_DIR / "sample_metrics.json"


def list_runs() -> list[str]:
    """Names of available backtest runs under backtest/results/runs/, sorted."""
    if not RUNS_DIR.exists():
        return []
    return sorted(p.name for p in RUNS_DIR.iterdir() if p.is_dir())


def load_run(run_name: str) -> tuple[pd.Series, dict]:
    """Load one run's equity curve and metrics by directory name (see list_runs)."""
    run_dir = RUNS_DIR / run_name
    equity = pd.read_csv(run_dir / "equity_curve.csv", index_col=0, parse_dates=True)["equity"]
    metrics = json.loads((run_dir / "metrics.json").read_text())
    return equity, metrics


def load_sample_metrics() -> dict | None:
    """The one committed sample run's full-period metrics, for when no local run/ dirs exist.

    Returns the same flat {metric_name: value} shape as ``load_run``'s metrics dict
    (sample_metrics.json additionally wraps this in a "run" description and a
    "pre_kill_switch" sub-window breakdown, which callers here don't render).
    """
    if not SAMPLE_METRICS_PATH.exists():
        return None
    return json.loads(SAMPLE_METRICS_PATH.read_text())["full_period"]
