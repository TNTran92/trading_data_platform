# S&P 500 constituents: fetch (Wikipedia / committed CSV), strict validation,
# date-stamped snapshot (DESIGN-DOC §4.2).
#
# The committed CSV in git is the fallback path so a scrape-format change
# never breaks the pipeline (DESIGN-DOC §5).
from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

import pandas as pd

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{0,8}[.-]?[A-Z0-9]{0,3}$")
_MIN_ROWS = 480
_MAX_ROWS = 530
_WIKI_URL = "https://en.wikipedia.org/wiki/Lists_of_S%26P_500_companies"


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


def _parse_wikipedia(html: str) -> pd.DataFrame:
    """Parse the S&P 500 constituents' Wikipedia table (pinned, strict).

    Expects the first data table to carry a 'Symbol' column; any other layout
    raises so a format change fails loudly.
    """
    tables = pd.read_html(html)
    if not tables:
        raise UniverseValidationError(None, "no_table", "0", ">=1")
    df = tables[0]
    if "Symbol" not in df.columns:
        raise UniverseValidationError(None, "no_symbol_col", list(df.columns), "'Symbol'")
    out = df[["Symbol"]].rename(columns={"Symbol": "ticker"})
    return out[out["ticker"].notna()].reset_index(drop=True)


def _fetch_wikipedia_html() -> str:
    """Network helper (isolated so tests can patch it); returns page HTML."""
    import urllib.request

    resp = urllib.request.urlopen(_WIKI_URL, timeout=30)
    with io.TextIOWrapper(resp, encoding="utf-8") as fh:
        return fh.read()


def fetch_universe(source: str) -> pd.DataFrame:
    """Load constituents from `source`.

    - ``"wikipedia"``: fetches the constituents page and runs it through the
      pinned ``_parse_wikipedia`` parser.
    - anything else: treated as a committed CSV path with a ``ticker`` column.

    Returns a single-column DataFrame with the ``ticker`` column in order.
    """
    if source == "wikipedia":
        return _parse_wikipedia(_fetch_wikipedia_html())
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"universe source not found: {source}")
    return pd.read_csv(path)[["ticker"]].reset_index(drop=True)


def validate_universe(df: pd.DataFrame) -> None:
    """Raise UniverseValidationError if any ticker is malformed or the count
    is outside [480, 530]. A well-formed frame passes silently."""
    if "ticker" not in df.columns:
        raise UniverseValidationError(None, "missing_column", list(df.columns), "'ticker'")
    for value in df["ticker"]:
        if not _TICKER_RE.fullmatch(str(value)):
            raise UniverseValidationError(
                str(value), "ticker_not_well_formed", value, _TICKER_RE.pattern,
            )
    n = int(len(df))
    if not (_MIN_ROWS <= n <= _MAX_ROWS):
        raise UniverseValidationError(None, "row_count", n, f"{_MIN_ROWS}..{_MAX_ROWS}")


def snapshot_universe(df: pd.DataFrame, path: Path, fetch_date: date) -> Path:
    """Write `df` + a 'fetched' date column to `path`; return `path`."""
    out = df.assign(fetched=pd.Timestamp(fetch_date))
    out.to_csv(path, index=False)
    return path
