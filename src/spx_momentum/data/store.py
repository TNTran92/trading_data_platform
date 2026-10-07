# Thin DuckDB/Parquet read/write helpers shared by all stages (DESIGN-DOC §4.2;
# scaffold plan Task 3). Lake layout keyed by (ticker, date) with upsert
# semantics -> idempotent, safe reruns. PLACEHOLDER: typed interface only.
from __future__ import annotations

import enum
from pathlib import Path

import pandas as pd


class Stage(enum.StrEnum):
    """Lake directories under Settings.data_root (DESIGN-DOC §4.1)."""

    RAW = "raw"
    CLEAN = "clean"
    FEATURES = "features"
    POSITIONS = "positions"
    RESULTS = "results"


class LakeStore:
    """One DuckDB connection over the lake root; stage isolation by directory."""

    def __init__(self, root: Path) -> None:
        raise NotImplementedError("placeholder: DuckDB connect over lake root (plan Task 3)")

    def write_upsert(
        self,
        df: pd.DataFrame,
        stage: Stage,
        key_cols: tuple[str, str] = ("ticker", "date"),
    ) -> Path:
        """Plan Task 3: read existing stage frame, merge on key_cols, write back.

        Idempotent: upserting the same DataFrame twice leaves the row count
        unchanged (no duplicate accumulation).
        """
        raise NotImplementedError

    def read(self, stage: Stage) -> pd.DataFrame:
        """Plan Task 3: SELECT * over the stage's Parquet files."""
        raise NotImplementedError

    def sql(self, query: str) -> pd.DataFrame:
        """Plan Task 3: run DuckDB SQL against the lake, return a DataFrame."""
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
