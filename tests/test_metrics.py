# Closed-form invariants on the 6-observation toy series (Task 11).

import pandas as pd
import pytest
from spx_momentum.backtest import metrics


def test_sharpe_closed_form(toy_equity_series: pd.Series) -> None:
    """sharpe(toy) must equal the hand-computed mean/std*sqrt(252), 1e-9."""
    pytest.skip("plan Task 11")


def test_sortino_closed_form(toy_equity_series: pd.Series) -> None:
    pytest.skip("plan Task 11")


def test_max_drawdown_value_and_date(toy_equity_series: pd.Series) -> None:
    pytest.skip("plan Task 11: dd value AND argmin date")


def test_cagr_and_calmar_closed_form(toy_equity_series: pd.Series) -> None:
    pytest.skip("plan Task 11")
