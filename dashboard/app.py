"""Streamlit dashboard: live paper-trading status vs. backtested expectation.

Reads live state from live/storage.py's SQLite database and backtested
equity/metrics from backtest/results/. Every section degrades gracefully to an
empty-state message rather than crashing when live data doesn't exist yet
(e.g. before the scheduler has ever run).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.universe import TICKER_SECTOR
from live import storage
from risk.kill_switch import running_drawdown
from risk.var import historical_var, parametric_var

BACKTEST_RUNS_DIR = Path(__file__).resolve().parent.parent / "backtest" / "results" / "runs"
SAMPLE_METRICS_PATH = (
    Path(__file__).resolve().parent.parent / "backtest" / "results" / "sample_metrics.json"
)

st.set_page_config(page_title="Alpha Signal Lab", layout="wide")


@st.cache_data(ttl=60)
def load_live_snapshots() -> pd.DataFrame:
    if not storage.DB_PATH.exists():
        return pd.DataFrame()
    conn = storage.get_connection()
    df = storage.read_snapshots(conn)
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def list_backtest_runs() -> list[Path]:
    if not BACKTEST_RUNS_DIR.exists():
        return []
    return sorted(p for p in BACKTEST_RUNS_DIR.iterdir() if p.is_dir())


def load_backtest_run(run_dir: Path) -> tuple[pd.Series, dict]:
    equity = pd.read_csv(run_dir / "equity_curve.csv", index_col=0, parse_dates=True)["equity"]
    metrics = json.loads((run_dir / "metrics.json").read_text())
    return equity, metrics


st.title("Alpha Signal Lab")
st.caption("Event-driven factor research and paper-trading dashboard.")

live_snapshots = load_live_snapshots()
runs = list_backtest_runs()

selected_backtest_equity = None
selected_backtest_metrics = None
if runs:
    run_labels = [p.name for p in runs]
    choice = st.sidebar.selectbox("Backtest run", run_labels, index=len(run_labels) - 1)
    selected_backtest_equity, selected_backtest_metrics = load_backtest_run(
        runs[run_labels.index(choice)]
    )
elif SAMPLE_METRICS_PATH.exists():
    selected_backtest_metrics = json.loads(SAMPLE_METRICS_PATH.read_text())
    st.sidebar.info(
        "Showing the committed sample backtest metrics (no equity curve saved for this run)."
    )
else:
    st.sidebar.warning("No backtest runs found. Run `python -m backtest.engine` first.")

tab_equity, tab_positions, tab_risk, tab_factors = st.tabs(
    ["Equity Curve", "Positions & Exposure", "Rolling Risk", "Factor Breakdown"]
)

with tab_equity:
    fig = go.Figure()
    has_data = False
    if selected_backtest_equity is not None:
        fig.add_trace(
            go.Scatter(
                x=selected_backtest_equity.index,
                y=selected_backtest_equity.values,
                name="Backtested expectation",
                line={"dash": "dash"},
            )
        )
        has_data = True
    if not live_snapshots.empty:
        fig.add_trace(
            go.Scatter(x=live_snapshots["date"], y=live_snapshots["equity"], name="Live (paper)")
        )
        has_data = True

    if has_data:
        fig.update_layout(title="Equity: live vs. backtested expectation", yaxis_title="Equity ($)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity data yet. Run a backtest and/or `python -m live.scheduler`.")

    if selected_backtest_metrics:
        st.subheader("Backtest metrics")
        st.table(pd.Series(selected_backtest_metrics, name="value").to_frame())

with tab_positions:
    if live_snapshots.empty:
        st.info("No live positions yet. Run `python -m live.scheduler` to populate this.")
    else:
        latest = live_snapshots.iloc[-1]
        positions = json.loads(latest["positions_json"])
        if not positions:
            st.info(f"No open positions as of {latest['date'].date()}.")
        else:
            pos_df = pd.DataFrame(
                [
                    {"ticker": t, "shares": s, "sector": TICKER_SECTOR.get(t, "Unknown")}
                    for t, s in positions.items()
                ]
            )
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Current positions")
                st.dataframe(pos_df, use_container_width=True)
            with col2:
                st.subheader("Sector exposure")
                sector_exposure = pos_df.groupby("sector")["shares"].sum()
                st.plotly_chart(
                    go.Figure(go.Bar(x=sector_exposure.index, y=sector_exposure.values)),
                    use_container_width=True,
                )

with tab_risk:
    if live_snapshots.empty and selected_backtest_equity is None:
        st.info("No equity history yet to compute rolling risk metrics from.")
    else:
        equity = (
            live_snapshots.set_index("date")["equity"]
            if not live_snapshots.empty
            else selected_backtest_equity
        )
        returns = equity.pct_change().dropna()
        if len(returns) < 5:
            st.info(
                "Not enough history yet for rolling Sharpe/drawdown/VaR (need at least a few days)."
            )
        else:
            drawdown = running_drawdown(equity)
            rolling_sharpe = (returns.rolling(21).mean() / returns.rolling(21).std()) * (252**0.5)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Rolling 21-day Sharpe")
                st.plotly_chart(
                    go.Figure(go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe.values))
                )
            with col2:
                st.subheader("Drawdown from peak")
                st.plotly_chart(
                    go.Figure(go.Scatter(x=drawdown.index, y=drawdown.values, fill="tozeroy"))
                )

            st.subheader("Value at Risk (95%, daily)")
            st.write(
                {
                    "historical_var": round(historical_var(returns), 4),
                    "parametric_var": round(parametric_var(returns), 4),
                }
            )

with tab_factors:
    st.info(
        "Per-holding factor score breakdown requires a fresh factor computation and is not "
        "cached here. Use notebooks/research.ipynb to inspect factor scores and IC/turnover "
        "diagnostics for the current universe."
    )
