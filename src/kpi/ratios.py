"""
src/kpi/ratios.py
=================
Traffic-light signal engine for the NVIDIA DCF Valuation project.

Design (Task 4):
  - One signal function per KPI — returns "green", "yellow", or "red"
  - Thresholds calibrated to NVIDIA's actual FY2020–2025 historical ranges
  - A single evaluate_all() function returns the full signal dict
  - All functions handle None input gracefully — returns "neutral" (no data)
  - Pure functions — no side effects, no I/O

Threshold Calibration — Data-Driven (Tasks 3 & 4)
---------------------------------------------------
Every threshold below is anchored to NVIDIA's observed historical range
and cross-validated against standard FP&A benchmarks for semiconductor/
fabless companies.

  KPI             NVDA Min   NVDA Max   NVDA Avg   Green        Yellow        Red
  gross_margin    56.9%      75.0%      65.6%      > 60%        40–60%        < 40%
  ebitda_margin   21.4%      63.8%      41.1%      > 40%        20–40%        < 20%
  fcf_margin      14.1%      46.6%      33.8%      > 25%        10–25%        < 10%
  ar_days         51.8d      64.5d      58.5d      < 45d        45–70d        > 70d
  ap_days         37.5d      70.6d      60.6d      > 60d        30–60d        < 30d
  current_ratio   3.5×       6.7×       4.6×       > 2.0×       1.0–2.0×      < 1.0×
  revenue_growth  0.2%       125.9%     —          > 15%        0–15%         < 0%

Threshold philosophy (Task 3 — cross-validation with FP&A standards):
  - gross_margin  : 60% green is appropriate for fabless/software-heavy mix;
                    standard hardware cos use 40%, raised for NVDA's profile
  - ebitda_margin : 40% green reflects NVDA's mature AI-era efficiency;
                    20% floor aligns with semiconductor sector median
  - fcf_margin    : 25% green = strong cash conversion; 10% = acceptable;
                    below 10% = capital-intensive or working-capital-pressured
  - ar_days       : lower = faster collection = better; 45d is semiconductor norm
  - ap_days       : higher = longer supplier float = better; 60d reflects NVDA's
                    strong negotiating position at scale
  - current_ratio : >2× is universally healthy; NVDA runs 3.5–6.7× historically;
                    threshold kept at standard 2× / 1× to avoid false greens
  - revenue_growth: 15% green = sustained above-market growth; 0% = floor;
                    negative = structural concern
"""

from __future__ import annotations

# Sentinel for missing data — distinct from red
_NO_DATA = "neutral"


# ── Individual signal functions ────────────────────────────────────────────────


def gross_margin_signal(value: float | None) -> str:
    """
    Traffic-light signal for Gross Margin.

    Thresholds (NVDA-calibrated):
      Green  > 60%   — strong pricing power, high-value product mix
      Yellow 40–60%  — acceptable, but margin compression risk
      Red    < 40%   — commodity-like pricing or COGS spike

    NVIDIA historical range: 56.9% (FY2023 trough) – 75.0% (FY2025 peak)
    FY2023 dipped to 56.9% due to inventory write-downs — still yellow.

    Args:
        value: Gross margin as a decimal ratio (e.g. 0.75 for 75%)

    Returns:
        "green" | "yellow" | "red" | "neutral"
    """
    if value is None:
        return _NO_DATA
    if value > 0.60:
        return "green"
    if value >= 0.40:
        return "yellow"
    return "red"


def ebitda_margin_signal(value: float | None) -> str:
    """
    Traffic-light signal for EBITDA Margin.

    Thresholds (NVDA-calibrated):
      Green  > 40%   — exceptional operational leverage
      Yellow 20–40%  — solid, within semiconductor sector norms
      Red    < 20%   — operational pressure or heavy reinvestment phase

    NVIDIA historical range: 21.4% (FY2023) – 63.8% (FY2025)
    FY2023 at 21.4% was yellow — driven by flat revenue + cost ramp.

    Args:
        value: EBITDA margin as a decimal ratio (e.g. 0.638 for 63.8%)

    Returns:
        "green" | "yellow" | "red" | "neutral"
    """
    if value is None:
        return _NO_DATA
    if value > 0.40:
        return "green"
    if value >= 0.20:
        return "yellow"
    return "red"


def fcf_margin_signal(value: float | None) -> str:
    """
    Traffic-light signal for FCF Margin.

    Thresholds (NVDA-calibrated):
      Green  > 25%   — strong free cash generation; funds buybacks + R&D
      Yellow 10–25%  — adequate; investable but limited capital flexibility
      Red    < 10%   — capital-intensive or working-capital-pressured

    NVIDIA historical range: 14.1% (FY2023) – 46.6% (FY2025)
    FY2023 was yellow at 14.1% — NWC build + inventory spike absorbed cash.

    Args:
        value: FCF margin as a decimal ratio (e.g. 0.466 for 46.6%)

    Returns:
        "green" | "yellow" | "red" | "neutral"
    """
    if value is None:
        return _NO_DATA
    if value > 0.25:
        return "green"
    if value >= 0.10:
        return "yellow"
    return "red"


def revenue_growth_signal(value: float | None) -> str:
    """
    Traffic-light signal for YoY Revenue Growth.

    Thresholds (NVDA-calibrated):
      Green  > 15%   — above-market growth; structural demand tailwind
      Yellow 0–15%   — positive but slowing; monitor for deceleration
      Red    < 0%    — contraction; requires investigation

    NVIDIA historical range: 0.2% (FY2023) – 125.9% (FY2024 AI boom)
    FY2023 near-zero growth was yellow — end of crypto/gaming cycle.

    Args:
        value: Revenue growth as a decimal ratio (e.g. 1.142 for +114.2%)

    Returns:
        "green" | "yellow" | "red" | "neutral"
    """
    if value is None:
        return _NO_DATA
    if value > 0.15:
        return "green"
    if value >= 0.0:
        return "yellow"
    return "red"


def ar_days_signal(value: float | None) -> str:
    """
    Traffic-light signal for AR Days (DSO).

    Lower is better — faster collection of receivables.

    Thresholds (NVDA-calibrated):
      Green  < 45d   — efficient collection; strong customer terms
      Yellow 45–70d  — normal semiconductor range; monitor trend
      Red    > 70d   — collection risk or deteriorating customer terms

    NVIDIA historical range: 51.8d (FY2023) – 64.5d (FY2025)
    NVDA consistently runs in the yellow band — driven by hyperscaler
    payment terms. FY2025 AR Days rose with Data Center AR concentration.

    Args:
        value: AR Days in calendar days

    Returns:
        "green" | "yellow" | "red" | "neutral"
    """
    if value is None:
        return _NO_DATA
    if value < 45:
        return "green"
    if value <= 70:
        return "yellow"
    return "red"


def ap_days_signal(value: float | None) -> str:
    """
    Traffic-light signal for AP Days (DPO).

    Higher is better — longer supplier float conserves cash.

    Thresholds (NVDA-calibrated):
      Green  > 60d   — strong supplier negotiating position; good float
      Yellow 30–60d  — acceptable; standard fabless range
      Red    < 30d   — paying suppliers too quickly; may signal weakness

    NVIDIA historical range: 37.5d (FY2023) – 70.6d (FY2025)
    FY2023 dropped to 37.5d — yellow — NVDA paid suppliers fast to
    secure supply ahead of the AI demand surge.

    Args:
        value: AP Days in calendar days

    Returns:
        "green" | "yellow" | "red" | "neutral"
    """
    if value is None:
        return _NO_DATA
    if value > 60:
        return "green"
    if value >= 30:
        return "yellow"
    return "red"


def current_ratio_signal(value: float | None) -> str:
    """
    Traffic-light signal for Current Ratio.

    Thresholds (standard liquidity benchmarks, confirmed vs NVDA history):
      Green  > 2.0×  — strong liquidity; ample coverage of short-term obligations
      Yellow 1.0–2.0× — adequate; monitor for deterioration
      Red    < 1.0×  — current liabilities exceed current assets; liquidity risk

    NVIDIA historical range: 3.5× – 6.7× (annual); 4.25× – 8.09× (quarterly)
    NVDA consistently runs deep green. Thresholds kept at universal standards
    (2× / 1×) rather than NVDA-specific levels to remain meaningful if the
    model is applied to other companies.

    Args:
        value: Current ratio (e.g. 4.44)

    Returns:
        "green" | "yellow" | "red" | "neutral"
    """
    if value is None:
        return _NO_DATA
    if value > 2.0:
        return "green"
    if value >= 1.0:
        return "yellow"
    return "red"


# ── Composite evaluator ────────────────────────────────────────────────────────


def evaluate_all(kpis: dict) -> dict:
    """
    Convert a full KPI dict into a traffic-light signal dict.

    Accepts the dict produced by kpis.calculate_kpis() and returns
    a parallel dict with one signal string per KPI.

    Args:
        kpis: Dict with keys:
                gross_margin, ebitda_margin, fcf, fcf_margin,
                revenue_growth, ar_days, ap_days, current_ratio
              Values are float | None.

    Returns:
        Dict with the same keys, values replaced by signal strings:
            "green" | "yellow" | "red" | "neutral"

        Note: "fcf" has no signal (it is an absolute dollar value,
              not a ratio) — its signal is derived from "fcf_margin".

    Example:
        >>> from src.kpi.kpis import calculate_kpis
        >>> from src.kpi.ratios import evaluate_all
        >>> kpis = calculate_kpis(revenue=130497, cogs=32639, ...)
        >>> signals = evaluate_all(kpis)
        >>> signals['gross_margin']   # "green"
        >>> signals['ar_days']        # "yellow"
    """
    return {
        "gross_margin": gross_margin_signal(kpis.get("gross_margin")),
        "ebitda_margin": ebitda_margin_signal(kpis.get("ebitda_margin")),
        "fcf": "neutral",  # absolute value — no threshold signal
        "fcf_margin": fcf_margin_signal(kpis.get("fcf_margin")),
        "revenue_growth": revenue_growth_signal(kpis.get("revenue_growth")),
        "ar_days": ar_days_signal(kpis.get("ar_days")),
        "ap_days": ap_days_signal(kpis.get("ap_days")),
        "current_ratio": current_ratio_signal(kpis.get("current_ratio")),
    }


def signal_to_color(signal: str) -> str:
    """
    Map a signal string to a hex color for UI rendering.

    Designed to work with both Streamlit and standard HTML/CSS.

    Returns:
        str — hex color code

    Color palette (accessibility-safe):
        green  →  #22C55E   (Tailwind green-500)
        yellow →  #F59E0B   (yellow signal)
        red    →  #EF4444   (Tailwind red-500)
        neutral → #9CA3AF   (Tailwind gray-400, for missing data)
    """
    _map = {
        "green": "#22C55E",
        "yellow": "#F59E0B",
        "red": "#EF4444",
        "neutral": "#9CA3AF",
    }
    return _map.get(signal, "#9CA3AF")


def signal_to_emoji(signal: str) -> str:
    """
    Map a signal string to an emoji indicator for text-based display.

    Useful for terminal output, notebooks, or lightweight UI contexts
    where CSS styling is not available.

    Returns:
        str — single emoji character
    """
    _map = {
        "green": "🟢",
        "yellow": "🟡",
        "red": "🔴",
        "neutral": "⚪",
    }
    return _map.get(signal, "⚪")
