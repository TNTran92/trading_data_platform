# Top-N signal: cross-sectional rank -> top-N -> equal weight, gated to
# schedule dates only (DESIGN-DOC §4.2; scaffold plan Task 8). PLACEHOLDER.
from __future__ import annotations

from datetime import date

import pandas as pd

from spx_momentum.config import Settings
from spx_momentum.strategy.base import PositionSet, Strategy


def select_top_n(scores_row: pd.Series, n: int) -> list[str]:
    """Plan Task 8 contract: pick the `n` highest-scoring tickers on one date.
    Ties broken deterministically (index order); NaN scores are excluded."""
    raise NotImplementedError


def equal_weights(tickers: list[str]) -> tuple[float, ...]:
    """Plan Task 8: each weight = 1.0 / len(tickers); sums to 1.0 before costs."""
    raise NotImplementedError


class MomentumStrategy(Strategy):
    """Cross-sectional momentum: monthly top-N rotation on last-trading-day
    schedule; weights sum to 1.0; non-schedule dates carry forward."""

    def __init__(self, cfg: Settings) -> None:
        raise NotImplementedError

    def generate_target_weights(
        self,
        prices: pd.DataFrame,
        features: pd.DataFrame,
        as_of: date,
    ) -> PositionSet:
        """Plan Task 8 contract:

        - Only on schedule dates (last trading day of month) compute
          select_top_n(features.loc[d], cfg.top_n) + equal_weights.
        - Non-schedule dates inherit the previous PositionSet (no trading).
        - Sum of weights == 1.0 (within float tol) on every schedule date.
        - Returns a PositionSet with dates sorted ascending.
        """
        raise NotImplementedError
