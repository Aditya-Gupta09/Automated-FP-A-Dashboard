"""
src/modeling/engine.py
========================
Master Financial Model Orchestrator

Maps to: run_all.py (original DCF project) — fully rewritten.

Execution sequence (per module_mapping.md):
  1. wacc.py              → produces: wacc scalar
  2. income_statement.py  → produces: IS DataFrame (FY2026–2030)
  3. depreciation.py      → produces: DA schedule (feeds IS + BS + FCFF)
  4. working_capital.py   → produces: NWC schedule (feeds BS + FCFF)
  5. balance_sheet.py     → produces: BS DataFrame (FY2026–2030)
  6. cashflow.py          → produces: CF DataFrame (FY2026–2030)
  7. fcff.py              → produces: FCFF DataFrame (FY2026–2030)
  8. dcf_valuation.py     → produces: DCF valuation dict (scalar outputs)
  9. comps.py             → produces: comps results dict
  10. reconciliation.py   → validates: BS tie / CF / revenue cross-checks

RULE: engine.py is the ONLY module that calls other modules.
No financial calculations live here — pure orchestration.

Function signature per module_mapping.md:
  run_pipeline(scenario, verbose) → dict
"""

from __future__ import annotations
import json
import copy
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from src.etl.data_contracts import deep_merge

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
_CONFIG_DIR = ROOT_DIR / "config"
_VALID_SCENARIOS = ("base", "upside", "downside")


# ── Config loaders ────────────────────────────────────────────────────────────


def _load_json(filename: str) -> dict:
    path = _CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"[engine] Config file not found: {path}. " f"Expected in {_CONFIG_DIR}/"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_assumptions() -> dict:
    return _load_json("assumptions.json")


def _load_scenarios() -> dict:
    return _load_json("scenarios.json")


def _validate_scenario(scenario: str) -> str:
    if scenario not in _VALID_SCENARIOS:
        raise ValueError(
            f"Invalid scenario: {scenario}. Allowed: base, upside, downside"
        )
    return scenario


def _scenario_expected_outputs(assumptions: dict, scenario: str) -> dict:
    expected_outputs = assumptions.get("dcf", {}).get("expected_outputs", {})
    if (
        isinstance(expected_outputs, dict)
        and scenario in expected_outputs
        and isinstance(expected_outputs[scenario], dict)
    ):
        return copy.deepcopy(expected_outputs[scenario])
    return copy.deepcopy(expected_outputs)


def _apply_scenario(base: dict, scenarios: dict, scenario: str) -> dict:
    """Return final_assumptions for the given scenario."""
    _validate_scenario(scenario)
    if scenario == "base":
        return copy.deepcopy(base)
    overrides = scenarios.get(scenario, {})
    return deep_merge(base, overrides)


# ── Revenue helper ────────────────────────────────────────────────────────────


def _revenue_from_is(is_df: pd.DataFrame) -> pd.Series:
    """Extract total revenue series from IS DataFrame, indexed by fiscal_year."""
    total = (
        is_df[is_df.get("segment", pd.Series()) == "total"]
        if "segment" in is_df.columns
        else is_df
    )
    return is_df.set_index("fiscal_year")["revenue_usdm"]


# ── Main entry point ──────────────────────────────────────────────────────────


def run_pipeline(
    scenario: str = "base",
    verbose: bool = False,
    canonical_data: Optional[dict] = None,
    assumptions_override: Optional[dict] = None,
) -> dict:
    """
    Master orchestrator. Runs all modeling modules in dependency order.

    Args:
        scenario:        'base', 'upside', or 'downside'
        verbose:         If True, print progress to stdout
        canonical_data:  Optional pre-loaded ETL output dict.
                         If None, skips historical data integration.

    Returns:
        dict with keys per model_output_schema.json:
            income_statement  pd.DataFrame
            balance_sheet     pd.DataFrame
            cash_flow_statement pd.DataFrame
            fcff              pd.DataFrame
            dcf_valuation     dict
            comps             dict
            reconciliation    dict
            scenario          str
            assumptions_used  dict
            run_timestamp     str
            status            str
    """
    scenario = _validate_scenario(scenario)
    start = datetime.utcnow()

    if verbose:
        print(f"\n{'='*60}")
        print(f"  NVIDIA Financial Model — scenario={scenario}")
        print(f"{'='*60}")

    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d:
                deep_update(d[k], v)
            else:
                d[k] = v

    # ── Load and merge assumptions ─────────────────────────────────────────
    base_assumptions = _load_assumptions()
    scenarios_config = _load_scenarios()
    final_assumptions = _apply_scenario(base_assumptions, scenarios_config, scenario)

    # 🔥 NEW: apply overrides for P3 diagnostics
    if assumptions_override:
        deep_update(final_assumptions, assumptions_override)
    validation_assumptions = copy.deepcopy(final_assumptions)
    validation_assumptions.setdefault("dcf", {})["expected_outputs"] = (
        _scenario_expected_outputs(final_assumptions, scenario)
    )

    logger.info(
        "[engine] Scenario '%s' loaded | WACC=%.4f",
        scenario,
        final_assumptions.get("wacc", {}).get("wacc", 0),
    )

    # ── Step 1: WACC ──────────────────────────────────────────────────────
    if verbose:
        print("  Step 1/10: WACC...")
    from src.modeling.wacc import compute_wacc

    wacc_result = compute_wacc(final_assumptions)
    wacc_value = wacc_result["wacc_computed"]
    logger.info("[engine] WACC = %.6f (%.4f%%)", wacc_value, wacc_value * 100)

    # ── Step 2: Income Statement ──────────────────────────────────────────
    if verbose:
        print("  Step 2/10: Income Statement...")
    from src.modeling.income_statement import build_revenue, build_income_statement

    revenue_df = build_revenue(final_assumptions, scenario)
    is_df = build_income_statement(revenue_df, final_assumptions, scenario)

    # ── Step 3: Depreciation ──────────────────────────────────────────────
    if verbose:
        print("  Step 3/10: Depreciation & D&A schedule...")
    from src.modeling.depreciation import build_da_schedule

    # Build capex series from IS revenue
    is_total = is_df.set_index("fiscal_year")
    capex_pct_base = final_assumptions.get("capex", {}).get(
        f"{scenario}_case", final_assumptions.get("capex", {}).get("base_case", {})
    )
    capex_series = pd.Series(
        {
            yr: is_total.loc[yr, "revenue_usdm"] * capex_pct_base.get(f"fy{yr}f", 0.030)
            for yr in is_total.index
        }
    )
    da_df = build_da_schedule(capex_series, final_assumptions, scenario)

    # Update IS with modelled D&A (re-run with da_schedule)
    is_df = build_income_statement(
        revenue_df, final_assumptions, scenario, da_schedule=da_df
    )

    # Step 4: Working Capital
    if verbose:
        print(" Step 4/10: Working Capital NWC schedule...")
    from src.modeling.working_capital import build_nwc_schedule

    wc_df = build_nwc_schedule(is_df, final_assumptions, scenario)

    # Step 5: Balance Sheet (PROVISIONAL)
    if verbose:
        print(" Step 5/10: Balance Sheet (provisional)...")
    from src.modeling.balance_sheet import build_balance_sheet

    bs_df_provisional = build_balance_sheet(
        is_df,
        wc_df,
        da_df,
        final_assumptions,
        scenario,
        ending_cash=None,
    )

    # Step 6: Cash Flow Statement
    if verbose:
        print(" Step 6/10: Cash Flow Statement...")
    from src.modeling.cashflow import build_cashflow

    cf_df = build_cashflow(
        is_df,
        bs_df_provisional,
        wc_df,
        da_df,
        final_assumptions,
        scenario,
    )

    # Step 7: Balance Sheet (FINAL)
    if verbose:
        print(" Step 7/10: Balance Sheet (final)...")
    ending_cash = cf_df.set_index("fiscal_year")["ending_cash_usdm"].copy()
    ending_cash.index = ending_cash.index.map(lambda y: f"fy{y}f")
    bs_df = build_balance_sheet(
        is_df,
        wc_df,
        da_df,
        final_assumptions,
        scenario,
        ending_cash=ending_cash,
    )

    # ── Step 7: FCFF ─────────────────────────────────────────────────────
    if verbose:
        print("  Step 8/11: FCFF schedule...")
    from src.modeling.fcff import build_fcff

    fcff_df = build_fcff(is_df, da_df, wc_df, final_assumptions, scenario)

    # ── Step 8: DCF Valuation ─────────────────────────────────────────────
    if verbose:
        print("  Step 9/11: DCF Valuation...")
    from src.modeling.dcf_valuation import run_dcf

    fcff_by_year = fcff_df.set_index("fiscal_year")["fcff_usdm"].to_dict()
    dcf_result = run_dcf(
        fcff_by_year=fcff_by_year,
        assumptions=validation_assumptions,
        scenario=scenario,
    )

    # ── Step 9: Comps ─────────────────────────────────────────────────────
    if verbose:
        print("  Step 10/11: Comparable company analysis...")
    comps_result = {}
    try:
        from src.modeling.comps import run_comps

        comps_result = run_comps("data/raw/comps_data.csv", validation_assumptions)
    except Exception as e:
        logger.warning("[engine] Comps skipped: %s", e)
        comps_result = {"status": "skipped", "reason": str(e)}

    # ── Step 10: Reconciliation ───────────────────────────────────────────
    if verbose:
        print("  Step 11/11: Reconciliation checks...")
    from src.modeling.reconciliation import run_all_checks

    # Convert DataFrames to year-keyed dicts for reconciliation
    is_results = is_df.set_index("fiscal_year").to_dict("index")
    bs_results = bs_df.set_index("fiscal_year").to_dict("index")
    cf_results = cf_df.set_index("fiscal_year").to_dict("index")
    fcff_results = (
        fcff_df.set_index("fiscal_year").to_dict("index") if not fcff_df.empty else {}
    )

    # Rename keys to match what reconciliation.py expects
    for yr in bs_results:
        bs_results[yr]["total_assets"] = bs_results[yr].get("total_assets_usdm", 0)
        bs_results[yr]["total_liabilities"] = bs_results[yr].get(
            "total_liabilities_usdm", 0
        )
        bs_results[yr]["shareholders_equity"] = bs_results[yr].get(
            "shareholders_equity_usdm", 0
        )

    for yr in cf_results:
        cf_results[yr]["cfo"] = cf_results[yr].get("cfo_usdm", 0)
        cf_results[yr]["cfi"] = cf_results[yr].get("cfi_usdm", 0)
        cf_results[yr]["cff"] = cf_results[yr].get("cff_usdm", 0)
        cf_results[yr]["net_change_cash"] = cf_results[yr].get(
            "net_change_cash_usdm", 0
        )

    for yr in is_results:
        is_results[yr]["revenue"] = is_results[yr].get("revenue_usdm", 0)
    for yr in fcff_results:
        fcff_results[yr]["revenue"] = fcff_results[yr].get("revenue_usdm", 0)

    recon_result = run_all_checks(
        is_results=is_results,
        bs_results=bs_results,
        cf_results=cf_results,
        fcff_results=fcff_results,
        dcf_result=dcf_result,
        assumptions=validation_assumptions,
        scenario=scenario,
    )

    duration = (datetime.utcnow() - start).total_seconds()
    dcf_passed = recon_result.get("dcf_check", {}).get("all_passed", True)
    status = "PASS" if (recon_result["all_passed"] and dcf_passed) else "WARN"

    if verbose:
        print(f"\n  Reconciliation: {recon_result['summary']['status']}")
        print(
            f"  Implied share price: ${dcf_result.get('implied_share_price_usd', 0):.2f}"
        )
        print(f"  Duration: {duration:.2f}s")
        print(f"{'='*60}\n")

    logger.info(
        "[engine] Pipeline complete | scenario=%s | %.2fs | " "recon=%s | price=$%.2f",
        scenario,
        duration,
        recon_result["summary"]["status"],
        dcf_result.get("implied_share_price_usd", 0),
    )

    return {
        "income_statement": is_df,
        "balance_sheet": bs_df,
        "cash_flow_statement": cf_df,
        "fcff": fcff_df,
        "dcf_valuation": dcf_result,
        "comps": comps_result,
        "reconciliation": recon_result,
        "scenario": scenario,
        "assumptions_used": copy.deepcopy(final_assumptions),
        "run_timestamp": start.isoformat(),
        "status": status,
        "duration_seconds": round(duration, 2),
    }


def run_3stmt(
    canonical_data: dict,
    assumptions: dict,
    scenario: str = "base",
) -> dict:
    """
    Simplified 3-statement model entry point.
    Matches the contract defined in model_input_schema.json.

    Args:
        canonical_data: ETL output dict {revenue, costs, working_capital, actuals}
        assumptions:    Final merged assumptions dict (already scenario-applied)
        scenario:       Active scenario label

    Returns:
        dict with keys: pnl, bs, cf
        (Subset of run_pipeline output — compatible with data_contracts.py)
    """
    scenario = _validate_scenario(scenario)

    # Inject assumptions into config temporarily for run_pipeline
    # In production, engine reads from config/ — this wrapper supports
    # the run_3stmt(canonical_data, assumptions) contract
    from src.modeling.income_statement import build_revenue, build_income_statement
    from src.modeling.depreciation import build_da_schedule
    from src.modeling.working_capital import build_nwc_schedule
    from src.modeling.balance_sheet import build_balance_sheet
    from src.modeling.cashflow import build_cashflow

    revenue_df = build_revenue(assumptions, scenario)
    is_df = build_income_statement(revenue_df, assumptions, scenario)

    is_total = is_df.set_index("fiscal_year")
    capex_pct_dict = assumptions.get("capex", {}).get(
        f"{scenario}_case", assumptions.get("capex", {}).get("base_case", {})
    )
    capex_series = pd.Series(
        {
            yr: is_total.loc[yr, "revenue_usdm"] * capex_pct_dict.get(f"fy{yr}f", 0.030)
            for yr in is_total.index
        }
    )

    da_df = build_da_schedule(capex_series, assumptions, scenario)
    is_df = build_income_statement(revenue_df, assumptions, scenario, da_schedule=da_df)
    wc_df = build_nwc_schedule(is_df, assumptions, scenario)
    bs_df_provisional = build_balance_sheet(
        is_df,
        wc_df,
        da_df,
        assumptions,
        scenario,
        ending_cash=None,
    )
    cf_df = build_cashflow(
        is_df, bs_df_provisional, wc_df, da_df, assumptions, scenario
    )
    ending_cash = cf_df.set_index("fiscal_year")["ending_cash_usdm"].copy()
    ending_cash.index = ending_cash.index.map(lambda y: f"fy{y}f")
    bs_df = build_balance_sheet(
        is_df,
        wc_df,
        da_df,
        assumptions,
        scenario,
        ending_cash=ending_cash,
    )

    return {"pnl": is_df, "bs": bs_df, "cf": cf_df}
