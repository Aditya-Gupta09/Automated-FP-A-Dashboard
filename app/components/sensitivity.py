"""
app/components/sensitivity.py  v3.0
Light theme · scenario-aware base cell
"""

from __future__ import annotations
from typing import Any
import streamlit as st

_EXCEL_GRID = {
    0.109: {
        0.02: 115.30,
        0.025: 120.90,
        0.03: 127.22,
        0.035: 134.38,
        0.04: 142.59,
        0.045: 152.08,
        0.05: 163.18,
        0.055: 176.33,
        0.06: 192.17,
    },
    0.114: {
        0.02: 108.86,
        0.025: 113.78,
        0.03: 119.29,
        0.035: 125.49,
        0.04: 132.53,
        0.045: 140.59,
        0.05: 149.91,
        0.055: 160.81,
        0.06: 173.73,
    },
    0.119: {
        0.02: 103.13,
        0.025: 107.47,
        0.03: 112.31,
        0.035: 117.71,
        0.04: 123.81,
        0.045: 130.72,
        0.05: 138.64,
        0.055: 147.79,
        0.06: 158.50,
    },
    0.124: {
        0.02: 97.99,
        0.025: 101.85,
        0.03: 106.11,
        0.035: 110.86,
        0.04: 116.17,
        0.045: 122.16,
        0.05: 128.95,
        0.055: 136.73,
        0.06: 145.72,
    },
    0.129: {
        0.02: 93.36,
        0.025: 96.80,
        0.03: 100.59,
        0.035: 104.78,
        0.04: 109.44,
        0.045: 114.66,
        0.05: 120.54,
        0.055: 127.22,
        0.06: 134.86,
    },
    0.134: {
        0.02: 89.17,
        0.025: 92.25,
        0.03: 95.64,
        0.035: 99.36,
        0.04: 103.48,
        0.045: 108.06,
        0.05: 113.19,
        0.055: 118.96,
        0.06: 125.52,
    },
    0.139: {
        0.02: 85.37,
        0.025: 88.14,
        0.03: 91.17,
        0.035: 94.50,
        0.04: 98.15,
        0.045: 102.20,
        0.05: 106.70,
        0.055: 111.74,
        0.06: 117.42,
    },
    0.144: {
        0.02: 81.90,
        0.025: 84.41,
        0.03: 87.14,
        0.035: 90.12,
        0.04: 93.38,
        0.045: 96.98,
        0.05: 100.95,
        0.055: 105.38,
        0.06: 110.33,
    },
    0.149: {
        0.02: 78.74,
        0.025: 81.01,
        0.03: 83.48,
        0.035: 86.16,
        0.04: 89.08,
        0.045: 92.29,
        0.05: 95.82,
        0.055: 99.73,
        0.06: 104.08,
    },
}

_WACC_LABELS = [
    "10.9%",
    "11.4%",
    "11.9%",
    "12.4%",
    "12.9%",
    "13.4%",
    "13.9%",
    "14.4%",
    "14.9%",
]
_G_LABELS = ["2.0%", "2.5%", "3.0%", "3.5%", "4.0%", "4.5%", "5.0%", "5.5%", "6.0%"]
_WACC_KEYS = [0.109, 0.114, 0.119, 0.124, 0.129, 0.134, 0.139, 0.144, 0.149]
_G_KEYS = [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06]

_SCENARIO_ACTIVE_CELL = {
    "base": (4, 4),
    "upside": (1, 5),
    "downside": (6, 2),
}

_SCENARIO_IMPLIED = {
    "base": 109.16,
    "upside": 229.53,
    "downside": 32.76,
}


def _cell_style(price: float, is_active_cell: bool, scenario: str) -> str:
    if is_active_cell:
        color_map = {"base": "#0891b2", "upside": "#10b981", "downside": "#ef4444"}
        c = color_map.get(scenario, "#0891b2")
        return f"background:{c}15;color:{c};border:1px solid {c}40;font-weight:700;"

    base_p = _SCENARIO_IMPLIED.get(scenario, 109.16)
    if scenario == "downside":
        if price >= 80:
            return "background:#10b98120;color:#10b981;"
        if price >= 50:
            return "background:#10b98110;color:#34d399;"
        if price >= 32:
            return "background:#f1f5f940;color:#64748b;"
        if price >= 20:
            return "background:#ef444420;color:#f87171;"
        alpha = min(int((20 - price) / 20 * 150) + 50, 200)
        return f"background:#ef4444{alpha:02x};color:#f87171;"
    elif scenario == "upside":
        if price >= 300:
            return "background:#10b981dd;color:#fff;"
        if price >= 200:
            return "background:#10b98180;color:#dcfce7;"
        if price >= 150:
            return "background:#10b98150;color:#34d399;"
        if price >= 109:
            return "background:#f1f5f940;color:#64748b;"
        if price >= 85:
            return "background:#ef444420;color:#f87171;"
        return "background:#ef444450;color:#f87171;"
    else:  # base
        if price >= 150:
            alpha = min(int((price - 150) / 80 * 150) + 40, 200)
            return f"background:#10b981{alpha:02x};color:#dcfce7;"
        if price >= 120:
            alpha = min(int((price - 120) / 30 * 80) + 30, 120)
            return f"background:#10b981{alpha:02x};color:#34d399;"
        if price >= 100:
            return "background:#f1f5f940;color:#64748b;"
        if price >= 85:
            alpha = min(int((100 - price) / 15 * 80) + 30, 120)
            return f"background:#ef4444{alpha:02x};color:#f87171;"
        alpha = min(int((85 - price) / 20 * 150) + 50, 200)
        return f"background:#ef4444{alpha:02x};color:#f87171;"


def _get_grid(result: dict) -> dict:
    sens = result.get("dcf_valuation", {}).get("sensitivity")
    if isinstance(sens, dict) and "implied_price" in sens:
        return sens["implied_price"]
    return _EXCEL_GRID


def render_sensitivity_matrix(result: dict, scenario: str = "base") -> None:
    active_wi, active_gi = _SCENARIO_ACTIVE_CELL.get(scenario, (4, 4))
    scenario_label = {"base": "Base", "upside": "Upside", "downside": "Downside"}.get(
        scenario, "Base"
    )
    active_wacc = _WACC_LABELS[active_wi]
    active_g = _G_LABELS[active_gi]

    st.markdown(
        '<div class="nv-section-title">WACC × terminal growth sensitivity matrix</div>'
        f'<div class="nv-section-sub">'
        f"Implied share price — 9×9 grid · 06_Sensitivity sheet · "
        f'<span style="color:#0891b2">■</span> {scenario_label} cell '
        f"(WACC {active_wacc}, g {active_g}) · "
        f'<span style="color:#10b981">■</span> Upside territory · '
        f'<span style="color:#ef4444">■</span> Downside territory'
        f"</div>",
        unsafe_allow_html=True,
    )

    grid = _get_grid(result)
    header_cells = (
        '<div style="font-size:9px;color:#475569;display:flex;align-items:flex-end;padding-bottom:2px;font-weight:600">WACC ↓</div>'
        + "".join(
            f'<div style="text-align:center;font-size:9px;color:#64748b;padding:2px 0;font-weight:600">{g}</div>'
            for g in _G_LABELS
        )
    )

    rows_html = ""
    for wi, (wk, wl) in enumerate(zip(_WACC_KEYS, _WACC_LABELS)):
        is_active_row = wi == active_wi
        lc = "#0891b2" if is_active_row else "#64748b"
        lw = "700" if is_active_row else "500"
        if scenario == "upside":
            lc = "#10b981" if is_active_row else "#64748b"
        if scenario == "downside":
            lc = "#ef4444" if is_active_row else "#64748b"
        rows_html += (
            f'<div style="font-size:9px;color:{lc};font-weight:{lw};'
            f'display:flex;align-items:center;justify-content:flex-end;padding-right:4px">{wl}</div>'
        )
        g_row = grid.get(wk, {})
        for gi, gk in enumerate(_G_KEYS):
            is_active_cell = wi == active_wi and gi == active_gi
            price = g_row.get(gk) if isinstance(g_row, dict) else None
            if price is None:
                price = _EXCEL_GRID.get(wk, {}).get(gk, 0)
            price = float(price) if price else 0
            style = _cell_style(price, is_active_cell, scenario)
            rows_html += f'<div class="nv-sg-cell" style="{style}">${price:.0f}</div>'

    st.markdown(
        f'<div class="nv-panel">'
        f'<div style="font-size:9px;color:#475569;margin-bottom:4px;padding-left:60px;font-weight:600">Terminal growth rate →</div>'
        f'<div class="nv-sens-grid">{header_cells}{rows_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
