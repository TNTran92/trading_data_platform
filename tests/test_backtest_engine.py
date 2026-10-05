# Stubs pinning the hand-verifiable backtest invariants (Task 10).

import pytest
from spx_momentum.backtest import engine


def test_no_cost_equity_equals_geometric_product(synthetic_prices) -> None:
    """0 bp run: equity curve must equal the hand-computed geometric product
    of held returns, exact within 1e-9 (DESIGN-DOC §4.5 key invariant)."""
    pytest.skip("plan Task 10")


def test_costs_strictly_reduce_terminal_value() -> None:
    pytest.skip("plan Task 10: 10 bp strictly lowers terminal_value")


def test_cost_delta_matches_turnover_weighted_model() -> None:
    """The equity delta between 0 bp and 10 bp runs equals the
    turnover-weighted cost of the trades in the trade log."""
    pytest.skip("plan Task 10")
