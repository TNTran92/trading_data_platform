# Task 6 contract: LOUD-FAIL validation gate (named ticker + metric, no partial
# clean output) + union-calendar alignment + idempotent clean upsert.

import pandas as pd
import pytest

from spx_momentum import config
from spx_momentum.data.store import Stage
from spx_momentum.data.transform import ValidationGateError, transform

DEFAULTS = dict(null_ratio_max=0.20, coverage_min=0.90)


def _long(prices: pd.DataFrame) -> pd.DataFrame:
    """Panel (index=date, cols=ticker) -> RAW layout: ticker / date / adj_close."""
    long = prices.stack().rename("adj_close").reset_index()
    return long.rename(columns={"level_0": "date", "level_1": "ticker"})[
        ["ticker", "date", "adj_close"]
    ]


def test_null_ratio_gate_raises_named_ticker(
    synthetic_prices: pd.DataFrame, lake, tmp_path
) -> None:
    """A ticker with 25% nulls (limit 20%) makes transform raise
    ValidationGateError(ticker=AAA, metric='null_ratio')."""
    cfg = config.load_settings(data_root=tmp_path / "data", **DEFAULTS)
    raw = synthetic_prices.copy()
    raw.loc[synthetic_prices.index[::4], "AAA"] = float("nan")  # 25% nulls > 20% limit
    with pytest.raises(ValidationGateError) as excinfo:
        transform(_long(raw), lake, cfg)
    err = excinfo.value
    assert err.ticker == "AAA"
    assert err.metric == "null_ratio"
    assert err.value > cfg.null_ratio_max
    assert lake.read(Stage.CLEAN).empty, "failed gate must not leave partial clean output"


def test_coverage_gate_raises_named_ticker(synthetic_prices: pd.DataFrame, lake, tmp_path) -> None:
    """A ticker at ~98% coverage with coverage_min=99% makes transform raise
    ValidationGateError(ticker=..., metric='coverage')."""
    cfg = config.load_settings(data_root=tmp_path / "data", null_ratio_max=1.0, coverage_min=0.99)
    raw = synthetic_prices.copy()
    raw.loc[synthetic_prices.index[::50], "BBB"] = float("nan")  # ~2% nulls
    with pytest.raises(ValidationGateError) as excinfo:
        transform(_long(raw), lake, cfg)
    err = excinfo.value
    assert err.ticker == "BBB"
    assert err.metric == "coverage"
    assert err.value < cfg.coverage_min
    assert lake.read(Stage.CLEAN).empty, "failed gate must not leave partial clean output"


def test_clean_roundtrip_is_idempotent(synthetic_prices: pd.DataFrame, lake, tmp_path) -> None:
    """write_upsert twice -> same row count (DESIGN-DOC §4.4 idempotency)."""
    cfg = config.load_settings(data_root=tmp_path / "data", **DEFAULTS)
    raw = _long(synthetic_prices)
    out = transform(raw, lake, cfg)
    first = lake.read(Stage.CLEAN)
    transform(raw, lake, cfg)
    second = lake.read(Stage.CLEAN)
    expected = len(synthetic_prices) * len(synthetic_prices.columns)
    assert len(first) == expected
    assert len(second) == len(first)
    assert set(second.columns) >= {"ticker", "date", "adj_close"}
    assert out["adj_close"].notna().all()


def test_union_calendar_aligns_missing_days(synthetic_prices: pd.DataFrame, lake, tmp_path) -> None:
    """A ticker with a shorter history is reindexed to the FULL union calendar
    (missing days as NaN), not dropped — gates then see the true null ratio."""
    cfg = config.load_settings(data_root=tmp_path / "data", null_ratio_max=0.5, coverage_min=0.5)
    full = _long(synthetic_prices)
    shortened = _long(synthetic_prices.iloc[:-100][["EEE"]])  # EEE missing last 100 days
    combined = pd.concat(
        [full[full["ticker"] != "EEE"], shortened], ignore_index=True
    )
    out = transform(combined, lake, cfg)
    eee = out[out["ticker"] == "EEE"]
    assert len(eee) == len(synthetic_prices), "EEE must span the full union calendar"
    assert int(eee["adj_close"].isna().sum()) == 100
    assert out[out["ticker"] == "AAA"]["adj_close"].notna().all()
