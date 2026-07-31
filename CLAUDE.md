# CLAUDE.md

Working context for Claude Code in this repo. Full methodology, architecture, and results live in `README.md` — don't duplicate that here, just point to it.

## What this is
Event-driven factor research and paper-trading platform for systematic equities. See `README.md` for methodology.

## Commands

```bash
# Install deps
python3.11 -m pip install -r requirements.txt --break-system-packages

# Run tests
pytest tests/

# Lint
ruff check .

# Format
ruff format .

# Run a backtest
python -m backtest.engine --start 2020-01-01 --end 2025-01-01

# Run factor research notebook
jupyter notebook notebooks/research.ipynb

# Start live paper trading scheduler
python -m live.scheduler

# Launch dashboard
streamlit run dashboard/app.py
```

## Environment
- Python 3.11. Always install packages with `python3.11 -m pip install <pkg> --break-system-packages`, not plain `pip`.
- Required env vars (see `.env.example`): `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL` (paper endpoint), `NEWSAPI_KEY`, `LLM_API_KEY`.
- Never commit `.env` or any real API keys.

## Repo map
- `data/` — data loaders (price + news). New data sources go here.
- `factors/` — one file per factor. New factors must follow the interface in `composite.py` (take a price/news panel, return a cross-sectional score per ticker per day).
- `backtest/` — event-driven simulator. Must stay bar-by-bar / point-in-time; no vectorized shortcuts that could introduce look-ahead bias.
- `risk/` — position sizing and kill-switch logic.
- `live/` — Alpaca order execution and scheduling.
- `dashboard/` — Streamlit app.
- `notebooks/` — research notebooks, keep outputs committed (pre-executed).
- `tests/` — mirrors the module structure above.

## Boundaries — do not touch without explicit confirmation
- `live/alpaca_client.py` — places real (paper) orders. Any change to order logic, sizing, or execution triggers needs a human review before merging, even though it's paper money.
- `risk/kill_switch.py` — drawdown safety logic. Treat changes here as high-stakes; don't loosen thresholds without being asked directly.
- `.env` / any credentials file.

## Conventions
- Type hints on all function signatures.
- Docstrings (Google style) on every factor and every public function in `backtest/` and `risk/`.
- No em dashes in docstrings, comments, or generated markdown.
- New factors: add the function, add a unit test in `tests/factors/`, and add one line to the Factor Methodology table in `README.md` — don't leave a factor undocumented.

## Definition of done
- All changes touching `backtest/`, `factors/`, or `risk/` must pass `pytest tests/` before being considered complete.
- Any change to live trading logic (`live/`) should be run once against paper trading and confirmed not to error before merging.