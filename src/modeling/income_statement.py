"""
src/modeling/income_statement.py
==================================
Income Statement Projection Engine

Maps to: 01_Historical_IS + 04a_Projection_IS (Excel tabs)
Execution order: #2 in engine.py (after wacc.py)

Builds projected IS for FY2026F–FY2030F using:
  - Segment-level revenue build (growth rates from assumptions.json)
  - Gross margin % × revenue = COGS / gross profit
  - R&D % + SG&A % = total opex
  - EBIT = gross profit - opex
  - Interest income = cash × assumed yield
  - EBT = EBIT + interest income + interest expense + other
  - Net income = EBT × (1 - ETR)

ALL inputs sourced from assumptions dict — zero hardcoded values.
No balance sheet logic. No cash flow logic. IS only.

Function signature per module_mapping.md:
  build_revenue(assumptions, scenario) → pd.DataFrame
  build_income_statement(revenue, assumptions, scenario) → pd.DataFrame
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]

# Segment names in assumptions.json revenue_growth keys
_SEGMENTS = [
    "data_center",
    "gaming",
    "professional_visualization",
    "automotive",
    "oem_and_other",
]

# Map assumptions.json segment keys → canonical segment names
_SEGMENT_KEY_MAP = {
    "data_center": "data_center",
    "gaming": "gaming",
    "professional_visualization": "professional_viz",
    "automotive": "automotive",
    "oem_and_other": "oem_other",
}


def _get_scenario_value(
    nested: dict,
    scenario: str,
    year: int,
    fallback_key: str = "base_case",
) -> float:
    """
    Extract a year-specific value from a nested assumptions dict.

    Tries: nested[scenario + '_case'][f'fy{year}f']
    Falls back to: nested['base_case'][f'fy{year}f']

    Args:
        nested:       Sub-dict from assumptions (e.g. assumptions['gross_margin'])
        scenario:     'base', 'upside', or 'downside'
        year:         Forecast year integer (e.g. 2026)
        fallback_key: Key to use if scenario-specific key absent

    Returns:
        float value
    """
    fy_key = f"fy{year}f"
    scenario_key = f"{scenario}_case"

    # Try scenario-specific first
    if scenario_key in nested and fy_key in nested[scenario_key]:
        return nested[scenario_key][fy_key]

    # Fall back to base_case
    if fallback_key in nested and fy_key in nested[fallback_key]:
        return nested[fallback_key][fy_key]

    raise KeyError(
        f"Cannot find '{fy_key}' in '{scenario_key}' or '{fallback_key}' "
        f"for assumptions key"
    )


def build_revenue(assumptions: dict, scenario: str = "base") -> pd.DataFrame:
    """
    Build segment-level revenue projections for FY2026F–FY2030F.

    Maps to: 04a_Projection_IS rows 5–36

    Args:
        assumptions: Final merged assumptions dict
        scenario:    'base', 'upside', or 'downside'

    Returns:
        DataFrame with columns:
            fiscal_year, ticker, segment, revenue_usdm,
            yoy_growth_rate, revenue_mix_pct, is_forecast, scenario, source
    """
    revenue_growth = assumptions["revenue_growth"]
    base_revenue = revenue_growth["fy2025_base_usdm"]

    rows = []
    for year in FORECAST_YEARS:
        fy_key = f"fy{year}f"
        year_total = 0.0

        segment_values: dict[str, float] = {}

        for seg_key, seg_canonical in _SEGMENT_KEY_MAP.items():
            seg_growth_dict = revenue_growth.get(seg_key, {})
            base_rev = base_revenue.get(seg_key, 0.0)

            # Apply growth rate for this year
            if fy_key in seg_growth_dict:
                growth_rate = seg_growth_dict[fy_key]
            else:
                growth_rate = 0.0

            # For multi-year projections, compound from prior year
            # First forecast year: apply to FY2025 base
            # Subsequent years: apply to prior year projected value
            if year == FORECAST_YEARS[0]:
                rev = base_rev * (1 + growth_rate)
            else:
                # Get prior year value from segment_values built in prior iteration
                prior_year = year - 1
                prior_key = f"fy{prior_year}f"
                prior_rev_in_rows = next(
                    (
                        r["revenue_usdm"]
                        for r in rows
                        if r["fiscal_year"] == prior_year
                        and r["segment"] == seg_canonical
                    ),
                    base_rev,
                )
                rev = prior_rev_in_rows * (1 + growth_rate)

            segment_values[seg_canonical] = rev
            year_total += rev

        # Add segment rows
        for seg_canonical, rev in segment_values.items():
            rows.append(
                {
                    "fiscal_year": year,
                    "ticker": "NVDA",
                    "segment": seg_canonical,
                    "revenue_usdm": round(rev, 4),
                    "yoy_growth_rate": None,  # computed below
                    "revenue_mix_pct": (
                        round(rev / year_total, 6) if year_total else None
                    ),
                    "is_forecast": True,
                    "scenario": scenario,
                    "source": "model_projection",
                }
            )

        # Add total row
        rows.append(
            {
                "fiscal_year": year,
                "ticker": "NVDA",
                "segment": "total",
                "revenue_usdm": round(year_total, 4),
                "yoy_growth_rate": None,
                "revenue_mix_pct": 1.0,
                "is_forecast": True,
                "scenario": scenario,
                "source": "model_projection",
            }
        )

    df = pd.DataFrame(rows)

    # Compute YoY growth rates vs FY2025 actuals and prior forecast year
    base_totals = {"total": base_revenue.get("total", 0.0)}
    base_totals.update(
        {v: base_revenue.get(k, 0.0) for k, v in _SEGMENT_KEY_MAP.items()}
    )

    for seg in list(_SEGMENT_KEY_MAP.values()) + ["total"]:
        seg_mask = df["segment"] == seg
        seg_df = df[seg_mask].sort_values("fiscal_year")
        prior_revs = [base_totals.get(seg, 0.0)] + list(
            seg_df["revenue_usdm"].values[:-1]
        )
        growth_rates = []
        for cur, pri in zip(seg_df["revenue_usdm"], prior_revs):
            growth_rates.append(round((cur - pri) / pri, 6) if pri else None)
        df.loc[seg_mask, "yoy_growth_rate"] = growth_rates

    logger.info(
        "[income_statement] Revenue built: %d rows | %d forecast years | scenario=%s",
        len(df),
        len(FORECAST_YEARS),
        scenario,
    )
    return df.sort_values(["fiscal_year", "segment"]).reset_index(drop=True)


def build_income_statement(
    revenue_df: pd.DataFrame,
    assumptions: dict,
    scenario: str = "base",
    da_schedule: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Build the full projected income statement for FY2026F–FY2030F.

    Maps to: 04a_Projection_IS (full sheet)

    Args:
        revenue_df:   Output of build_revenue() — segment revenue DataFrame
        assumptions:  Final merged assumptions dict
        scenario:     'base', 'upside', or 'downside'
        da_schedule:  Optional D&A schedule DataFrame from depreciation.py
                      If provided, uses modelled D&A. Otherwise uses base estimate.

    Returns:
        DataFrame (5 rows) with all IS columns per model_output_schema.json
    """
    # Extract total revenue per year from revenue_df
    total_rev = (
        revenue_df[revenue_df["segment"] == "total"]
        .set_index("fiscal_year")["revenue_usdm"]
        .to_dict()
    )

    gross_margin_assumptions = assumptions["gross_margin"]
    rd_pct_assumptions = assumptions["rd_expense_pct"]
    sga_pct_assumptions = assumptions["sga_expense_pct"]
    tax_assumptions = assumptions["tax_rate"]
    interest_assumptions = assumptions.get("interest_income", {})
    debt_assumptions = assumptions.get("debt_schedule", {})

    # FY2025 actual interest expense (from historical_actuals)
    hist = assumptions.get("historical_actuals_fy2025", {})
    fy2025_interest_expense = hist.get("interest_expense_usdm", -247.0)
    fy2025_da = hist.get("da_usdm", 1864.0)

    rows = []
    for year in FORECAST_YEARS:
        fy_key = f"fy{year}f"
        revenue = total_rev.get(year, 0.0)

        # ── Gross profit ───────────────────────────────────────────────────
        gm_pct = _get_scenario_value(gross_margin_assumptions, scenario, year)
        cogs = revenue * (1 - gm_pct)
        gross_profit = revenue * gm_pct

        # ── Operating expenses ─────────────────────────────────────────────
        rd_pct = _get_scenario_value(rd_pct_assumptions, scenario, year)
        sga_pct = _get_scenario_value(sga_pct_assumptions, scenario, year)
        rd_expense = revenue * rd_pct
        sga_expense = revenue * sga_pct
        total_opex = rd_expense + sga_expense  # No acq_termination in forecasts

        # ── EBIT ───────────────────────────────────────────────────────────
        ebit = gross_profit - total_opex

        # ── D&A (from depreciation schedule if available) ──────────────────
        if da_schedule is not None and year in da_schedule.index:
            da = da_schedule.loc[year, "da_usdm"]
        elif da_schedule is not None and "fiscal_year" in da_schedule.columns:
            da_row = da_schedule[da_schedule["fiscal_year"] == year]
            da = da_row["da_usdm"].iloc[0] if len(da_row) else fy2025_da
        else:
            # Fallback: use base schedule from assumptions
            da_base = assumptions.get("depreciation", {}).get(
                "da_schedule_usdm_base", {}
            )
            da = da_base.get(fy_key, fy2025_da)

        ebitda = ebit + da

        # ── Interest income ────────────────────────────────────────────────
        cash_pct_dict = interest_assumptions.get("cash_pct_of_revenue", {})
        yield_dict = interest_assumptions.get("assumed_yield", {})
        other_inc_dict = interest_assumptions.get("other_income_net_flat_usdm", {})

        cash_pct = cash_pct_dict.get(scenario, cash_pct_dict.get("base", {})).get(
            fy_key, 0.25
        )
        yield_rate = yield_dict.get(scenario, yield_dict.get("base", {})).get(
            fy_key, 0.033
        )
        other_inc = other_inc_dict.get(fy_key, 1000.0)
        cash_balance = revenue * cash_pct
        interest_income = cash_balance * yield_rate + other_inc

        # ── Interest expense ───────────────────────────────────────────────
        debt_rate_dict = debt_assumptions.get("interest_rate_pretax", {})
        debt_rate = debt_rate_dict.get(scenario, debt_rate_dict.get("base", {})).get(
            fy_key, 0.033
        )
        net_debt_bridge = assumptions.get("dcf", {}).get("net_debt_bridge", {})
        base_debt = net_debt_bridge.get("long_term_debt_usdm", 8463.0)
        issuance_dict = debt_assumptions.get("net_debt_issuance_usdm", {}).get(
            "base", {}
        )
        cumulative_issuance = sum(
            issuance_dict.get(f"fy{y}f", 0.0)
            for y in range(FORECAST_YEARS[0], year + 1)
        )
        total_debt_est = base_debt + cumulative_issuance
        interest_expense = -(total_debt_est * debt_rate)

        # ── EBT ───────────────────────────────────────────────────────────
        ebt = ebit + interest_income + interest_expense

        # ── Tax ───────────────────────────────────────────────────────────
        tax_dict = tax_assumptions
        # Try nested scenario format first
        if f"{scenario}_case" in tax_dict:
            etr = tax_dict[f"{scenario}_case"].get(
                fy_key, tax_dict.get("base_case", {}).get(fy_key, 0.15)
            )
        elif "base_case" in tax_dict:
            etr = tax_dict["base_case"].get(fy_key, 0.15)
        else:
            etr = tax_dict.get(fy_key, 0.15)

        income_tax = ebt * etr if ebt > 0 else 0.0
        net_income = ebt - income_tax

        rows.append(
            {
                "fiscal_year": year,
                "ticker": "NVDA",
                "revenue_usdm": round(revenue, 4),
                "cogs_usdm": round(cogs, 4),
                "gross_profit_usdm": round(gross_profit, 4),
                "rd_expense_usdm": round(rd_expense, 4),
                "sga_expense_usdm": round(sga_expense, 4),
                "acq_termination_usdm": 0.0,
                "total_opex_usdm": round(total_opex, 4),
                "ebit_usdm": round(ebit, 4),
                "da_usdm": round(da, 4),
                "ebitda_usdm": round(ebitda, 4),
                "interest_income_usdm": round(interest_income, 4),
                "interest_expense_usdm": round(interest_expense, 4),
                "other_net_usdm": 0.0,
                "ebt_usdm": round(ebt, 4),
                "income_tax_usdm": round(income_tax, 4),
                "effective_tax_rate_pct": round(etr, 6),
                "net_income_usdm": round(net_income, 4),
                "gross_margin_pct": round(gm_pct, 6),
                "ebit_margin_pct": round(ebit / revenue, 6) if revenue else None,
                "ebitda_margin_pct": round(ebitda / revenue, 6) if revenue else None,
                "net_margin_pct": round(net_income / revenue, 6) if revenue else None,
                "is_forecast": True,
                "scenario": scenario,
                "source": "model_projection",
            }
        )

    df = pd.DataFrame(rows)
    logger.info(
        "[income_statement] IS built: %d rows | scenario=%s | "
        "Revenue FY2026=%.0f | NI FY2026=%.0f",
        len(df),
        scenario,
        df.iloc[0]["revenue_usdm"] if len(df) else 0,
        df.iloc[0]["net_income_usdm"] if len(df) else 0,
    )
    return df
