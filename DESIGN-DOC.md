# Design: S&P 500 Cross-Sectional Momentum System

- **Date:** 2026-10-02
- **Status:** Proposed
- **Author:** ttran (with Hermes brainstorming session)

## 1. Purpose

A portfolio-grade demonstration project that proves the ability to build:

1. A real **data pipeline** — scheduled, orchestrated, idempotent — ingesting
   Yahoo Finance market data for the S&P 500 universe into a queryable store.
2. A real **trading system** — a clearly defined cross-sectional momentum
   strategy evaluated by a **custom-built backtesting engine** with explicit
   cost/slippage modeling and honest performance reporting.

This is a research/proof-of-capability project, not a production trading
system. It will not place, simulate placement of, or connect to real orders.

## 2. Goals / Non-Goals

**Goals**

- End-to-end pipeline: universe definition → ingest → clean → features →
  signal → backtest → report, orchestrated as a genuine Airflow DAG.
- One strategy executed correctly and defensibly: monthly cross-sectional
  momentum rotation on the S&P 500 (hold top-N by trailing return).
- Custom backtester (hand-written on pandas/numpy): portfolio construction,
  rebalancing, transaction cost + slippage model, and standard metrics
  (CAGR, Sharpe, Sortino, max drawdown, turnover, buy-and-hold benchmark).
- Deterministic, network-free test suite; hand-verifiable backtest math.
- Streamlit dashboard showing equity curve, drawdown, holdings over time,
  and rolling risk metrics.
- Professional repo hygiene: uv, ruff, mypy, pytest, pre-commit, CI.

**Non-Goals (explicitly out of scope)**

- Live or paper trading, broker integrations.
- Additional strategies, ML factor mining, multi-asset classes.
- Sub-daily (intraday) data — daily bars only.
- Subscriptions, multi-tenancy, production infra hardening.

## 3. Strategic Decisions (agreed in brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Depth | Portfolio demo — breadth and polish, one clean strategy | Strongest per-hour "I can build a system" signal |
| Strategy | Cross-sectional momentum, top-N monthly rotation | Natural fit for a 500-ticker pipeline; honest, defensible math |
| Strategy library | **Custom lightweight backtester** written by hand | Defensible core of the project; not just configuring a library |
| Universe | S&P 500 constituents (via Wikipedia list, date-stamped) | Strongest "real system" signal; moderate data volume |
| Data store | DuckDB over Parquet files (lake layout) | Zero-infra database semantics; honest pipeline story |
| **Orchestrator** | **Apache Airflow** (local dev; Docker Compose for server+worker) | Chosen for strongest data-engineering signal; tasks kept framework-agnostic so the DAG wrapper stays thin |
| UI | Streamlit | Fastest credible trading dashboard |
| Python | 3.12 pinned (`.python-version`) | Broadest compatibility for the stack; system 3.14 is too new for some wheels |

## 4. Architecture

### 4.1 High-level data flow

```
universe (spx500.csv, date-stamped)
   │
   ▼
[ingest] yfinance daily OHLCV → raw/          (Airflow task)
   │
   ▼
[transform] dedupe, gap check, adjust prices, align calendars → clean/
   │
   ▼
[features] trailing 3/6/12-mo returns, rank scores → features/
   │
   ▼
[signal] monthly rebalance: rank → top-N → target weights → positions/
   │
   ▼
[backtest] custom engine + cost model → results (equity curve, trades)
   │
   ▼
[report + dashboard] metrics summary, plots, Streamlit app
```

Every bracketed stage is one **task function** with explicit typed I/O,
wired into an Airflow DAG. Task functions live in
`src/spx_momentum/pipeline/tasks.py` and are pure Python (no Airflow
imports), so they are directly unit-testable and portable.

### 4.2 Components

**Config (`src/spx_momentum/config.py`)**
Pydantic settings loaded from `config/default.yaml` (overridable by env).
Holds: universe source, N (default 20), lookback months (default 12,
skipping the most recent 1 month — classic 12-1 momentum), rebalance
schedule (last trading day of month), transaction cost bps, slippage bps,
data paths.

**Data layer (`src/spx_momentum/data/`)**
- `universe.py` — fetch S&P 500 constituents (Wikipedia), validate
  (tickers well-formed, count in [480, 530]), snapshot with fetch date.
- `ingest.py` — yfinance download with chunking, per-ticker retry (3x,
  exponential backoff), partial-failure tolerance, writes raw Parquet.
  Records fetch metadata (timestamp, rows, null counts) per ticker.
- `transform.py` — validation (null ratios, date coverage, bad bars),
  use adjusted close, align all tickers to a common trading calendar,
  upsert into clean Parquet keyed by (ticker, date) — idempotent.
- `store.py` — thin DuckDB/Parquet read/write helpers shared by all stages.

**Pipeline (`src/spx_momentum/pipeline/`)**
- `tasks.py` — task functions (universe, ingest, transform, features,
  signal, backtest, report). Each takes and returns explicit data paths
  (file-based passing — no shared in-memory state between tasks, so tasks
  are independently rerunnable and inspectable).
- The Airflow DAG lives in the top-level `dags/` folder (Airflow's
  conventional DAG location) and only imports the package's task functions:
  `dags/momentum_dag.py` — Airflow DAG: schedule, task dependencies,
  retries (2) with backoff on network stages, `execution_timeout` /
  `retry_delay`, tags. Thin: it only wires task functions.
- Compose: `docker compose up` → Airflow webserver + scheduler + worker
  (or local in-process scheduler for simplest dev: `airflow standalone`).

**Features (`src/spx_momentum/features/momentum.py`)**
Compute rolling returns (3/6/12 months, 1-month skip), rank cross-section,
emit per-date score tables. Pure pandas; deterministic.

**Strategy (`src/spx_momentum/strategy/`)**
- `base.py` — `Strategy` ABC: `generate_target_weights(prices, features, as_of) -> PositionSet`.
- `signal.py` — top-N selection, equal weights, rebalance only on schedule
  dates, produces (date, ticker, weight) tables.

**Backtest (`src/spx_momentum/backtest/`)**
- `engine.py` — custom engine: on each rebalance date, compute turnover
  vs previous weights, apply cost model to the traded notional, hold
  weights, mark-to-market daily between rebalances. Returns: equity curve,
  trade log, exposure.
- `costs.py` — proportional cost bps + slippage bps, applied one-way on
  turnover; configurable.
- `metrics.py` — CAGR, annualized vol, Sharpe, Sortino, max drawdown
  (and date), Calmar, turnover, win rate on rebalance periods,
  vs equal-weight S&P 500 (SPY) benchmark.
- `report.py` — writes human-readable `artifacts/report.md` + equity
  curve + drawdown + top-10 holdings-heatmap (matplotlib, no JS deps).

**UI (`src/spx_momentum/ui/dashboard.py`)**
Streamlit app reading artifacts + Parquet: equity curve vs benchmark
(toggle), drawdown band, metrics table, holdings-over-time selection,
parameter re-run (N, lookback, costs) that executes the backtest in-process
for a "what-if" mode.

### 4.3 Repo layout

```
spx-momentum/
  pyproject.toml            # uv-managed; ruff/mypy/pytest config inline
  .python-version           # 3.12
  Makefile                  # sync, test, lint, run-dag, dashboard
  Dockerfile (app), docker-compose.yaml  # airflow standalone profile
  dags/momentum_dag.py      # thin DAG importing package tasks
  config/default.yaml
  data/                     # gitignored lake: raw/, clean/, features/, positions/, results/
  src/spx_momentum/         # package per §4.2
  tests/                    # unit + one end-to-end smoke (synthetic data)
  docs/superpowers/specs/   # this design doc
  docs/methodology.md       # how it works, biases (survivorship, lookback), caveats
  artifacts/                # gitignored outputs
  .github/workflows/ci.yml  # lint + test
  .gitignore, README.md
```

### 4.4 Error handling & idempotency

- Every stage writes to its own lake directory keyed by (ticker, date)
  with upsert semantics → safe reruns, no duplicate accumulation.
- Network stages: retries with exponential backoff; per-ticker isolation
  (one dead ticker never fails the DAG; failures logged to a fetch-manifest
  table the pipeline reports on).
- Validation gates: transform refuses to emit if a ticker's null-ratio or
  date coverage exceeds thresholds (configurable); a failed gate fails the
  task loudly rather than silently propagating bad data.
- Backtest/report are pure functions of stored tables → rerunnable
  deterministically without network.

### 4.5 Testing strategy

- **No network in tests.** yfinance is monkeypatched; the universe CSV is
  a fixture. A deterministic synthetic price generator (seeded, 3-5
  tickers, multi-year, with engineered trends) drives feature/signal/
  backtest tests so results are hand-verifiable.
- **Key invariants asserted:**
  - Top-N selection picks the actual top performers on synthetic data.
  - Rebalance occurs only on schedule dates; weights sum to 1 before costs.
  - A pure no-cost run's equity curve equals the hand-computed geometric
    product of held returns (exact match within float tol).
  - Adding 10 bp cost strictly reduces terminal value; the delta matches
    the turnover-weighted cost model.
  - Sharpe/Sortino/max-drawdown match closed-form hand calculations on a
    6-observation toy series.
- **End-to-end smoke:** full task-function chain (no Airflow) on the
  synthetic universe; asserts every lake stage produces consistent row
  counts.
- DAG wiring itself is smoke-checked by importing and asserting task
  dependencies (Airflow programmatic-API test).

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| yfinance rate limiting on 503 tickers | Chunked downloads (≈25/ticker calls or bulk download), per-ticker retry + backoff, caching raw data so reruns don't refetch |
| Wikipedia universe scrape format changes | Pinned parsing with strict validation; snapshot CSV committed into git as the fallback |
| Survivorship bias (constituence list is today's) | Documented explicitly in methodology.md as a known limitation; noted in report |
| Python 3.14 wheel gaps (system) | Pin 3.12 via uv/`.python-version`; no reliance on system Python deps |
| Airflow local friction (env vars, alembic) | Provide `Makefile` one-command `airflow standalone` profile; Docker Compose as alternative |
| Over-polish / scope creep | Non-goals above are hard limits; YAGNI enforced in plan |

## 6. Skills being built (learning outcomes)

1. Data-pipeline & orchestration (tasks, DAGs, retries, idempotency) — Airflow
2. Analytical storage: Parquet lake + DuckDB SQL from Python
3. Custom quantitative backtesting math: portfolio construction, cost
   modeling, Sharpe/Sortino/drawdown from first principles
4. Cross-sectional momentum strategy design & 12-1 lookback conventions
5. Deterministic testing of data/quant code with synthetic fixtures
6. Python packaging/professional tooling: uv, ruff, mypy, pre-commit, CI
7. Streamlit dashboarding of quantitative results
8. yfinance data quirks: adjusted prices, rate limits, missing bars

## 7. Effort estimate

| Phase | Work | Hours |
|---|---|---|
| 0 | Repo, uv, ruff, mypy, pytest, pre-commit, CI | 4–8 |
| 1 | Data pipeline (universe→ingest→transform→store) + Airflow wiring | 18–32 |
| 2 | Momentum features + strategy signal + rebalance logic | 8–16 |
| 3 | Custom backtest engine + cost model + metrics (core) | 24–40 |
| 4 | Report + Streamlit dashboard + methodology doc | 16–24 |
| 5 | Polish: README, plots, E2E run, demo script | 8–16 |
| | **Total** | **≈ 100–135 h** |

Rhythm options: part-time ~10 h/week → 2.5–3.5 months; full-time → 3–5 weeks.

Milestones (in order, each independently demonstrable):
1. Single ticker ingested → validated → queryable in DuckDB.
2. Full universe pipeline green + DAG run clean on Airflow.
3. First backtest with cost model + hand-verified metrics.
4. Dashboard tells the full story with a "what-if" rerun.
