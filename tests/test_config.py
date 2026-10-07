# Stubs for load_settings (Task 2).

import pytest


def test_defaults_match_yaml() -> None:
    """load_settings() equals config/default.yaml (top_n=20, lookback 12,
    skip 1, cost/slip 5 bps, gates 0.20 / 0.95)."""
    pytest.skip("plan Task 2")


def test_env_override_wins() -> None:
    """SPX_TOP_N=10 env var wins over the yaml default."""
    pytest.skip("plan Task 2")


def test_bad_value_raises_typed_error() -> None:
    """top_n='abc' -> pydantic ValidationError (typed, not a crash)."""
    pytest.skip("plan Task 2")
