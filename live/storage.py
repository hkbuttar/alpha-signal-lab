"""SQLite logging for the live paper-trading loop.

Every order, fill, and daily portfolio snapshot is logged here for later
analysis and for the dashboard to read from. No ORM: the schema is small and
stable enough that raw SQL is more legible than an abstraction over it.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "trading.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    shares REAL NOT NULL,
    submitted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    shares REAL NOT NULL,
    price REAL NOT NULL,
    commission REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    equity REAL NOT NULL,
    cash REAL NOT NULL,
    positions_json TEXT NOT NULL
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def log_order(
    conn: sqlite3.Connection, date: str, ticker: str, shares: float, submitted_at: str
) -> None:
    conn.execute(
        "INSERT INTO orders (date, ticker, shares, submitted_at) VALUES (?, ?, ?, ?)",
        (date, ticker, shares, submitted_at),
    )
    conn.commit()


def log_fill(
    conn: sqlite3.Connection, date: str, ticker: str, shares: float, price: float, commission: float
) -> None:
    conn.execute(
        "INSERT INTO fills (date, ticker, shares, price, commission) VALUES (?, ?, ?, ?, ?)",
        (date, ticker, shares, price, commission),
    )
    conn.commit()


def log_snapshot(
    conn: sqlite3.Connection, date: str, equity: float, cash: float, positions: dict[str, float]
) -> None:
    conn.execute(
        """INSERT INTO portfolio_snapshots (date, equity, cash, positions_json)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET equity=excluded.equity, cash=excluded.cash,
               positions_json=excluded.positions_json""",
        (date, equity, cash, json.dumps(positions)),
    )
    conn.commit()


def read_snapshots(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM portfolio_snapshots ORDER BY date", conn)


def read_fills(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM fills ORDER BY date", conn)


def read_orders(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM orders ORDER BY date", conn)
