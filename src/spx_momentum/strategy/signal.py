# Top-N signal: cross-sectional rank -> top-N -> equal weight, gated to
# schedule dates only (DESIGN-DOC §4.2; scaffold plan Task 8).
#
# Schedule = last trading day of each month present in the features calendar
# (a business day that is the month's last index entry). Weights sum to 1.0
# before costs; non-schedule dates carry the prior position forward (no
# trading); dates before the first scheduled day carry no position yet.
from __future__ import annotations

from datetime import date

import pandas as pd

from spx_momentum.config import Settings
from spx_momentum.strategy.base import PositionSet, Strategy


def select_top_n(scores_row: pd.Series, n: int) -> list[str]:
    """Plan Task 8 contract: pick the `n` highest-scoring tickers on one date.
    Ties broken deterministically (index order); NaN scores are excluded."""
    if n <= 0:
        return []
    ranked = scores_row.dropna().nlargest(n)
    return [str(ticker) for ticker in ranked.index]


def equal_weights(tickers: list[str]) -> tuple[float, ...]:
    """Plan Task 8: each weight = 1.0 / len(tickers); sums to 1.0 before costs."""
    if not tickers:
        raise ValueError("equal_weights: need at least one ticker")
    w = 1.0 / len(tickers)
    return (w,) * len(tickers)


class MomentumStrategy(Strategy):
    """Cross-sectional momentum: monthly top-N rotation on last-trading-day
    schedule; weights sum to 1.0; non-schedule dates carry forward.

    `as_of` delimits the returned history: only feature dates <= as_of are
    emitted, so a mid-window as_of returns positions up to (and including) it.
    """

    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg

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
        - Returns a PositionSet with dates sorted ascending; the weights frame
          is indexed by date, columns by ticker (rows share one ticker index).
        """
        if features.empty:
            raise ValueError("generate_target_weights: empty features frame")
        idx = features.index
        if not isinstance(idx, pd.DatetimeIndex):
            raise ValueError("generate_target_weights: features must be indexed by date")
        idx = idx.sort_values()
        horizon = pd.Timestamp(as_of)

        months = idx.to_period("M")
        last_per_month = pd.DataFrame({"d": idx.to_numpy(), "m": months}).groupby("m")["d"].max()
        sched = set(last_per_month)
        tickers = [str(t) for t in features.columns]

        rows: dict[pd.Timestamp, pd.Series] = {}
        current: pd.Series | None = None
        for d in idx:
            if d > horizon:
                break
            if d in sched:
                top = select_top_n(features.loc[d], self.cfg.top_n)
                if top:
                    current = pd.Series(
                        dict(zip(top, equal_weights(top), strict=True))
                    ).reindex(
                        tickers, fill_value=0.0
                    )
                # An all-NaN schedule row keeps the prior position (no selection).
            if current is None:
                continue  # before the first scheduled day: no position yet
            rows[d] = current
        if not rows:
            raise ValueError(
                f"generate_target_weights: no scheduled date on or before as_of {as_of}"
            )
        weights = pd.DataFrame(
            {t: [float(rows[d].loc[t]) for d in rows] for t in tickers},
            index=list(rows),
        )
        return PositionSet(
            dates=[d.date() for d in sorted(rows)],
            weights=weights,
        )
