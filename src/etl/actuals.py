"""
src/etl/actuals.py
===================
Canonical Table 4 builder — actuals

Produces the full consolidated historical financials table by merging
IS + BS + CF into a single annual DataFrame.

Rules (canonical_schema.md Table 4):
  - 1 row per fiscal year (FY2020–FY2025)
  - No forecasts — actuals only (is_forecast = False)
  - NaN is valid for CF columns FY2020–FY2021 (data genuinely absent)
  - BS must balance: total_assets == total_liabilities + shareholders_equity

Architecture slot: transformer.py calls this builder.
No financial calculations here — pure structural assembly.
"""

from __future__ import annotations
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Columns to keep from each statement (canonical names only)
_IS_COLS = [
    "fiscal_year",
    "ticker",
    "revenue_usdm",
    "cogs_usdm",
    "gross_profit_usdm",
    "rd_expense_usdm",
    "sga_expense_usdm",
    "acq_termination_usdm",
    "total_opex_usdm",
    "ebit_usdm",
    "da_usdm",
    "ebitda_usdm",
    "interest_income_usdm",
    "interest_expense_usdm",
    "other_net_usdm",
    "ebt_usdm",
    "income_tax_usdm",
    "net_income_usdm",
    "gross_margin_pct",
    "ebit_margin_pct",
    "ebitda_margin_pct",
    "net_margin_pct",
    "rd_pct_revenue",
    "effective_tax_rate_pct",
]

_BS_COLS = [
    "fiscal_year",
    "cash_only_usdm",
    "short_term_investments_usdm",
    "cash_and_investments_usdm",
    "accounts_receivable_usdm",
    "inventory_usdm",
    "prepaid_expenses_usdm",
    "total_current_assets_usdm",
    "ppe_net_usdm",
    "operating_lease_assets_usdm",
    "goodwill_usdm",
    "intangible_assets_usdm",
    "lt_deferred_tax_assets_usdm",
    "other_assets_usdm",
    "total_assets_usdm",
    "accounts_payable_usdm",
    "accrued_liabilities_usdm",
    "short_term_debt_usdm",
    "current_lease_liabilities_usdm",
    "income_taxes_payable_usdm",
    "current_deferred_revenue_usdm",
    "other_current_liabilities_usdm",
    "total_current_liabilities_usdm",
    "long_term_debt_usdm",
    "lt_lease_liabilities_usdm",
    "lt_deferred_revenue_usdm",
    "lt_deferred_tax_liabilities_usdm",
    "other_lt_liabilities_usdm",
    "total_liabilities_usdm",
    "common_stock_usdm",
    "apic_usdm",
    "retained_earnings_usdm",
    "treasury_stock_usdm",
    "aoci_usdm",
    "shareholders_equity_usdm",
    "total_liabilities_equity_usdm",
]

_CF_COLS = [
    "fiscal_year",
    "stock_based_comp_usdm",
    "deferred_taxes_usdm",
    "chg_accounts_receivable_usdm",
    "chg_inventory_usdm",
    "chg_prepaid_other_usdm",
    "chg_accounts_payable_usdm",
    "chg_accrued_liabilities_usdm",
    "change_in_nwc_usdm",
    "cfo_usdm",
    "capex_usdm",
    "cfi_usdm",
    "cff_usdm",
    "net_change_cash_usdm",
    "fcf_usdm",
    "cash_beginning_usdm",
    "cash_ending_usdm",
]

# Derived ratio columns to add if missing
_DERIVED_RATIO_COLS = {
    "capex_pct_revenue": ("capex_usdm", "revenue_usdm"),
}


def build_actuals(
    is_df: pd.DataFrame,
    bs_df: pd.DataFrame,
    cf_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge IS + BS + CF DataFrames into the canonical actuals table.

    IS is the spine — all 6 years (FY2020–2025).
    BS adds balance sheet columns (FY2021–2025, NaN for FY2020).
    CF adds cash flow columns (FY2022–2025, NaN for FY2020–2021 by design).

    Args:
        is_df: Cleaned, transformed IS DataFrame (canonical column names)
        bs_df: Cleaned, transformed BS DataFrame (canonical column names)
        cf_df: Cleaned, transformed CF DataFrame (canonical column names)

    Returns:
        actuals DataFrame sorted by fiscal_year ascending.
        Columns: all fields from canonical_schema.md Table 4.
    """
    # ── 1. Start with IS as the spine ──────────────────────────────────────
    is_keep = [c for c in _IS_COLS if c in is_df.columns]
    actuals = is_df[is_keep].copy()
    logger.info(
        "[actuals] IS spine: %d rows × %d cols", len(actuals), len(actuals.columns)
    )

    # ── 2. Merge BS columns ─────────────────────────────────────────────────
    bs_keep = [c for c in _BS_COLS if c in bs_df.columns]
    # Avoid duplicate columns (fiscal_year is the join key)
    bs_merge = [c for c in bs_keep if c not in actuals.columns or c == "fiscal_year"]
    actuals = actuals.merge(
        bs_df[bs_merge],
        on="fiscal_year",
        how="left",
    )
    logger.info("[actuals] After BS merge: %d cols", len(actuals.columns))

    # ── 3. Merge CF columns ─────────────────────────────────────────────────
    cf_keep = [c for c in _CF_COLS if c in cf_df.columns]
    cf_merge = [c for c in cf_keep if c not in actuals.columns or c == "fiscal_year"]
    actuals = actuals.merge(
        cf_df[cf_merge],
        on="fiscal_year",
        how="left",
    )
    logger.info("[actuals] After CF merge: %d cols", len(actuals.columns))

    # ── 4. Derive missing ratio columns ────────────────────────────────────
    for ratio_col, (num_col, den_col) in _DERIVED_RATIO_COLS.items():
        if ratio_col not in actuals.columns:
            if num_col in actuals.columns and den_col in actuals.columns:
                denom = actuals[den_col].replace(0, float("nan"))
                actuals[ratio_col] = actuals[num_col].abs() / denom

    # ── 5. Derive total_debt if missing ────────────────────────────────────
    if "total_debt_usdm" not in actuals.columns:
        std = actuals.get("short_term_debt_usdm", pd.Series(0, index=actuals.index))
        ltd = actuals.get("long_term_debt_usdm", pd.Series(0, index=actuals.index))
        actuals["total_debt_usdm"] = std.fillna(0) + ltd.fillna(0)

    # ── 6. Ensure metadata columns ─────────────────────────────────────────
    if "ticker" not in actuals.columns:
        actuals.insert(1, "ticker", "NVDA")
    actuals["is_forecast"] = False
    actuals["scenario"] = "base"
    actuals["source"] = "10-K (EDGAR)"

    # ── 7. Sort and reset index ─────────────────────────────────────────────
    actuals = actuals.sort_values("fiscal_year").reset_index(drop=True)

    logger.info(
        "[actuals] Final table: %d rows × %d cols | FY%s–FY%s",
        len(actuals),
        len(actuals.columns),
        actuals["fiscal_year"].min(),
        actuals["fiscal_year"].max(),
    )
    return actuals
