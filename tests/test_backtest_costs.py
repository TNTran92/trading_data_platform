# Cost-model invariants (Task 9).
from __future__ import annotations

import pytest

from spx_momentum.backtest.costs import apply_costs


def test_10bp_on_one_million() -> None:
    """apply_costs(1_000_000, 5, 5) == 1_000 exactly (within float tol)."""
    assert apply_costs(1_000_000, 5, 5) == pytest.approx(1_000, abs=1e-9)


def test_zero_bps_is_zero() -> None:
    assert apply_costs(1_000_000, 0, 0) == 0.0
    # Zero in either leg still leaves the other leg active.
    assert apply_costs(1_000_000, 5, 0) == pytest.approx(500, abs=1e-9)
    assert apply_costs(1_000_000, 0, 5) == pytest.approx(500, abs=1e-9)


def test_linearity_in_notional() -> None:
    """cost scales linearly with notional (proportional bps model)."""
    one = apply_costs(1_000_000, 5, 5)
    for k in (0.5, 2.0, 7.3):
        assert apply_costs(1_000_000 * k, 5, 5) == pytest.approx(one * k, rel=1e-9)


def test_defaults_are_10bp_total() -> None:
    """The plan's default signature (5 bp + 5 bp) is 10 bp on traded notional."""
    assert apply_costs(1_000_000) == pytest.approx(1_000, abs=1e-9)


def test_negative_inputs_rejected() -> None:
    """Negative notional / bps are a caller error, not a rebate — raise, not
    silently produce a cost drag."""
    with pytest.raises(ValueError):
        apply_costs(-1.0, 5, 5)
    with pytest.raises(ValueError):
        apply_costs(1_000_000, -1, 5)
    with pytest.raises(ValueError):
        apply_costs(1_000_000, 5, -1)
