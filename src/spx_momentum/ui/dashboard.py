# Streamlit dashboard: equity curve vs SPY (toggle), drawdown band,
# holdings over time, metrics table, in-process what-if rerun (DESIGN-DOC §4.2;
# scaffold plan Task 15). Entry point bound as `spx-dashboard` in pyproject.
# PLACEHOLDER.
from __future__ import annotations


def main() -> None:
    """Plan Task 15: four screens —

    1. Equity curve (toggle: strategy vs equal-weight S&P 500 benchmark).
    2. Drawdown band (rolling max drawdown on a shared axis).
    3. Metrics table (CAGR, Sharpe, Sortino, MaxDD, Calmar, turnover,
       win rate) — reads artifacts/report.md or artifacts/ parquet directly.
    4. Holdings-over-time (month selector + bar chart).

    Plus a What-if panel: N / lookback / cost-bps sliders -> re-run
    run_backtest in-process with the same (already cached) lake tables.
    No network calls; no live order routing (DESIGN-DOC non-goal).
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
