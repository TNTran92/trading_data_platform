# Stubs pinning the selection / schedule / weight invariants (Task 8).

import pandas as pd
import pytest
from spx_momentum.features import momentum
from spx_momentum.strategy import signal


def test_top_n_picks_actual_top_performers(synthetic_prices: pd.DataFrame) -> None:
    """On engineered synthetic data (AAA best ... EEE worst), top-2 must be
    ['AAA', 'BBB'] on every schedule date."""
    pytest.skip("plan Task 8")


def test_weights_sum_to_one_before_costs() -> None:
    """weights.loc[d].sum() == 1.0 (within float tol) on schedule dates."""
    pytest.skip("plan Task 8")


def test_rebalance_only_on_schedule_dates() -> None:
    """Non-schedule dates carry the previous PositionSet forward (no trading)."""
    pytest.skip("plan Task 8")
