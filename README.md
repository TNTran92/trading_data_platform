# spx-momentum — S&P 500 Cross-Sectional Momentum

Portfolio-grade **research demo** (NOT a production trading system; no live or
simulated orders): a scheduled, idempotent data pipeline ingesting S&P 500
daily bars into a Parquet/DuckDB lake, a 12-1 cross-sectional momentum
strategy (top-N monthly rotation), a **custom hand-written backtester** with
explicit cost/slippage modeling, and a Streamlit dashboard.

- **Design spec:** [`DESIGN-DOC.md`](DESIGN-DOC.md)
- **Scaffold plan:** [`docs/superpowers/plans/2026-10-05-spx-momentum-scaffold.md`](docs/superpowers/plans/2026-10-05-spx-momentum-scaffold.md)

## Status

Scaffold: every module exists as a typed placeholder (import-safe; test stubs
are explicit skips). Implementation proceeds task-by-task per the plan above.

## Layout

```
config/default.yaml         # config source of truth (env-overridable)
dags/momentum_dag.py        # THIN Airflow wrapper — no business logic
src/spx_momentum/
  config.py                 # Pydantic settings
  data/                     # store, universe, ingest, transform
  features/momentum.py      # 3/6/12-mo rolling returns, cross-sectional ranks
  strategy/                 # Strategy ABC + top-N signal
  backtest/                 # engine, costs, metrics, report (custom, hand-written)
  pipeline/tasks.py         # task_* functions — pure, explicit path I/O, no Airflow
  ui/dashboard.py           # Streamlit
tests/                      # deterministic, network-free
data/                       # gitignored lake (raw/, clean/, features/, positions/, results/)
artifacts/                  # gitignored outputs (report.md + plots)
```

## Quickstart

```
make sync        # uv sync --all-extras
make test        # pytest (network-free)
make lint        # ruff + mypy
make run-dag     # Airflow via docker compose
make dashboard   # Streamlit dashboard
```

## Guarantees (DESIGN-DOC §4.4–§4.5)

- **Deterministic:** backtest + report are pure functions of stored tables;
  rerunnable without network.
- **Idempotent:** every stage upserts into its own lake dir keyed by
  (ticker, date); safe reruns, no duplicate accumulation.
- **Isolated:** one dead ticker never fails the DAG; failures are recorded in
  a fetch manifest.
- **Honest:** survivorship bias + 12-1 lookback documented in
  `docs/methodology.md`; no live/paper trading, ever.
