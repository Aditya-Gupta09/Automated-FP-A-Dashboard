"""
src/modeling/reconciliation.py
================================
Balance Sheet Plug Logic + All Model Invariant Checks

This module validates the model against financial invariants and DCF outputs.
It is designed to be conservative: keep model formulas untouched and use
reconciliation logic that is tolerant, scenario-aware, and explicit about
failures.
"""

from __future__ import annotations

from numbers import Real
from typing import Any, Mapping

# ─── TOLERANCES ───────────────────────────────────────────────────────────────

BS_TOLERANCE_USDM = 0.01  # $0.01M — same as 99_Validation sheet
CF_TOLERANCE_USDM = 0.01
REV_TOLERANCE_USDM = 0.01

# DCF tolerances are intentionally modest and scale-aware.
# Absolute floors keep tiny expected values from making relative tolerance too strict.
DCF_DEFAULT_REL_TOL = 0.005  # 0.5%
DCF_METRIC_TOLERANCES = {
    "implied_share_price_usd": {"abs": 0.25, "rel": 0.005},
    "enterprise_value_usdm": {"abs": 5.0, "rel": 0.005},
    "equity_value_usdm": {"abs": 5.0, "rel": 0.005},
    "sum_pv_fcf_usdm": {"abs": 5.0, "rel": 0.005},
    "terminal_value_usdm": {"abs": 10.0, "rel": 0.005},
    "pv_terminal_value_usdm": {"abs": 5.0, "rel": 0.005},
}


# ─── BALANCE SHEET PLUG ASSUMPTIONS ──────────────────────────────────────────
# All sourced from 04b_Projection_BS. No hardcoded values in engine code.

BS_ASSUMPTIONS = {
    "sbc_pct_revenue": {
        "base": {2026: 0.024, 2027: 0.019, 2028: 0.017, 2029: 0.016, 2030: 0.016},
        "upside": {2026: 0.025, 2027: 0.021, 2028: 0.019, 2029: 0.019, 2030: 0.019},
        "downside": {2026: 0.023, 2027: 0.018, 2028: 0.015, 2029: 0.014, 2030: 0.013},
    },
    "dividend_payout_ratio": {
        "base": {2026: 0.010, 2027: 0.009, 2028: 0.009, 2029: 0.008, 2030: 0.008},
        "upside": {2026: 0.012, 2027: 0.015, 2028: 0.020, 2029: 0.025, 2030: 0.030},
        "downside": {2026: 0.009, 2027: 0.008, 2028: 0.007, 2029: 0.006, 2030: 0.006},
    },
    "new_lease_obligations_usdm_per_year": 1520.0,
    "current_lease_pct_of_total": 0.15938018815716656,
    "current_taxes_pct_of_tax_expense": 0.07904180872061727,
    "other_lt_liabilities_flat_usdm": 4245.0,
    "goodwill_flat_usdm": 5188.0,
    "lt_deferred_tax_assets_flat_usdm": 10979.0,
    "other_assets_flat_usdm": 6425.0,
    "common_stock_flat_usdm": 24.0,
    "treasury_stock_flat_usdm": 0.0,
    "oci_flat_usdm": 28.0,
    "fy2025_retained_earnings_usdm": 68038.0,
    "fy2025_apic_usdm": 11237.0,
}


# ─── SMALL HELPERS ───────────────────────────────────────────────────────────


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if _is_number(value):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _extract_total_assets(assets: Any) -> float:
    if _is_number(assets):
        return float(assets)
    if isinstance(assets, Mapping):
        for key in ("total_assets", "total_assets_usdm", "assets", "value"):
            if key in assets:
                return _coerce_float(assets.get(key), 0.0)
    return 0.0


def _normalize_scenario(scenario: Any) -> str | None:
    if scenario is None:
        return None
    text = str(scenario).strip().lower()
    return text or None


def _is_metric_dict(payload: Any) -> bool:
    return isinstance(payload, Mapping) and any(
        key in payload for key in DCF_METRIC_TOLERANCES.keys()
    )


def _resolve_expected_dcf(
    expected: Mapping[str, Any] | None, scenario: str | None
) -> dict[str, Any]:
    """
    Accepts either:
      - a flat dict of expected DCF outputs, or
      - a scenario map like {"base": {...}, "upside": {...}, "downside": {...}}
    and returns the most appropriate flat dict.
    """
    if not isinstance(expected, Mapping):
        return {}

    # Common nested shapes seen in configs.
    for wrapper_key in ("expected_outputs", "dcf_expected_outputs", "outputs"):
        nested = expected.get(wrapper_key)
        if isinstance(nested, Mapping):
            return _resolve_expected_dcf(nested, scenario)

    if _is_metric_dict(expected):
        return dict(expected)

    normalized = _normalize_scenario(scenario)
    if (
        normalized
        and normalized in expected
        and isinstance(expected[normalized], Mapping)
    ):
        candidate = expected[normalized]
        if _is_metric_dict(candidate):
            return dict(candidate)

    for fallback_key in ("base", "default", "standard"):
        candidate = expected.get(fallback_key)
        if isinstance(candidate, Mapping) and _is_metric_dict(candidate):
            return dict(candidate)

    # Last resort: if the current mapping already contains numeric values, keep it.
    return dict(expected)


def _metric_tolerance(expected_value: float, abs_tol: float, rel_tol: float) -> float:
    expected_abs = abs(_coerce_float(expected_value, 0.0))
    return max(abs_tol, expected_abs * rel_tol)


def _compare_metric(
    model_value: Any, expected_value: Any, abs_tol: float, rel_tol: float
):
    model = _coerce_float(model_value, 0.0)
    expected = _coerce_float(expected_value, 0.0)
    diff = model - expected
    tol = _metric_tolerance(expected, abs_tol, rel_tol)
    passed = abs(diff) <= tol
    return model, expected, diff, tol, passed


# ─── RETAINED EARNINGS PLUG ───────────────────────────────────────────────────


def compute_retained_earnings(
    prior_re: float, net_income: float, dividends: float
) -> float:
    """
    RE(t) = RE(t-1) + Net Income(t) - Dividends(t)
    """
    return prior_re + net_income - dividends


def compute_apic(prior_apic: float, sbc: float) -> float:
    """APIC roll-forward: APIC grows by SBC each year."""
    return prior_apic + sbc


def compute_shareholders_equity(
    common_stock: float,
    apic: float,
    retained_earnings: float,
    treasury_stock: float,
    oci: float,
) -> float:
    """Shareholders' Equity = Common Stock + APIC + RE + Treasury + OCI"""
    return common_stock + apic + retained_earnings + treasury_stock + oci


# ─── CHECK 1: BALANCE SHEET TIE ──────────────────────────────────────────────


def check_balance_sheet_tie(
    assets: Any,
    liabilities: Any,
    equity: Any,
    year: int,
    tolerance: float = BS_TOLERANCE_USDM,
) -> dict:
    """Validates: Total Assets == Total Liabilities + Shareholders' Equity"""
    total_assets = _extract_total_assets(assets)
    total_liabilities = _coerce_float(liabilities, 0.0)
    total_equity = _coerce_float(equity, 0.0)
    total_le = total_liabilities + total_equity
    diff = total_assets - total_le
    passed = abs(diff) <= tolerance

    return {
        "check": "balance_sheet_tie",
        "year": year,
        "total_assets_usdm": round(total_assets, 4),
        "total_liab_plus_equity_usdm": round(total_le, 4),
        "difference_usdm": round(diff, 4),
        "tolerance_usdm": tolerance,
        "passed": passed,
        "message": (
            f"FY{year} BS PASS: diff={diff:.4f}$M"
            if passed
            else f"FY{year} BS FAIL: Assets={total_assets:.2f}, L+E={total_le:.2f}, diff={diff:.2f}$M"
        ),
    }


def auto_plug_retained_earnings(
    total_assets: float, total_liabilities: float, equity_ex_re: float
) -> float:
    """RE plug used only for rounding reconciliation."""
    return total_assets - total_liabilities - equity_ex_re


# ─── CHECK 2: CASH FLOW RECONCILIATION ───────────────────────────────────────


def check_cashflow_reconciliation(
    cfo: Any,
    cfi: Any,
    cff: Any,
    net_change_cash: Any,
    year: int,
    tolerance: float = CF_TOLERANCE_USDM,
) -> dict:
    """Validates: CFO + CFI + CFF == Net Change in Cash"""
    cfo_v = _coerce_float(cfo, 0.0)
    cfi_v = _coerce_float(cfi, 0.0)
    cff_v = _coerce_float(cff, 0.0)
    stated = _coerce_float(net_change_cash, 0.0)
    computed_net = cfo_v + cfi_v + cff_v
    diff = computed_net - stated
    passed = abs(diff) <= tolerance

    return {
        "check": "cashflow_reconciliation",
        "year": year,
        "cfo_usdm": cfo_v,
        "cfi_usdm": cfi_v,
        "cff_usdm": cff_v,
        "sum_cfo_cfi_cff_usdm": round(computed_net, 4),
        "net_change_cash_usdm": stated,
        "difference_usdm": round(diff, 4),
        "tolerance_usdm": tolerance,
        "passed": passed,
        "message": (
            f"FY{year} CF PASS: diff={diff:.4f}$M"
            if passed
            else f"FY{year} CF FAIL: computed={computed_net:.2f}, stated={stated:.2f}, diff={diff:.2f}$M"
        ),
    }


# ─── CHECK 3: REVENUE CROSS-CHECK ─────────────────────────────────────────────


def check_revenue_crosscheck(
    revenue_is: Any, revenue_fcff: Any, year: int, tolerance: float = REV_TOLERANCE_USDM
) -> dict:
    """Validates: Revenue in IS == Revenue in FCFF schedule"""
    revenue_is_v = _coerce_float(revenue_is, 0.0)
    revenue_fcff_v = _coerce_float(revenue_fcff, 0.0)
    diff = revenue_is_v - revenue_fcff_v
    passed = abs(diff) <= tolerance

    return {
        "check": "revenue_crosscheck",
        "year": year,
        "revenue_is_usdm": round(revenue_is_v, 4),
        "revenue_fcff_usdm": round(revenue_fcff_v, 4),
        "difference_usdm": round(diff, 4),
        "tolerance_usdm": tolerance,
        "passed": passed,
        "message": (
            f"FY{year} REV PASS: diff={diff:.4f}$M"
            if passed
            else f"FY{year} REV FAIL: IS={revenue_is_v:.2f}, FCFF={revenue_fcff_v:.2f}, diff={diff:.2f}$M"
        ),
    }


# ─── CHECK 4: DCF OUTPUT SNAPSHOT ─────────────────────────────────────────────


def check_dcf_outputs(
    dcf_result: Mapping[str, Any],
    expected: Mapping[str, Any] | None,
    price_tolerance_usd: float = 0.25,
    rel_tolerance: float = DCF_DEFAULT_REL_TOL,
    scenario: str | None = None,
) -> dict:
    """
    Validates DCF outputs against benchmark values.

    This version is scenario-aware, uses the passed price tolerance, and
    produces detailed failures instead of collapsing everything into one generic
    message.
    """
    normalized_scenario = _normalize_scenario(
        scenario
        or (dcf_result.get("scenario") if isinstance(dcf_result, Mapping) else None)
    )
    expected_flat = _resolve_expected_dcf(expected, normalized_scenario)

    metric_specs = {
        "implied_share_price_usd": {
            "expected_key": "implied_share_price_usd",
            "abs_tol": price_tolerance_usd,
            "rel_tol": rel_tolerance,
        },
        **{
            metric: {
                "expected_key": metric,
                "abs_tol": cfg["abs"],
                "rel_tol": cfg["rel"],
            }
            for metric, cfg in DCF_METRIC_TOLERANCES.items()
            if metric != "implied_share_price_usd"
        },
    }

    checks: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    all_passed = True

    for metric, spec in metric_specs.items():
        computed_val = (
            dcf_result.get(metric) if isinstance(dcf_result, Mapping) else None
        )
        expected_val = (
            expected_flat.get(spec["expected_key"])
            if isinstance(expected_flat, Mapping)
            else None
        )

        if computed_val is None or expected_val is None:
            all_passed = False
            msg = f"Missing value for {metric}"
            checks[metric] = {
                "passed": False,
                "message": msg,
                "computed": None,
                "expected": None,
                "difference": None,
                "tolerance": None,
            }
            failures.append(msg)
            continue

        model, expected_num, diff, tol, passed = _compare_metric(
            computed_val, expected_val, spec["abs_tol"], spec["rel_tol"]
        )
        if not passed:
            all_passed = False
            failures.append(
                f"{metric}: model={model:.4f}, expected={expected_num:.4f}, diff={diff:.4f}, tol={tol:.4f}"
            )

        checks[metric] = {
            "computed": round(model, 4),
            "expected": round(expected_num, 4),
            "difference": round(diff, 4),
            "tolerance": round(tol, 4),
            "passed": passed,
        }

    return {
        "check": "dcf_output_crosscheck",
        "scenario": normalized_scenario,
        "all_passed": all_passed,
        "sub_checks": checks,
        "failures": failures,
    }


# ─── RUN ALL CHECKS ───────────────────────────────────────────────────────────


def run_all_checks(
    is_results: Mapping[int, Any],
    bs_results: Mapping[int, Any],
    cf_results: Mapping[int, Any],
    fcff_results: Mapping[int, Any],
    dcf_result: Mapping[str, Any],
    assumptions: Mapping[str, Any],
    forecast_years: list | None = None,
    scenario: str | None = None,
) -> dict:
    """
    Master reconciliation runner. Executes all checks across forecast years.
    """
    if forecast_years is None:
        forecast_years = [2026, 2027, 2028, 2029, 2030]

    resolved_scenario = _normalize_scenario(
        scenario
        or (dcf_result.get("scenario") if isinstance(dcf_result, Mapping) else None)
    )

    bs_checks: dict[int, dict[str, Any]] = {}
    cf_checks: dict[int, dict[str, Any]] = {}
    rev_checks: dict[int, dict[str, Any]] = {}
    failures: list[str] = []

    for yr in forecast_years:
        bs = bs_results.get(yr, {}) or {}
        cf = cf_results.get(yr, {}) or {}
        is_ = is_results.get(yr, {}) or {}
        ff = fcff_results.get(yr, {}) or {}

        bs_check = check_balance_sheet_tie(
            assets=bs.get("total_assets", bs.get("total_assets_usdm", 0)),
            liabilities=bs.get(
                "total_liabilities", bs.get("total_liabilities_usdm", 0)
            ),
            equity=bs.get("shareholders_equity", bs.get("shareholders_equity_usdm", 0)),
            year=yr,
        )
        bs_checks[yr] = bs_check
        if not bs_check["passed"]:
            failures.append(bs_check["message"])

        cf_check = check_cashflow_reconciliation(
            cfo=cf.get("cfo", cf.get("cfo_usdm", 0)),
            cfi=cf.get("cfi", cf.get("cfi_usdm", 0)),
            cff=cf.get("cff", cf.get("cff_usdm", 0)),
            net_change_cash=cf.get(
                "net_change_cash", cf.get("net_change_cash_usdm", 0)
            ),
            year=yr,
        )
        cf_checks[yr] = cf_check
        if not cf_check["passed"]:
            failures.append(cf_check["message"])

        rev_check = check_revenue_crosscheck(
            revenue_is=is_.get("revenue", is_.get("revenue_usdm", 0)),
            revenue_fcff=ff.get("revenue", ff.get("revenue_usdm", 0)),
            year=yr,
        )
        rev_checks[yr] = rev_check
        if not rev_check["passed"]:
            failures.append(rev_check["message"])

    expected_dcf = (
        assumptions.get("dcf", {}).get("expected_outputs", {})
        if isinstance(assumptions, Mapping)
        else {}
    )
    dcf_check = check_dcf_outputs(
        dcf_result=dcf_result,
        expected=expected_dcf,
        scenario=resolved_scenario,
    )
    if not dcf_check["all_passed"]:
        failures.extend(
            dcf_check["failures"] or ["DCF output mismatch vs Excel expected values"]
        )

    total_checks = len(forecast_years) * 3 + 1
    passed_checks = total_checks - len(failures)
    all_passed = len(failures) == 0

    return {
        "all_passed": all_passed,
        "scenario": resolved_scenario,
        "bs_checks": bs_checks,
        "cf_checks": cf_checks,
        "revenue_checks": rev_checks,
        "dcf_check": dcf_check,
        "failures": failures,
        "summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": len(failures),
            "status": "PASS" if all_passed else "FAIL",
        },
    }


# ─── CLI ENTRY POINT ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═" * 64)
    print("  reconciliation.py — Balance Sheet Plug Documentation")
    print("═" * 64)
    print("""
  PLUG MECHANISM: Retained Earnings
  ───────────────────────────────────
  RE(t) = RE(t-1) + Net Income(t) - Dividends(t)

  Invariant: Total Assets - Total Liabilities - Total Equity = 0
  Tolerance: ±$0.01M  (same as 99_Validation tab)
""")
    print("═" * 64 + "\n")
