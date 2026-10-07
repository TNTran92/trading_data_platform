# Ingest contract (plan Task 5): per-ticker ISOLATION + retry + raw-stage landing.
# yfinance is monkeypatched (DESIGN-DOC §4.5: no network in tests).

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd
import pytest

from spx_momentum import config
from spx_momentum.config import Settings
from spx_momentum.data import ingest
from spx_momentum.data.store import Stage


def _settings(tmp_path) -> Settings:
    """Fast, tmp-rooted settings for ingest tests (backoff 0 => no sleeps)."""
    return config.load_settings(
        data_root=tmp_path / "data",
        fetch_chunk_size=25,
        fetch_retries=3,
        fetch_backoff_s=0.0,
    )


def _multi_price_frame(symbols: list[str], start: str = "2024-01-02", n: int = 5) -> pd.DataFrame:
    """yfinance-shaped multi-ticker result: MultiIndex columns (ticker, field)."""
    idx = pd.DatetimeIndex(pd.bdate_range(start, periods=n), name="Date")
    cols = pd.MultiIndex.from_product([symbols, ["Open", "High", "Low", "Close", "Volume"]])
    rng = np.random.default_rng(0)
    arr = (100.0 + rng.normal(0.0, 1.0, (n, len(symbols) * 5))).astype(float)
    return pd.DataFrame(arr, index=idx, columns=cols)


def _single_price_frame(symbol: str, start: str = "2024-01-02", n: int = 5) -> pd.DataFrame:
    """yfinance single-ticker result: flat OHLCV columns, DateTime index."""
    idx = pd.DatetimeIndex(pd.bdate_range(start, periods=n), name="Date")
    rng = np.random.default_rng(1)
    arr = (100.0 + rng.normal(0.0, 1.0, (n, 5))).astype(float)
    return pd.DataFrame(arr, index=idx, columns=["Open", "High", "Low", "Close", "Volume"])


class _FakeYF:
    """Replacement for yfinance.download (patched onto ingest.yf).

    Behavior:
    - batch call (list): returns a multi-ticker frame for the GOOD requested
      symbols only; `raise_batch` makes the whole call raise instead;
      `raise_single` makes the per-ticker retry calls raise.
    - single call (str): raises if the symbol is in `raise_single`, else a
      flat single-ticker frame.
    Records every call for assertions.
    """

    def __init__(self, raise_single: set[str] | None = None, raise_batch: bool = False) -> None:
        self.raise_single = set(raise_single or ())
        self.raise_batch = raise_batch
        self.calls: list[Any] = []

    def download(self, tickers: Any, **kwargs: Any) -> Any:
        symbols = list(tickers) if isinstance(tickers, (list, tuple)) else [tickers]
        self.calls.append(symbols)
        if len(symbols) == 1:
            sym = symbols[0]
            if sym in self.raise_single:
                raise RuntimeError(f"network blip ({sym})")
            return _single_price_frame(sym)
        if self.raise_batch:
            raise RuntimeError("network blip (batch)")
        good = [t for t in symbols if t not in self.raise_single]
        return _multi_price_frame(good)


def test_one_dead_ticker_still_returns_all_records(
    lake, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """A 50-ticker batch where ticker #37 is dead: 50 records (49 ok, 1 not),
    and ingest never raises. The bad ticker's failure never takes others down."""
    fake = _FakeYF(raise_single={"T037"})
    monkeypatch.setattr(ingest.yf, "download", fake.download)
    cfg = _settings(tmp_path)
    tickers = pd.DataFrame({"ticker": [f"T{i:03d}" for i in range(50)]})
    records = ingest.ingest(tickers, dt.date(2024, 1, 2), dt.date(2024, 1, 8), lake, cfg)
    assert len(records) == 50
    bad = [r for r in records if not r.ok]
    assert len(bad) == 1
    assert bad[0].ticker == "T037"
    assert bad[0].error and "network blip" in bad[0].error
    good = sorted(r.ticker for r in records if r.ok)
    assert good == sorted(set(f"T{i:03d}" for i in range(50)) - {"T037"})


def test_good_tickers_land_in_raw_stage(
    lake, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """ok tickers (and only they) land in the raw stage, with adj_close."""
    fake = _FakeYF(raise_single={"BBB"})
    monkeypatch.setattr(ingest.yf, "download", fake.download)
    cfg = _settings(tmp_path)
    tickers = pd.DataFrame({"ticker": ["AAA", "BBB", "CCC"]})
    records = ingest.ingest(tickers, dt.date(2024, 1, 2), dt.date(2024, 1, 8), lake, cfg)
    assert {r.ticker for r in records if not r.ok} == {"BBB"}
    raw = lake.read(Stage.RAW)
    assert set(raw["ticker"]) == {"AAA", "CCC"}
    assert "adj_close" in raw.columns
    assert raw["adj_close"].notna().all()
    for t in ("AAA", "CCC"):
        assert (
            len(raw[raw["ticker"] == t]) == 5
        ), f"each ticker should have 5 days of daily bars, not {len(raw[raw['ticker'] == t])}"


def test_retry_backoff_sequence(
    lake, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """A dead ticker is retried `fetch_retries` times (per-ticker singles
    after the failed batch); a good ticker is fetched once (no retry)."""
    fake = _FakeYF(raise_single={"DEAD"})
    monkeypatch.setattr(ingest.yf, "download", fake.download)
    cfg = _settings(tmp_path)
    tickers = pd.DataFrame({"ticker": ["DEAD", "GOOD"]})
    records = ingest.ingest(tickers, dt.date(2024, 1, 2), dt.date(2024, 1, 8), lake, cfg)
    by = {r.ticker: r for r in records}
    assert by["DEAD"].ok is False and "network blip" in (by["DEAD"].error or "")
    assert by["GOOD"].ok is True

    single_deads = [c for c in fake.calls if c == ["DEAD"]]
    single_goods = [c for c in fake.calls if c == ["GOOD"]]
    assert len(single_deads) == cfg.fetch_retries, (
        f"dead ticker retried {len(single_deads)}x, want {cfg.fetch_retries}"
    )
    assert len(single_goods) == 0, "good ticker should not be retried"
