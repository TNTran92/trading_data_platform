# Cost-model invariants (Task 9).

import pytest
from spx_momentum.backtest import costs


def test_10bp_on_one_million() -> None:
    """apply_costs(1_000_000, 5, 5) == 1_000 exactly (within float tol)."""
    pytest.skip("plan Task 9")


def test_zero_bps_is_zero() -> None:
    pytest.skip("plan Task 9")
