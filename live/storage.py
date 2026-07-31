"""Postgres logging for the live paper-trading loop.

Every order, fill, and daily portfolio snapshot is logged here for later
analysis and for the dashboards (Streamlit and the FastAPI backend behind the
React dashboard) to read from. No ORM: the schema is small and stable enough
that raw SQL is more legible than an abstraction over it.

Connects via ``DATABASE_URL`` (Render's standard convention for its managed
Postgres). This is shared, persistent storage reachable from the GitHub
Actions scheduler, the FastAPI backend, and a local Streamlit process alike,
which is the whole point: a local SQLite file can't be reached from all three.
"""

from __future__ import annotations

import os

import pandas as pd
import psycopg
from psycopg.types.json import Json

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker TEXT NOT NULL,
    shares DOUBLE PRECISION NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker TEXT NOT NULL,
    shares DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    equity DOUBLE PRECISION NOT NULL,
    cash DOUBLE PRECISION NOT NULL,
    positions_json JSONB NOT NULL
);
"""


def get_connection() -> psycopg.Connection:
    """Connect using DATABASE_URL and ensure the schema exists."""
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.commit()
    return conn


def log_order(
    conn: psycopg.Connection, date: str, ticker: str, shares: float, submitted_at: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO orders (date, ticker, shares, submitted_at) VALUES (%s, %s, %s, %s)",
            (date, ticker, shares, submitted_at),
        )
    conn.commit()


def log_fill(
    conn: psycopg.Connection, date: str, ticker: str, shares: float, price: float, commission: float
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fills (date, ticker, shares, price, commission) "
            "VALUES (%s, %s, %s, %s, %s)",
            (date, ticker, shares, price, commission),
        )
    conn.commit()


def log_snapshot(
    conn: psycopg.Connection, date: str, equity: float, cash: float, positions: dict[str, float]
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO portfolio_snapshots (date, equity, cash, positions_json)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (date) DO UPDATE SET equity = excluded.equity, cash = excluded.cash,
                   positions_json = excluded.positions_json""",
            (date, equity, cash, Json(positions)),
        )
    conn.commit()


def _fetch_df(conn: psycopg.Connection, query: str) -> pd.DataFrame:
    # Not pd.read_sql_query: pandas only recognizes SQLAlchemy engines and
    # sqlite3 connections as "supported" DBAPI2 objects and warns on anything
    # else (including psycopg3, despite it working correctly) - fetching
    # manually avoids that noise without pulling in SQLAlchemy for one query.
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        columns = [col.name for col in cur.description]
    return pd.DataFrame(rows, columns=columns)


def read_snapshots(conn: psycopg.Connection) -> pd.DataFrame:
    return _fetch_df(conn, "SELECT * FROM portfolio_snapshots ORDER BY date")


def read_fills(conn: psycopg.Connection) -> pd.DataFrame:
    return _fetch_df(conn, "SELECT * FROM fills ORDER BY date")


def read_orders(conn: psycopg.Connection) -> pd.DataFrame:
    return _fetch_df(conn, "SELECT * FROM orders ORDER BY date")
