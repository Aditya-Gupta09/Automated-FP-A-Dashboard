"""
src/modeling/comps.py
======================
Comparable Company Analysis — Canonical Layer Integration

Refactored from: src/comps.py (original repo)
Key changes vs original:
  1. CANONICAL DATA LAYER: reads from comps_data.csv, NOT directly from Excel
  2. load_comps_from_canonical() is the ONLY data entry point
  3. NVIDIA subject data loaded from assumptions.json (not Excel)
  4. Excel reading completely removed from this module
  5. Moved to src/modeling/ — clean module boundary
  6. All statistical logic (compute_stats, implied prices) preserved exactly

Original src/comps.py functionality fully preserved:
  - EV/Revenue, EV/EBITDA, P/E multiples per peer
  - 6-level statistics: high, p75, mean, median, p25, low
  - Implied prices via EV bridge and P/E
  - Premium/discount vs current price
  - comps_results.json output schema identical

Canonical CSV schema (comps_data.csv):
  ticker, company_name, market_cap, net_debt, ev, ltm_revenue,
  ltm_ebitda, ltm_ebitda_adj, ltm_net_income, ev_ebitda, ev_ebitda_adj,
  p_e, ev_sales, ltm_price, ltm_eps, data_date, notes

Usage:
    from src.modeling.comps import run_comps
    result = run_comps(
        comps_csv="data/raw/comps_data.csv",
        assumptions=assumptions
    )
"""

import os
import csv
import json
import statistics
from datetime import datetime

# ─── CANONICAL DATA LOADER ────────────────────────────────────────────────────


def load_comps_from_canonical(comps_csv_path: str) -> tuple:
    """
    Load comps data from canonical CSV.

    This is the ONLY data entry point for this module.
    Does NOT read from Excel. Does NOT call openpyxl.

    Canonical CSV is written by run_all.py Step 5 (run_comps_csv).
    Schema: ticker, company_name, market_cap, net_debt, ev, ltm_revenue,
            ltm_ebitda, ltm_ebitda_adj, ltm_net_income, ev_ebitda, ev_ebitda_adj,
            p_e, ev_sales, ltm_price, ltm_eps, data_date, notes

    Args:
        comps_csv_path: path to comps_data.csv

    Returns:
        (subject, peers) where:
            subject: dict for NVIDIA (ticker == "NVDA")
            peers:   list of dicts for all other companies

    Raises:
        FileNotFoundError: if CSV not found
        ValueError: if NVDA row not found in CSV
    """
    if not os.path.exists(comps_csv_path):
        raise FileNotFoundError(
            f"Canonical comps CSV not found: {comps_csv_path}\n"
            f"Run run_all.py (Step 5) to generate comps_data.csv first."
        )

    def safe_float(val):
        """Convert string to float, return None if blank or invalid."""
        if val is None or str(val).strip() in ("", "None", "nan", "NaN"):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    rows = []
    with open(comps_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {
                "ticker": row.get("ticker", ""),
                "company_name": row.get("company_name", ""),
                "market_cap": safe_float(row.get("market_cap")),
                "net_debt": safe_float(row.get("net_debt")),
                "ev": safe_float(row.get("ev")),
                "ltm_revenue": safe_float(row.get("ltm_revenue")),
                "ltm_ebitda": safe_float(row.get("ltm_ebitda")),
                "ltm_ebitda_adj": safe_float(row.get("ltm_ebitda_adj")),
                "ltm_net_income": safe_float(row.get("ltm_net_income")),
                "ev_ebitda": safe_float(row.get("ev_ebitda")),
                "p_e": safe_float(row.get("p_e")),
                "ev_sales": safe_float(row.get("ev_sales")),
                "ltm_price": safe_float(row.get("ltm_price")),
                "ltm_eps": safe_float(row.get("ltm_eps")),
                "data_date": row.get("data_date", ""),
                "notes": row.get("notes", ""),
            }
            rows.append(parsed)

    # Split subject (NVDA) from peers
    subject_rows = [r for r in rows if r["ticker"] == "NVDA"]
    peer_rows = [r for r in rows if r["ticker"] != "NVDA"]

    if not subject_rows:
        raise ValueError(
            f"NVDA row not found in {comps_csv_path}. "
            f"Check that the canonical CSV includes the subject company."
        )

    subject = subject_rows[0]
    return subject, peer_rows


def load_subject_from_assumptions(assumptions: dict) -> dict:
    """
    Load NVIDIA subject data from assumptions.json.
    Used when comps_data.csv does not include NVDA row,
    or to override with model-consistent subject financials.

    Args:
        assumptions: full assumptions dict

    Returns:
        subject dict with keys matching canonical comps schema
    """
    hist = assumptions["historical_actuals_fy2025"]
    dcf = assumptions["dcf"]
    expected_outputs = dcf.get("expected_outputs", {})
    if (
        isinstance(expected_outputs, dict)
        and "base" in expected_outputs
        and isinstance(expected_outputs["base"], dict)
    ):
        expected_outputs = expected_outputs["base"]

    return {
        "ticker": "NVDA",
        "company_name": "NVIDIA",
        "ev": expected_outputs["enterprise_value_usdm"] / 1000,  # → $B
        "ltm_revenue": hist["revenue_usdm"] / 1000,
        "ltm_ebitda": hist["ebitda_usdm"] / 1000,
        "ltm_net_income": hist["net_income_usdm"] / 1000,
        "net_debt": dcf["net_debt_bridge"]["net_debt_usdm"] / 1000,
        "ltm_price": dcf["market_price_valuation_date_usd"],
        "ltm_eps": None,
        "market_cap": assumptions["wacc"]["market_cap_equity_usdm"] / 1000,
    }


# ─── MULTIPLE CALCULATION (preserved from original) ─────────────────────────


def compute_multiples(peer: dict) -> dict:
    """
    Compute EV/Revenue, EV/EBITDA, P/E for a single peer.
    If pre-computed values exist in CSV, use those (avoids re-computation).
    Otherwise compute from raw financials.

    Excludes multiples where inputs are None, zero, or economically invalid
    (e.g. negative earnings for P/E).

    Args:
        peer: dict from canonical CSV

    Returns:
        dict: {ev_revenue, ev_ebitda, pe} — each value or None
    """
    # Prefer pre-computed values from canonical CSV
    ev_revenue = peer.get("ev_sales")
    ev_ebitda = peer.get("ev_ebitda")
    pe = peer.get("p_e")

    # Fall back to computing from raw if pre-computed is None
    ev = peer.get("ev")
    rev = peer.get("ltm_revenue")
    ebt = peer.get("ltm_ebitda")
    pr = peer.get("ltm_price")
    eps = peer.get("ltm_eps")

    if ev_revenue is None and ev and rev and rev > 0:
        ev_revenue = ev / rev

    if ev_ebitda is None and ev and ebt and ebt > 0:
        ev_ebitda = ev / ebt

    if pe is None and pr and eps and eps > 0:
        pe = pr / eps

    return {
        "ev_revenue": ev_revenue,
        "ev_ebitda": ev_ebitda,
        "pe": pe,
    }


# ─── STATISTICS (preserved exactly from original src/comps.py) ───────────────


def compute_stats(values: list) -> dict:
    """
    Compute 6-level statistics for a list of multiples.
    Nones are filtered before computation.

    Statistics: high, p75, mean, median, p25, low, n
    Uses linear interpolation for percentiles (same as Excel PERCENTILE.INC).

    Preserved from original src/comps.py compute_stats().
    """
    clean = sorted([v for v in values if v is not None])
    if not clean:
        return {k: None for k in ["high", "p75", "mean", "median", "p25", "low", "n"]}

    n = len(clean)

    def percentile(data, p):
        """Linear interpolation — matches Excel PERCENTILE.INC"""
        idx = (p / 100) * (len(data) - 1)
        lo = int(idx)
        hi = lo + 1
        if hi >= len(data):
            return data[-1]
        frac = idx - lo
        return data[lo] + frac * (data[hi] - data[lo])

    return {
        "high": max(clean),
        "p75": percentile(clean, 75),
        "mean": sum(clean) / n,
        "median": statistics.median(clean),
        "p25": percentile(clean, 25),
        "low": min(clean),
        "n": n,
    }


# ─── IMPLIED PRICE CALCULATION (preserved from original) ─────────────────────


def implied_price_from_ev_multiple(
    multiple, subject_metric_b, net_debt_b, shares_b
) -> float:
    """
    Derive implied share price from EV-based multiple.

    Formula:
        Implied EV         = multiple × subject_metric ($B)
        Implied Equity Val = Implied EV − Net Debt ($B)
        Implied Price      = Implied Equity Val / Shares ($B) → $/share

    Note: net_debt_b is negative for NVIDIA (net cash).
    Subtracting a negative = adding cash back to equity value.

    Preserved from original src/comps.py implied_price_from_ev_multiple().
    """
    if multiple is None or subject_metric_b is None or shares_b is None:
        return None
    if shares_b == 0:
        return None
    implied_ev = multiple * subject_metric_b
    implied_equity = implied_ev - net_debt_b
    implied_price = implied_equity / shares_b
    return implied_price


def implied_price_from_pe(pe_multiple, subject_eps) -> float:
    """
    Derive implied price from P/E multiple.
    Formula: Implied Price = P/E × EPS
    Preserved from original.
    """
    if pe_multiple is None or subject_eps is None:
        return None
    return pe_multiple * subject_eps


def premium_discount(current_price, implied_price) -> float:
    """
    Upside/downside of implied price vs current price.
    Positive = upside, Negative = downside.
    Preserved from original.
    """
    if implied_price is None or current_price is None or current_price == 0:
        return None
    return implied_price / current_price - 1


# ─── MASTER COMPS RUNNER ──────────────────────────────────────────────────────


def run_comps(
    comps_csv_path: str,
    assumptions: dict,
    output_path: str = None,
    verbose: bool = False,
) -> dict:
    """
    Full comparable analysis pipeline.
    Reads from canonical CSV → computes multiples → derives implied prices.

    Args:
        comps_csv_path: path to canonical comps_data.csv
        assumptions:    full assumptions dict from config/assumptions.json
        output_path:    optional path for comps_results.json
        verbose:        print detailed output

    Returns:
        dict matching original comps_results.json schema (backward compatible)
    """
    # ── Load from canonical CSV ────────────────────────────────────────────
    subject, peers = load_comps_from_canonical(comps_csv_path)

    # Use pre-computed subject data from assumptions for model consistency
    # (subject in CSV may have stale EV vs model-computed EV)
    if "dcf" in assumptions:
        current_price = (
            subject.get("ltm_price")
            or assumptions["dcf"]["market_price_valuation_date_usd"]
        )
        market_cap_b = subject.get("market_cap")
        shares_b = (
            market_cap_b / current_price
            if (market_cap_b is not None and current_price)
            else None
        )
        net_debt_b = subject.get("net_debt") or (
            assumptions["dcf"]["net_debt_bridge"]["net_debt_usdm"] / 1000
        )
        nvidia_rev = subject.get("ltm_revenue") or (
            assumptions["historical_actuals_fy2025"]["revenue_usdm"] / 1000
        )
        nvidia_ebitda = subject.get("ltm_ebitda") or (
            assumptions["historical_actuals_fy2025"]["ebitda_usdm"] / 1000
        )
        nvidia_eps = subject.get("ltm_eps")

        # Use shares from assumptions (more reliable)
        shares_b = assumptions["dcf"]["diluted_shares_outstanding_millions"] / 1000
    else:
        current_price = subject.get("ltm_price")
        shares_b = (
            subject.get("shares_millions") / 1000
            if subject.get("shares_millions") is not None
            else None
        )
        net_debt_b = (
            subject.get("net_debt_usdm") / 1000
            if subject.get("net_debt_usdm") is not None
            else subject.get("net_debt")
        )
        nvidia_rev = (
            subject.get("revenue_usdm") / 1000
            if subject.get("revenue_usdm") is not None
            else subject.get("ltm_revenue")
        )
        nvidia_ebitda = (
            subject.get("ebitda_usdm") / 1000
            if subject.get("ebitda_usdm") is not None
            else subject.get("ltm_ebitda")
        )
        nvidia_eps = subject.get("ltm_eps")

    # ── Compute peer multiples ─────────────────────────────────────────────
    peer_multiples = []
    for peer in peers:
        mults = compute_multiples(peer)
        peer_multiples.append(
            {
                "company": peer["company_name"],
                "ev_revenue": (
                    round(mults["ev_revenue"], 3) if mults["ev_revenue"] else None
                ),
                "ev_ebitda": (
                    round(mults["ev_ebitda"], 3) if mults["ev_ebitda"] else None
                ),
                "pe": round(mults["pe"], 2) if mults["pe"] else None,
            }
        )

    # ── Statistics ────────────────────────────────────────────────────────
    stat_labels = ["high", "p75", "mean", "median", "p25", "low"]

    stats = {
        "ev_revenue": compute_stats([p["ev_revenue"] for p in peer_multiples]),
        "ev_ebitda": compute_stats([p["ev_ebitda"] for p in peer_multiples]),
        "pe": compute_stats([p["pe"] for p in peer_multiples]),
    }

    # ── Implied prices ────────────────────────────────────────────────────
    def _r(v, dp=2):
        return round(v, dp) if v is not None else None

    implied = {}
    for stat in stat_labels:
        implied[stat] = {
            "ev_revenue": _r(
                implied_price_from_ev_multiple(
                    stats["ev_revenue"].get(stat), nvidia_rev, net_debt_b, shares_b
                )
            ),
            "ev_ebitda": _r(
                implied_price_from_ev_multiple(
                    stats["ev_ebitda"].get(stat), nvidia_ebitda, net_debt_b, shares_b
                )
            ),
            "pe": _r(implied_price_from_pe(stats["pe"].get(stat), nvidia_eps)),
        }

    med = implied["median"]

    if verbose:
        _print_comps_table(peer_multiples, stats, implied, current_price)

    # ── Build output ───────────────────────────────────────────────────────
    result = {
        "meta": {
            "step": "comps",
            "run_timestamp": datetime.now().isoformat(),
            "data_source": "canonical_csv",
            "comps_csv_path": comps_csv_path,
            "subject": "NVIDIA",
            "n_peers": len(peer_multiples),
            "peer_universe": [p["company"] for p in peer_multiples],
        },
        "subject_inputs": {
            "current_price": current_price,
            "eps": nvidia_eps,
            "shares_b": shares_b,
            "net_debt_b": net_debt_b,
            "revenue_b": nvidia_rev,
            "ebitda_b": nvidia_ebitda,
        },
        "peer_multiples": peer_multiples,
        "multiple_statistics": {
            metric: {
                stat: (
                    round(stats[metric][stat], 4)
                    if stats[metric][stat] is not None
                    else None
                )
                for stat in stat_labels + ["n"]
            }
            for metric in ["ev_revenue", "ev_ebitda", "pe"]
        },
        "implied_prices": implied,
        "summary": {
            "current_price": current_price,
            "median_implied_ev_revenue": med["ev_revenue"],
            "median_implied_ev_ebitda": med["ev_ebitda"],
            "median_implied_pe": med["pe"],
            "updown_vs_current_ev_revenue": _r(
                premium_discount(current_price, med["ev_revenue"]), 4
            ),
            "updown_vs_current_ev_ebitda": _r(
                premium_discount(current_price, med["ev_ebitda"]), 4
            ),
            "updown_vs_current_pe": _r(premium_discount(current_price, med["pe"]), 4),
        },
    }

    # ── Write JSON ─────────────────────────────────────────────────────────
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    return result


# ─── PRINT HELPER ─────────────────────────────────────────────────────────────


def _print_comps_table(peers: list, stats: dict, implied: dict, current_price: float):
    """Print comps table — mirrors original src/comps.py output."""
    print(f"\n{'─'*64}")
    print(f"  PEER TRADING MULTIPLES")
    print(f"{'─'*64}")
    print(f"\n  {'Company':<22} {'EV/Revenue':>11} {'EV/EBITDA':>11} {'P/E':>8}")
    print(f"  {'─'*20} {'─'*11} {'─'*11} {'─'*8}")
    for p in peers:
        ev_r = f"{p['ev_revenue']:.1f}x" if p["ev_revenue"] else "  n/m"
        ev_e = f"{p['ev_ebitda']:.1f}x" if p["ev_ebitda"] else "  n/m"
        pe = f"{p['pe']:.1f}x" if p["pe"] else "  n/m"
        print(f"  {p['company']:<22} {ev_r:>11} {ev_e:>11} {pe:>8}")

    print(f"\n  MEDIAN IMPLIED vs CURRENT ${current_price:.2f}")
    med = implied["median"]
    for key, label in [
        ("ev_revenue", "EV/Revenue"),
        ("ev_ebitda", "EV/EBITDA"),
        ("pe", "P/E"),
    ]:
        v = med[key]
        if v:
            ud = (v / current_price - 1) * 100
            sign = "+" if ud >= 0 else ""
            print(f"  {label:<12} → ${v:.2f}  ({sign}{ud:.1f}%)")
    print()


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Comps — canonical CSV mode")
    parser.add_argument("--comps-csv", default="comps/comps_data.csv")
    parser.add_argument(
        "--config",
        default=os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "assumptions.json"
        ),
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    with open(args.config) as f:
        assumptions = json.load(f)

    result = run_comps(
        comps_csv_path=args.comps_csv,
        assumptions=assumptions,
        output_path=args.output,
        verbose=args.verbose,
    )

    print(f"  Peers:           {result['meta']['n_peers']}")
    print(f"  EV/Rev median:   ${result['summary']['median_implied_ev_revenue']}")
    print(f"  EV/EBITDA median:${result['summary']['median_implied_ev_ebitda']}")
    print(f"  P/E median:      ${result['summary']['median_implied_pe']}")
    print(f"  Current price:   ${result['summary']['current_price']}")
    sys.exit(0)
