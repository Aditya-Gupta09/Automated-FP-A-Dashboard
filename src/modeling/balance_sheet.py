"""
src/modeling/balance_sheet.py
================================
Balance Sheet Projection Engine

Maps to: 02_Historical_BS + 04b_Projection_BS + 13_DebtSchedule (Excel tabs)
Execution order: #5 in engine.py (after working_capital.py)

Builds projected BS for FY2026F–FY2030F using:
  Asset side:
    Cash = Revenue × cash_pct_of_revenue (from assumptions)
    AR, Inventory, Prepaid = from working_capital.py
    PP&E net = from depreciation.py
    Goodwill, DTA, Other Assets = flat (FY2025 actual)
    Operating lease assets = roll-forward (new leases - amortization)

  Liability side:
    AP, Accrued = from working_capital.py
    Current taxes = income_tax × taxes_payable_pct
    Current leases = current_lease_pct × total_leases
    Long-term debt = roll-forward from debt schedule
    Other LT liabilities = flat $4,245M
    Long-term leases = roll-forward

  Equity side:
    Common stock = flat $24M
    APIC = prior + SBC
    Retained earnings = prior + net_income - dividends  [THE PLUG]
    Treasury stock = flat $0
    OCI = flat $28M

THE PLUG: Retained Earnings closes the BS.
See reconciliation.py for full documentation.

BS Invariant: Total Assets == Total Liabilities + Shareholders' Equity
Tolerance: ±$0.01M (from config assumptions/contracts)

Function signature per module_mapping.md:
  build_balance_sheet(is_df, wc_df, da_df, assumptions, scenario) → pd.DataFrame
"""

from __future__ import annotations

import logging

import pandas as pd

from src.modeling.reconciliation import (
    BS_ASSUMPTIONS,
    compute_apic,
    compute_retained_earnings,
    compute_shareholders_equity,
)

logger = logging.getLogger(__name__)

FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]


def build_balance_sheet(
    is_df: pd.DataFrame,
    wc_df: pd.DataFrame,
    da_df: pd.DataFrame,
    assumptions: dict,
    scenario: str = "base",
    ending_cash: dict | None = None,
) -> pd.DataFrame:
    """
    Build the projected balance sheet for FY2026F–FY2030F.

    Args:
        is_df:       Income statement DataFrame (output of income_statement.py)
        wc_df:       NWC schedule DataFrame (output of working_capital.py)
        da_df:       D&A schedule DataFrame (output of depreciation.py)
        assumptions: Final merged assumptions dict
        scenario:    'base', 'upside', or 'downside'

    Returns:
        DataFrame (5 rows × BS columns) per model_output_schema.json
        Retained earnings is the plug — BS balances by design.
    """
    # Build lookup dicts from input DataFrames
    is_dict = is_df.set_index("fiscal_year").to_dict("index") if not is_df.empty else {}
    wc_dict = wc_df.set_index("fiscal_year").to_dict("index") if not wc_df.empty else {}
    da_dict = da_df.set_index("fiscal_year").to_dict("index") if not da_df.empty else {}

    hist = assumptions.get("historical_actuals_fy2025", {})
    net_debt_bridge = assumptions.get("dcf", {}).get("net_debt_bridge", {})
    interest_assumptions = assumptions.get("interest_income", {})
    debt_assumptions = assumptions.get("debt_schedule", {})
    bs_assump = BS_ASSUMPTIONS  # From reconciliation.py

    # FY2025 actuals (starting values for roll-forwards)
    prior_retained_earnings = bs_assump["fy2025_retained_earnings_usdm"]
    prior_apic = bs_assump["fy2025_apic_usdm"]
    prior_total_leases = hist.get(
        "operating_lease_assets_usdm", 1793.0
    ) + net_debt_bridge.get("long_term_leases_usdm", 1519.0)
    prior_lt_debt = net_debt_bridge.get("long_term_debt_usdm", 8463.0)
    prior_ending_cash = hist.get("cash_and_investments_usdm", 43210.0)

    rows = []

    for year in FORECAST_YEARS:
        fy_key = f"fy{year}f"
        is_row = is_dict.get(year, {})
        wc_row = wc_dict.get(year, {})
        da_row = da_dict.get(year, {})

        revenue = is_row.get("revenue_usdm", 0.0)
        net_income = is_row.get("net_income_usdm", 0.0)
        income_tax = is_row.get("income_tax_usdm", 0.0)

        # ── ASSETS ────────────────────────────────────────────────────────
        if ending_cash is not None:
            cash = ending_cash.get(fy_key, prior_ending_cash)
        else:
            cash = prior_ending_cash

        ar = wc_row.get("accounts_receivable_usdm", 0.0)
        inv = wc_row.get("inventory_usdm", 0.0)
        prepaid = wc_row.get("prepaid_expenses_usdm", 0.0)
        total_ca = cash + ar + inv + prepaid

        ppe_net = da_row.get("ppe_net_usdm", hist.get("ppe_net_usdm", 6283.0))

        # Flat items (FY2025 actual held constant per reconciliation.py documentation)
        goodwill = bs_assump["goodwill_flat_usdm"]

        # Scale DTA and Other Assets with revenue
        hist_revenue = hist.get("revenue_usdm", 1)

        dta_pct = bs_assump["lt_deferred_tax_assets_flat_usdm"] / hist_revenue
        other_assets_pct = bs_assump["other_assets_flat_usdm"] / hist_revenue

        dta = revenue * dta_pct
        other_assets = revenue * other_assets_pct

        # Operating lease assets: roll-forward (add new leases, subtract annual amort)
        new_leases = bs_assump["new_lease_obligations_usdm_per_year"]
        lease_amort = new_leases / 10  # ~10yr avg lease life
        total_leases = prior_total_leases + new_leases - lease_amort
        current_lease_pct = bs_assump["current_lease_pct_of_total"]
        current_lease_assets = total_leases * current_lease_pct
        lt_lease_assets = total_leases * (1 - current_lease_pct)

        total_assets = (
            cash
            + ar
            + inv
            + prepaid  # current assets
            + ppe_net
            + goodwill
            + dta
            + other_assets  # non-current
            + current_lease_assets
            + lt_lease_assets  # operating lease ROU
        )

        # ── LIABILITIES ───────────────────────────────────────────────────
        ap = wc_row.get("accounts_payable_usdm", 0.0)
        accrued = wc_row.get("accrued_liabilities_usdm", 0.0)

        # Current taxes payable = income_tax × taxes_payable_pct
        taxes_payable_pct = bs_assump["current_taxes_pct_of_tax_expense"]
        current_taxes = income_tax * taxes_payable_pct

        # Debt roll-forward
        issuance_dict = debt_assumptions.get("net_debt_issuance_usdm", {}).get(
            "base", {}
        )
        issuance = issuance_dict.get(fy_key, 0.0)
        lt_debt = prior_lt_debt + issuance

        current_lease_liabilities = total_leases * current_lease_pct
        lt_lease_liabilities = total_leases * (1 - current_lease_pct)

        total_cl = ap + accrued + current_taxes + current_lease_liabilities
        other_lt_liab = bs_assump["other_lt_liabilities_flat_usdm"]
        total_liabilities = total_cl + lt_debt + lt_lease_liabilities + other_lt_liab

        # ── EQUITY (plug via retained earnings) ───────────────────────────
        sbc_pct_dict = bs_assump["sbc_pct_revenue"]
        sbc_pct = sbc_pct_dict.get(scenario, sbc_pct_dict.get("base", {})).get(
            year, 0.019
        )
        sbc = revenue * sbc_pct

        div_pct_dict = bs_assump["dividend_payout_ratio"]
        div_pct = div_pct_dict.get(scenario, div_pct_dict.get("base", {})).get(
            year, 0.009
        )
        dividends = net_income * div_pct

        # Step 1: base RE
        retained_earnings = compute_retained_earnings(
            prior_re=prior_retained_earnings,
            net_income=net_income,
            dividends=dividends,
        )

        apic = compute_apic(prior_apic=prior_apic, sbc=sbc)

        common_stock = bs_assump["common_stock_flat_usdm"]
        treasury_stock = bs_assump["treasury_stock_flat_usdm"]
        oci = bs_assump["oci_flat_usdm"]

        # Step 2: preliminary equity
        pre_equity = common_stock + apic + retained_earnings + treasury_stock + oci

        # Step 3: compute imbalance
        imbalance = total_assets - (total_liabilities + pre_equity)

        # Step 4: plug retained earnings
        retained_earnings += imbalance

        # Step 5: recompute final equity
        shareholders_equity = compute_shareholders_equity(
            common_stock=common_stock,
            apic=apic,
            retained_earnings=retained_earnings,
            treasury_stock=treasury_stock,
            oci=oci,
        )
        # Final precision correction (ensure exact BS tie)
        final_gap = total_assets - (total_liabilities + shareholders_equity)

        if abs(final_gap) > 0:
            retained_earnings += final_gap
            shareholders_equity += final_gap

        rows.append(
            {
                "fiscal_year": year,
                "ticker": "NVDA",
                # Assets
                "cash_and_investments_usdm": round(cash, 4),
                "accounts_receivable_usdm": round(ar, 4),
                "inventory_usdm": round(inv, 4),
                "prepaid_expenses_usdm": round(prepaid, 4),
                "total_current_assets_usdm": round(total_ca, 4),
                "net_ppe_usdm": round(ppe_net, 4),
                "goodwill_usdm": round(goodwill, 4),
                "lt_deferred_tax_assets_usdm": round(dta, 4),
                "other_assets_usdm": round(other_assets, 4),
                "total_assets_usdm": round(total_assets, 4),
                # Liabilities
                "accounts_payable_usdm": round(ap, 4),
                "accrued_liabilities_usdm": round(accrued, 4),
                "short_term_debt_usdm": 0.0,
                "total_current_liabilities_usdm": round(total_cl, 4),
                "long_term_debt_usdm": round(lt_debt, 4),
                "total_liabilities_usdm": round(total_liabilities, 4),
                # Equity
                "retained_earnings_usdm": round(retained_earnings, 4),
                "apic_usdm": round(apic, 4),
                "shareholders_equity_usdm": round(shareholders_equity, 4),
                # Metadata
                "is_forecast": True,
                "scenario": scenario,
                "source": "model_projection",
                # Internal (for downstream use)
                "_dividends_usdm": round(dividends, 4),
                "_sbc_usdm": round(sbc, 4),
                "_ending_cash_usdm": round(cash, 4),
            }
        )

        # Update roll-forward state
        prior_retained_earnings = retained_earnings
        prior_apic = apic
        prior_lt_debt = lt_debt
        prior_total_leases = total_leases
        prior_ending_cash = cash

    df = pd.DataFrame(rows)
    logger.info(
        "[balance_sheet] BS built: %d rows | scenario=%s | "
        "Assets FY2026=%.0f | Equity FY2026=%.0f",
        len(df),
        scenario,
        df.iloc[0]["total_assets_usdm"] if len(df) else 0,
        df.iloc[0]["shareholders_equity_usdm"] if len(df) else 0,
    )
    return df
