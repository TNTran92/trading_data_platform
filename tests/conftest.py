# Shared fixtures (DESIGN-DOC §4.5).
#
# - NO NETWORK: yfinance is monkeypatched in test_ingest.py only; here we
#   supply a seeded synthetic price generator (3-5 tickers, multi-year, with
#   ENGINEERED trends so top-N and backtest results are hand-verifiable) and a
#   500-row universe fixture.
# - `lake(tmp_path)`: a fresh LakeStore rooted in a tmp dir (Task 3).
#
# No test opens the network (DESIGN-DOC §4.5): yfinance is monkeypatched in
# test_ingest.py; socket.create_connection is guarded by _no_network below.
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_prices() -> pd.DataFrame:
    """Seeded: index=bdate_range(2015-01-01 .. 2025-01-01), cols=ticker.

    Ticker order encodes the engineered strength (AAA best ... EEE worst) so
    'top-N picks the actual top performers' is trivially hand-verifiable:

        AAA trend +0.4%/d, BBB +0.3%/d, CCC 0.0, DDD -0.2%, EEE -0.4%
    with daily vol ~1% on top (seed=13).
    """
    rng = np.random.default_rng(13)
    idx = pd.bdate_range("2015-01-01", "2025-01-01")
    trends = {"AAA": 0.004, "BBB": 0.003, "CCC": 0.0, "DDD": -0.002, "EEE": -0.004}
    data = {
        t: 100.0 * np.exp(np.cumsum(tr + rng.normal(0.0, 0.01, len(idx))))
        for t, tr in trends.items()
    }
    return pd.DataFrame(data, index=idx)


@pytest.fixture
def small_universe() -> pd.DataFrame:
    """Tiny valid universe for unit tests (gate 480..530 uses the large one)."""
    return pd.DataFrame({"ticker": ["AAA", "BBB", "CCC", "DDD", "EEE"]})


@pytest.fixture
def universe_500() -> pd.DataFrame:
    """500 well-formed tickers — validates the [480, 530] gate (plan Task 4)."""
    return pd.DataFrame({"ticker": [f"T{i:03d}" for i in range(500)]})


@pytest.fixture
def lake(tmp_path):
    """A fresh LakeStore rooted in a tmp dir (auto-closed on teardown)."""
    from spx_momentum.data.store import LakeStore

    store = LakeStore(tmp_path / "data")
    yield store
    store.close()


@pytest.fixture
def toy_equity_series() -> pd.Series:
    """6-observation equity curve for the closed-form metric invariants
    (plan Task 11): 1.0, 1.02, 0.99, 1.01, 0.98, 1.03 on consecutive bdays."""
    idx = pd.bdate_range("2024-01-01", periods=6)
    return pd.Series([1.0, 1.02, 0.99, 1.01, 0.98, 1.03], index=idx)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail loudly if any test under tests/ reaches the network (§4.5)."""

    def guard(*args: object, **kwargs: object) -> None:
        pytest.fail("network access attempted — DESIGN-DOC §4.5 forbids it in tests")

    import socket

    monkeypatch.setattr(socket, "create_connection", guard)
    yield
