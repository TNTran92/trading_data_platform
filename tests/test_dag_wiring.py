# Stubs pinning the DAG contract (Task 14): 7-task chain, retries only on
# the network stage. Airflow programmatic-API (no server needed).

import pytest


def test_dag_chain_has_seven_tasks_in_order() -> None:
    """import dags.momentum_dag -> assert task order
    universe > ingest > transform > features > signal > backtest > report."""
    pytest.skip("plan Task 14 (requires apache-airflow installed)")


def test_only_ingest_has_retries() -> None:
    """ingest.retries == 2; every other operator's retries == 0."""
    pytest.skip("plan Task 14")
