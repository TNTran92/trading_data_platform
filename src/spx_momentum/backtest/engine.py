# Custom backtest engine: turn over on schedule dates, hold between
# rebalances, mark-to-market daily (DESIGN-DOC §4.2; scaffold plan Task 10).
# PLACEHOLDER: typed interface only.
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from spx_momentum.config import Settings
from spx_momentum.strategy.base import PositionSet


@dataclass(frozen=True)
class BacktestResult:
    """Consumed by metrics (Task 11) and report (Task 12)."""

    equity_curve: pd.Series  # index=date, values=factor (start=1.0)
    trade_log: pd.DataFrame  # (date, ticker, w_before, w_after, cost)
    exposure: pd.Series      # index=date, values=1.0 or 0.0 (full investment)
    terminal_value: float


def run_backtest(
    prices: pd.DataFrame,
    positions: PositionSet,
    cfg: Settings,
) -> BacktestResult:
    """Plan Task 10 contract.

    For each schedule date in `positions.dates`:
      1. turnover  = 0.5 * sum(|w_new - w_prev|)       (w_prev zero on day 1)
      2. cost      = apply_costs(turnover * equity, cfg.cost_bps, cfg.slippage_bps)
      3. equity   *= (1 - cost/equity)  ==  (1 - turnover*(bps) / 1e4)
      4. mark-to-market daily between rebalances:
         equity   *= prod(1 + sum w_i * r_i / day-holded)

    INVARIANT: with cfg.cost_bps=cfg.slippage_bps=0, terminal_value equals the
    hand-computed geometric product of held returns (exact within 1e-9).
    Adding any bps strictly lowers terminal_value by a turnover-weighted amount.
    """
    raise NotImplementedError
