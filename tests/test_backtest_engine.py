# Stubs pinning the hand-verifiable backtest invariants (Task 10).
# Replaced with real tests; names kept as the contract.
from __future__ import annotations

import pandas as pd
import pytest

from spx_momentum.backtest.engine import run_backtest
from spx_momentum.config import Settings, load_settings
from spx_momentum.strategy.base import PositionSet

TOL = 1e-9


# ── Hand-constructed fixture: 5 bdays, 2 tickers, exact ±10% moves ──────────
def _prices() -> pd.DataFrame:
    """T: +10%/day. U: −10% then +10% ×3. Exact ±0.10 daily returns so the
    hand arithmetic stays exact."""
    idx = pd.bdate_range("2024-01-01", periods=5)
    return pd.DataFrame(
        {
            "T": [100.0, 110.0, 121.0, 133.1, 146.41],
            "U": [100.0, 90.0, 99.0, 108.9, 119.79],
        },
        index=idx,
    )


def _positions() -> PositionSet:
    idx = pd.bdate_range("2024-01-01", periods=5)
    days = idx[1:5]
    weights = pd.DataFrame(
        {"T": [1.0, 0.0, 1.0, 1.0], "U": [0.0, 1.0, 0.0, 0.0]},
        index=days,
    )
    return PositionSet(dates=[d.date() for d in days], weights=weights)


def _cfg0() -> Settings:
    return load_settings(cost_bps=0.0, slippage_bps=0.0)


def _cfg10() -> Settings:
    return load_settings(cost_bps=5.0, slippage_bps=5.0)


# ── DoD invariant: 0 bp terminal == hand product of held returns ───────────
def test_no_cost_equity_equals_geometric_product() -> None:
    """0 bp run: equity curve equals the hand-computed geometric product of
    held returns, within 1e-9 (DESIGN-DOC §4.5 key invariant)."""
    prices, pos = _prices(), _positions()
    res = run_backtest(prices, pos, _cfg0())

    # Hand-computed: each day holds one ticker, held_d = that ticker's daily
    # return. T idx[0]→idx[1]=+0.10, U idx[1]→idx[2]=+0.10, T ×2 = +0.10 each.
    expected = 1.10 * 1.10 * 1.10 * 1.10  # 1.4641
    assert expected == pytest.approx(1.4641, abs=TOL)
    assert res.terminal_value == pytest.approx(expected, abs=TOL)

    hand = [1.10, 1.21, 1.331, 1.4641]
    for d, want in zip(pos.dates, hand, strict=True):
        got = float(res.equity_curve.loc[pd.Timestamp(d)])
        assert got == pytest.approx(want, abs=TOL), f"{d}: got {got}, want {want}"

    assert float(res.exposure.sum()) == pytest.approx(4.0, abs=TOL)
    assert (res.exposure == 1.0).all()


# ── DoD invariant: adding bps strictly lowers terminal value ───────────────
def test_costs_strictly_reduce_terminal_value() -> None:
    res_0 = run_backtest(_prices(), _positions(), _cfg0())
    res_10 = run_backtest(_prices(), _positions(), _cfg10())
    assert res_10.terminal_value < res_0.terminal_value


# ── Cost delta equals the turnover-weighted drag (identity of the model) ──
def test_cost_delta_matches_turnover_weighted_model() -> None:
    """res_10.terminal == res_0.terminal * ∏(1 − turnover_d · bps_total).

    Because each day multiplies by (1 − t_d·bps)·(1 + held_d) and the (1+held_d)
    factors are identical in the 0-bp run, the cost run is exactly the 0-bp run
    scaled by the turnover-weighted drag. Verify the identity holds to 1e-9."""
    prices, pos = _prices(), _positions()
    res_0 = run_backtest(prices, pos, _cfg0())
    res_10 = run_backtest(prices, pos, _cfg10())
    bps = (5.0 + 5.0) / 1e4

    # Hand-computed turn-over per position day:
    #   idx[1] (0,0)->(1,0): 0.5·Σ|Δ|=0.5
    #   idx[2] (1,0)->(0,1): 0.5·2=1.0
    #   idx[3] (0,1)->(1,0): 1.0
    #   idx[4] (1,0)->(1,0): 0.0
    drag = 1.0
    for t in (0.5, 1.0, 1.0, 0.0):
        drag *= 1.0 - t * bps

    assert res_10.terminal_value == pytest.approx(res_0.terminal_value * drag, abs=TOL)

    # The trade log's prorated per-ticker costs must sum to the day's cost.
    day0_mask = res_10.trade_log["date"] == pd.Timestamp(pos.dates[0])
    day0_cost = float(res_10.trade_log.loc[day0_mask, "cost"].sum())
    assert day0_cost == pytest.approx(0.5 * 1.0 * bps, abs=TOL)
    assert float(res_10.trade_log["cost"].sum()) > 0.0


def test_missing_position_date_raises() -> None:
    """A position date absent from the price panel is a caller error."""
    idx = pd.bdate_range("2024-01-01", periods=2)
    prices = pd.DataFrame({"T": [100.0, 110.0]}, index=idx)
    pos = PositionSet(
        dates=[idx[0].date(), idx[1].date(), (idx[1] + pd.Timedelta(days=3)).date()],
        weights=pd.DataFrame(
            {"T": [1.0, 1.0, 1.0]},
            index=pd.DatetimeIndex([idx[0], idx[1], idx[1] + pd.Timedelta(days=3)]),
        ),
    )
    with pytest.raises(ValueError):
        run_backtest(prices, pos, _cfg0())


def test_empty_positions_rejected() -> None:
    with pytest.raises(ValueError):
        run_backtest(_prices(), PositionSet(dates=[], weights=pd.DataFrame()), _cfg0())
