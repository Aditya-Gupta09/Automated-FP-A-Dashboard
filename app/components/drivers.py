"""
app/components/drivers.py  v3.0
Light theme · waterfall floating bars
"""

from __future__ import annotations
from typing import Any
import streamlit as st


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except:
        return None


def _dcf(result: dict, key: str) -> float | None:
    return _num(result.get("dcf_valuation", {}).get(key))


def build_driver_bridge(base_result: dict, selected_result: dict) -> list[dict]:
    shares = _dcf(base_result, "diluted_shares_millions") or 24300
    drivers = [
        ("PV of Terminal Value", "pv_terminal_value_usdm"),
        ("PV of Explicit FCFF", "sum_pv_fcf_usdm"),
        ("Net Debt Bridge", "net_debt_usdm"),
    ]
    rows = []
    for label, key in drivers:
        base_v = _dcf(base_result, key) or 0
        sel_v = _dcf(selected_result, key) or 0
        if key == "net_debt_usdm":
            base_contrib = -base_v / shares
            sel_contrib = -sel_v / shares
        else:
            base_contrib = base_v / shares
            sel_contrib = sel_v / shares
        impact = sel_contrib - base_contrib
        rows.append(
            {
                "driver": label,
                "base": base_contrib,
                "selected": sel_contrib,
                "impact": impact,
                "direction": "pos" if impact >= 0 else "neg",
            }
        )
    return rows


def render_driver_bridge(
    driver_rows: list[dict], selected_result: dict, base_result: dict, scenario: str
) -> None:
    if scenario == "base":
        st.markdown(
            '<div class="nv-section-title">DCF value decomposition · Base</div>'
            '<div class="nv-section-sub">Per-share contribution of each DCF component · absolute values</div>',
            unsafe_allow_html=True,
        )
        max_abs = max((abs(r["base"]) for r in driver_rows), default=1)
        html = '<div class="nv-panel"><div class="nv-bar-list">'
        for row in driver_rows:
            pct = min(abs(row["base"]) / max_abs * 95, 95) if max_abs else 2
            val_str = f"${row['base']:,.2f}"
            html += (
                f'<div class="nv-bar-row">'
                f'<span class="nv-bar-label">{row["driver"]}</span>'
                f'<div class="nv-bar-track">'
                f'<div class="nv-bar-fill-pos" style="width:{max(pct,2):.0f}%">'
                f'<span class="nv-bar-val">{val_str}</span>'
                f"</div></div></div>"
            )
        total = _dcf(base_result, "implied_share_price_usd") or 0
        html += (
            f'<div style="border-top:1px solid #e2e8f0;margin-top:8px;padding-top:8px;'
            f'display:flex;justify-content:space-between;font-size:11px">'
            f'<span style="color:#64748b;font-weight:700">= Implied share price</span>'
            f'<span style="color:#0891b2;font-weight:700;font-family:monospace">${total:,.2f}</span>'
            f"</div>"
        )
        html += "</div></div>"
        st.markdown(html, unsafe_allow_html=True)
        return

    st.markdown(
        f'<div class="nv-section-title">Driver bridge · {scenario.title()}</div>'
        '<div class="nv-section-sub">Share-price Δ vs base · from pipeline dcf_valuation</div>',
        unsafe_allow_html=True,
    )
    max_abs = max((abs(r["impact"]) for r in driver_rows), default=1)
    html = '<div class="nv-panel"><div class="nv-bar-list">'
    for row in driver_rows:
        impact = row["impact"]
        pct = min(abs(impact) / max_abs * 95, 95) if max_abs else 2
        cls = "nv-bar-fill-pos" if impact >= 0 else "nv-bar-fill-neg"
        sign = "+" if impact >= 0 else ""
        val_str = f"{sign}${impact:,.2f}"
        html += (
            f'<div class="nv-bar-row">'
            f'<span class="nv-bar-label">{row["driver"]}</span>'
            f'<div class="nv-bar-track">'
            f'<div class="{cls}" style="width:{max(pct,2):.0f}%">'
            f'<span class="nv-bar-val">{val_str}</span>'
            f"</div></div></div>"
        )
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
