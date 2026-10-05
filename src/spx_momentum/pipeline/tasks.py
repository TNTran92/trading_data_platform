# Task functions — explicit file-path I/O, no Airflow imports, independently
# rerunnable and unit-testable (DESIGN-DOC §4.2; scaffold plan Task 13).
#
# Every function reads its inputs from the lake and writes its outputs to the
# lake (Stage -> next Stage). The Airflow DAG in dags/momentum_dag.py is a
# THIN wrapper around these functions. PLACEHOLDER.
from __future__ import annotations

from pathlib import Path

from spx_momentum.config import Settings


def task_universe(cfg: Settings) -> Path:
    """Plan Task 13: fetch -> validate -> snapshot; write universe CSV under
    `cfg.data_root / 'universe.csv'`. Returns the path."""
    raise NotImplementedError


def task_ingest(cfg: Settings, universe_path: Path) -> Path:
    """Plan Task 13: ingest(tickers) -> Stage.RAW. Returns the raw stage path
    (or fetch manifest path). Per-ticker isolation — never raises for N-1-1
    failures (see data/ingest.py)."""
    raise NotImplementedError


def task_transform(cfg: Settings) -> Path:
    """Plan Task 13: Stage.RAW -> Stage.CLEAN with the validation gate.
    Raises ValidationGateError (loud fail) if a gate is breached."""
    raise NotImplementedError


def task_features(cfg: Settings) -> Path:
    """Plan Task 13: Stage.CLEAN -> Stage.FEATURES (rolling returns + ranks)."""
    raise NotImplementedError


def task_signal(cfg: Settings) -> Path:
    """Plan Task 13: Stage.FEATURES -> Stage.POSITIONS via MomentumStrategy.
    Weights sum to 1.0 on every schedule date."""
    raise NotImplementedError


def task_backtest(cfg: Settings) -> Path:
    """Plan Task 13: Stage.POSITIONS -> Stage.RESULTS via run_backtest.
    Pure function of stored tables — rerunnable without network."""
    raise NotImplementedError


def task_report(cfg: Settings) -> Path:
    """Plan Task 13: Stage.RESULTS -> artifacts/report.md + plots.
    Returns the report.md path."""
    raise NotImplementedError
