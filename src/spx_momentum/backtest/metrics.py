# Performance metrics: CAGR, vol, Sharpe, Sortino, max-drawdown+date,
# Calmar, turnover, regime win-rate, vs benchmark (DESIGN-DOC §4.2;
# scaffold plan Task 11). Pure, deterministic. PLACEHOLDER.
from __future__ import annotations

from datetime import date

import pandas as pd

from spx_momentum.backtest.engine import BacktestResult
from spx_momentum.strategy.base import PositionSet


def cagr(equity: pd.Series) -> float:
    """Plan Task 11: (terminal / start) ** (252/year_obs) - 1."""
    raise NotImplementedError


def annualized_vol(equity: pd.Series) -> float:
    """Plan Task 11: std(daily_ret) * sqrt(252)."""
    raise NotImplementedError


def sharpe(equity: pd.Series, rf: float = 0.0) -> float:
    """Plan Task 11: mean(daily_ret - rf/252) / std(daily_ret) * sqrt(252).
    On a 6-obs toy series must match a closed-form hand calc (1e-9 tol)."""
    raise NotImplementedError


def sortino(equity: pd.Series, rf: float = 0.0) -> float:
    """Plan Task 11: mean / std(downside deviations only) * sqrt(252)."""
    raise NotImplementedError


def max_drawdown(equity: pd.Series) -> tuple[float, date]:
    """Plan Task 11: (worst dd value, argmin date). Must match closed-form
    on the 6-obs toy series."""
    raise NotImplementedError


def calmar(equity: pd.Series) -> float:
    """Plan Task 11: CAGR / |max_drawdown| (guard div-by-zero)."""
    raise NotImplementedError


def total_turnover(trade_log: pd.DataFrame) -> float:
    """Plan Task 11: sum of one-way turnover across all schedule dates."""
    raise NotImplementedError


def regime_win_rate(positions: PositionSet) -> float:
    """Plan Task 11: fraction of held periods where the strategy beat the
    equal-weight S&P 500 over the same horizon."""
    raise NotImplementedError


def vs_benchmark(equity: pd.Series, benchmark: pd.Series) -> dict[str, float]:
    """Plan Task 11: excess CAGR, tracking error, information ratio, beta."""
    raise NotImplementedError


def summarize(result: BacktestResult, benchmark: pd.Series | None = None) -> dict[str, object]:
    """Convenience aggregator used by report.py and the dashboard."""
    raise NotImplementedError
