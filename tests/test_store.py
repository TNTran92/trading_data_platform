# LakeStore contract (plan Task 3): roundtrip, upsert idempotency, isolation.

import datetime as dt

import pandas as pd

from spx_momentum.data.store import LakeStore, Stage


def _raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "date": [dt.date(2024, 1, 2), dt.date(2024, 1, 3), dt.date(2024, 1, 2)],
            "adj_close": [10.5, 10.8, 20.0],
        }
    )


def test_upsert_is_idempotent(lake: LakeStore) -> None:
    """write_upsert(df) twice -> read back the same row count (no duplicates)."""
    lake.write_upsert(_raw_frame(), Stage.RAW)
    n1 = lake.read(Stage.RAW).shape[0]
    lake.write_upsert(_raw_frame(), Stage.RAW)
    n2 = lake.read(Stage.RAW).shape[0]
    assert n1 == 3
    assert n2 == 3


def test_upsert_updates_existing_rows(lake: LakeStore) -> None:
    """Same (ticker, date) key with a new value -> the value is REPLACED,
    not duplicated (upsert, not append)."""
    lake.write_upsert(_raw_frame(), Stage.RAW)
    updated = _raw_frame().copy()
    updated.loc[updated.ticker == "AAA", "adj_close"] = 99.0
    lake.write_upsert(updated, Stage.RAW)
    got = lake.read(Stage.RAW).sort_values(["ticker", "date"]).reset_index(drop=True)
    assert got.shape[0] == 3
    assert got.loc[got.ticker == "AAA", "adj_close"].tolist() == [99.0, 99.0]


def test_sql_roundtrip(lake: LakeStore) -> None:
    """sql('SELECT count(*) ...') matches read(stage).shape[0]."""
    lake.write_upsert(_raw_frame(), Stage.RAW)
    n = lake.sql("SELECT count(*) AS n FROM raw").iloc[0, 0]
    assert int(n) == lake.read(Stage.RAW).shape[0]


def test_stage_isolation(lake: LakeStore) -> None:
    """Writing to RAW never appears under CLEAN/FEATURES/POSITIONS/RESULTS."""
    lake.write_upsert(_raw_frame(), Stage.RAW)
    for other in (Stage.CLEAN, Stage.FEATURES, Stage.POSITIONS, Stage.RESULTS):
        assert lake.read(other).shape[0] == 0, f"{other.value} should be empty"


def test_read_empty_stage_is_empty_frame(lake: LakeStore) -> None:
    """Reading a stage nothing has been written to yields an empty frame."""
    df = lake.read(Stage.CLEAN)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 0

