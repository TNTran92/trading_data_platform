# Proportional cost + slippage bps, one-way on traded notional
# (DESIGN-DOC §4.2; scaffold plan Task 9). PLACEHOLDER.
from __future__ import annotations


def apply_costs(notional: float, cost_bps: float = 5.0, slippage_bps: float = 5.0) -> float:
    """Plan Task 9 contract.

    total_cost = notional * (cost_bps + slippage_bps) / 10_000, applied once
    on the traded notional (both buys and sells counted as traded notional
    inside `turnover = 0.5 * sum(|w_new - w_old|)` — see Task 10).

    Invariant: apply_costs(1_000_000, 5, 5) == 1_000 exactly (within float
    tol); zero bps -> 0.0.
    """
    raise NotImplementedError
