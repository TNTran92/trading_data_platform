# Task 8 invariants: top-N selection, schedule gating, weights sum to 1.
# Replaces the scaffold pytest.skip stubs; names kept as the contract.
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spx_momentum.config import load_settings
from spx_momentum.features.momentum import build_features
from spx_momentum.strategy.base import PositionSet
from spx_momentum.strategy.signal import (
    MomentumStrategy,
    equal_weights,
    select_top_n,
)

TOL = 1e-9


def _make_prices() -> pd.DataFrame:
    """Mirror the conftest synthetic_prices construction (seed 13, engineered
    AAA..EEE trends, 2015-2019 so build_features output stays small)."""
    rng = np.random.default_rng(13)
    idx = pd.bdate_range("2015-01-01", "2019-01-01")
    trends = {"AAA": 0.004, "BBB": 0.003, "CCC": 0.0, "DDD": -0.002, "EEE": -0.004}
    data = {
        t: 100.0 * np.exp(np.cumsum(tr + rng.normal(0.0, 0.01, len(idx))))
        for t, tr in trends.items()
    }
    return pd.DataFrame(data, index=idx)


def _schedule(index: pd.DatetimeIndex) -> set[pd.Timestamp]:
    """Last calendar day of each month in the feature index (per-month max bday)."""
    months = index.to_period("M")
    df = pd.DataFrame({"d": index.to_numpy(), "m": months})
    return set(df.groupby("m")["d"].max())


def _features(prices: pd.DataFrame, store: object, top_n: int = 2) -> pd.DataFrame:
    """Real Task-7 features on the engineered panel; top_n=2 so the
    'actual top performers' clause is hand-verifiable (AAA, BBB)."""
    cfg = load_settings(top_n=top_n)
    return build_features(prices, store=store, cfg=cfg)


def test_top_n_picks_actual_top_performers(
    synthetic_prices: pd.DataFrame, lake: object
) -> None:
    """On engineered synthetic data (AAA best ... EEE worst), top-2 must be
    ['AAA', 'BBB'] on every schedule date."""
    cfg = load_settings(top_n=2)
    feats = _features(synthetic_prices, lake)
    strat = MomentumStrategy(cfg)
    as_of = feats.index[-1].date()
    pos = strat.generate_target_weights(synthetic_prices, feats, as_of=as_of)
    assert isinstance(pos, PositionSet)
    assert pos.dates, "expected at least one scheduled position"
    for d in pos.dates:
        row = pos.weights.loc[pd.Timestamp(d)]
        held = row[row > 0].index.tolist()
        assert held == ["AAA", "BBB"], f"schedule date {d}: held {held}"


def test_weights_sum_to_one_before_costs(lake: object) -> None:
    """weights.loc[d].sum() == 1.0 (within float tol) on schedule dates."""
    prices = _make_prices()
    feats = _features(prices, lake)
    strat = MomentumStrategy(load_settings(top_n=2))
    pos = strat.generate_target_weights(prices, feats, as_of=feats.index[-1].date())
    for d in pos.dates:
        s = pos.weights.loc[pd.Timestamp(d)].sum()
        assert s == pytest.approx(1.0, abs=TOL), f"date {d}: sum={s}"


def test_rebalance_only_on_schedule_dates(lake: object) -> None:
    """Non-schedule dates carry the previous PositionSet forward (no trading)."""
    prices = _make_prices()
    feats = _features(prices, lake)
    sched = _schedule(feats.index)
    strat = MomentumStrategy(load_settings(top_n=2))
    pos = strat.generate_target_weights(prices, feats, as_of=feats.index[-1].date())
    idx = pos.weights.index

    def row_of(ts: pd.Timestamp) -> pd.Series:
        return pos.weights.loc[ts].fillna(0.0)

    # The first scheduled position must exist and be a pure top-2 equal weight.
    first = idx[0]
    assert row_of(first).sum() == pytest.approx(1.0, abs=TOL)
    assert (row_of(first) == 0.5).sum() == 2

    # DoD clause: on EVERY non-schedule date the held row equals the most
    # recent schedule row (carried forward, no trading). A row may change only
    # on a schedule date.
    last_sched_row = None
    for ts in idx:
        cur = row_of(ts)
        if ts in sched:
            assert cur.sum() == pytest.approx(1.0, abs=TOL), f"schedule {ts.date()}"
            last_sched_row = cur
        else:
            assert last_sched_row is not None, f"non-schedule {ts.date()} before first schedule"
            assert cur.equals(last_sched_row), (
                f"non-schedule {ts.date()} must inherit prior schedule row"
            )


def test_carries_forward_across_an_actual_rotation() -> None:
    """A forced top-2 flip (AAA/BBB -> CCC/DDD) may land ONLY on schedule
    dates; every non-schedule day before/after must carry the prior row."""
    idx = pd.bdate_range("2024-03-01", "2024-04-30")
    scores = pd.DataFrame(
        {
            "AAA": [0.90] * len(idx),
            "BBB": [0.80] * len(idx),
            "CCC": [0.10] * len(idx),
            "DDD": [0.05] * len(idx),
        },
        index=idx,
    )
    # Flip the ranking in April: CCC/DDD become the top 2 (AAA/BBB fall).
    apr = scores.index[scores.index.month == 4]
    scores.loc[apr, ["CCC", "DDD"]] = [0.85, 0.80]
    scores.loc[apr, ["AAA", "BBB"]] = [0.10, 0.05]

    strat = MomentumStrategy(load_settings(top_n=2))
    pos = strat.generate_target_weights(scores, scores, as_of=idx[-1].date())
    idx_p = pos.weights.index

    def row_of(ts: pd.Timestamp) -> pd.Series:
        return pos.weights.loc[ts].fillna(0.0)

    def sched(idx_: pd.DatetimeIndex) -> set[pd.Timestamp]:
        m = idx_.to_period("M")
        return set(pd.DataFrame({"d": idx_.to_numpy(), "m": m}).groupby("m")["d"].max())

    sched_set = sched(idx_p)

    # March must hold AAA/BBD (the pre-flip top 2); April CCC/DDD after flip.
    mar = [t for t in idx_p if t.month == 3]
    assert row_of(mar[-1]).loc["AAA"] == pytest.approx(0.5, abs=TOL)
    assert row_of(mar[-1]).loc["CCC"] == 0.0
    apr_days = [t for t in idx_p if t.month == 4]
    assert row_of(apr_days[-1]).loc["CCC"] == pytest.approx(0.5, abs=TOL)
    assert row_of(apr_days[-1]).loc["AAA"] == 0.0

    # The ONLY day the held row may differ from the day before is a schedule
    # day — every other day is exact inheritance.
    prev = row_of(idx_p[0])
    changed_days: list[pd.Timestamp] = []
    for ts in list(idx_p)[1:]:
        cur = row_of(ts)
        if not cur.equals(prev):
            changed_days.append(ts)
        prev = cur
    assert changed_days, "expected the April flip to be visible"
    assert all(d in sched_set for d in changed_days), (
        f"rotation landed on non-schedule day(s): {changed_days}"
    )
    # And the flip landed on the LAST trading day of April, not an earlier day.
    assert changed_days == [max(t for t in idx_p if t.month == 4)]


def test_select_top_n_handles_ties_and_nans() -> None:
    """NaN scores excluded; ties broken deterministically by index order."""
    s = pd.Series({"A": 1.0, "B": 3.0, "C": 3.0, "D": float("nan"), "E": -1.0})
    assert select_top_n(s, 1) == ["B"]
    assert select_top_n(s, 2) == ["B", "C"]
    assert select_top_n(pd.Series(dtype=float), 3) == []
    assert select_top_n(s, 0) == []


def test_equal_weights_sums_to_one_and_rejects_empty() -> None:
    """Each weight = 1.0/len; sums to 1.0; empty input is a programming error."""
    w = equal_weights(["X", "Y"])
    assert tuple(w) == pytest.approx((0.5, 0.5), abs=TOL)
    assert sum(equal_weights(["X"])) == pytest.approx(1.0, abs=TOL)
    with pytest.raises(ValueError):
        equal_weights([])
