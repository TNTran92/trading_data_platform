# Momentum features: 3/6/12-mo rolling returns with 1-month skip, cross-
# sectional rank scores (DESIGN-DOC §4.2; scaffold plan Task 7).
#
# Pure pandas; deterministic (no randomness, no network, no wall-clock).
#
# Frequency unit: prices are daily, so 1 month = TRADING_DAYS_PER_MONTH rows
# (the average US trading month). The classic 12-1 boundary: ret_m measures
# the window ending `skip_months` months ago (the most recent month excluded)
# and spanning `m` months before that.
from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pandas as pd

from spx_momentum.config import Settings
from spx_momentum.data.store import Stage

if TYPE_CHECKING:  # typing only (store never imports momentum; no cycle)
    from spx_momentum.data.store import LakeStore

#: Average US trading month; converts plan "months" to row offsets on daily data.
TRADING_DAYS_PER_MONTH = 21

#: Blend weights from the plan (Task 7 pseudocode) — 12m-dominant classic blend.
SCORE_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("ret_12m", 0.5),
    ("ret_6m", 0.3),
    ("ret_3m", 0.2),
)


def _long_frame(panel: pd.DataFrame, value_name: str) -> pd.DataFrame:
    """Panel (index=date, cols=ticker) -> long rows (date, ticker, value)."""
    body = panel.rename_axis("date").reset_index()
    long = body.melt(id_vars="date", var_name="ticker", value_name=value_name)
    return long[["date", "ticker", value_name]]


def _as_panel(prices: pd.DataFrame) -> pd.DataFrame:
    """Accept either shape: the CLEAN long frame (ticker/date/adj_close) or an
    already-pivoted panel (index=date, cols=ticker, values=adjusted close)."""
    if {"ticker", "date", "adj_close"}.issubset(prices.columns):
        long = prices[["date", "ticker", "adj_close"]].drop_duplicates(
            subset=["date", "ticker"], keep="last"
        )
        return long.pivot(index="date", columns="ticker", values="adj_close")
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError("build_features: panel input must be indexed by date")
    return prices


def rolling_returns(
    prices: pd.DataFrame,
    months: tuple[int, ...] = (3, 6, 12),
    skip_months: int = 1,
) -> pd.DataFrame:
    """Per-ticker rolling returns, dropping the most recent `skip_months`
    months of each window (classic 12-1).

    - Input: panel, index=date, cols=ticker, values=adjusted close.
    - Window for `m`: rows [t - (skip+m)*D, t - skip*D] with D =
      TRADING_DAYS_PER_MONTH — the most recent month is excluded entirely;
      skip_months=0 gives the plain m-month return.
    - Output: long frame (date, ticker, ret_3m, ret_6m, ret_12m — one ret
      column per entry of `months`); leading rows are NaN (insufficient
      history). Deterministic: pure arithmetic + shifts on the input.
    """
    if prices.empty:
        raise ValueError("rolling_returns: empty price panel")
    if not months:
        raise ValueError("rolling_returns: `months` must be non-empty")
    d = TRADING_DAYS_PER_MONTH
    end_shift = skip_months * d
    parts: list[pd.DataFrame] = []
    for m in months:
        ret = prices.shift(end_shift) / prices.shift(end_shift + m * d) - 1
        parts.append(_long_frame(ret, f"ret_{m}m"))
    out = parts[0]
    for part in parts[1:]:
        out = out.merge(part, on=["date", "ticker"], how="inner")
    return out.sort_values(["date", "ticker"]).reset_index(drop=True)


def cross_sectional_scores(ret: pd.DataFrame) -> pd.DataFrame:
    """Per-date cross-sectional rank blend into one score column.

    - Input: long frame from rolling_returns (date, ticker, ret_*m columns).
    - rank(pct=True) across tickers within each date (ties averaged — the
      deterministic 'average' method), blended by SCORE_WEIGHTS
      (0.5/0.3/0.2 — plan Task 7).
    - Output: long frame (date, ticker, score) with scores in [0, 1]; a date
      whose tickers all lack history scores NaN. Reproducible: two runs on the
      same input yield bit-identical frames (no timestamps, no randomness).
    """
    missing = [col for col, _ in SCORE_WEIGHTS if col not in ret.columns]
    if missing:
        raise ValueError(f"cross_sectional_scores: missing return columns {missing}")
    if ret[["date", "ticker"]].duplicated().any():
        raise ValueError("cross_sectional_scores: duplicate (date, ticker) rows")
    ranked: dict[str, pd.Series] = {}
    for col, _ in SCORE_WEIGHTS:
        grouped = ret.groupby("date", sort=False)[col]
        ranked[col] = grouped.rank(pct=True, method="average")
    score = sum(weight * ranked[col] for col, weight in SCORE_WEIGHTS)
    out = pd.DataFrame({"date": ret["date"], "ticker": ret["ticker"]})
    out["score"] = score.to_numpy()
    return out


def build_features(
    prices: pd.DataFrame,
    store: object,
    cfg: Settings,
) -> pd.DataFrame:
    """Compute rolling_returns + cross_sectional_scores and upsert into
    Stage.FEATURES (keyed (ticker, date) — an idempotent rerun is a no-op on
    row count).

    - `prices`: either the CLEAN long frame (ticker/date/adj_close) as the
      pipeline passes it, or a price panel (index=date, cols=ticker).
    - Returns the score frame in the wide ruling shape (SDD ledger T7):
      index=date, cols=ticker, blended score.
    """
    panel = _as_panel(prices)
    ret = rolling_returns(panel, months=(3, 6, 12), skip_months=cfg.skip_months)
    scores = cross_sectional_scores(ret)
    cast("LakeStore", store).write_upsert(scores, Stage.FEATURES, key_cols=("ticker", "date"))
    wide = scores.pivot(index="date", columns="ticker", values="score")
    return wide.sort_index()
