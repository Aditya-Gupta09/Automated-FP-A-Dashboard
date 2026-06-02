"""
src/modeling/dcf_valuation.py
==============================
DCF Valuation Engine — NVIDIA Corporation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 DOCUMENTATION: DCF DISCOUNTING METHOD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Source: 05b_DCF sheet rows 1–38 | methodology.md | 06_Sensitivity

1. DISCOUNTING CONVENTION: END-OF-YEAR
────────────────────────────────────────
Excel formula (05b_DCF row 8, col H–L):
    PV_FCF(t) = FCFF(t) / (1 + WACC)^t

Where t = projection year number (1, 2, 3, 4, 5)
NOT mid-year (no 0.5 offset in denominator).

Evidence from 05b_DCF row 7 (Projection Year): 1, 2, 3, 4, 5
Evidence from 05b_DCF row 8 formula: =H5/(1+$C$14)^H7

This is STANDARD end-of-year discounting, consistent with
most academic DCF frameworks. NVIDIA's model does NOT use
mid-year convention (Damodaran style).

2. TERMINAL VALUE METHOD: GORDON GROWTH MODEL (PRIMARY)
─────────────────────────────────────────────────────────
Formula (05b_DCF rows 24–28):
    TV = FCF_5 × (1 + g) / (WACC - g)

Where:
    FCF_5 = FCFF in year 5 (FY2030F) = $308,055.69M
    g     = terminal growth rate = 4.0% (= 0.04)
    WACC  = 12.91424510009221%

PV of Terminal Value:
    PV_TV = TV / (1 + WACC)^5

Excel values (05b_DCF):
    FCF_5         = 308,055.69M
    g             = 0.04
    TV            = 3,593,999.41M
    PV_TV         = 1,958,097.55M

EXIT MULTIPLE METHOD (SECONDARY — cross-check only):
    TV_exit = FY2030 EBITDA × peer median EV/EBITDA
    EV/EBITDA peer median = 22.3x (05b_DCF rows 41–45)
    FY2030 EBITDA = $387,542.51M
    TV_exit = 387,542.51 × 22.3 = $8,642,198M

The Gordon Growth method is the PRIMARY method used for
the base case implied share price. Exit multiple is shown
as a reference range but NOT used in the final price.

3. EV → EQUITY → PER SHARE BRIDGE
────────────────────────────────────
Step-by-step (05b_DCF rows 11–21):

    (a) Sum of PV(FCFs)     = Σ [FCFF(t) / (1+WACC)^t] for t=1..5
                            = $664,084.81M

    (b) PV of Terminal Value = TV / (1+WACC)^5
                            = $1,958,097.55M

    (c) Enterprise Value    = (a) + (b)
                            = $2,622,182.37M

    (d) (-) Net Debt        = Total Debt - Cash & Investments
                            = $10,270M - $43,210M
                            = -$32,940M  (NVIDIA is in NET CASH)
        ⚠ Net debt is NEGATIVE = net cash. Subtracting a negative
          INCREASES equity value (net cash adds to equity).

    (e) Equity Value        = EV - Net Debt
                            = $2,622,182.37 - (-$32,940)
                            = $2,655,122.37M

    (f) Diluted Shares      = 24,300M shares

    (g) Implied Share Price = Equity Value / Shares
                            = $2,655,122.37M / 24,300M
                            = $109.26 per share

4. SENSITIVITY ANALYSIS GRIDS
───────────────────────────────
Source: 06_Sensitivity sheet
Two 9×9 grids:
    - WACC range:     [10.9%, 11.4%, 11.9%, 12.4%, 12.9%, 13.4%, 13.9%, 14.4%, 14.9%]
    - Growth (g) range: [2.0%, 2.5%, 3.0%, 3.5%, 4.0%, 4.5%, 5.0%, 5.5%, 6.0%]

Grid 1: Implied Share Price = (Sum_PV_FCF + TV(g,WACC) / (1+WACC)^5 - Net_Debt) / Shares
Grid 2: Enterprise Value     = Sum_PV_FCF + TV(g,WACC) / (1+WACC)^5

Base case cell: WACC=12.91%, g=4.0% → $109.26

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Usage:
    from src.modeling.dcf_valuation import run_dcf
    result = run_dcf(fcff_series, assumptions)
"""

import json
import os

# ─── LOAD CONFIG ──────────────────────────────────────────────────────────────


def load_assumptions(config_path: str = None) -> dict:
    """Load assumptions from config/assumptions.json."""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "assumptions.json"
        )
    with open(config_path) as f:
        return json.load(f)


# ─── STEP 1: DISCOUNT CASH FLOWS (END-OF-YEAR) ───────────────────────────────


def discount_cash_flows(fcff_by_year: dict, wacc: float) -> dict:
    """
    Discounts each year's FCFF to present value using END-OF-YEAR convention.

    Formula: PV(t) = FCFF(t) / (1 + WACC)^t
    Where t = projection year number (1 = FY2026F, 5 = FY2030F)

    Source: 05b_DCF row 8 formula =H5/(1+$C$14)^H7

    Args:
        fcff_by_year: dict {fiscal_year: fcff_usdm}
                      e.g. {2026: 99314.87, 2027: 149945.96, ...}
        wacc:         WACC as decimal (e.g. 0.1291424510009221)

    Returns:
        dict {fiscal_year: pv_fcff_usdm}
    """
    pv_by_year = {}
    projection_year_map = {yr: (i + 1) for i, yr in enumerate(sorted(fcff_by_year))}

    for fiscal_year, fcff in fcff_by_year.items():
        t = projection_year_map[fiscal_year]
        pv = fcff / ((1 + wacc) ** t)
        pv_by_year[fiscal_year] = pv

    return pv_by_year


def sum_pv_fcf(pv_by_year: dict) -> float:
    """Sum of all discounted FCFs (years 1–5)."""
    return sum(pv_by_year.values())


# ─── STEP 2: TERMINAL VALUE (GORDON GROWTH) ───────────────────────────────────


def compute_terminal_value_gordon(fcf_final: float, wacc: float, g: float) -> float:
    """
    Gordon Growth Model terminal value.

    Formula: TV = FCF_5 × (1 + g) / (WACC - g)
    Source: 05b_DCF rows 24–28

    Args:
        fcf_final: FCFF in final projection year (year 5) in $M
        wacc:      WACC as decimal
        g:         Terminal growth rate as decimal (0.04)

    Returns:
        Terminal value in $M

    Raises:
        ValueError if WACC <= g (denominator would be zero or negative)
    """
    if wacc <= g:
        raise ValueError(
            f"WACC ({wacc:.4%}) must exceed terminal growth rate ({g:.4%}). "
            f"Model is undefined when WACC ≤ g."
        )
    return fcf_final * (1 + g) / (wacc - g)


def compute_pv_terminal_value(
    terminal_value: float, wacc: float, horizon_years: int = 5
) -> float:
    """
    Discount terminal value back to present.

    Formula: PV_TV = TV / (1 + WACC)^n
    Source: 05b_DCF row 16

    Args:
        terminal_value: Terminal value from Gordon Growth ($M)
        wacc:           WACC as decimal
        horizon_years:  Number of explicit forecast years (5)

    Returns:
        Present value of terminal value ($M)
    """
    return terminal_value / ((1 + wacc) ** horizon_years)


def compute_terminal_value_exit_multiple(
    ebitda_final: float, ev_ebitda_multiple: float
) -> float:
    """
    Exit multiple terminal value (CROSS-CHECK ONLY — not primary method).

    Formula: TV_exit = FY2030_EBITDA × EV/EBITDA multiple
    Source: 05b_DCF rows 41–45

    Args:
        ebitda_final:      EBITDA in final projection year ($M)
        ev_ebitda_multiple: Peer median EV/EBITDA (22.3x from comps)

    Returns:
        Terminal EV from exit multiple ($M)
    """
    return ebitda_final * ev_ebitda_multiple


# ─── STEP 3: EV → EQUITY → PER SHARE BRIDGE ──────────────────────────────────


def compute_enterprise_value(sum_pv_fcf_val: float, pv_tv: float) -> float:
    """
    Enterprise Value = Sum of PV(FCFs) + PV(Terminal Value)
    Source: 05b_DCF row 17
    """
    return sum_pv_fcf_val + pv_tv


def compute_equity_value(enterprise_value: float, net_debt: float) -> float:
    """
    Equity Value = Enterprise Value - Net Debt

    IMPORTANT: Net debt = Total Debt - Cash.
    For NVIDIA, net_debt = -$32,940M (net cash position).
    Subtracting a negative number INCREASES equity value.

    Source: 05b_DCF rows 17–19

    Args:
        enterprise_value: EV in $M
        net_debt:         Total debt minus cash ($M). Negative = net cash.

    Returns:
        Equity value ($M)
    """
    return enterprise_value - net_debt


def compute_implied_share_price(
    equity_value: float, diluted_shares_millions: float
) -> float:
    """
    Implied Share Price = Equity Value ($M) / Diluted Shares (millions)

    Note: Both in millions → result is in $/share.
    Source: 05b_DCF row 21

    Args:
        equity_value:            Equity value in $M
        diluted_shares_millions: Diluted shares outstanding in millions

    Returns:
        Implied share price in USD
    """
    if diluted_shares_millions == 0:
        raise ValueError("Diluted shares outstanding cannot be zero.")
    return equity_value / diluted_shares_millions


# ─── STEP 4: SENSITIVITY ANALYSIS ─────────────────────────────────────────────


def build_sensitivity_grid(
    sum_pv_fcf_val: float,
    fcf_final: float,
    net_debt: float,
    shares_millions: float,
    wacc_range: list,
    g_range: list,
    horizon_years: int = 5,
) -> dict:
    """
    9×9 sensitivity grids: Implied Price and Enterprise Value.
    Replicates 06_Sensitivity sheet exactly.

    Formula per cell:
        TV(g, WACC)      = fcf_final × (1+g) / (WACC-g)
        PV_TV(g, WACC)   = TV / (1+WACC)^5
        EV(g, WACC)      = sum_pv_fcf + PV_TV
        Price(g, WACC)   = (EV - net_debt) / shares

    Args:
        sum_pv_fcf_val:  Σ PV(FCFs) — fixed, does not change with g/WACC in sensitivity
        fcf_final:       FCF in year 5 ($M)
        net_debt:        Net debt ($M) — fixed
        shares_millions: Diluted shares (M)
        wacc_range:      list of WACC values (decimals)
        g_range:         list of g values (decimals)
        horizon_years:   discount period for TV (5)

    Returns:
        dict with 'implied_price' and 'enterprise_value' grids:
        {
            "wacc_range": [...],
            "g_range": [...],
            "implied_price": {wacc: {g: price}},
            "enterprise_value": {wacc: {g: ev}},
        }
    """
    default_wacc_range = [0.109, 0.114, 0.119, 0.124, 0.129, 0.134, 0.139, 0.144, 0.149]
    default_g_range = [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06]

    wacc_range = wacc_range or default_wacc_range
    g_range = g_range or default_g_range

    price_grid = {}
    ev_grid = {}

    for w in wacc_range:
        price_grid[w] = {}
        ev_grid[w] = {}
        for g in g_range:
            if w <= g:
                price_grid[w][g] = None
                ev_grid[w][g] = None
                continue
            tv = compute_terminal_value_gordon(fcf_final, w, g)
            pv_tv = compute_pv_terminal_value(tv, w, horizon_years)
            ev = sum_pv_fcf_val + pv_tv
            price = (ev - net_debt) / shares_millions
            price_grid[w][g] = round(price, 4)
            ev_grid[w][g] = round(ev, 4)

    return {
        "wacc_range": wacc_range,
        "g_range": g_range,
        "implied_price": price_grid,
        "enterprise_value": ev_grid,
    }


# ─── MASTER DCF RUNNER ────────────────────────────────────────────────────────


def run_dcf(
    fcff_by_year: dict,
    assumptions: dict,
    scenario: str = "base",
    run_sensitivity: bool = True,
) -> dict:
    """
    Full DCF valuation engine. Replicates 05b_DCF sheet exactly.

    Args:
        fcff_by_year: dict {fiscal_year: fcff_usdm} from fcff.py
        assumptions:  full assumptions dict from config/assumptions.json
        scenario:     "base" | "upside" | "downside"
        run_sensitivity: whether to compute 9×9 sensitivity grids

    Returns:
        dict with full DCF results including bridge, sensitivity, and cross-check
    """
    dcf_cfg = assumptions["dcf"]
    wacc = assumptions["wacc"]["wacc"]
    g = dcf_cfg["terminal_growth_rate"]
    n_years = dcf_cfg["projection_horizon_years"]
    net_debt = dcf_cfg["net_debt_bridge"]["net_debt_usdm"]
    shares = dcf_cfg["diluted_shares_outstanding_millions"]
    mkt_price = dcf_cfg["market_price_valuation_date_usd"]

    # ── Step 1: Discount FCFs ─────────────────────────────────────────────
    pv_by_year = discount_cash_flows(fcff_by_year, wacc)
    sum_pv_fcf_v = sum_pv_fcf(pv_by_year)

    # ── Step 2: Terminal Value ────────────────────────────────────────────
    final_year = max(fcff_by_year.keys())
    fcf_final = fcff_by_year[final_year]

    tv = compute_terminal_value_gordon(fcf_final, wacc, g)
    pv_tv = compute_pv_terminal_value(tv, wacc, n_years)

    # ── Step 3: EV → Equity Bridge ────────────────────────────────────────
    ev = compute_enterprise_value(sum_pv_fcf_v, pv_tv)
    eq_val = compute_equity_value(ev, net_debt)
    impl_price = compute_implied_share_price(eq_val, shares)
    updown_pct = (impl_price / mkt_price - 1) if mkt_price else None

    # ── Step 4: Sensitivity ───────────────────────────────────────────────
    sensitivity = None
    if run_sensitivity:
        sensitivity = build_sensitivity_grid(
            sum_pv_fcf_val=sum_pv_fcf_v,
            fcf_final=fcf_final,
            net_debt=net_debt,
            shares_millions=shares,
            wacc_range=None,
            g_range=None,
        )

    # ── Cross-check vs Excel expected values ──────────────────────────────
    expected = dcf_cfg.get("expected_outputs", {})
    cross_checks = {}
    for key, exp_val in expected.items():
        if key in (
            "sum_pv_fcf_usdm",
            "terminal_value_usdm",
            "pv_terminal_value_usdm",
            "enterprise_value_usdm",
            "equity_value_usdm",
            "implied_share_price_usd",
        ):
            computed_val = {
                "sum_pv_fcf_usdm": sum_pv_fcf_v,
                "terminal_value_usdm": tv,
                "pv_terminal_value_usdm": pv_tv,
                "enterprise_value_usdm": ev,
                "equity_value_usdm": eq_val,
                "implied_share_price_usd": impl_price,
            }.get(key)
            if computed_val is not None:
                diff = abs(computed_val - exp_val)
                tol = 1.0 if "usdm" in key else 0.01
                cross_checks[key] = {
                    "computed": round(computed_val, 4),
                    "expected": round(exp_val, 4),
                    "difference": round(diff, 4),
                    "passed": diff <= tol,
                }

    all_cross_check_passed = all(v["passed"] for v in cross_checks.values())

    return {
        "scenario": scenario,
        "wacc_used": wacc,
        "terminal_growth_rate": g,
        "discounting_convention": "end_of_year",
        "terminal_value_method": "gordon_growth",
        "fcff_by_year": {str(k): round(v, 4) for k, v in fcff_by_year.items()},
        "pv_fcff_by_year": {str(k): round(v, 4) for k, v in pv_by_year.items()},
        "sum_pv_fcf_usdm": round(sum_pv_fcf_v, 4),
        "terminal_value_usdm": round(tv, 4),
        "pv_terminal_value_usdm": round(pv_tv, 4),
        "enterprise_value_usdm": round(ev, 4),
        "net_debt_bridge": dcf_cfg["net_debt_bridge"],
        "net_debt_usdm": net_debt,
        "equity_value_usdm": round(eq_val, 4),
        "diluted_shares_millions": shares,
        "implied_share_price_usd": round(impl_price, 4),
        "market_price_usd": mkt_price,
        "upside_downside_pct": round(updown_pct, 4) if updown_pct else None,
        "sensitivity": sensitivity,
        "cross_check": {
            "all_passed": all_cross_check_passed,
            "sub_checks": cross_checks,
            "status": "PASS" if all_cross_check_passed else "FAIL",
        },
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    assumptions = load_assumptions()
    expected = assumptions["dcf"]["expected_outputs"]

    # Use pre-computed Excel FCFF values for standalone validation
    fcff_by_year = {
        2026: 99314.87674960226,
        2027: 149945.9602138523,
        2028: 200234.93729952897,
        2029: 246422.56910654268,
        2030: 308055.6886365452,
    }

    result = run_dcf(fcff_by_year, assumptions, scenario="base", run_sensitivity=True)

    print("\n" + "═" * 64)
    print("  dcf_valuation.py — DCF Results")
    print("═" * 64)
    print(f"\n  Discounting:     {result['discounting_convention']}")
    print(f"  Terminal Value:  {result['terminal_value_method']}")
    print(f"  WACC:            {result['wacc_used']*100:.4f}%")
    print(f"  g:               {result['terminal_growth_rate']*100:.2f}%")
    print(f"\n  {'─'*48}")
    print(f"  Sum PV FCFs:     ${result['sum_pv_fcf_usdm']:>15,.2f}M")
    print(f"  Terminal Value:  ${result['terminal_value_usdm']:>15,.2f}M")
    print(f"  PV(TV):          ${result['pv_terminal_value_usdm']:>15,.2f}M")
    print(f"  Enterprise Value:${result['enterprise_value_usdm']:>15,.2f}M")
    print(f"  Net Debt:        ${result['net_debt_usdm']:>15,.2f}M")
    print(f"  Equity Value:    ${result['equity_value_usdm']:>15,.2f}M")
    print(f"  Diluted Shares:  {result['diluted_shares_millions']:>15,.0f}M")
    print(f"  Implied Price:   ${result['implied_share_price_usd']:>15.2f}")
    print(f"  Market Price:    ${result['market_price_usd']:>15.2f}")
    print(f"  Up/Downside:     {result['upside_downside_pct']*100:>14.1f}%")
    print(f"\n  Cross-check vs Excel: {result['cross_check']['status']}")
    for k, v in result["cross_check"]["sub_checks"].items():
        status = "✓" if v["passed"] else "✗"
        print(f"    {status}  {k:<35} diff={v['difference']:.4f}")
    print()
    sys.exit(0 if result["cross_check"]["all_passed"] else 1)
