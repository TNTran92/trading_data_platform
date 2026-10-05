# Momentum features: 3/6/12-mo rolling returns with 1-month skip, cross-
# sectional rank scores (DESIGN-DOC §4.2; scaffold plan Task 7).
# Pure pandas; deterministic. PLACEHOLDER.
from __future__ import annotations

import pandas as pd

from spx_momentum.config import Settings


def rolling_returns(
    prices: pd.DataFrame,
    months: tuple[int, ...] = (3, 6, 12),
    skip_months: int = 1,
) -> pd.DataFrame:
    """Plan Task 7: rolling return per ticker, dropping the most recent
    `skip_months` month from each window (classic 12-1). Input: index=date,
    cols=ticker, values=adjusted close. Output: index=date, cols=`ret_{m}m`."""
    raise NotImplementedError


def cross_sectional_scores(ret: pd.DataFrame) -> pd.DataFrame:
    """Plan Task 7: per-date rank(pct=True) blended into a single score column;
    output reproducible across two runs (no timestamp leakage)."""
    raise NotImplementedError


def build_features(
    prices: pd.DataFrame,
    store: object,
    cfg: Settings,
) -> pd.DataFrame:
    """Plan Task 7: compute rolling_returns + cross_sectional_scores on the
    clean frame and upsert into Stage.FEATURES. Returns the score frame."""
    raise NotImplementedError
