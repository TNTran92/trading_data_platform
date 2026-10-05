# S&P 500 Cross-Sectional Momentum — Project Scaffold Plan

> **For agentic workers:** This is a **scaffold plan** (pseudocode level, per the user's
> explicit request — no serious coding yet). It defines the repo layout, the module
> boundaries, and each stage's interface (names + types). When it is executed, each task
> should land a working, importable, empty-or-stubbed file so the whole package type-checks
> and the smoke test imports green. Keep every body pseudocode until a task is promoted to
> real implementation.

**Goal:** Scaffold the full `spx-momentum` repo — repo hygiene, config, data pipeline,
strategy, custom backtester, report + dashboard, and a network-free test harness — so that
every module exists, has a typed interface, and imports cleanly.

**Architecture:** A single Python package `spx_momentum` with file-based task passing
(every stage reads/writes Parquet in a lake layout, no in-memory handoff), wrapped by one
thin Airflow DAG. A hand-written pandas/numpy backtester sits downstream of the strategy.
Streamlit reads the artifacts.

**Tech Stack:** Python 3.12 (uv, pinned via `.python-version`), pandas/numpy, DuckDB +
Parquet, Pydantic, yfinance, Airflow (Docker Compose / `airflow standalone`), Streamlit,
matplotlib, pytest, ruff, mypy, pre-commit.

**Spec:** `DESIGN-DOC.md` (repo root). This plan scaffolds §4 (architecture + repo layout),
§4.4 (idempotency), and §4.5 (test strategy skeleton).

## Global Constraints (copied verbatim from the spec)

- Python **3.12** pinned (`.python-version`); no reliance on system Python 3.14 wheels.
- Strategy: cross-sectional momentum, **top-N monthly rotation, N default 20**, lookback
  **12 months skip 1** (classic 12-1). Rebalance on **last trading day of month**.
- Data store: **DuckDB over Parquet** in a lake layout: `data/` → `raw/`, `clean/`,
  `features/`, `positions/`, `results/`.
- Transaction cost bps + slippage bps are **configurable**, applied one-way on turnover.
- **No network in tests** (yfinance monkeypatched; universe is a fixture).
- Daily bars only; no intraday. No live/paper trading; no broker integrations.
- Package is framework-agnostic: task functions in `src/spx_momentum/pipeline/tasks.py`
  have **no Airflow imports** and pass explicit file paths (file-based I/O).
- Each stage writes to its own lake dir keyed by **(ticker, date)** with **upsert** semantics
  → idempotent, safe reruns.

## Review Focus (failure modes the spec implies but a scaffold won't yet exercise)

- **A single dead ticker must never fail the DAG** → ingest isolates per-ticker; scaffold
  the `FetchManifest` type now so the isolation contract is visible.
- **Transform must fail loudly (not propagate bad data)** → a failed validation gate raises;
  scaffold `ValidationGateError` + the gate signature.
- **Top-N selection picks the actual top performers** → the invariant test owns this; scaffold
  the `PositionSet` shape so the test can assert it.
- **No-cost equity curve must equal the hand-computed geometric product** → scaffold the
  `BacktestResult` + `run_backtest` signature so the exact-match test has a target.
- **Rebalance only on schedule dates; weights sum to 1 before costs** → scaffold
  `generate_positions` + `Strategy.generate_target_weights` signatures.

---

## File Structure (decomposition locked here)

```
trading_data_platform/                       # == repo root (a.k.a. spx-momentum/)
  pyproject.toml            # uv-managed; deps + ruff/mypy/pytest config inline
  .python-version           # 3.12
  .gitignore                # data/, artifacts/, .venv/, __pycache__
  README.md                 # how to sync/test/run-dag/dashboard
  Makefile                  # sync, test, lint, run-dag, dashboard
  docker-compose.yaml       # airflow webserver + scheduler + (worker)
  dags/
    momentum_dag.py         # THIN: imports package task fns, wires deps + retries
  config/
    default.yaml            # cfg defaults (N, lookback, cost/slip bps, paths)
  data/                     # gitignored lake (created at runtime)
  src/spx_momentum/
    __init__.py
    config.py               # Pydantic settings <- config/default.yaml (env-overridable)
    data/
      __init__.py
      store.py              # LakeStore: DuckDB/Parquet upsert + read + sql
      universe.py           # fetch / validate / snapshot
      ingest.py             # chunked yfinance + per-ticker retry + manifest
      transform.py          # validate gate + align calendar + upsert clean
    features/
      __init__.py
      momentum.py           # rolling returns + cross-sectional rank
    strategy/
      __init__.py
      base.py               # Strategy ABC
      signal.py             # top-N, equal weight, schedule-gated
    backtest/
      __init__.py
      costs.py              # proportional bps + slippage
      engine.py             # turn over, hold, mark-to-market
      metrics.py            # CAGR/Sharpe/Sortino/MaxDD/Calmar/turnover/winrate
      report.py             # report.md + plots -> artifacts/
    pipeline/
      __init__.py
      tasks.py              # task_* fns: explicit typed path I/O, no Airflow
    ui/
      __init__.py
      dashboard.py          # Streamlit app
  tests/
    __init__.py
    conftest.py             # synthetic_price_generator() + universe fixture + tmp lake
    test_universe.py
    test_ingest.py          # yfinance monkeypatched
    test_transform.py
    test_features.py
    test_strategy.py
    test_backtest_engine.py
    test_backtest_costs.py
    test_metrics.py
    test_e2e_smoke.py
    test_dag_wiring.py
  docs/
    methodology.md          # survivorship bias, lookback caveats, cost model
```

One clear responsibility per file; split by stage/responsibility, not by tech layer. Task
functions and Airflow wiring are separated (thin DAG, portable tasks). Tests live beside the
stage they own; `conftest.py` owns the shared synthetic fixture.

---

## Task 1: Repo hygiene + package skeleton

**Files:**
- Create: `.python-version`, `pyproject.toml`, `.gitignore`, `README.md`, `Makefile`
- Create: `src/spx_momentum/__init__.py` and the `__init__.py` of every subpackage listed above.

**Interfaces:**
- Produces: an importable package `spx_momentum` (all subpackages present, empty-but-valid).
- Pins: `pyproject.toml` `[tool.uv]`-managed deps: `pandas`, `numpy`, `duckdb`, `pydantic`,
  `pydantic-settings`, `yfinance`, `pyyaml`, `streamlit`, `matplotlib`,
  `[dev]` `pytest`, `ruff`, `mypy`, `pre-commit`, `apache-airflow`.

**Pseudocode (what "done" looks like):**
```
.python-version:               "3.12"

pyproject.toml:                name="spx-momentum", requires-python=">=3.12,<3.13"
                               [project.scripts] spx-dashboard = "spx_momentum.ui.dashboard:main"
                               [tool.ruff] line-length=100, select=[E,F,I,UP,B]
                               [tool.mypy] python_version=3.12, strict=true
                               [tool.pytest.ini_options] testpaths=["tests"]

Makefile:
  sync    : uv sync
  test    : uv run pytest
  lint    : uv run ruff check . && uv run mypy src
  run-dag : docker compose up airflow  (or: make airflow-standalone)
  dashboard : uv run streamlit run src/spx_momentum/ui/dashboard.py

__init__.py per subpackage:    empty (or a one-line docstring)
```
**Definition of done:** `uv sync` succeeds; `uv run python -c "import spx_momentum"` is clean;
`uv run ruff check .` and `uv run mypy src` pass on the (empty) skeleton.

---

## Task 2: Config

**Files:**
- Create: `src/spx_momentum/config.py`, `config/default.yaml`, `tests/test_config.py`

**Interfaces:**
- Produces: `settings: Settings` (module-level singleton) and
  `def load_settings(path: str | None = None, **overrides) -> Settings`.
- Consumes: nothing.
- `Settings` fields (typed): `universe_source: str`, `top_n: int = 20`,
  `lookback_months: int = 12`, `skip_months: int = 1`,
  `rebalance: str = "last_trading_day"`, `cost_bps: float`, `slippage_bps: float`,
  `data_root: Path`, `artifacts_dir: Path`,
  `null_ratio_max: float`, `coverage_min: float`,
  `fetch_chunk_size: int = 25`, `fetch_retries: int = 3`, `fetch_backoff_s: float`.

**Pseudocode:**
```
class Settings(pydantic_settings.BaseSettings):
    top_n: int = 20
    lookback_months: int = 12
    skip_months: int = 1
    cost_bps: float = 5.0
    slippage_bps: float = 5.0
    data_root: Path = Path("data")
    ...
def load_settings(path=None, **overrides):
    base = yaml.safe_load(default_yaml)
    merged = {**base, **overrides}
    return Settings(**merged)
settings = load_settings()
```
**Definition of done:** `load_settings()` returns a valid `Settings` from `config/default.yaml`;
an env var / kwarg override wins; a missing required field raises a typed Pydantic error.

---

## Task 3: Data store (`store.py`)

**Files:**
- Create: `src/spx_momentum/data/store.py`, `tests/test_store.py`

**Interfaces:**
- Produces: `class LakeStore`:
  - `__init__(self, root: Path)`
  - `write_upsert(df: pd.DataFrame, stage: Stage, key_cols: tuple[str, str]) -> Path`
  - `read(stage: Stage) -> pd.DataFrame`
  - `sql(query: str) -> pd.DataFrame`
  - `close() -> None`
- Enums: `Stage = Enum{RAW, CLEAN, FEATURES, POSITIONS, RESULTS}`.
- Consumes: `Settings.data_root`.

**Pseudocode:**
```
class LakeStore:
    def __init__(self, root):        self.root = root; self._conn = duckdb.connect()
    def write_upsert(self, df, stage, key_cols=("ticker","date")):
        # partition by stage dir; upsert = read existing, merge on key_cols, write back
        # idempotent: rerunning with same df yields same rows (no dupes)
    def read(self, stage):           # select * from <stage>.parquet
    def sql(self, q):                # returns df via duckdb
```
**Definition of done:** write-then-read roundtrip is stable; upserting the same frame twice
leaves row count unchanged; `sql("select count(*) ...")` works against a written stage.

---

## Task 4: Universe (`universe.py`)

**Files:**
- Create: `src/spx_momentum/data/universe.py`, `tests/test_universe.py`

**Interfaces:**
- Produces:
  - `def fetch_universe(source: str) -> pd.DataFrame`  # columns: ticker (str)
  - `def validate_universe(df: pd.DataFrame) -> None`  # raises on bad shape
  - `def snapshot_universe(df: pd.DataFrame, path: Path, fetch_date: date) -> Path`
- Consumes: `Settings.universe_source`.
- Contract: `validate_universe` raises `UniverseValidationError` if any ticker is not
  well-formed (uppercase alnum, `.`/`-` allowed) or if `not (480 <= len(df) <= 530)`.

**Pseudocode:**
```
def fetch_universe(source):
    if source == "wikipedia":        # pin a parsing fn; strict column expectation
        return parse_wikipedia_spx500(html)   # -> DataFrame[ticker]
    else:                            # fallback: committed CSV snapshot in git
        return pd.read_csv(source)[["ticker"]]
def validate_universe(df):
    assert df["ticker"].notna().all()
    if not df["ticker"].str.fullmatch(r"[A-Z]{1,6}[.-]?[A-Z]{0,3}").all(): raise UniverseValidationError
    if not (480 <= len(df) <= 530):   raise UniverseValidationError
def snapshot_universe(df, path, fetch_date):
    df.assign(fetched=fetch_date).to_csv(path)     # committed fallback
    return path
```
**Definition of done:** a well-formed 500-row frame validates; a 501-off-by-one or a lowercase
ticker raises `UniverseValidationError`; snapshot writes a CSV with a `fetched` column.

---

## Task 5: Ingest (`ingest.py`) — the isolation contract lives here

**Files:**
- Create: `src/spx_momentum/data/ingest.py`, `tests/test_ingest.py`

**Interfaces:**
- Produces:
  - `@dataclass FetchRecord: ticker, ok: bool, rows: int, nulls: int, ts: datetime, error: str|None`
  - `def ingest(tickers: pd.DataFrame, start: date, end: date, store: LakeStore, cfg: Settings) -> list[FetchRecord]`
- Consumes: `LakeStore.write_upsert`, `Settings.fetch_*`.
- Contract: **one failed ticker never raises out of `ingest`**; failures are captured as a
  `FetchRecord(ok=False)` row. Returns one record per ticker (including failures).

**Pseudocode:**
```
def _download_chunk(chunk: list[str], start, end) -> dict[str, px_df]:
    # yfinance.download(chunk, start, end, auto_adjust=True)  # ~25/call
    # per-ticker retry: for attempt in range(cfg.fetch_retries):
    #     try: ... return  except TransientError: sleep(cfg.fetch_backoff_s * 2**attempt)
def ingest(tickers, start, end, store, cfg):
    records = []
    for chunk in chunked(tickers["ticker"], cfg.fetch_chunk_size):
        data = _download_chunk(chunk, start, end)
        for t in chunk:
            if t in data and data[t].notna().any().any():
                store.write_upsert(with_ticker(data[t]), Stage.RAW, ("ticker","date"))
                records.append(FetchRecord(t, True, len(data[t]), nulls, now, None))
            else:
                records.append(FetchRecord(t, False, 0, 0, now, "no data / transient"))
    return records                      # never raises for a single bad ticker
```
**Definition of done:** with yfinance monkeypatched, a batch where ticker #37 returns an
exception still yields N records, one `ok=False` for #37, and the rest `ok=True`; the raw
stage contains the good tickers only.

---

## Task 6: Transform (`transform.py`) — the validation gate lives here

**Files:**
- Create: `src/spx_momentum/data/transform.py`, `tests/test_transform.py`

**Interfaces:**
- Produces:
  - `class ValidationGateError(Exception)` carrying `(ticker, metric, value, limit)`
  - `def transform(raw: pd.DataFrame, store: LakeStore, cfg: Settings) -> pd.DataFrame`
- Consumes: `Stage.RAW`, `Stage.CLEAN`, `Settings.null_ratio_max`, `Settings.coverage_min`.
- Contract: uses **adjusted close**; aligns all tickers to a **common trading calendar**
  (the union/intersection per cfg); upserts clean keyed by (ticker, date); **raises
  `ValidationGateError`** if any ticker's null-ratio > `null_ratio_max` or date-coverage
  < `coverage_min` (fails loudly, does not propagate bad rows).

**Pseudocode:**
```
def transform(raw, store, cfg):
    cal = trading_calendar(raw["date"])                  # common axis
    for ticker, g in raw.groupby("ticker"):
        g = g.set_index("date").reindex(cal)
        null_ratio = g["adj_close"].isna().mean()
        coverage   = g["adj_close"].notna().mean()
        if null_ratio > cfg.null_ratio_max:  raise ValidationGateError(ticker,"null_ratio",null_ratio,cfg.null_ratio_max)
        if coverage < cfg.coverage_min:      raise ValidationGateError(ticker,"coverage",coverage,cfg.coverage_min)
        clean = g[["adj_close"]]                        # + OHLCV if needed
    store.write_upsert(clean_all, Stage.CLEAN, ("ticker","date"))
    return clean_all
```
**Definition of done:** a ticker with 40% nulls (limit 20%) makes `transform` raise
`ValidationGateError` naming the ticker + metric; a clean frame upserts idempotently to CLEAN.

---

## Task 7: Momentum features (`features/momentum.py`)

**Files:**
- Create: `src/spx_momentum/features/momentum.py`, `tests/test_features.py`

**Interfaces:**
- Produces:
  - `def rolling_returns(prices: pd.DataFrame, months=(3,6,12), skip_months=1) -> pd.DataFrame`
  - `def cross_sectional_scores(ret: pd.DataFrame) -> pd.DataFrame`  # per date, rank in [0,1]
  - `def build_features(prices: pd.DataFrame, store: LakeStore, cfg: Settings) -> pd.DataFrame`
- Consumes: `Stage.CLEAN`, `Stage.FEATURES`.
- Contract: `skip_months=1` drops the most recent month from each window (classic 12-1);
  output is per-date score tables, deterministic, pure pandas.

**Pseudocode:**
```
def rolling_returns(prices, months=(3,6,12), skip_months=1):
    out = {}
    for m in months:
        end = prices.shift(m*skip_months)            # drop last `skip` month
        start = prices.shift(m*(1+skip_months))
        out[f"ret_{m}m"] = end / start - 1
    return pd.DataFrame(out)
def cross_sectional_scores(ret):
    combined = (ret["ret_12m"].rank(pct=True) * .5 + ret["ret_6m"].rank(pct=True) * .3
                + ret["ret_3m"].rank(pct=True) * .2)
    return combined                                   # per date, per ticker score
def build_features(prices, store, cfg):
    px = prices[["adj_close"]].unstack()             # index=date, cols=ticker
    scores = cross_sectional_scores(rolling_returns(px, (3,6,12), cfg.skip_months))
    store.write_upsert(scores.reset_index().melt(...), Stage.FEATURES, ...)
    return scores
```
**Definition of done:** with a seeded synthetic price frame, `rolling_returns` uses the
skipped month boundary correctly; scores are a per-date cross-section and are reproducible
across two runs.

---

## Task 8: Strategy base + signal (`strategy/`)

**Files:**
- Create: `src/spx_momentum/strategy/base.py`, `src/spx_momentum/strategy/signal.py`,
  `tests/test_strategy.py`

**Interfaces:**
- Produces:
  - `@dataclass PositionSet: dates: list[date], weights: pd.DataFrame`  # index=date, cols=ticker
  - `class Strategy(abc.ABC)`: `@abstractmethod generate_target_weights(self, prices, features, as_of: date) -> PositionSet`
  - `class MomentumStrategy(Strategy)`
  - `def select_top_n(scores_row: pd.Series, n: int) -> list[str]`
  - `def equal_weights(tickers: list[str]) -> tuple[float]`  # sums to 1.0
- Consumes: `Settings.top_n`, `Settings.rebalance`.
- Contract: rebalance **only on schedule dates** (last trading day of month); weights sum to
  **1.0 before costs**; on non-schedule dates it carries the last PositionSet forward.

**Pseudocode:**
```
class Strategy(ABC):
    @abstractmethod
    def generate_target_weights(self, prices, features, as_of) -> PositionSet: ...
def select_top_n(row, n):
    return row.dropna().nlargest(n).index.tolist()
def equal_weights(tickers):
    w = 1.0/len(tickers);  return [w]*len(tickers)
class MomentumStrategy(Strategy):
    def __init__(self, cfg): self.cfg = cfg
    def generate_target_weights(self, prices, features, as_of):
        sched = months_end(features.index)
        pos = {}
        for d in features.index:
            if d in sched:
                top = select_top_n(features.loc[d], self.cfg.top_n)
                pos[d] = equal_weights(top)           # -> 1.0
            # else: inherit prior pos (no trading)
        return PositionSet(sorted(pos), pd.DataFrame(pos))
```
**Definition of done:** on the synthetic features, selection picks the actual top performers;
`weights.loc[d].sum() == 1.0` (within float tol) on every schedule date; no PositionSet changes
on non-schedule dates.

---

## Task 9: Backtest — costs (leaf)

**Files:**
- Create: `src/spx_momentum/backtest/costs.py`, `tests/test_backtest_costs.py`

**Interfaces:**
- Produces:
  - `def apply_costs(notional: float, cost_bps: float, slippage_bps: float) -> float`
    # returns total cost = notional * (cost_bps + slippage_bps) / 10_000 (one-way, on traded notional)
- Consumes: `Settings.cost_bps`, `Settings.slippage_bps`.

**Pseudocode:**
```
def apply_costs(notional, cost_bps=5.0, slippage_bps=5.0):
    return notional * (cost_bps + slippage_bps) / 1e4
```
**Definition of done:** `apply_costs(1_000_000, 5, 5) == 1_000` exactly (within float tol);
zero bps → 0.0.

---

## Task 10: Backtest — engine

**Files:**
- Create: `src/spx_momentum/backtest/engine.py`, `tests/test_backtest_engine.py`

**Interfaces:**
- Produces:
  - `@dataclass BacktestResult: equity_curve: pd.Series, trade_log: pd.DataFrame, exposure: pd.Series, terminal_value: float`
  - `def run_backtest(prices: pd.DataFrame, positions: PositionSet, cfg: Settings) -> BacktestResult`
- Consumes: `PositionSet`, `Settings` (cost/slip bps), `apply_costs`.
- Contract: on each **rebalance date** compute `turnover = 0.5*Σ|w_new − w_old|`, apply
  `apply_costs` to `turnover * current equity`; **hold** weights and **mark-to-market daily**
  between rebalances. No-cost run's equity must equal the hand-computed geometric product of
  held returns (exact, within float tol).

**Pseudocode:**
```
@dataclass
class BacktestResult:
    equity_curve: pd.Series          # indexed by date
    trade_log:   pd.DataFrame        # (date, ticker, weight_before, weight_after, cost)
    exposure:    pd.Series
    terminal_value: float
def run_backtest(prices, positions, cfg):
    equity = 1.0
    curve, trades = [], []
    w_prev = pd.Series(dtype=float)
    for d in positions.dates:
        w_new = positions.weights.loc[d]
        turnover = 0.5*(w_new.sub(w_prev, fill_value=0)).abs().sum()
        cost = apply_costs(turnover * equity, cfg.cost_bps, cfg.slippage_bps)
        equity *= (1 - turnover*(cfg.cost_bps+cfg.slippage_bps)/1e4)   # cost drag
        equity *= held_return(prices, d, w_new)                         # mark-to-market
        curve.append((d, equity)); trades.append(log(d, w_prev, w_new, cost))
        w_prev = w_new
    return BacktestResult(pd.Series(curkey...), pd.DataFrame(trades), exposure, equity)
```
**Definition of done:** a **0 bp** backtest's equity equals `∏ (1 + held_return)` over the
same held periods (assert equal within 1e-9); adding any bps strictly lowers
`terminal_value`.

---

## Task 11: Backtest — metrics

**Files:**
- Create: `src/spx_momentum/backtest/metrics.py`, `tests/test_metrics.py`

**Interfaces:**
- Produces (all pure, take the `BacktestResult` + optional benchmark):
  - `def cagr(equity: pd.Series) -> float`
  - `def annualized_vol(equity: pd.Series) -> float`
  - `def sharpe(equity: pd.Series, rf=0.0) -> float`
  - `def sortino(equity: pd.Series, rf=0.0) -> float`
  - `def max_drawdown(equity: pd.Series) -> tuple[float, date]`  # dd value + date
  - `def calmar(equity: pd.Series) -> float`
  - `def total_turnover(trade_log: pd.DataFrame) -> float`
  - `def regime_win_rate(positions: PositionSet) -> float`      # win rate on rebalances
  - `def vs_benchmark(equity, benchmark: pd.Series) -> dict`     # excess CAGR, etc.
- Consumes: `BacktestResult`.

**Pseudocode:**
```
cagr        = mean_ret  -> (terminal)**(1/years) - 1
annualized_vol = std(daily_ret) * sqrt(252)
sharpe      = mean(daily_ret) / std(daily_ret) * sqrt(252)
sortino     = mean(daily_ret) / std(downside) * sqrt(252)
max_drawdown= min(equity/cummax(equity) - 1)  + argmin date
calmar      = cagr / abs(max_dd)
```
**Definition of done:** on a **6-observation toy series** each metric equals a
closed-form hand calculation (assert exact within 1e-9); `max_drawdown` returns the correct
date.

---

## Task 12: Backtest — report

**Files:**
- Create: `src/spx_momentum/backtest/report.py`, (no dedicated unit test — covered by
  `test_e2e_smoke.py`)

**Interfaces:**
- Produces: `def write_report(result: BacktestResult, metrics: dict, artifacts_dir: Path) -> Path`
- Consumes: `BacktestResult`.
- Writes: `artifacts/report.md` (metrics table + survivorship-bias note from methodology) +
  `artifacts/equity_curve.png` + `artifacts/drawdown.png` + `artifacts/holdings_heatmap.png`
  (matplotlib, no JS deps).

**Pseudocode:**
```
def write_report(result, metrics, artifacts_dir):
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir/"report.md").write_text(render_md(metrics))
    plot_equity(result.equity_curve)   -> equity_curve.png
    plot_drawdown(result.equity_curve)-> drawdown.png
    plot_holdings(heatmap)            -> holdings_heatmap.png
    return artifacts_dir/"report.md"
```
**Definition of done:** given a `BacktestResult`, `write_report` emits the `.md` + three PNGs
under `artifacts/`.

---

## Task 13: Pipeline task functions (`pipeline/tasks.py`)

**Files:**
- Create: `src/spx_momentum/pipeline/tasks.py`, (exercised by `test_e2e_smoke.py`)

**Interfaces:**
- Produces (each is a **pure function taking and returning explicit file paths**, no Airflow
  imports, independently rerunnable):
  - `def task_universe(cfg) -> str`            # returns universe CSV path
  - `def task_ingest(cfg, universe_path) -> str`      # raw stage path / manifest
  - `def task_transform(cfg) -> str`           # clean stage path
  - `def task_features(cfg) -> str`            # features stage path
  - `def task_signal(cfg) -> str`              # positions stage path
  - `def task_backtest(cfg) -> str`            # results stage path
  - `def task_report(cfg) -> Path`             # artifacts/report.md
- Consumes: all prior tasks' produced types; `LakeStore`; `Strategy`; `run_backtest`.
- File-based passing: each task reads its input stage from the lake and writes its output
  stage → no in-memory handoff between tasks.

**Pseudocode (each body is a thin delegation to the module it wraps):**
```
def task_universe(cfg):        u=snapshot(fetch(cfg));  return path
def task_ingest(cfg, upath):   tickers=read(upath); recs=ingest(tickers,cfg); return store.raw_path()
def task_transform(cfg):       return store.read(Stage.CLEAN).path     # raises on gate fail
def task_features(cfg):        build_features(read_clean, store, cfg); return store.path(STAGE.FEATURES)
def task_signal(cfg):          MomentumStrategy(cfg).generate_target_weights(...) -> positions
def task_backtest(cfg):        run_backtest(read_prices, read_positions, cfg) -> results
def task_report(cfg):          write_report(read_results, metrics, cfg.artifacts_dir)
```
**Definition of done:** the full chain `task_universe → … → task_report` runs on the synthetic
fixtures (no Airflow, no network) and each stage's row counts are consistent end-to-end.

---

## Task 14: Airflow DAG (thin wrapper)

**Files:**
- Create: `dags/momentum_dag.py`, `tests/test_dag_wiring.py`, `docker-compose.yaml`

**Interfaces:**
- Consumes: `spx_momentum.pipeline.tasks.*` (imports the task functions only).
- Produces: a DAG `spx_momentum` with the linear dependency chain, retries(2) + exponential
  backoff **only on the network stage (ingest)**, `execution_timeout`/`retry_delay` set, tags.
- Contract: the DAG file contains **no strategy/backtest logic** — it only wires task fns.

**Pseudocode:**
```
@dag(schedule="0 1 1 * *", start_date=..., catchup=False, tags=["momentum"])
def spx_momentum():
    from spx_momentum.pipeline import tasks
    from spx_momentum.config import settings as cfg
    u = PythonOperator( "universe",  python_callable=lambda: tasks.task_universe(cfg))
    i = PythonOperator( "ingest",    python_callable=lambda: tasks.task_ingest(cfg,u.path), retries=2,
                        retry_delay=timedelta(minutes=5), execution_timeout=timedelta(minutes=30))
    t = PythonOperator( "transform", python_callable=lambda: tasks.task_transform(cfg))
    f = PythonOperator( "features",  python_callable=lambda: tasks.task_features(cfg))
    s = PythonOperator( "signal",    python_callable=lambda: tasks.task_signal(cfg))
    b = PythonOperator( "backtest",  python_callable=lambda: tasks.task_backtest(cfg))
    r = PythonOperator( "report",    python_callable=lambda: tasks.task_report(cfg))
    u >> i >> t >> f >> s >> b >> r
```
**Definition of done:** `import dags.momentum_dag` builds the DAG; a programmatic-API test asserts
the 7-task chain and that **only `ingest` has retries=2**; `docker compose config` parses.

---

## Task 15: Streamlit dashboard (`ui/dashboard.py`)

**Files:**
- Create: `src/spx_momentum/ui/dashboard.py`

**Interfaces:**
- Consumes: `artifacts/` + Parquet stages; `run_backtest` for the in-process "what-if" rerun.
- Produces: `def main()` (entry point bound in `pyproject.toml`).
- Screens: equity curve vs SPY (toggle), drawdown band, metrics table, holdings-over-time, and
  a **parameter re-run** (N / lookback / costs) that executes the backtest
  in-process (no network) for what-if mode.

**Pseudocode:**
```
def main():
    st.set_page_config("S&P 500 Momentum")
    res, metrics, bench = load("artifacts")
    if st.toggle("vs SPY bench"): plot(res.equity_curve, bench)
    plot_drawdown_band(res.equity_curve)
    st.dataframe(metrics)
    holdings = st.selectbox(range(months)); show_holdings(holdings)
    if st.button("What-if rerun"):
        cfg2 = rerun_cfg(top_n=..., lookback=..., cost_bps=...)
        st.plot(rerun_in_process(cfg2).equity_curve)
```
**Definition of done:** `streamlit run src/spx_momentum/ui/dashboard.py` renders the four screens
from existing artifacts; the what-if button recomputes and re-plots offline.

---

## Task 16: Test harness + docs

**Files:**
- Create: `tests/conftest.py`, all `tests/test_*.py` stubs (from tasks above),
  `docs/methodology.md`, `docs/superpowers/specs/` symlink to `DESIGN-DOC.md`

**Interfaces (conftest fixtures):**
- `synthetic_prices(tickers=5, years=5, seed=13, trends=...)` → a seeded, multi-year
  `pd.DataFrame` with engineered trends so top-N / backtest results are **hand-verifiable**.
- `universe_fixture()` → a 500-row (or small-N variant) valid ticker frame.
- `lake(tmp_path)` → a fresh `LakeStore` rooted in a tmp dir.
- Contract: **no test opens the network** (yfinance monkeypatched in `test_ingest` only); the
  synthetic generator is the single source of test data.

**Pseudocode (conftest):**
```
@pytest.fixture
def synthetic_prices():
    rng = np.random.default_rng(13)
    idx = pd.bdate_range("2015-01-01", "2025-01-01")
    px = {}
    for i,t in enumerate(["AAA","BBB","CCC","DDD","EEE"]):
        trend = [0.004, 0.003, 0.0, -0.002, -0.004][i]      # engineered: AAA best … EEE worst
        px[t] = 100*np.exp(np.cumsum(trend + rng.normal(0,0.01,len(idx))))
    return pd.DataFrame(px, index=idx)
@pytest.fixture
def universe_fixture(): return pd.DataFrame({"ticker":[f"T{i:03d}" for i in range(500)]})
@pytest.fixture
def lake(tmp_path):     return LakeStore(tmp_path/"data")
```
**Key invariants the stub tests must pin (one assert line each):**
```
test_features        : rolling_returns uses skip-month boundary
test_strategy        : select_top_n picks actual top + weights sum to 1.0
test_backtest_engine : no-cost equity == Σ geometric product (1e-9)
test_backtest_costs  : 10bp cost strictly lowers terminal; delta == turnover-weighted
test_metrics         : 6-obs toy series matches closed-form
test_e2e_smoke       : full task chain → consistent row counts per stage
test_dag_wiring      : 7-task chain; only ingest retries=2
```
**Definition of done:** `uv run pytest` collects all stubs; every invariant above is expressible
against the scaffolded interfaces; `docs/methodology.md` documents survivorship bias + 12-1
lookback + cost model.

---

## Self-Review (run against the spec)

- **Coverage:** §4.2 components → Tasks 2–12; §4.3 layout → File Structure; §4.4 idempotency
  → Tasks 3/5/6 (upsert + gate); §4.5 test strategy → Task 16 + per-task stubs; §5 risks →
  ingest isolation (T5), Wikipedia fallback (T4), 3.12 pin (T1), Airflow friction (T14).
- **Type consistency check:** `PositionSet` (T8) is consumed by `run_backtest` (T10) and
  `regime_win_rate` (T11) — consistent. `BacktestResult` (T10) is consumed by `metrics`
  (T11) and `report` (T12) — consistent. `LakeStore.write_upsert(df, Stage, key_cols)`
  (T3) is used identically in T5/T6/T7 — consistent. `Settings` (T2) fields referenced by
  later tasks (`top_n`, `skip_months`, `cost_bps`, `null_ratio_max`) all exist in T2. ✓
- **Proportion:** each task carries only the interface + one pseudocode sketch + a
  definition of done; no full implementation bodies transcribed. ✓ (per user: pseudocode only)

## Execution note

Per the user's instruction, this stays a **scaffold (pseudocode, not coded)**. When you're ready
to build it out, each task above maps 1:1 to a code task with a real TDD loop (failing test →
stub → pass → commit).
