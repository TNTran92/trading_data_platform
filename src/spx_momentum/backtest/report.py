# Artifacts writer: report.md + equity/drawdown/holdings plots (DESIGN-DOC
# §4.2; scaffold plan Task 12). matplotlib only — no JS. PLACEHOLDER.
from __future__ import annotations

from pathlib import Path

from spx_momentum.backtest.engine import BacktestResult


def write_report(
    result: BacktestResult,
    metrics: dict[str, object],
    artifacts_dir: Path,
) -> Path:
    """Plan Task 12: write

    - `artifacts/report.md`            — metrics table + survivorship
      bias + 12-1 lookback caveat (mirror docs/methodology.md)
    - `artifacts/equity_curve.png`
    - `artifacts/drawdown.png`
    - `artifacts/holdings_heatmap.png`

    and return the report.md path. Deterministic (no timestamp in filename).
    """
    raise NotImplementedError
