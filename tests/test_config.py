# Config contract (plan Task 2): yaml baseline -> env -> kwarg overrides.

import pytest
from pydantic import ValidationError

from spx_momentum import config
from spx_momentum.config import Settings


def test_settings_singleton_valid() -> None:
    """Module-level `settings` exists and parses the defaults from
    config/default.yaml."""
    assert isinstance(config.settings, Settings)


def test_defaults_match_yaml() -> None:
    """load_settings() equals config/default.yaml (top_n=20, lookback 12,
    skip 1, cost/slip 5 bps, gates 0.20 / 0.95, chunk 25, retries 3)."""
    cfg = config.load_settings()
    assert cfg.universe_source == "wikipedia"
    assert cfg.top_n == 20
    assert cfg.lookback_months == 12
    assert cfg.skip_months == 1
    assert cfg.rebalance == "last_trading_day"
    assert cfg.cost_bps == 5.0
    assert cfg.slippage_bps == 5.0
    assert cfg.null_ratio_max == 0.20
    assert cfg.coverage_min == 0.95
    assert cfg.fetch_chunk_size == 25
    assert cfg.fetch_retries == 3
    assert cfg.fetch_backoff_s == 2.0
    assert cfg.data_root.name == "data"
    assert cfg.artifacts_dir.name == "artifacts"


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPX_TOP_N=10 env var wins over the yaml default."""
    monkeypatch.setenv("SPX_TOP_N", "10")
    assert config.load_settings().top_n == 10


def test_kwarg_override_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """kwarg overrides win over both env and yaml."""
    monkeypatch.setenv("SPX_TOP_N", "10")
    assert config.load_settings(top_n=7).top_n == 7


def test_bad_value_raises_typed_error() -> None:
    """top_n='abc' -> pydantic ValidationError (typed, not a crash)."""
    with pytest.raises(ValidationError):
        config.load_settings(top_n="abc")  # type: ignore[arg-type]
