"""
src/modeling/wacc.py
=====================
WACC Extraction, Independent Recalculation & Cross-Check

Refactored from: src/wacc.py (original repo)
Key changes vs original:
  1. ALL CAPM inputs sourced from config/assumptions.json — ZERO hardcoded values
  2. Moved to src/modeling/ (modeling layer, not root src/)
  3. compute_wacc() is now a pure function — accepts assumptions dict
  4. Excel reading isolated in read_wacc_from_model() — testable separately
  5. Cross-check tolerance sourced from assumptions, not hardcoded constant
  6. Named range resolution preserved from original (robust to row shifts)

Original src/wacc.py functionality fully preserved:
  - Named range reads (5 ranges: risk_free_rate, adjusted_beta, etc.)
  - Address-based reads (5 cells: market_cap, weights, cost_of_debt)
  - CAPM formula: Ke = rf + β × ERP
  - WACC: w_e × Ke + w_d × Kd × (1-t)
  - Cross-check vs model output (tolerance: 1bp)
  - JSON output to datasets/processed/wacc_results.json

Usage:
    # Config-driven mode (no Excel needed):
    from src.modeling.wacc import compute_wacc
    from config.loader import load_assumptions
    result = compute_wacc(load_assumptions())

    # Full pipeline mode (reads from Excel + cross-checks):
    from src.modeling.wacc import run_wacc_pipeline
    result = run_wacc_pipeline(model_path, assumptions)
"""

import argparse
import json
import os
from datetime import datetime

try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


# ─── NAMED RANGE CONSTANTS ────────────────────────────────────────────────────
# Preserved from original src/wacc.py.
# These are stable cell references in the WACC sheet.

NAMED_RANGES = [
    "risk_free_rate",
    "adjusted_beta",
    "equity_risk_premium",
    "effective_tax_rate",
    "wacc_output",
]

ADDRESS_INPUTS = {
    "market_cap_equity": ("15_WACC", "F7"),
    "weight_equity": ("15_WACC", "F8"),
    "total_debt": ("15_WACC", "F14"),
    "weight_debt": ("15_WACC", "F15"),
    "pretax_cost_of_debt": ("15_WACC", "F16"),
}

# Fallback sheet/address map (for when named ranges resolve to None)
# Matches the original run_all.py fallback logic
FALLBACK_CELLS = {
    "risk_free_rate": ("15_WACC", "F10"),
    "adjusted_beta": ("15_WACC", "F11"),
    "equity_risk_premium": ("15_WACC", "F12"),
    "effective_tax_rate": ("15_WACC", "F17"),
    "wacc_output": ("15_WACC", "F19"),
}


# ─── PURE FUNCTION: CONFIG-DRIVEN WACC ───────────────────────────────────────


def compute_wacc(assumptions: dict) -> dict:
    """
    Compute WACC from config/assumptions.json inputs.
    Pure function — no Excel, no file I/O, fully testable.

    All inputs sourced from assumptions["wacc"] — ZERO hardcoded values.

    CAPM Formula:
        Ke   = rf + beta_adjusted × erp
        Kd   = pretax_cost_of_debt × (1 - effective_tax_rate)
        WACC = weight_equity × Ke + weight_debt × Kd

    Args:
        assumptions: full dict from config/assumptions.json

    Returns:
        dict with:
            cost_of_equity:         float (decimal)
            after_tax_cost_of_debt: float (decimal)
            wacc_computed:          float (decimal)
            inputs_used:            dict of all inputs applied
    """
    cfg = assumptions["wacc"]

    rf = cfg["risk_free_rate"]
    beta = cfg["beta_blume_adjusted"]
    erp = cfg["equity_risk_premium"]
    tax = cfg["effective_tax_rate_fy2025_actual"]
    w_eq = cfg["weight_equity"]
    w_d = cfg["weight_debt"]
    kd_pre = cfg["pretax_cost_of_debt"]

    # CAPM cost of equity
    ke = rf + beta * erp

    # After-tax cost of debt
    kd_post = kd_pre * (1 - tax)

    # WACC
    wacc = w_eq * ke + w_d * kd_post

    return {
        "cost_of_equity": ke,
        "after_tax_cost_of_debt": kd_post,
        "wacc_computed": wacc,
        "inputs_used": {
            "risk_free_rate": rf,
            "beta_blume_adjusted": beta,
            "equity_risk_premium": erp,
            "effective_tax_rate": tax,
            "weight_equity": w_eq,
            "weight_debt": w_d,
            "pretax_cost_of_debt": kd_pre,
        },
    }


# ─── CROSS-CHECK ──────────────────────────────────────────────────────────────


def cross_check_wacc(
    computed: float, model_value: float, tolerance_bps: float = 1.0
) -> dict:
    """
    Compare computed WACC to model WACC value.
    Tolerance sourced from assumptions["wacc"]["wacc_tolerance_bps"].

    Args:
        computed:       Python-computed WACC (decimal)
        model_value:    WACC from Excel model or assumptions.json (decimal)
        tolerance_bps:  Allowable difference in basis points

    Returns:
        dict with: passed, diff_bps, status_message
    """
    diff_bps = abs(computed - model_value) * 10000
    passed = diff_bps <= tolerance_bps

    return {
        "passed": passed,
        "diff_bps": round(diff_bps, 4),
        "computed_wacc": round(computed, 8),
        "model_wacc": round(model_value, 8),
        "tolerance_bps": tolerance_bps,
        "status": (
            "PASS" if passed else f"FAIL ({diff_bps:.2f} bps > {tolerance_bps} bps)"
        ),
    }


# ─── NAMED RANGE READER (preserved from original src/wacc.py) ─────────────────


def _resolve_named_range(wb, name: str):
    """
    Resolve a named range in the workbook to its cell value.
    Preserved from original src/wacc.py — handles 'Sheet'!$COL$ROW format.
    """
    if name not in wb.defined_names:
        return None, None, None

    defn = wb.defined_names[name]
    ref = defn.attr_text

    try:
        if "!" not in ref:
            return None, None, None
        sheet_part, cell_part = ref.rsplit("!", 1)
        sheet_name = sheet_part.strip("'")
        cell_addr = cell_part.replace("$", "")
        val = wb[sheet_name][cell_addr].value
        return val, sheet_name, cell_addr
    except Exception:
        return None, None, None


def _read_address_inputs(wb, addr_map: dict) -> dict:
    """
    Read cells by explicit sheet + address.
    Preserved from original src/wacc.py.
    """
    results = {}
    for key, (sheet_name, addr) in addr_map.items():
        val = wb[sheet_name][addr].value
        results[key] = float(val) if isinstance(val, (int, float)) else None
    return results


# ─── EXCEL READER (isolated for testability) ──────────────────────────────────


def read_wacc_from_model(model_path: str) -> dict:
    """
    Read WACC inputs directly from Excel model.
    Isolated function — only called when Excel model is available.
    Falls back to address-based reads if named ranges resolve to None.

    Args:
        model_path: path to Company_Valuation_Model.xlsx

    Returns:
        dict of raw inputs from Excel

    Raises:
        FileNotFoundError if model not found
        ImportError if openpyxl not installed
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError(
            "openpyxl is required to read from Excel. pip install openpyxl"
        )
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    wb = openpyxl.load_workbook(model_path, data_only=True)

    inputs = {}

    # Named ranges
    for name in NAMED_RANGES:
        val, sheet, addr = _resolve_named_range(wb, name)
        if val is None:
            # Fall back to direct address read
            fb_sheet, fb_addr = FALLBACK_CELLS[name]
            val = wb[fb_sheet][fb_addr].value
        inputs[name] = float(val) if isinstance(val, (int, float)) else None

    # Address inputs
    addr_vals = _read_address_inputs(wb, ADDRESS_INPUTS)
    inputs.update(addr_vals)

    return inputs


# ─── FULL PIPELINE MODE ───────────────────────────────────────────────────────


def run_wacc_pipeline(
    model_path: str, assumptions: dict, output_path: str = None, verbose: bool = False
) -> dict:
    """
    Full pipeline: read from Excel → compute → cross-check → write JSON.
    Integrates with run_all.py / engine.py.

    Steps:
        1. Read WACC inputs from Excel (named ranges + address cells)
        2. Compute WACC independently via compute_wacc()
        3. Cross-check computed vs model WACC (tolerance from assumptions)
        4. Write wacc_results.json

    Args:
        model_path:  Path to Company_Valuation_Model.xlsx
        assumptions: Full assumptions dict (for tolerance + expected values)
        output_path: Where to write wacc_results.json (optional)
        verbose:     Print detailed workings

    Returns:
        dict matching original wacc_results.json schema
    """
    tolerance_bps = assumptions["wacc"].get("wacc_tolerance_bps", 1.0)

    # ── Read from Excel ────────────────────────────────────────────────────
    excel_inputs = read_wacc_from_model(model_path)

    # Build a temporary assumptions dict with Excel-read values
    # (overrides config values with live Excel values)
    excel_assumption_patch = {
        "wacc": {
            **assumptions["wacc"],
            "risk_free_rate": excel_inputs.get(
                "risk_free_rate", assumptions["wacc"]["risk_free_rate"]
            ),
            "beta_blume_adjusted": excel_inputs.get(
                "adjusted_beta", assumptions["wacc"]["beta_blume_adjusted"]
            ),
            "equity_risk_premium": excel_inputs.get(
                "equity_risk_premium", assumptions["wacc"]["equity_risk_premium"]
            ),
            "effective_tax_rate_fy2025_actual": excel_inputs.get(
                "effective_tax_rate",
                assumptions["wacc"]["effective_tax_rate_fy2025_actual"],
            ),
            "weight_equity": excel_inputs.get(
                "weight_equity", assumptions["wacc"]["weight_equity"]
            ),
            "weight_debt": excel_inputs.get(
                "weight_debt", assumptions["wacc"]["weight_debt"]
            ),
            "pretax_cost_of_debt": excel_inputs.get(
                "pretax_cost_of_debt", assumptions["wacc"]["pretax_cost_of_debt"]
            ),
        }
    }

    # ── Compute WACC ───────────────────────────────────────────────────────
    computed = compute_wacc(excel_assumption_patch)
    wacc_model = excel_inputs.get("wacc_output", assumptions["wacc"]["wacc"])

    # ── Cross-check ────────────────────────────────────────────────────────
    check = cross_check_wacc(computed["wacc_computed"], wacc_model, tolerance_bps)

    if verbose:
        _print_wacc_workings(computed, check, excel_assumption_patch["wacc"])

    # ── Build output ───────────────────────────────────────────────────────
    result = {
        "meta": {
            "step": "wacc",
            "run_timestamp": datetime.now().isoformat(),
            "model_file": os.path.basename(model_path),
            "cross_check": "PASS" if check["passed"] else "FAIL",
            "diff_basis_pts": check["diff_bps"],
        },
        "inputs": {
            "risk_free_rate": excel_assumption_patch["wacc"]["risk_free_rate"],
            "adjusted_beta": excel_assumption_patch["wacc"]["beta_blume_adjusted"],
            "equity_risk_premium": excel_assumption_patch["wacc"][
                "equity_risk_premium"
            ],
            "effective_tax_rate": excel_assumption_patch["wacc"][
                "effective_tax_rate_fy2025_actual"
            ],
            "weight_equity": excel_assumption_patch["wacc"]["weight_equity"],
            "weight_debt": excel_assumption_patch["wacc"]["weight_debt"],
            "pretax_cost_of_debt": excel_assumption_patch["wacc"][
                "pretax_cost_of_debt"
            ],
            "market_cap_equity_m": excel_inputs.get("market_cap_equity"),
            "total_debt_m": excel_inputs.get("total_debt"),
        },
        "outputs": {
            "cost_of_equity": round(computed["cost_of_equity"], 8),
            "after_tax_cost_of_debt": round(computed["after_tax_cost_of_debt"], 8),
            "wacc_recalculated": round(computed["wacc_computed"], 8),
            "wacc_from_model": round(wacc_model, 8),
        },
        "display": {
            "cost_of_equity_pct": f"{computed['cost_of_equity']*100:.4f}%",
            "after_tax_cost_of_debt_pct": f"{computed['after_tax_cost_of_debt']*100:.4f}%",
            "wacc_recalculated_pct": f"{computed['wacc_computed']*100:.4f}%",
            "wacc_from_model_pct": f"{wacc_model*100:.4f}%",
        },
        "cross_check": check,
    }

    # ── Write JSON ─────────────────────────────────────────────────────────
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    return result


# ─── PRINT HELPER ─────────────────────────────────────────────────────────────


def _print_wacc_workings(computed: dict, check: dict, cfg: dict):
    """Print CAPM workings — mirrors original src/wacc.py console output."""
    rf = cfg["risk_free_rate"]
    beta = cfg["beta_blume_adjusted"]
    erp = cfg["equity_risk_premium"]
    ke = computed["cost_of_equity"]
    kd = computed["after_tax_cost_of_debt"]
    wacc = computed["wacc_computed"]

    print(f"\n{'─'*60}")
    print("  WACC CALCULATION")
    print(f"{'─'*60}")
    print(f"  Ke  = {rf:.4%} + {beta:.4f} × {erp:.4%} = {ke:.4%}")
    print(
        f"  Kd  = {cfg['pretax_cost_of_debt']:.4%} × (1 - {cfg['effective_tax_rate_fy2025_actual']:.4%}) = {kd:.4%}"
    )
    print(
        f"  WACC = {cfg['weight_equity']:.4%} × {ke:.4%} + {cfg['weight_debt']:.4%} × {kd:.4%} = {wacc:.4%}"
    )
    print(f"  Cross-check: {check['status']}  ({check['diff_bps']:.2f} bps)")
    print(f"{'─'*60}\n")


# ─── STANDALONE CONFIG-ONLY MODE ──────────────────────────────────────────────


def run_wacc_from_config(assumptions: dict, output_path: str = None) -> dict:
    """
    Config-only mode: compute WACC purely from assumptions.json.
    No Excel needed. Used when Excel model is not present.
    Used by engine.py in full-Python modeling mode.

    Args:
        assumptions:  Full assumptions dict
        output_path:  Optional output path for JSON

    Returns:
        dict with wacc result
    """
    computed = compute_wacc(assumptions)
    model_val = assumptions["wacc"]["wacc"]
    tolerance = assumptions["wacc"].get("wacc_tolerance_bps", 1.0)

    check = cross_check_wacc(computed["wacc_computed"], model_val, tolerance)

    result = {
        "meta": {
            "step": "wacc",
            "run_timestamp": datetime.now().isoformat(),
            "mode": "config_only",
            "cross_check": "PASS" if check["passed"] else "FAIL",
            "diff_basis_pts": check["diff_bps"],
        },
        "inputs": computed["inputs_used"],
        "outputs": {
            "cost_of_equity": round(computed["cost_of_equity"], 8),
            "after_tax_cost_of_debt": round(computed["after_tax_cost_of_debt"], 8),
            "wacc_recalculated": round(computed["wacc_computed"], 8),
            "wacc_from_model": round(model_val, 8),
        },
        "display": {
            "cost_of_equity_pct": f"{computed['cost_of_equity']*100:.4f}%",
            "after_tax_cost_of_debt_pct": f"{computed['after_tax_cost_of_debt']*100:.4f}%",
            "wacc_recalculated_pct": f"{computed['wacc_computed']*100:.4f}%",
            "wacc_from_model_pct": f"{model_val*100:.4f}%",
        },
        "cross_check": check,
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    return result


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    parser = argparse.ArgumentParser(description="WACC — config-driven recalculation")
    parser.add_argument("--model", default=None, help="Path to Excel model (optional)")
    parser.add_argument(
        "--config",
        default=os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "assumptions.json"
        ),
    )
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    with open(args.config) as f:
        assumptions = json.load(f)

    if args.model and os.path.exists(args.model):
        result = run_wacc_pipeline(
            args.model, assumptions, output_path=args.output, verbose=args.verbose
        )
    else:
        result = run_wacc_from_config(assumptions, output_path=args.output)
        if args.verbose:
            _print_wacc_workings(
                {
                    "cost_of_equity": result["outputs"]["cost_of_equity"],
                    "after_tax_cost_of_debt": result["outputs"][
                        "after_tax_cost_of_debt"
                    ],
                    "wacc_computed": result["outputs"]["wacc_recalculated"],
                },
                result["cross_check"],
                assumptions["wacc"],
            )

    print(f"  WACC: {result['display']['wacc_recalculated_pct']}")
    print(f"  Ke:   {result['display']['cost_of_equity_pct']}")
    print(f"  Kd:   {result['display']['after_tax_cost_of_debt_pct']}")
    print(f"  Cross-check: {result['meta']['cross_check']}")
    sys.exit(0 if result["meta"]["cross_check"] == "PASS" else 1)
