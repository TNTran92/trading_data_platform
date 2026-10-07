# Universe contract (plan Task 4): shape/count gates + date-stamped snapshot.

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

import spx_momentum.data.universe as universe


def test_validate_accepts_500(universe_500: pd.DataFrame) -> None:
    """A 500-ticker well-formed frame passes (no raise)."""
    universe.validate_universe(universe_500)  # must not raise


def test_validate_rejects_out_of_range_low() -> None:
    """479 rows (one under the 480 floor) -> UniverseValidationError."""
    df = pd.DataFrame({"ticker": [f"T{i:03d}" for i in range(479)]})
    with pytest.raises(universe.UniverseValidationError):
        universe.validate_universe(df)


def test_validate_rejects_out_of_range_high() -> None:
    """531 rows (one over the 530 cap) -> UniverseValidationError."""
    df = pd.DataFrame({"ticker": [f"T{i:03d}" for i in range(531)]})
    with pytest.raises(universe.UniverseValidationError):
        universe.validate_universe(df)


def test_validate_rejects_lowercase_ticker() -> None:
    """'abc' -> UniverseValidationError naming the bad ticker."""
    df = pd.DataFrame({"ticker": ["AAA", "abc", "BBB"]})
    with pytest.raises(universe.UniverseValidationError) as exc:
        universe.validate_universe(df)
    assert exc.value.ticker == "abc"


def test_validate_rejects_bad_characters() -> None:
    """'AAA 1' (space + digit) -> UniverseValidationError."""
    df = pd.DataFrame({"ticker": ["AAA 1"]})
    with pytest.raises(universe.UniverseValidationError):
        universe.validate_universe(df)


def test_snapshot_writes_fetched_column(tmp_path: Path) -> None:
    df = pd.DataFrame({"ticker": ["AAA", "BBB"]})
    path = universe.snapshot_universe(df, tmp_path / "sp5.csv", dt.date(2026, 10, 7))
    assert path.exists()
    out = pd.read_csv(path)
    assert (out["fetched"].map(pd.Timestamp) == pd.Timestamp("2026-10-07")).all()
    assert list(out["ticker"]) == ["AAA", "BBB"]


def test_fetch_universe_csv_source(tmp_path: Path) -> None:
    """Non-'wikipedia' source = committed CSV: returns only the 'ticker'
    column, in order (extra columns dropped)."""
    src = tmp_path / "sp5.csv"
    pd.DataFrame({"ticker": ["AAA", "BBB", "CCC"], "junk": [1, 2, 3]}).to_csv(src, index=False)
    out = universe.fetch_universe(str(src))
    assert list(out.columns) == ["ticker"]
    assert list(out["ticker"]) == ["AAA", "BBB", "CCC"]


def test_fetch_universe_wikipedia_routes_to_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    """source == 'wikipedia' routes through the pinned parser (fetch patched,
    network-guarded) and returns a [ticker] frame."""
    monkeypatch.setattr(universe, "_fetch_wikipedia_html", lambda: "<html>whatever</html>")
    monkeypatch.setattr(
        universe, "_parse_wikipedia", lambda html: pd.DataFrame({"ticker": ["AAA", "BBB"]})
    )
    out = universe.fetch_universe("wikipedia")
    assert list(out.columns) == ["ticker"]
    assert list(out["ticker"]) == ["AAA", "BBB"]
