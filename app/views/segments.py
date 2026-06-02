"""
app/views/segments.py  v3.0
Light theme · combo stacked+line · donut center labels
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

_SEGMENTS = {
    "data_center": {"label": "Data Center", "color": "#3b82f6"},
    "gaming": {"label": "Gaming", "color": "#8b5cf6"},
    "professional_viz": {"label": "Prof. Visualization", "color": "#10b981"},
    "automotive": {"label": "Automotive", "color": "#f59e0b"},
    "oem_and_other": {"label": "OEM & Other", "color": "#6b7280"},
}
_FY2025_BASE = {
    "data_center": 115186,
    "gaming": 11350,
    "professional_viz": 1878,
    "automotive": 1694,
    "oem_and_other": 389,
    "total": 130497,
}
_GEO_FY2025 = {
    "United States": {"rev": 61257, "pct": 0.469, "color": "#3b82f6"},
    "Singapore": {"rev": 23684, "pct": 0.182, "color": "#10b981"},
    "Taiwan": {"rev": 20573, "pct": 0.158, "color": "#8b5cf6"},
    "China + HK": {"rev": 17108, "pct": 0.131, "color": "#f59e0b"},
    "Other": {"rev": 7875, "pct": 0.060, "color": "#6b7280"},
}
_GROWTH_FY26 = {
    "data_center": {"base": 0.69, "upside": 0.95, "downside": 0.50},
    "gaming": {"base": 0.05, "upside": 0.15, "downside": -0.05},
    "professional_viz": {"base": 0.06, "upside": 0.15, "downside": -0.02},
    "automotive": {"base": 0.45, "upside": 0.65, "downside": 0.10},
    "oem_and_other": {"base": 0.02, "upside": 0.10, "downside": -0.05},
}
_SCENARIO_COLOR = {"base": "#3b82f6", "upside": "#10b981", "downside": "#ef4444"}
_L = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(color="#475569", size=11),
    margin=dict(l=8, r=8, t=28, b=8),
)


def _project(scenario):
    gm = {
        "data_center": {
            2026: _GROWTH_FY26["data_center"][scenario],
            2027: (
                0.42 if scenario == "base" else (0.55 if scenario == "upside" else 0.12)
            ),
            2028: (
                0.27 if scenario == "base" else (0.35 if scenario == "upside" else 0.04)
            ),
            2029: (
                0.16
                if scenario == "base"
                else (0.22 if scenario == "upside" else -0.05)
            ),
            2030: (
                0.22 if scenario == "base" else (0.42 if scenario == "upside" else 0.02)
            ),
        },
        "gaming": {
            2026: _GROWTH_FY26["gaming"][scenario],
            2027: (
                0.03
                if scenario == "base"
                else (0.10 if scenario == "upside" else -0.05)
            ),
            2028: 0.02,
            2029: 0.02,
            2030: 0.03,
        },
        "professional_viz": {
            2026: _GROWTH_FY26["professional_viz"][scenario],
            2027: 0.07,
            2028: 0.05,
            2029: 0.04,
            2030: 0.05,
        },
        "automotive": {
            2026: _GROWTH_FY26["automotive"][scenario],
            2027: (
                0.50 if scenario == "base" else (1.00 if scenario == "upside" else 0.05)
            ),
            2028: 0.35,
            2029: 0.26,
            2030: 0.35,
        },
        "oem_and_other": {
            2026: _GROWTH_FY26["oem_and_other"][scenario],
            2027: 0.03,
            2028: 0.02,
            2029: 0.02,
            2030: 0.03,
        },
    }
    out = {}
    for seg, bv in _FY2025_BASE.items():
        if seg == "total":
            continue
        out[seg] = {}
        prev = bv
        for yr in [2026, 2027, 2028, 2029, 2030]:
            v = prev * (1 + gm.get(seg, {}).get(yr, 0.05))
            out[seg][yr] = v
            prev = v
    return out


def render_segments_tab(results, scenario):
    total = _FY2025_BASE["total"]

    # ── 1. FY2025 segment bars ──────────────────────────────────────────────
    st.markdown(
        '<div class="nv-section-title">Revenue by segment · FY2025 actual</div>'
        '<div class="nv-section-sub">Data Center now 88.3% of total revenue · from 01_Historical_IS</div>',
        unsafe_allow_html=True,
    )

    html = '<div class="nv-panel">'
    for sk, m in _SEGMENTS.items():
        rev = _FY2025_BASE.get(sk, 0)
        pct = rev / total * 100
        bar_w = max(pct, 0.4)
        if pct < 5:
            inner_label = ""
            outer_label = f'<span style="font-size:9px;font-weight:700;color:{m["color"]};margin-left:4px">{pct:.1f}%</span>'
        else:
            inner_label = f'<span class="nv-seg-pct">{pct:.1f}%</span>'
            outer_label = ""
        html += (
            f'<div class="nv-seg-row">'
            f'<span class="nv-seg-label">{m["label"]}</span>'
            f'<div class="nv-seg-track">'
            f'<div class="nv-seg-fill" style="width:{bar_w:.1f}%;'
            f'background:linear-gradient(90deg,{m["color"]}80,{m["color"]})">'
            f"{inner_label}</div></div>"
            f"{outer_label}"
            f'<span class="nv-seg-val">${rev:,.0f}M</span></div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 2. Data Center bar + growth table ───────────────────────────────────
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(
            '<div class="nv-section-title">Data Center · the AI inflection</div>'
            '<div class="nv-section-sub">FY2023–FY2026F absolute revenue ($M)</div>',
            unsafe_allow_html=True,
        )
        dc_proj = int(115186 * (1 + _GROWTH_FY26["data_center"][scenario]))
        dc_labels = ["FY2023A", "FY2024A", "FY2025A", f"FY2026F · {scenario.title()}"]
        dc_vals = [15005, 47467, 115186, dc_proj]
        dc_colors = [
            "rgba(59,130,246,0.25)",
            "rgba(59,130,246,0.50)",
            "rgba(59,130,246,0.69)",
            _SCENARIO_COLOR.get(scenario, "#3b82f6"),
        ]
        fig = go.Figure(
            go.Bar(
                x=dc_labels,
                y=dc_vals,
                marker_color=dc_colors,
                text=[f"${v/1000:.0f}K" for v in dc_vals],
                textposition="outside",
                textfont=dict(color="#3b82f6", size=10),
            )
        )
        fig.update_layout(
            **_L,
            height=240,
            showlegend=False,
            bargap=0.35,
            yaxis=dict(
                title=None, gridcolor="#e2e8f0", showticklabels=False, zeroline=False
            ),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown(
            '<div class="nv-section-title">FY2026F growth rates · all scenarios</div>'
            '<div class="nv-section-sub">From 04a_Projection_IS · scenarios.json</div>',
            unsafe_allow_html=True,
        )
        tbl = (
            '<div class="nv-panel"><table style="width:100%;font-size:11px;border-collapse:collapse">'
            '<tr style="border-bottom:1px solid #e2e8f0">'
            '<td style="padding:4px 0;color:#475569;font-weight:600">Segment</td>'
            '<td style="text-align:right;color:#3b82f6;font-weight:600">Base</td>'
            '<td style="text-align:right;color:#10b981;font-weight:600">Upside</td>'
            '<td style="text-align:right;color:#ef4444;font-weight:600">Bear</td></tr>'
        )
        for sk, m in _SEGMENTS.items():
            g = _GROWTH_FY26.get(sk, {})
            tbl += (
                f'<tr style="border-bottom:1px solid #e2e8f0">'
                f'<td style="padding:4px 0;color:#475569;font-weight:500">{m["label"]}</td>'
                f'<td style="text-align:right;color:#3b82f6;font-family:monospace;font-weight:600">+{g["base"]*100:.0f}%</td>'
                f'<td style="text-align:right;color:#10b981;font-family:monospace;font-weight:600">+{g["upside"]*100:.0f}%</td>'
                f'<td style="text-align:right;color:#ef4444;font-family:monospace;font-weight:600">{g["downside"]*100:+.0f}%</td>'
                f"</tr>"
            )
        tbl += "</table></div>"
        st.markdown(tbl, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3. Combo chart: Stacked bars + line overlay ────────────────────────
    st.markdown(
        f'<div class="nv-section-title">Segment revenue FY2023–2030F · {scenario.title()}</div>'
        '<div class="nv-section-sub">Stacked bars + total revenue trend line · forecast from assumptions.json</div>',
        unsafe_allow_html=True,
    )

    hist = {
        "data_center": {2023: 15005, 2024: 47467, 2025: 115186},
        "gaming": {2023: 9068, 2024: 10448, 2025: 11350},
        "professional_viz": {2023: 1544, 2024: 1591, 2025: 1878},
        "automotive": {2023: 903, 2024: 1090, 2025: 1694},
        "oem_and_other": {2023: 454, 2024: 326, 2025: 389},
    }
    projected = _project(scenario)
    hy = [2023, 2024, 2025]
    py = [2026, 2027, 2028, 2029, 2030]
    xl = [str(y) for y in hy] + [f"{y}F" for y in py]

    fig2 = go.Figure()

    # Add stacked bars
    for sk, m in _SEGMENTS.items():
        yvals = [hist.get(sk, {}).get(y, 0) for y in hy] + [
            projected.get(sk, {}).get(y, 0) for y in py
        ]
        fig2.add_trace(
            go.Bar(
                name=m["label"],
                x=xl,
                y=yvals,
                marker_color=m["color"],
                hovertemplate=f"<b>{m['label']}</b><br>%{{x}}: $%{{y:,.0f}}M<extra></extra>",
            )
        )

    # Add total revenue line overlay
    total_vals = []
    for y in hy + py:
        seg_sum = sum(
            [
                (
                    hist.get(sk, {}).get(y, 0)
                    if y in hy
                    else projected.get(sk, {}).get(y, 0)
                )
                for sk in hist.keys()
                if sk != "total"
            ]
        )
        total_vals.append(seg_sum)

    fig2.add_trace(
        go.Scatter(
            x=xl,
            y=total_vals,
            name="Total Revenue",
            mode="lines+markers",
            line=dict(color=_SCENARIO_COLOR[scenario], width=3, dash="solid"),
            marker=dict(size=6),
            yaxis="y2",
            hovertemplate="<b>Total Revenue</b><br>%{x}: $%{y:,.0f}M<extra></extra>",
        )
    )

    fig2.add_vline(
        x=2.5,
        line_dash="dot",
        line_color="#9ca3af",
        line_width=1,
        annotation_text="Forecast →",
        annotation_font_color="#64748b",
        annotation_font_size=9,
    )

    fig2.update_layout(
        **_L,
        barmode="stack",
        height=300,
        yaxis=dict(title="Segment Revenue ($M)", gridcolor="#e2e8f0", zeroline=False),
        yaxis2=dict(
            title="Total Revenue ($M)",
            overlaying="y",
            side="right",
            gridcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.2, bgcolor="rgba(0,0,0,0)"),
    )

    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<hr style="margin:4px 0 12px;border-color:#e2e8f0">', unsafe_allow_html=True
    )

    # ── 4. Geographic revenue ────────────────────────────────────────────────
    st.markdown(
        '<div class="nv-section-title">Geographic revenue · FY2025 actual</div>'
        '<div class="nv-section-sub">From 10_GrowthRates sheet</div>',
        unsafe_allow_html=True,
    )
    gh = '<div class="nv-panel">'
    for geo, d in _GEO_FY2025.items():
        pct = d["pct"] * 100
        gh += (
            f'<div class="nv-seg-row">'
            f'<span class="nv-seg-label" style="width:100px">{geo}</span>'
            f'<div class="nv-seg-track">'
            f'<div class="nv-seg-fill" style="width:{pct:.1f}%;'
            f'background:linear-gradient(90deg,{d["color"]}80,{d["color"]})">'
            f'<span class="nv-seg-pct">{pct:.1f}%</span></div></div>'
            f'<span class="nv-seg-val">${d["rev"]:,.0f}M</span></div>'
        )
    gh += (
        '<div style="font-size:9px;color:#64748b;margin-top:8px;line-height:1.5">'
        "China + HK: 13.1% of FY2025 revenue ($17.1B). "
        "Export control risk = key downside scenario driver.</div></div>"
    )
    st.markdown(gh, unsafe_allow_html=True)
