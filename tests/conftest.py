"""
tests/conftest.py — Shared fixtures wired to REAL NVIDIA data.

All fixtures derive from the actual CSV files:
  data/raw/nvidia_historical_BS.csv  (FY2021–FY2025, 5 rows)
  data/raw/nvidia_historical_CF.csv  (FY2022–FY2025, 4 rows — CF absent FY2020-21 by design)
  data/raw/nvidia_historical_IS.csv  (FY2020–FY2025, 6 rows)
  data/raw/cleaned_financials.csv    (FY2020–FY2025, merged)
  config/assumptions.json            (WACC, growth rates, margins)
  config/scenarios.json              (scenario override deltas)

Column names match the CANONICAL schema defined in validator.py
(post-transformer mapping), not the raw file names.
All dollar values are in $M (USD millions) per data_contracts.md.
"""

import json
import os
import numpy as np
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

TOLERANCE = 0.01  # $0.01M — per data_contracts.md


# ══════════════════════════════════════════════════════════════════════════════
# RAW FILE FIXTURES  (pre-transform — column names as in source CSVs)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def raw_bs() -> pd.DataFrame:
    return pd.read_csv(os.path.join(RAW_DATA_DIR, "nvidia_historical_BS.csv"))


@pytest.fixture(scope="session")
def raw_cf() -> pd.DataFrame:
    return pd.read_csv(os.path.join(RAW_DATA_DIR, "nvidia_historical_CF.csv"))


@pytest.fixture(scope="session")
def raw_is() -> pd.DataFrame:
    return pd.read_csv(os.path.join(RAW_DATA_DIR, "nvidia_historical_IS.csv"))


@pytest.fixture(scope="session")
def cleaned_financials() -> pd.DataFrame:
    return pd.read_csv(os.path.join(RAW_DATA_DIR, "cleaned_financials.csv"))


@pytest.fixture(scope="session")
def assumptions() -> dict:
    with open(os.path.join(CONFIG_DIR, "assumptions.json")) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def scenarios() -> dict:
    with open(os.path.join(CONFIG_DIR, "scenarios.json")) as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# CANONICAL FIXTURES  (post-transform — names match validator.py schema)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def bs_canonical() -> pd.DataFrame:
    """
    Balance Sheet mapped to canonical column names.
    Source: nvidia_historical_BS.csv  (FY2021–FY2025).

    Real 10-K values (all $M):
      FY2021: assets=28791, liabilities=11898, equity=16893
      FY2022: assets=44187, liabilities=17575, equity=26612
      FY2023: assets=41182, liabilities=19081, equity=22101
      FY2024: assets=65728, liabilities=22750, equity=42978
      FY2025: assets=111601, liabilities=32274, equity=79327
    """
    raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "nvidia_historical_BS.csv"))
    df = raw.rename(
        columns={
            "year": "fiscal_year",
            "total_assets": "total_assets_usdm",
            "total_liabilities": "total_liabilities_usdm",
            "shareholders_equity": "shareholders_equity_usdm",
            "retained_earnings": "retained_earnings_usdm",
            "cash_and_st_investments": "cash_and_investments_usdm",
            "receivables": "accounts_receivable_usdm",
            "accounts_payable": "accounts_payable_usdm",
            "inventory": "inventory_usdm",
            "prepaid_expenses": "prepaid_expenses_usdm",
            "ppe_net": "ppe_net_usdm",
            "goodwill": "goodwill_usdm",
            "intangible_assets": "intangible_assets_usdm",
            "short_term_debt": "short_term_debt_usdm",
            "long_term_debt": "long_term_debt_usdm",
            "accrued_expenses": "accrued_liabilities_usdm",
            "total_liabilities_equity": "total_liabilities_equity_usdm",
        }
    )
    return df.sort_values("fiscal_year").reset_index(drop=True)


@pytest.fixture(scope="session")
def cf_canonical() -> pd.DataFrame:
    """
    Cash Flow mapped to canonical column names.
    Source: nvidia_historical_CF.csv  (FY2022–FY2025).
    FY2020–FY2021 CF is absent by architecture design — NaN is valid.

    Verified reconciliations (CFO+CFI+CFF = Net Change Cash, $M):
      FY2022: 9108 + (-9830) + 1865 = 1143  ✓
      FY2023: 5641 + 7375 + (-11617) = 1399 ✓
      FY2024: 28090 + (-10566) + (-13633) = 3891 ✓
      FY2025: 64089 + (-20421) + (-42359) = 1309 ✓
    """
    raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "nvidia_historical_CF.csv"))
    df = raw.rename(
        columns={
            "year": "fiscal_year",
            "net_income": "net_income_usdm",
            "depreciation_amortization": "da_usdm",
            "cfo": "cfo_usdm",
            "cfi": "cfi_usdm",
            "cff": "cff_usdm",
            "net_change_cash": "net_change_cash_usdm",
            "cash_beginning": "cash_beginning_usdm",
            "cash_ending": "cash_ending_usdm",
            "capex": "capex_usdm",
            "fcf": "fcf_usdm",
            "stock_comp": "stock_comp_usdm",
            "deferred_taxes": "deferred_taxes_usdm",
            "chg_accounts_receivable": "chg_accounts_receivable_usdm",
            "chg_inventory": "chg_inventory_usdm",
            "chg_accounts_payable": "chg_accounts_payable_usdm",
        }
    )
    return df.sort_values("fiscal_year").reset_index(drop=True)


@pytest.fixture(scope="session")
def is_canonical() -> pd.DataFrame:
    """
    Income Statement mapped to canonical column names.
    Source: nvidia_historical_IS.csv  (FY2020–FY2025).

    Key FY2025 actuals (all $M):
      Revenue: 130497 | COGS: 32639 | Gross Profit: 97858
      EBIT: 81453 | Net Income: 72880
    """
    raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "nvidia_historical_IS.csv"))
    df = raw.rename(
        columns={
            "year": "fiscal_year",
            "revenue": "revenue_usdm",
            "cogs": "cogs_usdm",
            "gross_profit": "gross_profit_usdm",
            "rd_expense": "rd_expense_usdm",
            "sga_expense": "sga_expense_usdm",
            "acq_termination": "acq_termination_usdm",
            "total_opex": "total_opex_usdm",
            "ebit": "ebit_usdm",
            "da": "da_usdm",
            "ebitda": "ebitda_usdm",
            "interest_income": "interest_income_usdm",
            "interest_expense": "interest_expense_usdm",
            "other_net": "other_net_usdm",
            "ebt": "ebt_usdm",
            "income_tax": "income_tax_usdm",
            "net_income": "net_income_usdm",
        }
    )
    return df.sort_values("fiscal_year").reset_index(drop=True)


@pytest.fixture(scope="session")
def re_rollforward_df(bs_canonical, is_canonical) -> pd.DataFrame:
    """
    Merged frame for Retained Earnings rollforward invariant.
    RE_t = RE_(t-1) + NI_t - Dividends_t

    Dividends implied from: Dividends = RE_prior + NI - RE_current
    FY2021–FY2025 (intersection of BS and IS coverage).
    """
    bs_cols = ["fiscal_year", "retained_earnings_usdm"]
    is_cols = ["fiscal_year", "net_income_usdm"]
    df = bs_canonical[bs_cols].merge(
        is_canonical[is_cols], on="fiscal_year", how="inner"
    )
    df = df.sort_values("fiscal_year").reset_index(drop=True)
    df["re_prior"] = df["retained_earnings_usdm"].shift(1)
    df["implied_dividends_usdm"] = (
        df["re_prior"] + df["net_income_usdm"] - df["retained_earnings_usdm"]
    )
    return df


# ══════════════════════════════════════════════════════════════════════════════
# BAD-DATA FIXTURES  (for negative / guard tests)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def bs_broken_identity() -> pd.DataFrame:
    """BS where Assets ≠ Liabilities + Equity — must fail invariant 1."""
    return pd.DataFrame(
        {
            "fiscal_year": [2023, 2024, 2025],
            "total_assets_usdm": [41182.0, 65728.0, 111601.0],
            "total_liabilities_usdm": [19081.0, 22750.0, 32274.0],
            "shareholders_equity_usdm": [22101.0, 99999.0, 79327.0],  # FY2024 corrupted
        }
    )


@pytest.fixture
def cf_broken_reconciliation() -> pd.DataFrame:
    """CF where CFO+CFI+CFF ≠ net_change_cash — must fail invariant 2."""
    return pd.DataFrame(
        {
            "fiscal_year": [2023, 2024, 2025],
            "cfo_usdm": [5641.0, 28090.0, 64089.0],
            "cfi_usdm": [7375.0, -10566.0, -20421.0],
            "cff_usdm": [-11617.0, -13633.0, -42359.0],
            "net_change_cash_usdm": [
                1399.0,
                3891.0,
                9999.0,
            ],  # FY2025 wrong (should be 1309)
        }
    )


@pytest.fixture
def is_missing_revenue() -> pd.DataFrame:
    """IS with NaN in revenue_usdm — must be rejected by cleaner (policy=error)."""
    return pd.DataFrame(
        {
            "fiscal_year": [2024, 2025],
            "ticker": ["NVDA", "NVDA"],
            "revenue_usdm": [60922.0, np.nan],
            "cogs_usdm": [16621.0, 32639.0],
            "gross_profit_usdm": [44301.0, 97858.0],
            "rd_expense_usdm": [8675.0, 12914.0],
            "sga_expense_usdm": [2654.0, 3491.0],
            "total_opex_usdm": [11329.0, 16405.0],
            "ebit_usdm": [32972.0, 81453.0],
            "ebt_usdm": [33818.0, 84026.0],
            "net_income_usdm": [29760.0, 72880.0],
        }
    )


@pytest.fixture
def is_conflicting_duplicates() -> pd.DataFrame:
    """IS with conflicting duplicate fiscal_year — must raise in validator."""
    return pd.DataFrame(
        {
            "fiscal_year": [2025, 2025],
            "revenue_usdm": [130497.0, 999999.0],  # Same year, different revenue
        }
    )


@pytest.fixture
def is_exact_duplicates() -> pd.DataFrame:
    """IS with byte-for-byte identical rows — must be silently deduplicated."""
    row = {"fiscal_year": 2025, "revenue_usdm": 130497.0, "cogs_usdm": 32639.0}
    return pd.DataFrame([row, row])


@pytest.fixture
def bs_ar_gap() -> pd.DataFrame:
    """BS where AR has a NaN in latest year — must be forward-filled."""
    return pd.DataFrame(
        {
            "fiscal_year": [2024, 2025],
            "accounts_receivable_usdm": [9999.0, np.nan],
        }
    )
