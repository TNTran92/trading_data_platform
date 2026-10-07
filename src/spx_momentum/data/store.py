# Thin DuckDB/Parquet read/write helpers shared by all stages (DESIGN-DOC §4.2).
# Lane layout: one directory per Stage under the lake root, Parquet on disk,
# one live DuckDB view per stage.
#
# Upsert semantics: write_upsert replaces rows matching key_cols with the
# incoming frame and appends new keys — rerunning a stage with the same frame
# leaves the row count unchanged (DESIGN-DOC §4.4 idempotency).
from __future__ import annotations

import enum
from pathlib import Path

import duckdb
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
        self.root = root
        self._conn = duckdb.connect()
        for value in Stage:
            directory = root / value
            directory.mkdir(parents=True, exist_ok=True)
            self._recreate_view(value, directory)

    def _stage_dir(self, stage: Stage) -> Path:
        return self.root / stage

    def write_upsert(
        self,
        df: pd.DataFrame,
        stage: Stage,
        key_cols: tuple[str, str] = ("ticker", "date"),
    ) -> Path:
        """Merge `df` into the stage on `key_cols` and write parquet back out.

        Idempotent: writing the same frame twice does not duplicate rows.
        """
        df = df.copy()
        if key_cols and "date" in key_cols:
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df = df[df["date"].notna()]
        directory = self._stage_dir(stage)
        existing = self._read_pq(directory)
        key = [c for c in key_cols if c in existing.columns and c in df.columns]
        if existing.empty:
            merged = df
        elif not key or df.empty:
            merged = pd.concat([existing, df], ignore_index=True)
        else:
            new_keys = set(df[key].apply(tuple, axis=1))
            kept = existing[~existing[key].apply(tuple, axis=1).isin(new_keys)]
            merged = pd.concat([kept, df], ignore_index=True, sort=False)
        out = self._write_pq(merged, directory)
        self._recreate_view(stage, directory)
        return out[0] if out else directory

    def _recreate_view(self, stage: Stage, directory: Path) -> None:
        """(Re)point the stage view at its parquet files (or an empty select).

        DuckDB rejects a glob view over an empty directory, so an unpopulated
        stage resolves to `SELECT NULL WHERE false` (zero rows, any
        count-style query still works).
        """
        if sorted(directory.glob("*.parquet")):
            self._conn.execute(
                f"CREATE OR REPLACE VIEW {stage} AS SELECT * FROM '{directory}/*.parquet'",
            )
        else:
            self._conn.execute(f"CREATE OR REPLACE VIEW {stage} AS SELECT NULL WHERE false")

    def _read_pq(self, directory: Path) -> pd.DataFrame:
        files = sorted(directory.glob("*.parquet"))
        if not files:
            return pd.DataFrame()
        return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True, sort=False)

    def _write_pq(self, df: pd.DataFrame, directory: Path) -> list[Path]:
        out: list[Path] = []
        files = sorted(directory.glob("*.parquet"))
        if files:
            for f in files:
                f.unlink()
        if df.empty:
            return out
        out_path = directory / "stage.parquet"
        df.reset_index(drop=True).to_parquet(out_path)
        out.append(out_path)
        return out

    def read(self, stage: Stage) -> pd.DataFrame:
        """SELECT * over the stage's Parquet files (empty frame if none)."""
        directory = self._stage_dir(stage)
        files = sorted(directory.glob("*.parquet"))
        if not files:
            return pd.DataFrame()
        return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True, sort=False)

    def sql(self, query: str) -> pd.DataFrame:
        """Run DuckDB SQL (stage names resolve as views); return a DataFrame."""
        return self._conn.execute(query).fetchdf()

    def close(self) -> None:
        self._conn.close()

