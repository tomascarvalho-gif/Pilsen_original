"""
Smoke tests for indicators.py

Run with:  python -m pytest tests/ -v
"""
import pytest
from indicators import (
    calculate_ROE,
    calculate_ROA,
    calculate_EPS,
    calculate_PE,
    calculate_PFCF,
    calculate_PCF,
    calculate_debt_eq_ratio,
    calculate_pretax_margin,
)

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

FULL_VARS = {
    # Income
    "us-gaap_NetIncomeLoss": 10_000_000,
    # Balance sheet
    "us-gaap_StockholdersEquity": 50_000_000,
    "us-gaap_Assets": 200_000_000,
    # EPS (reported)
    "us-gaap_EarningsPerShareDiluted": 2.50,
    # Shares
    "us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding": 4_000_000,
    "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic": 3_800_000,
    # Cash flow
    "us-gaap_NetCashProvidedByUsedInOperatingActivities": 15_000_000,
    "us-gaap_PaymentsToAcquirePropertyPlantAndEquipment": 3_000_000,
    # Debt
    "us-gaap_Debt": 20_000_000,
    # Revenue & pretax income
    "us-gaap_Revenues": 80_000_000,
    "us-gaap_IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": 12_000_000,
}

EMPTY_VARS: dict = {}


# ---------------------------------------------------------------------------
# calculate_ROE
# ---------------------------------------------------------------------------

def test_roe_basic():
    result = calculate_ROE(FULL_VARS)
    # 10M / 50M * 100 = 20.0%
    assert result == pytest.approx(20.0)


def test_roe_negative_equity():
    vars_ = {**FULL_VARS, "us-gaap_StockholdersEquity": -10_000_000}
    result = calculate_ROE(vars_)
    # 10M / -10M * 100 = -100.0%
    assert result == pytest.approx(-100.0)


def test_roe_missing_equity():
    result = calculate_ROE(EMPTY_VARS)
    assert result is None


def test_roe_zero_equity():
    vars_ = {**FULL_VARS, "us-gaap_StockholdersEquity": 0}
    assert calculate_ROE(vars_) is None


# ---------------------------------------------------------------------------
# calculate_ROA
# ---------------------------------------------------------------------------

def test_roa_basic():
    result = calculate_ROA(FULL_VARS)
    # 10M / 200M * 100 = 5.0%
    assert result == pytest.approx(5.0)


def test_roa_missing_assets():
    assert calculate_ROA(EMPTY_VARS) is None


# ---------------------------------------------------------------------------
# calculate_EPS
# ---------------------------------------------------------------------------

def test_eps_uses_reported_diluted():
    result = calculate_EPS(FULL_VARS)
    assert result == pytest.approx(2.50)


def test_eps_fallback_to_computed():
    vars_ = {
        "us-gaap_NetIncomeLoss": 10_000_000,
        "us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding": 4_000_000,
    }
    result = calculate_EPS(vars_)
    # 10M / 4M = 2.50
    assert result == pytest.approx(2.50)


def test_eps_fallback_basic_shares():
    vars_ = {
        "us-gaap_NetIncomeLoss": 10_000_000,
        "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic": 5_000_000,
    }
    result = calculate_EPS(vars_)
    # 10M / 5M = 2.0
    assert result == pytest.approx(2.0)


def test_eps_missing_data():
    assert calculate_EPS(EMPTY_VARS) is None


# ---------------------------------------------------------------------------
# calculate_PE
# ---------------------------------------------------------------------------

def test_pe_with_inline_price():
    result = calculate_PE(FULL_VARS, stock_price=25.0)
    # 25 / 2.50 = 10.0
    assert result == pytest.approx(10.0)


def test_pe_from_dict_yf_value():
    data = {**FULL_VARS, "yf_value": 25.0}
    result = calculate_PE(FULL_VARS, file_or_json=data)
    assert result == pytest.approx(10.0)


def test_pe_no_price():
    assert calculate_PE(FULL_VARS) is None


def test_pe_zero_eps():
    vars_ = {**FULL_VARS, "us-gaap_EarningsPerShareDiluted": 0}
    assert calculate_PE(vars_, stock_price=25.0) is None


# ---------------------------------------------------------------------------
# calculate_PFCF
# ---------------------------------------------------------------------------

def test_pfcf_basic():
    result = calculate_PFCF(FULL_VARS, stock_price=30.0)
    # FCF = 15M - 3M = 12M
    # FCF/share = 12M / 4M = 3.0
    # P/FCF = 30 / 3 = 10.0
    assert result == pytest.approx(10.0)


def test_pfcf_missing_cfo():
    vars_ = {k: v for k, v in FULL_VARS.items()
             if "Operating" not in k and "ContinuingOperations" not in k}
    assert calculate_PFCF(vars_, stock_price=30.0) is None


def test_pfcf_no_price():
    assert calculate_PFCF(FULL_VARS) is None


# ---------------------------------------------------------------------------
# calculate_PCF
# ---------------------------------------------------------------------------

def test_pcf_basic():
    result = calculate_PCF(FULL_VARS, stock_price=30.0)
    # CFO/share = 15M / 4M = 3.75
    # P/CF = 30 / 3.75 = 8.0
    assert result == pytest.approx(8.0)


def test_pcf_no_price():
    assert calculate_PCF(FULL_VARS) is None


# ---------------------------------------------------------------------------
# calculate_debt_eq_ratio
# ---------------------------------------------------------------------------

def test_de_uses_total_debt_tag():
    result = calculate_debt_eq_ratio(FULL_VARS)
    # 20M / 50M = 0.4
    assert result == pytest.approx(0.4)


def test_de_falls_back_to_components():
    vars_ = {
        "us-gaap_StockholdersEquity": 50_000_000,
        "us-gaap_DebtCurrent": 5_000_000,
        "us-gaap_DebtNoncurrent": 15_000_000,
    }
    result = calculate_debt_eq_ratio(vars_)
    # (5M + 15M) / 50M = 0.4
    assert result == pytest.approx(0.4)


def test_de_no_debt():
    vars_ = {"us-gaap_StockholdersEquity": 50_000_000}
    assert calculate_debt_eq_ratio(vars_) is None


def test_de_zero_equity():
    vars_ = {**FULL_VARS, "us-gaap_StockholdersEquity": 0}
    assert calculate_debt_eq_ratio(vars_) is None


# ---------------------------------------------------------------------------
# calculate_pretax_margin
# ---------------------------------------------------------------------------

def test_pretax_margin_basic():
    result = calculate_pretax_margin(FULL_VARS)
    # 12M / 80M * 100 = 15.0%
    assert result == pytest.approx(15.0)


def test_pretax_margin_missing_revenue():
    vars_ = {"us-gaap_IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": 12_000_000}
    assert calculate_pretax_margin(vars_) is None


def test_pretax_margin_zero_revenue():
    vars_ = {**FULL_VARS, "us-gaap_Revenues": 0}
    assert calculate_pretax_margin(vars_) is None
