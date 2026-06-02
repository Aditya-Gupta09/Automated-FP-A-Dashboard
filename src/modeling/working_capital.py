"""
src/modeling/working_capital.py
================================
Forecast working capital schedule for FY2026-FY2030.

Builds the modeling-layer NWC schedule consumed by engine.py, balance_sheet.py,
cashflow.py, and fcff.py.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]


def _get_scenario_series(config: dict, scenario: str, default_key: str) -> dict:
    return config.get(scenario, config.get(default_key, {}))


def _get_year_value(
    config: dict, scenario: str, fy_key: str, default_key: str
) -> float:
    series = _get_scenario_series(config, scenario, default_key)
    return float(series.get(fy_key, 0.0))


def _get_scalar_value(
    config: dict, scenario: str, default_key: str, fallback: float = 1.0
) -> float:
    if not isinstance(config, dict):
        return fallback
    if scenario in config:
        return float(config[scenario])
    if default_key in config:
        return float(config[default_key])
    return fallback


def build_nwc_schedule(
    is_df: pd.DataFrame,
    assumptions: dict,
    scenario: str = "base",
) -> pd.DataFrame:
    """
    Build the projected working capital schedule for FY2026-FY2030.

    Args:
        is_df: Projected income statement DataFrame.
        assumptions: Final merged assumptions dict.
        scenario: "base", "upside", or "downside".

    Returns:
        DataFrame with forecast working-capital balances and delta NWC.
    """
    wc_assumptions = assumptions.get("working_capital", {})
    hist = assumptions.get("historical_actuals_fy2025", {})
    is_dict = is_df.set_index("fiscal_year").to_dict("index") if not is_df.empty else {}

    prior_nwc = float(hist.get("nwc_usdm", 0.0))
    change_in_nwc_prev = 0.0
    rows = []

    for year in FORECAST_YEARS:
        fy_key = f"fy{year}f"
        is_row = is_dict.get(year, {})

        revenue = float(is_row.get("revenue_usdm", 0.0))
        cogs = float(is_row.get("cogs_usdm", 0.0))
        total_opex = float(is_row.get("total_opex_usdm", 0.0))

        dso_days = _get_year_value(
            wc_assumptions.get("dso_days", {}), scenario, fy_key, "base"
        )
        dio_days = _get_year_value(
            wc_assumptions.get("dio_days", {}), scenario, fy_key, "base"
        )
        dpo_days = _get_year_value(
            wc_assumptions.get("dpo_days", {}), scenario, fy_key, "base"
        )
        prepaid_pct = _get_year_value(
            wc_assumptions.get("prepaid_pct_of_opex", {}), scenario, fy_key, "base"
        )
        accrued_pct = _get_year_value(
            wc_assumptions.get("accrued_pct_of_cogs_plus_opex", {}),
            scenario,
            fy_key,
            "base",
        )

        wc_scale = _get_scalar_value(
            wc_assumptions.get("operating_balance_scale", {}),
            scenario,
            "base",
            fallback=1.0,
        )

        accounts_receivable = wc_scale * revenue * dso_days / 365.0
        inventory = wc_scale * cogs * dio_days / 365.0
        accounts_payable = wc_scale * cogs * dpo_days / 365.0

        prepaid_expenses = total_opex * prepaid_pct
        accrued_liabilities = (cogs + total_opex) * accrued_pct

        # Core operating NWC only
        net_working_capital = accounts_receivable + inventory - accounts_payable
        if year == FORECAST_YEARS[-1]:
            # Terminal year: enforce steady-state WC behavior
            change_in_nwc = change_in_nwc_prev
        else:
            change_in_nwc = net_working_capital - prior_nwc

        change_in_nwc_prev = change_in_nwc

        nwc_assets = accounts_receivable + inventory
        nwc_liabilities = accounts_payable

        rows.append(
            {
                "fiscal_year": year,
                "ticker": "NVDA",
                "accounts_receivable_usdm": round(accounts_receivable, 4),
                "inventory_usdm": round(inventory, 4),
                "prepaid_expenses_usdm": round(prepaid_expenses, 4),
                "accounts_payable_usdm": round(accounts_payable, 4),
                "accrued_liabilities_usdm": round(accrued_liabilities, 4),
                "nwc_assets_usdm": round(nwc_assets, 4),
                "nwc_liabilities_usdm": round(nwc_liabilities, 4),
                "net_working_capital_usdm": round(net_working_capital, 4),
                "change_in_nwc_usdm": round(change_in_nwc, 4),
                "ar_days_dso": round(dso_days, 4),
                "inventory_days_dio": round(dio_days, 4),
                "ap_days_dpo": round(dpo_days, 4),
                "cash_conversion_cycle": round(dso_days + dio_days - dpo_days, 4),
                "is_forecast": True,
                "scenario": scenario,
                "source": "model_projection",
            }
        )

        prior_nwc = net_working_capital

    df = pd.DataFrame(rows).sort_values("fiscal_year").reset_index(drop=True)
    logger.info(
        "[working_capital] NWC schedule built: %d rows | scenario=%s | FY2026 Delta NWC=%.0f",
        len(df),
        scenario,
        df.iloc[0]["change_in_nwc_usdm"] if len(df) else 0.0,
    )
    return df
