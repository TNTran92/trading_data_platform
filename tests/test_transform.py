# Stubs pinning the LOUD-FAIL gate contract (plan Task 6 review focus).

import pandas as pd
import pytest
import spx_momentum.data.transform as transform


def test_null_ratio_gate_raises_named_ticker(synthetic_prices: pd.DataFrame) -> None:
    """A ticker with null-ratio > limit makes transform raise
    ValidationGateError(ticker=..., metric='null_ratio')."""
    pytest.skip("plan Task 6")


def test_coverage_gate_raises_named_ticker(synthetic_prices: pd.DataFrame) -> None:
    pytest.skip("plan Task 6")


def test_clean_roundtrip_is_idempotent(synthetic_prices: pd.DataFrame) -> None:
    pytest.skip("plan Task 6: write_upsert twice -> same row count")
