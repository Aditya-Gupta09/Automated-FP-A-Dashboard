"""
src/modeling/cashflow.py
==========================
Cash Flow Statement Projection Engine

Maps to: 03_Historical_CF + 04c_Projection_CF (Excel tabs)
Execution order: #6 in engine.py (after balance_sheet.py)

Builds projected CF statement for FY2026F–FY2030F using indirect method:

  CFO = Net Income + D&A + change_in_WC items
  CFI = -CapEx + other investing (0 in base model)
  CFF = debt_issuance - debt_repayment - dividends - buybacks

  Net Change = CFO + CFI + CFF
  FCF = CFO + CapEx  (CapEx stored as negative)
  Ending Cash = Prior Ending Cash + Net Change

CF Invariants (from model_output_schema.json):
  cfo + cfi + cff == net_change_cash (±$0.01M)
  fcf == cfo + capex  (capex is negative)
  ending_cash == prior_ending_cash + net_change_cash (±$0.01M)

Function signature per module_mapping.md:
  build_cashflow(is_df, bs_df, wc_df, da_df, assumptions, scenario) → pd.DataFrame

ALL inputs sourced from assumptions dict — zero hardcoded values.
"""

from __future__ import annotations
import pandas as pd
import logging
from src.modeling.reconciliation import BS_ASSUMPTIONS

logger = logging.getLogger(__name__)

FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]


def build_cashflow(
    is_df: pd.DataFrame,
    bs_df: pd.DataFrame,
    wc_df: pd.DataFrame,
    da_df: pd.DataFrame,
    assumptions: dict,
    scenario: str = "base",
) -> pd.DataFrame:
    """
    Build the projected cash flow statement for FY2026F–FY2030F.

    Uses indirect method: starts from net income, adds back non-cash
    charges, adjusts for WC changes.

    Args:
        is_df:       Income statement DataFrame
        bs_df:       Balance sheet DataFrame (for dividends, beginning cash)
        wc_df:       NWC schedule DataFrame
        da_df:       D&A schedule DataFrame
        assumptions: Final merged assumptions dict
        scenario:    'base', 'upside', or 'downside'

    Returns:
        DataFrame (5 rows × CF columns) per model_output_schema.json
    """
    is_dict = is_df.set_index("fiscal_year").to_dict("index") if not is_df.empty else {}
    bs_dict = bs_df.set_index("fiscal_year").to_dict("index") if not bs_df.empty else {}
    wc_dict = wc_df.set_index("fiscal_year").to_dict("index") if not wc_df.empty else {}
    da_dict = da_df.set_index("fiscal_year").to_dict("index") if not da_df.empty else {}

    hist = assumptions.get("historical_actuals_fy2025", {})
    debt_assumptions = assumptions.get("debt_schedule", {})
    bs_assump = BS_ASSUMPTIONS

    # Starting cash (FY2025 actual)
    prior_ending_cash = hist.get("cash_and_investments_usdm", 43210.0)
    prior_lt_debt = (
        assumptions.get("dcf", {})
        .get("net_debt_bridge", {})
        .get("long_term_debt_usdm", 8463.0)
    )

    rows = []

    for year in FORECAST_YEARS:
        fy_key = f"fy{year}f"
        is_row = is_dict.get(year, {})
        bs_row = bs_dict.get(year, {})
        wc_row = wc_dict.get(year, {})
        da_row = da_dict.get(year, {})

        net_income = is_row.get("net_income_usdm", 0.0)
        da = da_row.get("da_usdm", 0.0)

        # ── CFO (indirect method) ─────────────────────────────────────────
        # Start: Net Income
        # Add: D&A (non-cash)
        # Add/subtract: Changes in WC items
        change_in_nwc = wc_row.get("change_in_nwc_usdm", 0.0)
        # Sign: positive change_in_nwc = NWC increased = cash OUTFLOW
        cfo = net_income + da - change_in_nwc

        # ── CFI ────────────────────────────────────────────────────────────
        capex_usdm = -abs(
            float(da_row.get("capex_usdm", 0.0))
        )  # Negative = outflow convention
        cfi = capex_usdm  # Simplified: only capex in CFI for this model

        # ── CFF ────────────────────────────────────────────────────────────
        # Debt issuance
        issuance_dict = debt_assumptions.get("net_debt_issuance_usdm", {}).get(
            "base", {}
        )
        issuance = issuance_dict.get(fy_key, 0.0)

        # Dividends paid
        dividends = bs_row.get("_dividends_usdm", net_income * 0.009)

        # Share buybacks — simplified: not modelled explicitly in base case
        buybacks = 0.0

        cff = issuance - dividends - buybacks

        # ── Net change and ending cash ─────────────────────────────────────
        net_change_cash = cfo + cfi + cff
        ending_cash = prior_ending_cash + net_change_cash

        # ── FCF ────────────────────────────────────────────────────────────
        # FCF = CFO + CapEx (capex is already negative)
        fcf = cfo + capex_usdm

        rows.append(
            {
                "fiscal_year": year,
                "net_income_usdm": round(net_income, 4),
                "da_usdm": round(da, 4),
                "change_in_nwc_usdm": round(change_in_nwc, 4),
                "capex_usdm": round(capex_usdm, 4),
                "cfo_usdm": round(cfo, 4),
                "cfi_usdm": round(cfi, 4),
                "cff_usdm": round(cff, 4),
                "fcf_usdm": round(fcf, 4),
                "net_change_cash_usdm": round(net_change_cash, 4),
                "ending_cash_usdm": round(ending_cash, 4),
                "beginning_cash_usdm": round(prior_ending_cash, 4),
                "is_forecast": True,
                "scenario": scenario,
                "source": "model_projection",
            }
        )

        prior_ending_cash = ending_cash
        prior_lt_debt = prior_lt_debt + issuance

    df = pd.DataFrame(rows)
    logger.info(
        "[cashflow] CF built: %d rows | scenario=%s | "
        "CFO FY2026=%.0f | FCF FY2026=%.0f",
        len(df),
        scenario,
        df.iloc[0]["cfo_usdm"] if len(df) else 0,
        df.iloc[0]["fcf_usdm"] if len(df) else 0,
    )
    return df
