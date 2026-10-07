# Stubs pinning the 12-1 skip-month + cross-sectional invariants (Task 7).

import pandas as pd
import pytest


def test_skip_month_boundary(synthetic_prices: pd.DataFrame) -> None:
    """rolling_returns must skip the most recent month of each window."""
    pytest.skip("plan Task 7")


def test_scores_per_date_cross_section(synthetic_prices: pd.DataFrame) -> None:
    pytest.skip("plan Task 7: scores are a per-date cross-section in [0, 1]")


def test_deterministic_across_runs(synthetic_prices: pd.DataFrame) -> None:
    pytest.skip("plan Task 7: two runs return bit-identical frames")
