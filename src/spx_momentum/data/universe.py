# S&P 500 constituents: fetch (Wikipedia), strict validation, date-stamped
# snapshot (DESIGN-DOC §4.2; scaffold plan Task 4). PLACEHOLDER.
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


class UniverseValidationError(ValueError):
    """One gate failed: ticker shape out of domain or count out of [480, 530]."""

    def __init__(
        self,
        ticker: str | None,
        metric: str,
        value: object,
        limit: object,
    ) -> None:
        super().__init__(f"universe gate: ticker={ticker!r} {metric}={value!r} limit={limit!r}")
        self.ticker = ticker
        self.metric = metric
        self.value = value
        self.limit = limit


def fetch_universe(source: str) -> pd.DataFrame:
    """Plan Task 4: 'wikipedia' -> pinned strict parser; else a committed CSV.

    Returns a DataFrame with a single well-formed 'ticker' column. The committed
    CSV acts as the git fallback so a scrape-format change never breaks the
    pipeline (DESIGN-DOC §5).
    """
    raise NotImplementedError


def validate_universe(df: pd.DataFrame) -> None:
    """Plan Task 4 contract: raise UniverseValidationError if any ticker is not
    well-formed (uppercase alnum, '.'/'-' allowed) or if not (480 <= len <= 530).
    """
    raise NotImplementedError


def snapshot_universe(df: pd.DataFrame, path: Path, fetch_date: date) -> Path:
    """Plan Task 4: write CSV + 'fetched' = fetch_date (commit-able fallback)."""
    raise NotImplementedError
