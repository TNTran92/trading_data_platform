# Stubs for LakeStore roundtrip + upsert idempotency (Task 3).

import pandas as pd
import pytest


def test_upsert_is_idempotent(small_universe: pd.DataFrame) -> None:
    """write_upsert(df) twice -> read back the same row count (no duplicates)."""
    pytest.skip("plan Task 3")


def test_sql_roundtrip() -> None:
    """sql('SELECT count(*) FROM ...') matches read(stage).shape[0]."""
    pytest.skip("plan Task 3")


def test_stage_isolation() -> None:
    """Writing to RAW never appears under CLEAN/FEATURES/POSITIONS/RESULTS."""
    pytest.skip("plan Task 3")
