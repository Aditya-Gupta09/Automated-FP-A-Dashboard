"""
src/from src.etl/data_contracts.py
==================================
Data contracts — converted from data_contracts.md v1.0.

Binding interface agreements between all system layers.
Every module must honour these contracts. Violations break the pipeline
predictably — not silently.

Source: data_contracts.md | Author: Aditya Gupta | Oct 2025
"""

from __future__ import annotations
import copy
from typing import Optional
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT 1 — ETL OUTPUT
# Produced by: etl/transformer.py via pipeline.py
# Consumed by: modeling/, kpi/, ui/
# ══════════════════════════════════════════════════════════════════════════════

ETL_OUTPUT_KEYS = ["costs", "working_capital", "actuals"]


def validate_etl_output(canonical_data: dict) -> list[str]:
    """
    Validate the ETL output dict has all required keys and correct types.

    Args:
        canonical_data: dict produced by pipeline.run_etl()

    Returns:
        List of error strings (empty = PASS)
    """
    errors: list[str] = []
    for key in ETL_OUTPUT_KEYS:
        if key not in canonical_data:
            errors.append(f"[ETL output] Missing key: '{key}'")
        elif not isinstance(canonical_data[key], pd.DataFrame):
            errors.append(
                f"[ETL output] Key '{key}' must be pd.DataFrame, "
                f"got {type(canonical_data[key]).__name__}"
            )
        elif canonical_data[key].empty:
            errors.append(f"[ETL output] Key '{key}' DataFrame is empty")
    return errors


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT 2 — SCENARIO ENGINE
# Deep merge pattern: base_assumptions + scenario_overrides → final_assumptions
# Rule: MUST use recursive deep_merge — NOT shallow dict.update()
# ══════════════════════════════════════════════════════════════════════════════

VALID_SCENARIOS = ["base", "upside", "downside"]


def deep_merge(base: dict, overrides: dict) -> dict:
    """
    Recursively merge overrides into base assumptions.

    This is the ONLY approved way to apply scenario overrides.
    Shallow dict.update() is forbidden — it silently replaces nested
    sub-dicts instead of merging individual keys.

    Rule: Scenarios never mutate base. base_assumptions is always
    a separate object from final_assumptions.

    Args:
        base:      Full base assumptions dict (from assumptions.json)
        overrides: Delta dict from src.scenarios.json[scenario]
                   (contains ONLY keys that differ from base)

    Returns:
        New dict — deep copy of base with overrides applied.
        The original base dict is NEVER modified.

    Example:
        base = {"wacc": {"capital_structure": {"wacc": 0.1291}}}
        overrides = {"capital_structure": {"wacc": 0.1191}}
        result = deep_merge(base, overrides)
        # result["capital_structure"]["wacc"] == 0.1191
        # base["capital_structure"]["wacc"] == 0.1291  (unchanged)
    """
    result = copy.deepcopy(base)
    for key, val in overrides.items():
        if key.startswith("_"):
            continue  # Skip comment/_metadata keys
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def apply_scenario(
    base_assumptions: dict, scenarios: dict, active_scenario: str
) -> dict:
    """
    Apply scenario overrides to base assumptions.

    Args:
        base_assumptions: Full assumptions dict from assumptions.json
        scenarios:        Full scenarios dict from src.scenarios.json
        active_scenario:  One of 'base', 'upside', 'downside'

    Returns:
        final_assumptions dict (deep merged, base never mutated)

    Raises:
        ValueError: If active_scenario is not a valid scenario name
    """
    if active_scenario not in VALID_SCENARIOS:
        raise ValueError(
            f"Invalid scenario: '{active_scenario}'. "
            f"Must be one of: {VALID_SCENARIOS}"
        )

    if active_scenario == "base":
        return copy.deepcopy(base_assumptions)

    overrides = scenarios.get(active_scenario, {})
    return deep_merge(base_assumptions, overrides)


def validate_scenario_output(
    final_assumptions: dict, base_assumptions: dict
) -> list[str]:
    """
    Verify scenario engine output is a new object (not the base reference).

    Returns error list (empty = PASS)
    """
    errors: list[str] = []
    if final_assumptions is base_assumptions:
        errors.append(
            "[Scenario] final_assumptions IS base_assumptions — "
            "scenario must produce a new dict, not mutate base"
        )
    return errors


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT 3 — MODEL INPUT
# Produced by: ETL + Scenario Engine
# Consumed by: All projection modules in src/modeling/
# ══════════════════════════════════════════════════════════════════════════════

MODEL_INPUT_REQUIRED_KEYS = [
    "actuals",
    "costs",
    "working_capital",
    "assumptions",
    "scenario",
]

ASSUMPTIONS_REQUIRED_TOP_KEYS = [
    "wacc",
    "dcf",
    "revenue_growth",
    "gross_margin",
    "rd_expense_pct",
    "sga_expense_pct",
    "tax_rate",
    "interest_income",
    "capex",
    "depreciation",
    "working_capital",
    "debt_schedule",
    "fcff_construction",
    "historical_actuals_fy2025",
]


def validate_model_input(model_input: dict) -> list[str]:
    """
    Validate the model input dict before passing to engine.py.

    Args:
        model_input: dict with keys: actuals, costs, working_capital,
                     assumptions, scenario

    Returns:
        List of error strings (empty = PASS)
    """
    errors: list[str] = []

    for key in MODEL_INPUT_REQUIRED_KEYS:
        if key not in model_input:
            errors.append(f"[Model input] Missing required key: '{key}'")

    # Validate DataFrames
    for df_key in ["actuals", "costs", "working_capital"]:
        if df_key in model_input:
            if not isinstance(model_input[df_key], pd.DataFrame):
                errors.append(
                    f"[Model input] '{df_key}' must be pd.DataFrame, "
                    f"got {type(model_input[df_key]).__name__}"
                )

    # Validate scenario label
    if "scenario" in model_input:
        if model_input["scenario"] not in VALID_SCENARIOS:
            errors.append(
                f"[Model input] Invalid scenario: '{model_input['scenario']}'"
            )

    # Validate assumptions dict has required top-level keys
    if "assumptions" in model_input:
        assumptions = model_input["assumptions"]
        for k in ASSUMPTIONS_REQUIRED_TOP_KEYS:
            if k not in assumptions:
                errors.append(f"[Model input] assumptions missing required key: '{k}'")

    return errors


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT 4 — MODEL OUTPUT
# Produced by: src/modeling/engine.py
# Consumed by: src/kpi/, app/
# ══════════════════════════════════════════════════════════════════════════════

MODEL_OUTPUT_REQUIRED_KEYS = [
    "income_statement",
    "balance_sheet",
    "cash_flow_statement",
    "fcff",
    "dcf_valuation",
    "comps",
    "reconciliation",
    "scenario",
    "assumptions_used",
    "run_timestamp",
    "status",
    "duration_seconds",
]

IS_REQUIRED_COLUMNS = [
    "fiscal_year",
    "revenue_usdm",
    "cogs_usdm",
    "gross_profit_usdm",
    "rd_expense_usdm",
    "sga_expense_usdm",
    "total_opex_usdm",
    "ebit_usdm",
    "da_usdm",
    "ebitda_usdm",
    "ebt_usdm",
    "income_tax_usdm",
    "effective_tax_rate_pct",
    "net_income_usdm",
    "gross_margin_pct",
    "ebit_margin_pct",
    "ebitda_margin_pct",
    "net_margin_pct",
]

BS_REQUIRED_COLUMNS = [
    "fiscal_year",
    "ticker",
    "cash_and_investments_usdm",
    "accounts_receivable_usdm",
    "inventory_usdm",
    "prepaid_expenses_usdm",
    "total_current_assets_usdm",
    "net_ppe_usdm",
    "total_assets_usdm",
    "accounts_payable_usdm",
    "accrued_liabilities_usdm",
    "short_term_debt_usdm",
    "total_current_liabilities_usdm",
    "long_term_debt_usdm",
    "total_liabilities_usdm",
    "retained_earnings_usdm",
    "shareholders_equity_usdm",
    "is_forecast",
    "scenario",
]

CF_REQUIRED_COLUMNS = [
    "fiscal_year",
    "net_income_usdm",
    "da_usdm",
    "change_in_nwc_usdm",
    "capex_usdm",
    "cfo_usdm",
    "cfi_usdm",
    "cff_usdm",
    "fcf_usdm",
    "net_change_cash_usdm",
    "ending_cash_usdm",
    "beginning_cash_usdm",
]

FCFF_REQUIRED_COLUMNS = [
    "fiscal_year",
    "revenue_usdm",
    "ebit_usdm",
    "nopat_usdm",
    "da_usdm",
    "capex_usdm",
    "change_in_nwc_usdm",
    "fcff_usdm",
    "pv_fcff_usdm",
    "projection_year",
]

DCF_REQUIRED_KEYS = [
    "scenario",
    "wacc_used",
    "terminal_growth_rate",
    "discounting_convention",
    "terminal_value_method",
    "fcff_by_year",
    "pv_fcff_by_year",
    "sum_pv_fcf_usdm",
    "terminal_value_usdm",
    "pv_terminal_value_usdm",
    "enterprise_value_usdm",
    "net_debt_bridge",
    "net_debt_usdm",
    "equity_value_usdm",
    "diluted_shares_millions",
    "implied_share_price_usd",
    "market_price_usd",
    "upside_downside_pct",
    "sensitivity",
    "cross_check",
]


def validate_model_output(model_output: dict) -> list[str]:
    """
    Validate the model output dict against Contract 4.

    Args:
        model_output: dict from engine.py

    Returns:
        List of error strings (empty = PASS)
    """
    errors: list[str] = []

    for key in MODEL_OUTPUT_REQUIRED_KEYS:
        if key not in model_output:
            errors.append(f"[Model output] Missing required key: '{key}'")

    # Validate DataFrames have required columns
    df_checks = [
        ("income_statement", IS_REQUIRED_COLUMNS),
        ("balance_sheet", BS_REQUIRED_COLUMNS),
        ("cash_flow_statement", CF_REQUIRED_COLUMNS),
        ("fcff", FCFF_REQUIRED_COLUMNS),
    ]

    for df_key, required_cols in df_checks:
        if df_key not in model_output:
            continue
        df = model_output[df_key]
        if not isinstance(df, pd.DataFrame):
            errors.append(f"[Model output] '{df_key}' must be pd.DataFrame")
            continue
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"[Model output] '{df_key}' missing column: '{col}'")

    # Validate DCF valuation dict
    if "dcf_valuation" in model_output:
        dcf = model_output["dcf_valuation"]
        if not isinstance(dcf, dict):
            errors.append("[Model output] 'dcf_valuation' must be a dict")
        else:
            for k in DCF_REQUIRED_KEYS:
                if k not in dcf:
                    errors.append(f"[Model output] dcf_valuation missing key: '{k}'")

    return errors


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT 5 — DCF VALUATION (scalar dict)
# All values USD millions except implied_share_price_usd (full USD)
# ══════════════════════════════════════════════════════════════════════════════

# Expected base case values from assumptions.json dcf.expected_outputs
# Used for cross-check validation against Excel model
DCF_EXPECTED_BASE = {
    "sum_pv_fcf_usdm": 664084.8149849618,
    "terminal_value_usdm": 3593999.4086396955,
    "pv_terminal_value_usdm": 1958097.5523661016,
    "enterprise_value_usdm": 2622182.3673510635,
    "equity_value_usdm": 2655122.3673510635,
    "implied_share_price_usd": 109.26429495271866,
}


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT 6 — KPI OUTPUT (ALL scalars — never DataFrame)
# ══════════════════════════════════════════════════════════════════════════════

KPI_OUTPUT_REQUIRED_KEYS = [
    "gross_margin_pct",
    "ebit_margin_pct",
    "ebitda_margin_pct",
    "net_margin_pct",
    "fcf_margin_pct",
    "revenue_growth_yoy_pct",
    "ar_days_dso",
    "inventory_days_dio",
    "ap_days_dpo",
    "cash_conversion_cycle_days",
    "current_ratio",
    "implied_share_price_usd",
    "enterprise_value_usdm",
    "scenario",
    "fiscal_year",
]


def validate_kpi_output(kpi_output: dict) -> list[str]:
    """
    Validate KPI output dict against Contract 6.

    Rules:
    - All values must be float or None (never NaN, never DataFrame)
    - 'scenario' must be a string
    - 'fiscal_year' must be an int

    Args:
        kpi_output: dict from src.kpi engine

    Returns:
        List of error strings (empty = PASS)
    """
    import math

    errors: list[str] = []

    for key in KPI_OUTPUT_REQUIRED_KEYS:
        if key not in kpi_output:
            errors.append(f"[KPI output] Missing key: '{key}'")
            continue

        val = kpi_output[key]

        if key == "scenario":
            if not isinstance(val, str):
                errors.append(f"[KPI output] 'scenario' must be str, got {type(val)}")
            elif val not in VALID_SCENARIOS:
                errors.append(f"[KPI output] Invalid scenario: '{val}'")
        elif key == "fiscal_year":
            if not isinstance(val, int):
                errors.append(
                    f"[KPI output] 'fiscal_year' must be int, got {type(val)}"
                )
        else:
            # Numeric KPI: must be float or None — never NaN
            if val is not None:
                if not isinstance(val, (int, float)):
                    errors.append(
                        f"[KPI output] '{key}' must be float or None, got {type(val)}"
                    )
                elif isinstance(val, float) and math.isnan(val):
                    errors.append(
                        f"[KPI output] '{key}' is NaN — must return None instead"
                    )

    return errors


# ══════════════════════════════════════════════════════════════════════════════
# MASTER CONTRACT VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════


def validate_all_contracts(
    canonical_data: Optional[dict] = None,
    model_input: Optional[dict] = None,
    model_output: Optional[dict] = None,
    kpi_output: Optional[dict] = None,
    raise_on_failure: bool = False,
) -> dict:
    """
    Run all available contract validations and return a summary.

    Args:
        canonical_data:  ETL output dict
        model_input:     Model input dict
        model_output:    Model output dict
        kpi_output:      KPI output dict
        raise_on_failure: If True, raises ValueError on first failure

    Returns:
        dict with 'all_passed', 'errors', 'summary'
    """
    all_errors: dict[str, list[str]] = {}

    if canonical_data is not None:
        errs = validate_etl_output(canonical_data)
        if errs:
            all_errors["etl_output"] = errs

    if model_input is not None:
        errs = validate_model_input(model_input)
        if errs:
            all_errors["model_input"] = errs

    if model_output is not None:
        errs = validate_model_output(model_output)
        if errs:
            all_errors["model_output"] = errs

    if kpi_output is not None:
        errs = validate_kpi_output(kpi_output)
        if errs:
            all_errors["kpi_output"] = errs

    all_passed = len(all_errors) == 0

    if not all_passed and raise_on_failure:
        flat = [e for errs in all_errors.values() for e in errs]
        raise ValueError(
            f"Contract validation failed with {len(flat)} error(s):\n"
            + "\n".join(f"  {e}" for e in flat)
        )

    total_errors = sum(len(v) for v in all_errors.values())
    return {
        "all_passed": all_passed,
        "errors": all_errors,
        "summary": {
            "contracts_checked": sum(
                [
                    canonical_data is not None,
                    model_input is not None,
                    model_output is not None,
                    kpi_output is not None,
                ]
            ),
            "total_errors": total_errors,
            "status": "PASS" if all_passed else "FAIL",
        },
    }
