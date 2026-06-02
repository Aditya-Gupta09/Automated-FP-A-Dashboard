"""
app/components/kpi_tile.py  v3.0
Light theme · big % KPI tiles · gradient headers
"""

from __future__ import annotations
from typing import Any
import streamlit as st

_SCENARIOS = ("base", "upside", "downside")
_META = {
    "base": {
        "label": "Base case",
        "accent": "linear-gradient(90deg,#3b82f6,#60a5fa)",
        "price_color": "#3b82f6",
        "delta_color": "#475569",
        "delta_prefix": "▸",
        "delta_suffix": "Reference scenario",
        "meta": "WACC 12.91% · g 3.675%",
        "spark_stroke": "#3b82f6",
        "spark_points": "0,20 20,17 40,14 60,11 80,8 100,5",
        "active_class": "nv-kcard-active-base",
        "inactive_border": "#3b82f615",
    },
    "upside": {
        "label": "Upside · bull case",
        "accent": "linear-gradient(90deg,#10b981,#34d399)",
        "price_color": "#10b981",
        "delta_color": "#10b981",
        "delta_prefix": "▲",
        "delta_suffix": "vs base",
        "meta": "WACC 11.91% · g 4.50% · DC +95%",
        "spark_stroke": "#10b981",
        "spark_points": "0,22 20,16 40,11 60,7 80,3 100,1",
        "active_class": "nv-kcard-active-up",
        "inactive_border": "#10b98115",
    },
    "downside": {
        "label": "Downside · bear case",
        "accent": "linear-gradient(90deg,#ef4444,#f87171)",
        "price_color": "#ef4444",
        "delta_color": "#ef4444",
        "delta_prefix": "▼",
        "delta_suffix": "vs base",
        "meta": "WACC 13.91% · g 3.00% · DC +50%",
        "spark_stroke": "#ef4444",
        "spark_points": "0,2 20,6 40,11 60,15 80,19 100,22",
        "active_class": "nv-kcard-active-dn",
        "inactive_border": "#ef444415",
    },
}


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except:
        return None


def _price(result: dict) -> float | None:
    return _num(result.get("dcf_valuation", {}).get("implied_share_price_usd"))


def _fmt_price(v: float | None) -> str:
    return "N/A" if v is None else f"${v:,.2f}"


def _fmt_delta(v: float | None, prefix: str, suffix: str) -> str:
    if suffix == "Reference scenario":
        return f"{prefix} {suffix}"
    if v is None:
        return "N/A"
    sign = "+" if v >= 0 else ""
    return f"{prefix} {sign}${v:,.2f} {suffix}"


def render_kpi_row(results: dict, active_scenario: str = "base") -> None:
    cols = st.columns(3, gap="medium")
    base_price = _price(results.get("base", {}))

    for col, scenario in zip(cols, _SCENARIOS):
        meta = _META[scenario]
        result = results.get(scenario, {})
        price = _price(result)
        delta = (
            None
            if (base_price is None or price is None or scenario == "base")
            else price - base_price
        )
        delta_str = _fmt_delta(delta, meta["delta_prefix"], meta["delta_suffix"])

        is_active = scenario == active_scenario
        border_style = (
            "border-color:transparent"
            if is_active
            else f"border-color:{meta['inactive_border']}"
        )
        extra_class = meta["active_class"] if is_active else ""

        with col:
            st.markdown(
                f'<div class="nv-kcard {extra_class}" style="{border_style}">'
                f'<div class="nv-kcard-accent" style="background:{meta["accent"]}"></div>'
                f'<div class="nv-kcard-label">{meta["label"]}'
                + (
                    ' <span style="font-size:9px;color:#0891b2;font-weight:700">● ACTIVE</span>'
                    if is_active
                    else ""
                )
                + f"</div>"
                f'<div class="nv-kcard-price" style="color:{meta["price_color"]}">{_fmt_price(price)}</div>'
                f'<div class="nv-kcard-delta" style="color:{meta["delta_color"]}">{delta_str}</div>'
                f'<div class="nv-kcard-meta">{meta["meta"]}</div>'
                f'<svg class="nv-sparkline" viewBox="0 0 100 24" preserveAspectRatio="none">'
                f'<polyline points="{meta["spark_points"]}" fill="none" '
                f'stroke="{meta["spark_stroke"]}" stroke-width="1.5" stroke-linecap="round"/></svg>'
                f"</div>",
                unsafe_allow_html=True,
            )
