# Task 7 contract: 12-1 skip-month boundary, per-date cross-sectional scores,
# determinism (no randomness, bit-identical across runs).

import numpy as np
import pandas as pd
import pytest

from spx_momentum import config
from spx_momentum.data.store import Stage
from spx_momentum.features import momentum as mod
from spx_momentum.features.momentum import (
    SCORE_WEIGHTS,
    build_features,
    cross_sectional_scores,
    rolling_returns,
)
from spx_momentum.features.momentum import (
    TRADING_DAYS_PER_MONTH as D,
)

# -- helpers ---------------------------------------------------------------

# Band of rows [LO, HI) that carries growth; everything outside is flat.
# Prices inside the band grow geometrically by `g` per row, so the window
# multiplier is exactly g^(row count inside the band) — position sensitive.
LO, HI = 250, 300
BAND = HI - LO  # 50 in-band rows


def _prices(growth: dict[str, float]) -> pd.DataFrame:
    n = 300
    t = np.arange(n)
    off = np.clip(t - LO, 0, BAND)  # 0 before the band, capped after
    col = {tk: 100.0 * (g ** off) for tk, g in growth.items()}
    return pd.DataFrame(col, index=pd.bdate_range("2020-01-01", periods=n))


def _window_rows(t: int, skip: int, m: int) -> int:
    """In-window growth steps for the model in `_prices`: price(row) =
    g^{clip(row - LO, 0, BAND)}, so the window return is g^{exp(b) - exp(a)}.
    """
    a = t - (skip + m) * D
    b = t - skip * D

    def exp(x: int) -> int:
        return int(np.clip(x - LO, 0, BAND))

    return exp(b) - exp(a)


# -- tests -----------------------------------------------------------------


def test_skip_month_boundary() -> None:
    """12-1: rolling returns must use the window that EXCLUDES the most
    recent month — i.e. ret_m with skip=1 differs measurably from skip=0,
    and the returned value matches the band-count hand math exactly.

    A step-growth price (rows [250,300) at ratio g per row, flat outside)
    makes the multiplier g^{in-band rows}, which depends on the window's
    exact position — so the skip boundary is observable and not absorbed by
    a uniform growth rate.
    """
    g = 1.02
    px = _prices({"AAA": g})
    t = 299  # anchor row: the skip (21) vs no-skip windows differ by one month.
    row = px[["AAA"]]

    def ret_of(skip: int, m: int) -> float:
        rets = rolling_returns(row, months=(m,), skip_months=skip)
        sub = rets[rets["ticker"] == "AAA"]
        val = sub[sub["date"] == px.index[t]]
        assert len(val) == 1
        return float(val[f"ret_{m}m"].iloc[0])

    for m in (3, 6, 12):
        skipped = ret_of(skip=1, m=m)
        unskipped = ret_of(skip=0, m=m)
        expected_skip = g ** _window_rows(t, 1, m) - 1.0
        expected_plain = g ** _window_rows(t, 0, m) - 1.0
        assert skipped == pytest.approx(expected_skip, rel=1e-12)
        assert unskipped == pytest.approx(expected_plain, rel=1e-12)
        # The boundary is real: skipping a whole month changes the value —
        # one full month (21 growth steps) drops out of the window.
        assert skipped != unskipped
        assert _window_rows(t, 0, m) - _window_rows(t, 1, m) == D

    # Leading rows: insufficient history -> NaN.
    rets = rolling_returns(row, months=(3, 6, 12), skip_months=1)
    first = rets[rets["ticker"] == "AAA"].iloc[0]
    assert pd.isna(first["ret_3m"]) and pd.isna(first["ret_12m"])
    assert int(rets["ret_3m"].isna().sum()) >= 1


def test_scores_per_date_cross_section() -> None:
    """Scores are a per-date cross-section: within each date the 5 rank spots
    appear, scores span [0.2, 1.0] (n=5 tickers), and the hand-checked
    blend is exact. The order is AAA > BBB > CCC > DDD > EEE everywhere —
    the engineered strengths must propagate through the returns to scores.
    """
    growth = {"AAA": 1.02, "BBB": 1.015, "CCC": 1.01, "DDD": 1.005, "EEE": 1.001}
    px = _prices(growth)
    rets = rolling_returns(px)
    scores = cross_sectional_scores(rets)
    valid = scores.dropna(subset=["score"])
    assert (valid["score"] >= 0.0).all() and (valid["score"] <= 1.0).all()
    for _, day in valid.groupby("date"):
        assert day["score"].nunique() == 5
        assert day["score"].min() == pytest.approx(0.2)
        assert day["score"].max() == pytest.approx(1.0)
        order = day.set_index("ticker")["score"].sort_values(ascending=False).index
        assert list(order) == list(growth)
    # Hand check at the first valid date.
    first = valid[valid["date"] == valid["date"].min()].set_index("ticker")
    w12, w6, w3 = (w for c, w in SCORE_WEIGHTS)
    # All tickers sit at the same position in the band at this date; ranks
    # are 1.0, 0.8, 0.6, 0.4, 0.2 (AAA best ... EEE worst), so
    # score(EEE) == 0.2 * (w12 + w6 + w3) and score(AAA) == w12 + w6 + w3.
    assert first.loc["AAA", "score"] == pytest.approx(w12 * 1.0 + w6 * 1.0 + w3 * 1.0)
    assert first.loc["EEE", "score"] == pytest.approx(0.2 * (w12 + w6 + w3))
    assert first.loc["CCC", "score"] == pytest.approx(0.6 * (w12 + w6 + w3))


def test_deterministic_across_runs() -> None:
    """Two runs over the same input return bit-identical frames."""
    growth = {"AAA": 1.02, "BBB": 1.01, "CCC": 1.005, "DDD": 1.002, "EEE": 1.001}
    px1 = _prices(growth)
    px2 = _prices(growth)
    pd.testing.assert_frame_equal(rolling_returns(px1), rolling_returns(px2), check_exact=True)
    s1 = cross_sectional_scores(rolling_returns(px1))
    s2 = cross_sectional_scores(rolling_returns(px2))
    pd.testing.assert_frame_equal(s1, s2, check_exact=True)


def test_build_features_wide_and_stage(lake, tmp_path) -> None:
    """build_features returns the wide ruling shape (index=date, cols=ticker)
    and lands the long (date, ticker, score) frame in Stage.FEATURES; the
    rerun is idempotent on row count; and it accepts the CLEAN long frame.
    """
    cfg = config.load_settings(data_root=tmp_path / "data", skip_months=1)
    growth = {"AAA": 1.02, "BBB": 1.015, "CCC": 1.008, "DDD": 1.003, "EEE": 1.001}
    px = _prices(growth)
    out = build_features(px, lake, cfg)
    assert list(out.columns) == sorted(px.columns)
    assert isinstance(out.index, pd.DatetimeIndex)
    stored = lake.read(Stage.FEATURES)
    assert set(stored.columns) >= {"date", "ticker", "score"}
    wide = stored.pivot(index="date", columns="ticker", values="score")
    assert len(wide) == len(out)
    first_count = len(stored)
    build_features(px, lake, cfg)
    assert len(lake.read(Stage.FEATURES)) == first_count
    # Accepts the CLEAN long frame too (pipeline passes stage output forward).
    long = (
        px.stack()
        .rename("adj_close")
        .reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})[["date", "ticker", "adj_close"]]
    )
    long2 = long.copy()
    out_long = build_features(long2, lake, cfg)
    assert list(out_long.columns) == sorted(px.columns)
    assert len(lake.read(Stage.FEATURES)) == first_count


def test_momentum_constants_are_the_plan_values() -> None:
    """The blend weights and the month unit are pinned by the plan (Task 7)."""
    assert list(mod.SCORE_WEIGHTS) == [("ret_12m", 0.5), ("ret_6m", 0.3), ("ret_3m", 0.2)]
    assert D == 21
    assert SCORE_WEIGHTS is mod.SCORE_WEIGHTS
