# Stubs pinning the per-ticker ISOLATION contract (plan Task 5 review focus).

import pytest


def test_one_dead_ticker_still_returns_all_records() -> None:
    """In a 50-ticker batch where ticker #37 raises, ingest returns 50 records
    (1 ok=False for #37) and never raises out. yfinance monkeypatched."""
    pytest.skip("plan Task 5")


def test_good_tickers_land_in_raw_stage() -> None:
    pytest.skip("plan Task 5: raw stage contains exactly the ok tickers")


def test_retry_backoff_sequence() -> None:
    pytest.skip("plan Task 5: 3 attempts, backoff_s * 2^attempt")
