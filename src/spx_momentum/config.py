# Pydantic settings loaded from config/default.yaml, env-overridable
# (DESIGN-DOC §4.2; scaffold plan Task 2). PLACEHOLDER: typed interface, no
# loader body yet, so the stub imports cleanly.
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Defaults mirror config/default.yaml; env (SPX_*) and kwargs win."""

    model_config = SettingsConfigDict(env_prefix="SPX_", extra="allow")

    universe_source: str = "wikipedia"

    # strategy
    top_n: int = 20
    lookback_months: int = 12
    skip_months: int = 1  # classic 12-1 momentum
    rebalance: str = "last_trading_day"

    # cost model (one-way, on traded notional)
    cost_bps: float = 5.0
    slippage_bps: float = 5.0

    # layout
    data_root: Path = Path("data")
    artifacts_dir: Path = Path("artifacts")

    # validation gates (transform fails loudly beyond these)
    null_ratio_max: float = 0.20
    coverage_min: float = 0.95

    # ingest tuning
    fetch_chunk_size: int = 25
    fetch_retries: int = 3
    fetch_backoff_s: float = 2.0


def load_settings(path: str | Path | None = None, **overrides: object) -> Settings:
    """Plan Task 2: yaml baseline -> env -> kwarg overrides.

    Raises a typed Pydantic error on missing required fields. Once implemented,
    a module-level singleton `settings = load_settings()` is exposed.
    """
    raise NotImplementedError("placeholder: yaml+env+kwarg loading per plan Task 2")
