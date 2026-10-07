# yfinance daily OHLCV ingest: chunked download, per-ticker retry (x3, exp
# backoff), partial-failure tolerance, fetch-manifest records (DESIGN-DOC §4.2;
# scaffold plan Task 5).
#
# THE ISOLATION CONTRACT LIVES HERE: one dead ticker never raises out of
# ingest() and never fails the DAG — failures are captured as FetchRecord(ok=False).
from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import ModuleType
from typing import TYPE_CHECKING

import pandas as pd
import yfinance

from spx_momentum.config import Settings
from spx_momentum.data.store import Stage

if TYPE_CHECKING:  # typing only at runtime (no import cycle risk; store never imports ingest)
    from spx_momentum.data.store import LakeStore

yf: ModuleType = yfinance  # module alias so tests can monkeypatch ingest.yf


def _chunked(seq: Sequence[str], size: int) -> list[list[str]]:
    return [list(seq[i : i + size]) for i in range(0, len(seq), size)]


@dataclass(frozen=True)
class FetchRecord:
    """One row of the fetch-manifest table the pipeline reports on."""

    ticker: str
    ok: bool
    rows: int
    nulls: int
    ts: datetime
    error: str | None


def _extract_chunk(chunk: list[str], data: object) -> dict[str, pd.DataFrame]:
    """Split a yfinance `download` result into per-ticker frames.

    Handles both response shapes:
    - MultiIndex columns `(ticker, field)` — the normal multi-ticker
      layout (group_by="ticker"): one sub-frame per ticker.
    - A flat single-frame `Open/.../Close/...` — yfinance's single-ticker
      fallback (and plain-DataFrame test doubles).

    Rows where every field is NaN are dropped; a ticker left with no valid
    rows simply has no key here.
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        return {}
    frame: pd.DataFrame = data
    result: dict[str, pd.DataFrame] = {}
    columns = frame.columns
    if isinstance(columns, pd.MultiIndex):
        for ticker in chunk:
            if ticker not in columns:
                continue
            sub: pd.DataFrame = frame.loc[:, ticker].dropna(how="all")
            if sub.empty:
                continue
            sub["ticker"] = ticker
            result[ticker] = sub
    elif len(chunk) == 1 and "Close" in columns:
        sub = frame.dropna(how="all")
        if sub.empty:
            return {}
        if "ticker" not in sub.columns:
            sub["ticker"] = chunk[0]
        result[chunk[0]] = sub
    return result


def _normalize(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Coerce a per-ticker frame into the raw-stage layout:
    ticker / date / adj_close.

    - date accepts a `date`/`Date` column or a datetime index; the result
      keeps a datelike column (LakeStore upsert normalizes to plain dates).
    - close accepts `Close`, `close`, `Adj Close` or `adj_close`; NaN stays
      NaN so it is counted as a null (dropped only if the date is
      unparseable).
    """
    cols = {c: c for c in frame.columns}
    if "ticker" in cols and pd.api.types.is_object_dtype(frame["ticker"]):
        t0 = frame["ticker"].iloc[0]
        if pd.notna(t0):
            ticker = str(t0)
    if "Date" in cols:
        frame = frame.rename(columns={"Date": "date"})
    if "date" not in frame.columns:
        if frame.index.name not in (None, "level_0"):
            frame = frame.reset_index().rename(columns={frame.index.name: "date"})
        else:
            frame = frame.rename(columns={frame.columns[0]: "date"})
    close_src = next((c for c in ("Close", "close", "Adj Close", "adj_close") if c in frame), None)
    if close_src is None:
        raise KeyError(f"no close column in {list(frame.columns)!r} for {ticker!r}")
    frame = frame.rename(columns={close_src: "Close"})
    frame = frame.reset_index(drop=True)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame[frame["date"].notna()]
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame["ticker"] = ticker
    frame["adj_close"] = frame["Close"].astype("float64")
    return frame[["ticker", "date", "adj_close"]]


def _download_chunk(chunk: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
    """One yfinance attempt for `chunk` (retry/backoff handled by caller)."""
    data: object = yf.download(
        chunk,
        start=start,
        end=end,
        auto_adjust=True,
        group_by="ticker",
        threads=False,
        progress=False,
    )
    return _extract_chunk(chunk, data)


def ingest(
    tickers: pd.DataFrame,
    start: date,
    end: date,
    store: LakeStore,
    cfg: Settings,
) -> list[FetchRecord]:
    """Plan Task 5 contract.

    - Walks chunks of `cfg.fetch_chunk_size` (≈25) tickers; one dead ticker
      never aborts the batch. A ticker missing from (or failing) a chunk
      download is retried up to `cfg.fetch_retries` times total with backoff
      `cfg.fetch_backoff_s * 2**(attempt-1)` between attempts.
    - Uses adjusted-close prices (yfinance auto_adjust=True).
    - Good tickers -> store.write_upsert(..., Stage.RAW, key_cols=("ticker","date")).
    - Failures -> FetchRecord(ok=False, error=...); NEVER raises for one bad
      ticker; returns exactly one record per input ticker.
    """
    symbols = [str(t) for t in tickers["ticker"].tolist()]
    records: list[FetchRecord] = []
    for chunk in _chunked(symbols, cfg.fetch_chunk_size):
        results: dict[str, pd.DataFrame] = {}
        errors: dict[str, str] = {t: "no data returned" for t in chunk}
        # 1) One batch attempt for the whole chunk (~25/call).
        try:
            batch = _download_chunk(chunk, start, end)
            for ticker, frame in batch.items():
                results[ticker] = frame
                errors.pop(ticker, None)
        except Exception as exc:  # noqa: BLE001 — isolation contract: catch everything
            for ticker in chunk:
                errors[ticker] = f"{type(exc).__name__}: {exc}"
        # 2) Tickers still missing get per-ticker retries: one dead symbol
        #    must never take the rest of the chunk down.
        for ticker in chunk:
            if ticker in results:
                continue
            for attempt in range(cfg.fetch_retries):
                if attempt:
                    time.sleep(cfg.fetch_backoff_s * 2 ** (attempt - 1))
                try:
                    single = _download_chunk([ticker], start, end)
                except Exception as exc:  # noqa: BLE001 — isolation contract
                    errors[ticker] = f"{type(exc).__name__}: {exc}"
                    continue
                if ticker in single:
                    results[ticker] = single[ticker]
                    errors.pop(ticker, None)
                    break
        for ticker in chunk:
            frame = results.get(ticker)
            if frame is None or frame.empty:
                records.append(
                    FetchRecord(ticker, False, 0, 0, datetime.now(UTC), errors.get(ticker))
                )
                continue
            long = _normalize(frame, ticker)
            nulls = int(long["adj_close"].isna().sum())
            store.write_upsert(long, Stage.RAW, ("ticker", "date"))
            records.append(
                FetchRecord(ticker, True, len(long), nulls, datetime.now(UTC), None)
            )
    return records
