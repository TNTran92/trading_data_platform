# Custom backtest engine: turn over on schedule dates, hold between
# rebalances, mark-to-market daily (DESIGN-DOC §4.2; scaffold plan Task 10).
#
# Mark convention: the trade is assumed to settle at the close of the prior
# trading day (equivalently, the open of the rebalance day), so day ``d``'s
# return is earned by ``w_new`` — the weights in force for day ``d``. On
# non-rebalance days ``w_new == w_prev`` (carried forward), so the mark uses
# the same position.
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from spx_momentum.backtest.costs import apply_costs
from spx_momentum.config import Settings
from spx_momentum.strategy.base import PositionSet


@dataclass(frozen=True)
class BacktestResult:
    """Consumed by metrics (Task 11) and report (Task 12)."""

    equity_curve: pd.Series  # index=date, values=factor (start=1.0)
    trade_log: pd.DataFrame  # (date, ticker, weight_before, weight_after, cost)
    exposure: pd.Series      # index=date, values=weights.sum() (1.0 if full)
    terminal_value: float


def run_backtest(
    prices: pd.DataFrame,
    positions: PositionSet,
    cfg: Settings,
) -> BacktestResult:
    """Plan Task 10 contract.

    For each day in ``positions.dates`` (ascending):
      1. ``turnover = 0.5 * Σ|w_new − w_prev|``  (w_prev zero on day 0)
      2. ``cost = apply_costs(turnover * eq_before, cost_bps, slippage_bps)``
      3. ``equity = eq_before * (1 − cost / eq_before)``  — cost drag BEFORE mark
      4. ``equity *= (1 + w_newᵀ r_d)``  — mark-to-market with ``w_new``
         where ``r_d = prices[d]/prices[d−1] − 1`` (0 on the panel's first row).

    **Invariant**: with ``cost_bps = slippage_bps = 0`` the terminal value is
    the geometric product ``∏(1 + w_newᵀ r_d)`` over ``positions.dates``
    (within 1e-9 for IEEE 754 doubles). Adding any bps strictly lowers the
    terminal value by the turnover-weighted drag ``∏(1 − turnover_d · bps)``.
    """
    if not positions.dates:
        raise ValueError("run_backtest: positions.dates must be non-empty")
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError("run_backtest: prices.index must be a pd.DatetimeIndex")
    if prices.empty:
        raise ValueError("run_backtest: prices must be non-empty")
    if not isinstance(positions.weights, pd.DataFrame) or positions.weights.empty:
        raise ValueError("run_backtest: positions.weights must be a non-empty DataFrame")

    prices = prices.sort_index()
    dates = sorted(positions.dates)

    price_index = set(prices.index)
    missing = [d for d in dates if pd.Timestamp(d) not in price_index]
    if missing:
        raise ValueError(
            f"run_backtest: prices panel is missing {len(missing)} position date(s), "
            f"e.g. {missing[:3]}"
        )

    # Union ticker set in stable order (first column list, then any extras
    # discovered in later rows).
    tickers: list[str] = [str(t) for t in positions.weights.columns]
    seen = set(tickers)
    for ts in positions.weights.index:
        for t in positions.weights.loc[ts].index:
            label = str(t)
            if label not in seen:
                seen.add(label)
                tickers.append(label)

    rets = prices.pct_change()

    equity = 1.0
    w_prev = pd.Series(0.0, index=tickers)

    eq_index: list[pd.Timestamp] = []
    eq_values: list[float] = []
    trade_rows: list[tuple[pd.Timestamp, str, float, float, float]] = []
    exposure_values: list[float] = []

    for d in dates:
        ts = pd.Timestamp(d)
        w_new = (
            positions.weights.loc[ts].reindex(tickers, fill_value=0.0).fillna(0.0)
        ).astype(float)
        delta = w_new - w_prev
        turnover = 0.5 * float(delta.abs().sum())

        eq_before = equity
        cost = apply_costs(turnover * eq_before, cfg.cost_bps, cfg.slippage_bps)
        equity = eq_before - cost  # == eq_before * (1 − cost/eq_before)

        r_d = rets.loc[ts].fillna(0.0)
        equity *= 1.0 + float((w_new * r_d).sum())

        eq_index.append(ts)
        eq_values.append(equity)
        exposure_values.append(float(w_new.sum()))

        for t in tickers:
            w_b = float(w_prev[t])
            w_a = float(w_new[t])
            if w_b == w_a:
                continue
            # Prorate the day's cost so Σ_t cost_t == cost exactly: weight each
            # ticker by |Δw_t| / Σ|Δw_t|.
            total_abs = float(delta.abs().sum())
            cost_t = (abs(w_a - w_b) / total_abs) * cost if total_abs > 0 else 0.0
            trade_rows.append((ts, t, w_b, w_a, cost_t))

        w_prev = w_new

    dtidx = pd.DatetimeIndex(eq_index)
    return BacktestResult(
        equity_curve=pd.Series(eq_values, index=dtidx),
        trade_log=pd.DataFrame(
            trade_rows,
            columns=["date", "ticker", "weight_before", "weight_after", "cost"],
        ),
        exposure=pd.Series(exposure_values, index=dtidx),
        terminal_value=float(equity),
    )
