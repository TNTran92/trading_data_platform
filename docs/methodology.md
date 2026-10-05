# Methodology: how the system works and its biases.
# DESIGN-DOC §4.3 / §5 — the report and dashboard both cite this file, so the
# claims below are the single source of truth.

# Methodology — S&P 500 Cross-Sectional Momentum

## What the system does

1. **Universe** — S&P 500 constituents are scraped from Wikipedia (pinned
   parser, strict validation 480–530 well-formed tickers) and date-stamped
   into a CSV snapshot. A committed CSV in git is the fallback if the scrape
   format changes.
2. **Ingest** — daily OHLCV from Yahoo Finance (yfinance, adjusted close),
   chunked (~25 tickers/call), per-ticker retry (3x, exponential backoff).
   One failing ticker never fails the run; it lands in a fetch-manifest table.
3. **Transform** — null-ratio and date-coverage gates per ticker; on breach
   the stage fails loudly. All tickers are aligned to a common trading
   calendar. Output is upserted (key: ticker, date) — reruns are idempotent.
4. **Features** — rolling 3/6/12-month returns (skipping the most recent 1
   month: the classic 12-1 signal) blended into a per-date cross-sectional
   score.
5. **Signal** — on the last trading day of each month, hold the top N=20 by
   score, equal-weighted; weights sum to 1 before costs; otherwise carry
   forward.
6. **Backtest** — custom engine (no library): turnover computed as
   `0.5 * sum |Δw|` on each rebalance, cost + slippage applied one-way on
   traded notional, mark-to-market daily, equity curve + trade log.
7. **Report** — CAGR, annualized vol, Sharpe, Sortino, max drawdown (+date),
   Calmar, turnover, win-rate, vs equal-weight S&P 500 benchmark. Artifacts
   are deterministic (same inputs → same outputs).

## Known biases and caveats (honest reporting)

- **Survivorship bias** — the constituent list is *today's* S&P 500. Tickers
  that were delisted, merged, or dropped during the backtest window are not
  in the universe, and back-in would flatter returns. This is a material
  upward bias for long-horizon backtests; see DESIGN-DOC §5 for the mitigation
  (committed snapshot as the best available proxy).
- **Lookback window & 1-month skip** — the 12-1 convention avoids the well
  documented short-term reversal that contaminates raw 12-month momentum.
- **Costs are a simplification** — bps applied to traded notional only.
  Market impact for very large notional, queue effects at rebalance time and
  borrow/dividend frictions are NOT modeled.
- **Benchmark** — equal-weight SPY as proxy; actual index (cap-weighted) is
  strictly better for a fair comparison but we use EW for a clean "does the
  signal add" read.
- **No live trading** — this is a research tool. Nothing places, simulates,
  or routes real orders (DESIGN-DOC §1 non-goal).

## Reproducibility

- All inputs (synthetic fixtures or committed YAML + committed universe CSV)
  are pinned. Running the full chain twice gives bit-identical artifacts
  (float-tol 1e-9). Any non-determinism (e.g. yfinance returning a different
  row count) is a *data* issue, flagged by the null-ratio / coverage gates.
