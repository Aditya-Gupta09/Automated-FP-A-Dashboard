"""
src/modeling/fcff.py
======================
Free Cash Flow to Firm (FCFF) Schedule

Maps to: 05a_FCFF (Excel tab)
Execution order: #7 in engine.py (after cashflow.py)

Formula (from assumptions.json fcff_construction):
  NOPAT  = EBIT × (1 - ETR)          [tax applied to EBIT, not EBT]
  FCFF   = NOPAT + D&A - |CapEx| - ΔNWC

Sign convention (per data_contracts.md):
  capex_in_formula:    positive absolute value
  change_in_nwc:       positive increase = cash outflow (reduces FCFF)

FCFF ≠ FCF:
  FCF  = CFO - |CapEx|         (levered, after interest & tax on EBT)
  FCFF = NOPAT + DA - CapEx - ΔNWC  (unlevered, tax on EBIT)

FCFF is used by dcf_valuation.py for the discounted cash flow analysis.
FCF (levered) is reported in the cash flow statement.

Function signature per module_mapping.md:
  build_fcff(is_df, da_df, wc_df, assumptions, scenario) → pd.DataFrame
"""

from __future__ import annotations
import pandas as pd
import logging

logger = logging.getLogger(__name__)

FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]


def build_fcff(
    is_df: pd.DataFrame,
    da_df: pd.DataFrame,
    wc_df: pd.DataFrame,
    assumptions: dict,
    scenario: str = "base",
) -> pd.DataFrame:
    """
    Build the FCFF schedule for FY2026F–FY2030F.

    Maps to: 05a_FCFF rows 13–20

    Args:
        is_df:       Income statement DataFrame (output of income_statement.py)
                     Must contain: fiscal_year, revenue_usdm, ebit_usdm,
                     effective_tax_rate_pct
        da_df:       D&A schedule DataFrame (output of depreciation.py)
                     Must contain: fiscal_year, da_usdm, capex_usdm
        wc_df:       NWC schedule DataFrame (output of working_capital.py)
                     Must contain: fiscal_year, change_in_nwc_usdm
        assumptions: Final merged assumptions dict
        scenario:    'base', 'upside', or 'downside'

    Returns:
        DataFrame (5 rows) with columns per model_output_schema.json:
            fiscal_year, revenue_usdm, ebit_usdm, nopat_usdm,
            da_usdm, capex_usdm, change_in_nwc_usdm,
            fcff_usdm, pv_fcff_usdm, projection_year
    """
    from src.modeling.wacc import compute_wacc

    # Build lookup dicts
    is_dict = is_df.set_index("fiscal_year").to_dict("index") if not is_df.empty else {}
    da_dict = da_df.set_index("fiscal_year").to_dict("index") if not da_df.empty else {}
    wc_dict = wc_df.set_index("fiscal_year").to_dict("index") if not wc_df.empty else {}

    # WACC for discounting
    wacc_result = compute_wacc(assumptions)
    wacc = wacc_result["wacc_computed"]

    # CapEx from assumptions (as % of revenue)
    capex_assumptions = assumptions.get("capex", {})
    scenario_key = f"{scenario}_case"
    capex_pct_dict = capex_assumptions.get(
        scenario_key, capex_assumptions.get("base_case", {})
    )

    rows = []
    for proj_year_num, year in enumerate(FORECAST_YEARS, start=1):
        fy_key = f"fy{year}f"
        is_row = is_dict.get(year, {})
        da_row = da_dict.get(year, {})
        wc_row = wc_dict.get(year, {})

        revenue = is_row.get("revenue_usdm", 0.0)
        ebit = is_row.get("ebit_usdm", 0.0)
        etr = is_row.get("effective_tax_rate_pct", 0.15)
        da = da_row.get("da_usdm", 0.0)

        # CapEx — use D&A schedule value (positive absolute) if available
        # otherwise compute from revenue × capex_pct
        capex_pct = capex_pct_dict.get(fy_key, 0.030)
        capex_abs = revenue * capex_pct  # Positive absolute value for formula

        # ΔNWC — positive = NWC increased = cash outflow
        change_in_nwc = wc_row.get("change_in_nwc_usdm", 0.0)

        # ── NOPAT = EBIT × (1 - ETR) ──────────────────────────────────────
        # Tax applied to EBIT, not EBT — this is unlevered (ignores interest)
        nopat = ebit * (1 - etr)

        # ── FCFF = NOPAT + D&A - CapEx - ΔNWC ────────────────────────────
        # capex_abs is positive absolute value (outflow subtracted)
        # change_in_nwc positive = outflow (subtracted)
        fcff = nopat + da - capex_abs - change_in_nwc

        # ── PV of FCFF = FCFF / (1 + WACC)^t ────────────────────────────
        # End-of-year discounting convention (confirmed in dcf_valuation.py docs)
        pv_fcff = fcff / ((1 + wacc) ** proj_year_num)

        rows.append(
            {
                "fiscal_year": year,
                "ticker": "NVDA",
                "revenue_usdm": round(revenue, 4),
                "ebit_usdm": round(ebit, 4),
                "nopat_usdm": round(nopat, 4),
                "da_usdm": round(da, 4),
                "capex_usdm": round(capex_abs, 4),  # Positive in FCFF context
                "change_in_nwc_usdm": round(change_in_nwc, 4),
                "fcff_usdm": round(fcff, 4),
                "pv_fcff_usdm": round(pv_fcff, 4),
                "projection_year": proj_year_num,
                "wacc_used": round(wacc, 6),
                "effective_tax_rate": round(etr, 6),
                "is_forecast": True,
                "scenario": scenario,
                "source": "model_projection",
            }
        )

    df = pd.DataFrame(rows)

    sum_pv = df["pv_fcff_usdm"].sum()
    logger.info(
        "[fcff] FCFF built: %d rows | scenario=%s | "
        "FCFF FY2026=%.0f | Sum PV FCF=%.0f | WACC=%.4f",
        len(df),
        scenario,
        df.iloc[0]["fcff_usdm"] if len(df) else 0,
        sum_pv,
        wacc,
    )
    return df
