# Pydantic settings loaded from config/default.yaml (DESIGN-DOC §4.2).
#
# Precedence (highest first): kwarg overrides > SPX_* env vars > yaml baseline
# > field defaults. A missing/invalid value raises a typed pydantic
# ValidationError, never a crash.
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

#: src/spx_momentum/config.py -> up three = repo root, holding config/default.yaml.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = _REPO_ROOT / "config" / "default.yaml"


class Settings(BaseSettings):
    """Defaults mirror config/default.yaml; SPX_* env and kwargs win."""

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


def _load_yaml(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    return loaded if isinstance(loaded, dict) else {}


def _env_overrides(for_fields: Mapping[str, object] | None = None) -> dict[str, str]:
    """SPX_<FIELD> env vars for known fields (only set ones, exact match).

    Unknown SPX_* env vars are ignored so a stray variable can't create an
    unexpected extra field.
    """
    overrides: dict[str, str] = {}
    for name in for_fields if for_fields is not None else Settings.model_fields:
        value = os.environ.get(f"SPX_{name.upper()}")
        if value is not None:
            overrides[name] = value
    return overrides


def load_settings(path: str | Path | None = None, **overrides: object) -> Settings:
    """yaml baseline -> SPX_* env -> kwarg overrides -> validated Settings.

    Raises a typed pydantic ValidationError on missing required fields or
    wrongly-typed values (e.g. top_n="abc").
    """
    base = _load_yaml(Path(path) if path is not None else DEFAULT_YAML)
    merged: dict[str, Any] = {**base, **_env_overrides(), **overrides}
    return Settings(**merged)


settings = load_settings()
