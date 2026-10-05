# Stubs pinning plan Task 4 contracts (see plan 'Task 4: Universe').

import pandas as pd
import pytest
import spx_momentum.data.universe as universe


def test_validate_accepts_500(universe_500: pd.DataFrame) -> None:
    pytest.skip("plan Task 4")


def test_validate_rejects_out_of_range() -> None:
    pytest.skip("plan Task 4: 479-row frame must raise UniverseValidationError")


def test_validate_rejects_lowercase_ticker(small_universe: pd.DataFrame) -> None:
    pytest.skip("plan Task 4: 'abc' must raise UniverseValidationError")


def test_snapshot_writes_fetched_column(tmp_path) -> None:
    pytest.skip("plan Task 4: snapshot_universe appends a 'fetched' date column")
