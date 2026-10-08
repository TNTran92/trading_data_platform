# Strategy ABC (DESIGN-DOC §4.2; scaffold plan Task 8).
from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class PositionSet:
    """The output of a strategy on one 'as_of' date — and the input to the
    backtest engine (consumed by Task 10) and metrics (Task 11)."""

    dates: list[date]
    weights: pd.DataFrame  # index=date, cols=ticker, values in (0, 1)


class Strategy(abc.ABC):
    """All strategies implement `generate_target_weights`. Pure function of
    (prices, features, as_of) — no side effects, independently testable."""

    @abc.abstractmethod
    def generate_target_weights(
        self,
        prices: pd.DataFrame,
        features: pd.DataFrame,
        as_of: date,
    ) -> PositionSet: ...
