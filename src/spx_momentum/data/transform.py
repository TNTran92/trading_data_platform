# Transform: validation gate + adjusted close + common trading calendar +
# upsert into clean stage (DESIGN-DOC §4.2; scaffold plan Task 6).
#
# THE LOUD-FAIL CONTRACT: a failed gate raises ValidationGateError instead of
# silently propagating bad rows to the next stage. All gates run BEFORE any
# clean-stage write, so a failed transform never leaves partial clean output.
from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from spx_momentum.config import Settings
from spx_momentum.data.store import Stage

if TYPE_CHECKING:  # typing only (store never imports transform; no cycle)
    from spx_momentum.data.store import LakeStore


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


def _trading_calendar(dates: pd.Series) -> pd.DatetimeIndex:
    """Common axis: sorted set of all valid dates (the union — plan clause)."""
    valid = pd.to_datetime(dates, errors="coerce").dropna()
    return pd.DatetimeIndex(valid).unique().sort_values()


def _gate(ticker: str, adj_close: pd.Series, cfg: Settings) -> None:
    """Both per-ticker gates on the calendar-aligned adjusted-close column."""
    null_ratio = float(adj_close.isna().mean())
    if null_ratio > cfg.null_ratio_max:
        raise ValidationGateError(ticker, "null_ratio", null_ratio, cfg.null_ratio_max)
    coverage = float(adj_close.notna().mean())
    if coverage < cfg.coverage_min:
        raise ValidationGateError(ticker, "coverage", coverage, cfg.coverage_min)


def _align(
    group: pd.DataFrame, ticker: object, cal: pd.DatetimeIndex, cfg: Settings
) -> pd.DataFrame:
    """One ticker: index by date over the common calendar, gate, return part."""
    t = str(ticker)
    close = pd.to_numeric(group["adj_close"], errors="coerce")
    dates = pd.to_datetime(group["date"], errors="coerce")
    mask = dates.notna()
    idx = dates[mask]
    indexed = pd.Series(close[mask].to_numpy(), index=idx, name="date")
    # Collapse duplicate dates (keep last) before reindexing to the union axis.
    indexed = indexed[~indexed.index.duplicated(keep="last")].sort_index()
    aligned = indexed.reindex(cal)
    _gate(t, aligned, cfg)
    return pd.DataFrame({"ticker": t, "date": cal.to_series().values, "adj_close": aligned.values})


def transform(raw: pd.DataFrame, store: LakeStore, cfg: Settings) -> pd.DataFrame:
    """Plan Task 6 contract.

    - Uses adjusted close (auto_adjusted upstream by ingest).
    - Aligns all tickers to the common trading calendar (the union of RAW
      dates): every ticker gets exactly one row per calendar date, missing
      days carried as NaN.
    - Per-ticker gates, checked BEFORE any stage write: null_ratio (over the
      calendar) <= cfg.null_ratio_max AND coverage >= cfg.coverage_min, else
      raise ValidationGateError (fail LOUDLY — no partial clean output).
    - Writes the aligned frame to Stage.CLEAN via
      store.write_upsert(key_cols=("ticker", "date")): idempotent rerun.
    - Returns the clean frame (columns: ticker, date, adj_close).
    """
    missing = {"ticker", "date", "adj_close"} - set(raw.columns)
    if missing:
        raise ValueError(f"transform: raw frame missing columns {sorted(missing)}")
    if raw["date"].dropna().empty:
        raise ValueError("transform: raw frame has no valid dates — nothing to validate")

    cal = _trading_calendar(raw["date"])
    parts = [_align(group, ticker, cal, cfg) for ticker, group in raw.groupby("ticker", sort=True)]
    clean = pd.concat(parts, ignore_index=True, sort=False)
    store.write_upsert(clean, Stage.CLEAN, key_cols=("ticker", "date"))
    return clean
