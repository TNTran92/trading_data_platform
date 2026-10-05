# Thin Airflow DAG for the S&P 500 momentum pipeline.
# PLACEHOLDER (scaffold plan Task 14).
#
# Final shape: import the task functions from spx_momentum.pipeline.tasks and
# wire the linear chain
#     universe -> ingest -> transform -> features -> signal -> backtest -> report
# with retries(2) + exponential backoff ONLY on the network stage (ingest),
# execution_timeout / retry_delay set, and tags.
#
# NO strategy/backtest logic in this file — it is a thin wrapper, not a
# business module (DESIGN-DOC §4.2). The `dags/` folder is Airflow's
# conventional location and is imported by Airflow's DagBag, NOT by the
# package (no circular import).
from __future__ import annotations


def build_dag() -> object:
    """Plan Task 14: build the 'spx_momentum' DAG from spx_momentum.pipeline.tasks."""
    raise NotImplementedError("placeholder: wire spx_momentum.pipeline.tasks per plan Task 14")


if __name__ == "__main__":
    build_dag()
