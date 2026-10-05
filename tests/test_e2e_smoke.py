# End-to-end smoke: full task-function chain (no Airflow) on synthetic data;
# asserts every lake stage produces consistent row counts (plan Task 13 +
# DESIGN-DOC §4.5). Network-free by conftest._no_network.

import pytest
from spx_momentum.pipeline import tasks


def test_full_chain_row_counts() -> None:
    """universe -> ingest -> transform -> features -> signal -> backtest ->
    report: each stage's row count is consistent with the previous and every
    lake directory exists."""
    pytest.skip("plan Task 13")


def test_rerun_is_idempotent() -> None:
    """Running the chain twice leaves every stage's row count unchanged
    (upsert semantics, DESIGN-DOC §4.4)."""
    pytest.skip("plan Task 13")
