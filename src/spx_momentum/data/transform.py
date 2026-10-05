# Transform: validation gate + adjusted close + common trading calendar +
# upsert into clean stage (DESIGN-DOC §4.2; scaffold plan Task 6).
#
# THE LOUD-FAIL CONTRACT: a failed gate raises ValidationGateError instead of
# silently propagating bad rows to the next stage. PLACEHOLDER.
from __future__ import annotations

import pandas as pd

from spx_momentum.config import Settings


class ValidationGateError(Exception):
    """One gate failed for one ticker — carries all context for the log line."""

    def __init__(
        self,
        ticker: str,
        metric: str,
        value: float,
        limit: float,
    ) -> None:
        super().__init__(f"transform gate: {ticker} {metric}={value:.4f} limit={limit:.4f}")
        self.ticker = ticker
        self.metric = metric
        self.value = value
        self.limit = limit


def transform(raw: pd.DataFrame, store: object, cfg: Settings) -> pd.DataFrame:
    """Plan Task 6 contract.

    - Uses adjusted close (auto_adjusted upstream).
    - Aligns all tickers to a common trading calendar (the union date axis).
    - Per-ticker gates: null_ratio <= cfg.null_ratio_max AND coverage >=
      cfg.coverage_min, else raise ValidationGateError (fail LOUDLY).
    - Writes to Stage.CLEAN via store.write_upsert keyed by ("ticker","date");
      idempotent (rerun with same frame leaves row count unchanged).
    - Returns the clean frame.
    """
    raise NotImplementedError
