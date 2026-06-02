"""
src/from src.etl/canonical_schema.py
====================================
Canonical schema definitions — converted from canonical_schema.md v1.0.

Single source of truth for column names, dtypes, and required fields
across all 4 canonical tables. Every downstream module (modeling, KPI, UI)
reads ONLY these tables and must respect these contracts.

Source: canonical_schema.md | Author: Aditya Gupta | Oct 2025
"""

from __future__ import annotations

import pandas as pd

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 1: revenue
# Segment-level annual revenue — historical and forecast
# PK: (fiscal_year, segment, scenario)
# ══════════════════════════════════════════════════════════════════════════════

REVENUE_SCHEMA: dict[str, str] = {
    "fiscal_year": "int64",
    "ticker": "object",
    "segment": "object",
    "revenue_usdm": "float64",
    "yoy_growth_rate": "float64",
    "revenue_mix_pct": "float64",
    "is_forecast": "bool",
    "scenario": "object",
    "source": "object",
}

REVENUE_REQUIRED = [
    "fiscal_year",
    "ticker",
    "segment",
    "revenue_usdm",
    "is_forecast",
    "scenario",
]

REVENUE_SEGMENTS = [
    "data_center",
    "gaming",
    "professional_viz",
    "automotive",
    "oem_other",
    "total",
]


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 2: costs
# Full income statement cost structure — historical and forecast
# PK: (fiscal_year, scenario)
# Constraint: gross_profit = revenue - cogs
#             ebit = gross_profit - total_opex
#             ebitda = ebit + da
# ══════════════════════════════════════════════════════════════════════════════

COSTS_SCHEMA: dict[str, str] = {
    "fiscal_year": "int64",
    "ticker": "object",
    "revenue_usdm": "float64",
    "cogs_usdm": "float64",
    "gross_profit_usdm": "float64",
    "gross_margin_pct": "float64",
    "rd_expense_usdm": "float64",
    "sga_expense_usdm": "float64",
    "acq_termination_usdm": "float64",
    "total_opex_usdm": "float64",
    "ebit_usdm": "float64",
    "ebit_margin_pct": "float64",
    "da_usdm": "float64",
    "ebitda_usdm": "float64",
    "ebitda_margin_pct": "float64",
    "interest_income_usdm": "float64",
    "interest_expense_usdm": "float64",
    "other_net_usdm": "float64",
    "ebt_usdm": "float64",
    "income_tax_usdm": "float64",
    "effective_tax_rate_pct": "float64",
    "net_income_usdm": "float64",
    "net_margin_pct": "float64",
    "is_forecast": "bool",
    "scenario": "object",
    "source": "object",
}

COSTS_REQUIRED = [
    "fiscal_year",
    "ticker",
    "revenue_usdm",
    "cogs_usdm",
    "gross_profit_usdm",
    "rd_expense_usdm",
    "sga_expense_usdm",
    "total_opex_usdm",
    "ebit_usdm",
    "ebt_usdm",
    "net_income_usdm",
    "is_forecast",
    "scenario",
]


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 3: working_capital
# Balance sheet WC drivers — historical and forecast
# PK: (fiscal_year, scenario)
# Constraint: nwc_assets = ar + inventory + prepaid
#             net_working_capital = nwc_assets - nwc_liabilities
#             change_in_nwc positive = NWC increase = cash OUTFLOW
# ══════════════════════════════════════════════════════════════════════════════

WORKING_CAPITAL_SCHEMA: dict[str, str] = {
    "fiscal_year": "int64",
    "ticker": "object",
    "accounts_receivable_usdm": "float64",
    "inventory_usdm": "float64",
    "prepaid_expenses_usdm": "float64",
    "accounts_payable_usdm": "float64",
    "accrued_liabilities_usdm": "float64",
    "nwc_assets_usdm": "float64",
    "nwc_liabilities_usdm": "float64",
    "net_working_capital_usdm": "float64",
    "change_in_nwc_usdm": "float64",
    "ar_days_dso": "float64",
    "inventory_days_dio": "float64",
    "ap_days_dpo": "float64",
    "cash_conversion_cycle": "float64",
    "revenue_usdm": "float64",
    "cogs_usdm": "float64",
    "is_forecast": "bool",
    "scenario": "object",
    "source": "object",
}

WORKING_CAPITAL_REQUIRED = [
    "fiscal_year",
    "ticker",
    "accounts_receivable_usdm",
    "inventory_usdm",
    "accounts_payable_usdm",
    "net_working_capital_usdm",
    "change_in_nwc_usdm",
    "ar_days_dso",
    "inventory_days_dio",
    "ap_days_dpo",
    "is_forecast",
    "scenario",
]


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 4: actuals
# Full consolidated historical financials — single source of truth
# PK: fiscal_year (no scenario — actuals are base only)
# Date range: FY2020–FY2025
# NaN is valid for CF columns FY2020–FY2021 (per architecture note)
# ══════════════════════════════════════════════════════════════════════════════

ACTUALS_SCHEMA: dict[str, str] = {
    "fiscal_year": "int64",
    "ticker": "object",
    # IS
    "revenue_usdm": "float64",
    "cogs_usdm": "float64",
    "gross_profit_usdm": "float64",
    "ebit_usdm": "float64",
    "ebitda_usdm": "float64",
    "net_income_usdm": "float64",
    "rd_expense_usdm": "float64",
    "sga_expense_usdm": "float64",
    "da_usdm": "float64",
    "interest_income_usdm": "float64",
    "interest_expense_usdm": "float64",
    "income_tax_usdm": "float64",
    # CF
    "cfo_usdm": "float64",
    "cfi_usdm": "float64",
    "cff_usdm": "float64",
    "capex_usdm": "float64",
    "fcf_usdm": "float64",
    "change_in_nwc_usdm": "float64",
    # BS
    "total_assets_usdm": "float64",
    "total_liabilities_usdm": "float64",
    "shareholders_equity_usdm": "float64",
    "cash_and_investments_usdm": "float64",
    "short_term_debt_usdm": "float64",
    "long_term_debt_usdm": "float64",
    "total_debt_usdm": "float64",
    "accounts_receivable_usdm": "float64",
    "inventory_usdm": "float64",
    "accounts_payable_usdm": "float64",
    # Derived ratios
    "gross_margin_pct": "float64",
    "ebit_margin_pct": "float64",
    "net_margin_pct": "float64",
    "rd_pct_revenue": "float64",
    "capex_pct_revenue": "float64",
    "source": "object",
}

ACTUALS_REQUIRED = [
    "fiscal_year",
    "ticker",
    "revenue_usdm",
    "cogs_usdm",
    "gross_profit_usdm",
    "ebit_usdm",
    "net_income_usdm",
    "total_assets_usdm",
    "total_liabilities_usdm",
    "shareholders_equity_usdm",
]


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

_SCHEMA_MAP = {
    "revenue": (REVENUE_SCHEMA, REVENUE_REQUIRED),
    "costs": (COSTS_SCHEMA, COSTS_REQUIRED),
    "working_capital": (WORKING_CAPITAL_SCHEMA, WORKING_CAPITAL_REQUIRED),
    "actuals": (ACTUALS_SCHEMA, ACTUALS_REQUIRED),
}


def validate_schema(df: pd.DataFrame, table_name: str) -> list[str]:
    """
    Validate a DataFrame against its canonical schema.

    Args:
        df:          DataFrame to validate
        table_name:  One of 'revenue', 'costs', 'working_capital', 'actuals'

    Returns:
        List of error strings (empty = PASS)
    """
    if table_name not in _SCHEMA_MAP:
        return [f"Unknown table: {table_name}"]

    schema, required = _SCHEMA_MAP[table_name]
    errors: list[str] = []

    # Check required columns present
    for col in required:
        if col not in df.columns:
            errors.append(f"[{table_name}] Missing required column: {col}")

    # Check no extra unexpected columns (warn only — not error)
    unexpected = [c for c in df.columns if c not in schema]
    if unexpected:
        # Not an error — just informational, logged by caller
        pass

    # Check dtypes for columns that are present
    for col, expected_dtype in schema.items():
        if col not in df.columns:
            continue
        actual = str(df[col].dtype)
        # Loose check — allow int64/Int64 interchange, object/string
        if expected_dtype == "int64" and actual not in ("int64", "Int64", "int32"):
            errors.append(
                f"[{table_name}] Column '{col}': expected int64, got {actual}"
            )
        elif (
            expected_dtype == "float64"
            and "float" not in actual
            and "int" not in actual
        ):
            errors.append(
                f"[{table_name}] Column '{col}': expected float64, got {actual}"
            )
        elif expected_dtype == "bool" and actual not in ("bool", "boolean", "object"):
            errors.append(f"[{table_name}] Column '{col}': expected bool, got {actual}")

    return errors


def get_required_columns(table_name: str) -> list[str]:
    """Return the required column list for a canonical table."""
    if table_name not in _SCHEMA_MAP:
        raise ValueError(f"Unknown canonical table: {table_name}")
    return _SCHEMA_MAP[table_name][1]


def get_schema(table_name: str) -> dict[str, str]:
    """Return the full schema dict for a canonical table."""
    if table_name not in _SCHEMA_MAP:
        raise ValueError(f"Unknown canonical table: {table_name}")
    return _SCHEMA_MAP[table_name][0]
