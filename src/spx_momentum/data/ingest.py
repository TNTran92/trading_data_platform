# yfinance daily OHLCV ingest: chunked download, per-ticker retry (x3, exp
# backoff), partial-failure tolerance, fetch-manifest records (DESIGN-DOC §4.2;
# scaffold plan Task 5).
#
# THE ISOLATION CONTRACT LIVES HERE: one dead ticker never raises out of
# ingest() and never fails the DAG — failures are captured as FetchRecord(ok=False).
# PLACEHOLDER: typed interface only.
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from spx_momentum.config import Settings


@dataclass(frozen=True)
class FetchRecord:
    """One row of the fetch-manifest table the pipeline reports on."""

    ticker: str
    ok: bool
    rows: int
    nulls: int
    ts: datetime
    error: str | None


def ingest(
    tickers: pd.DataFrame,
    start: date,
    end: date,
    store: object,  # spx_momentum.data.store.LakeStore (kept loose: no circular import)
    cfg: Settings,
) -> list[FetchRecord]:
    """Plan Task 5 contract.

    - Walks chunks of `cfg.fetch_chunk_size` (≈25) tickers.
    - Uses adjusted-close prices (yfinance auto_adjust=True).
    - Per-ticker retry `cfg.fetch_retries` times with backoff
      `cfg.fetch_backoff_s * 2**attempt`.
    - Good tickers -> store.write_upsert(..., Stage.RAW, key_cols=("ticker","date")).
    - Failures -> FetchRecord(ok=False, error=...); NEVER raises for one bad
      ticker; returns exactly one record per input ticker.
    """
    raise NotImplementedError
