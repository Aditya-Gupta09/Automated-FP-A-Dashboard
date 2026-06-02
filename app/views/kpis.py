"""
app/views/kpis.py  v3.0
Light theme · traffic light KPI signals · annotated charts
"""

from __future__ import annotations
from typing import Any
import plotly.graph_objects as go
import streamlit as st

_L = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(color="#475569", size=11),
    margin=dict(l=8, r=8, t=28, b=8),
)

_KPI_FY2025 = [
    ("Gross margin", 0.750, "green", "75.0%", 0.85),
    ("EBITDA margin", 0.638, "green", "63.8%", 0.80),
    ("FCF margin", 0.466, "green", "46.6%", 0.60),
    ("Revenue growth", 1.142, "green", "+114.2%", 1.50),
    ("AR days (DSO)", 64.5, "amber", "64.5d", 90.0),
    ("AP days (DPO)", 70.6, "green", "70.6d", 90.0),
    ("Current ratio", 4.44, "green", "4.44×", 7.0),
    ("Int. coverage", 329.8, "green", "329.8×", 400.0),
]

_SIGNAL_COLORS = {
    "green": "#10b981",
    "amber": "#f59e0b",
    "red": "#ef4444",
    "neutral": "#64748b",
}

_WC_HIST = {
    2021: {"dso": 53.2, "dio": 106.1, "dpo": 66.8, "ccc": 92.5},
    2022: {"dso": 63.1, "dio": 100.7, "dpo": 68.9, "ccc": 94.8},
    2023: {"dso": 51.8, "dio": 162.1, "dpo": 37.5, "ccc": 176.4},
    2024: {"dso": 59.9, "dio": 116.0, "dpo": 59.3, "ccc": 116.6},
    2025: {"dso": 64.5, "dio": 112.7, "dpo": 70.6, "ccc": 106.7},
}

_RATIO_HIST = {
    2020: {"gm": 0.619, "ebitda": 0.296, "current": None, "de": None},
    2021: {"gm": 0.623, "ebitda": 0.338, "current": 4.09, "de": 0.70},
    2022: {"gm": 0.649, "ebitda": 0.417, "current": 6.65, "de": 0.66},
    2023: {"gm": 0.569, "ebitda": 0.214, "current": 3.52, "de": 0.86},
    2024: {"gm": 0.727, "ebitda": 0.566, "current": 4.17, "de": 0.53},
    2025: {"gm": 0.750, "ebitda": 0.638, "current": 4.44, "de": 0.41},
}


def _cell_color(metric, val):
    if val is None:
        return "#94a3b8"
    if metric == "gm":
        return "#34d399" if val > 0.70 else ("#f59e0b" if val > 0.56 else "#f87171")
    if metric == "ebitda":
        return "#34d399" if val > 0.40 else ("#f59e0b" if val > 0.20 else "#f87171")
    if metric == "current":
        return "#34d399" if val > 2.0 else ("#f59e0b" if val >= 1.0 else "#f87171")
    if metric == "de":
        return "#34d399" if val < 0.5 else ("#f59e0b" if val < 1.0 else "#f87171")
    return "#475569"


def _kpi_bar_pct(name, raw, ceiling) -> int:
    if name == "AR days (DSO)":
        return max(int((ceiling - raw) / ceiling * 100), 5)
    return min(int(raw / ceiling * 100), 100)


def render_kpis_tab(results, scenario):
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            '<div class="nv-section-title">Traffic-light KPI signals · FY2025 actual</div>'
            '<div class="nv-section-sub">NVDA-calibrated thresholds from ratios.py</div>',
            unsafe_allow_html=True,
        )
        html = '<div class="nv-panel">'
        for name, raw, signal, display, ceiling in _KPI_FY2025:
            color = _SIGNAL_COLORS[signal]
            bar_pct = _kpi_bar_pct(name, raw, ceiling)
            html += (
                f'<div class="nv-kpi-signal">'
                f'<span class="nv-ks-name">{name}</span>'
                f'<span class="nv-ks-dot" style="background:{color}"></span>'
                f'<div class="nv-ks-bar"><div class="nv-ks-fill" style="width:{bar_pct}%;background:{color}"></div></div>'
                f'<span class="nv-ks-val">{display}</span>'
                f"</div>"
            )
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    with col2:
        st.markdown(
            '<div class="nv-section-title">Working capital efficiency · FY2021–2025</div>'
            '<div class="nv-section-sub">DSO / DIO / DPO / CCC — from 09_WorkingCapital sheet</div>',
            unsafe_allow_html=True,
        )
        tbl = (
            '<div class="nv-panel" style="padding:10px 12px">'
            '<table style="width:100%;font-size:10px;border-collapse:collapse">'
            '<tr style="border-bottom:1px solid #e2e8f0">'
            '<td style="padding:3px 0;color:#64748b;font-weight:600">Metric</td>'
        )
        for yr in sorted(_WC_HIST.keys()):
            tbl += f'<td style="text-align:right;color:#64748b;font-weight:600">FY{yr}</td>'
        tbl += "</tr>"
        anno = {
            2023: {
                "dso": "#475569",
                "dio": "#ef4444",
                "dpo": "#ef4444",
                "ccc": "#ef4444",
            },
            2025: {
                "dso": "#f59e0b",
                "dio": "#f59e0b",
                "dpo": "#10b981",
                "ccc": "#f59e0b",
            },
        }
        for label, key in [
            ("DSO (days)", "dso"),
            ("DIO (days)", "dio"),
            ("DPO (days)", "dpo"),
            ("CCC (days)", "ccc"),
        ]:
            tbl += f'<tr style="border-bottom:1px solid #e2e8f0"><td style="padding:3px 0;color:#475569;font-weight:500">{label}</td>'
            for yr in sorted(_WC_HIST.keys()):
                v = _WC_HIST[yr][key]
                c = anno.get(yr, {}).get(key, "#475569")
                tbl += f'<td style="text-align:right;color:{c};font-family:monospace;font-weight:600">{v:.1f}</td>'
            tbl += "</tr>"
        tbl += (
            "</table>"
            '<div style="font-size:9px;color:#64748b;margin-top:8px;line-height:1.5">'
            "FY2023 anomaly: DIO spiked to 162d (inventory build ahead of AI demand) · "
            "DPO compressed to 37.5d (paid suppliers fast to secure H100 supply). "
            "Both normalised by FY2025.</div></div>"
        )
        st.markdown(tbl, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="nv-section-title">Solvency & profitability ratios · FY2020–2025</div>'
        '<div class="nv-section-sub">From 08_RatioAnalysis sheet · color-coded vs thresholds</div>',
        unsafe_allow_html=True,
    )

    ratio_tbl = (
        '<div class="nv-dcf-wrap"><table class="nv-dcf-tbl"><thead><tr><th>Ratio</th>'
        + "".join(f"<th>FY{yr}</th>" for yr in sorted(_RATIO_HIST.keys()))
        + "</tr></thead><tbody>"
    )
    for label, key, fmt in [
        ("Gross margin", "gm", lambda v: f"{v*100:.1f}%"),
        ("EBITDA margin", "ebitda", lambda v: f"{v*100:.1f}%"),
        ("Current ratio", "current", lambda v: f"{v:.2f}×"),
        ("D/E ratio", "de", lambda v: f"{v:.2f}×"),
    ]:
        ratio_tbl += f"<tr><td>{label}</td>"
        for yr in sorted(_RATIO_HIST.keys()):
            v = _RATIO_HIST[yr].get(key)
            c = _cell_color(key, v)
            fw = "700" if yr == 2025 else "500"
            if v is None:
                ratio_tbl += '<td style="color:#94a3b8;font-size:10px">n/a</td>'
            else:
                ratio_tbl += f'<td style="color:{c};font-weight:{fw};font-family:monospace">{fmt(v)}</td>'
        ratio_tbl += "</tr>"

    ratio_tbl += (
        "</tbody></table>"
        '<div style="font-size:9px;color:#64748b;padding:6px 12px">'
        "* FY2020 balance sheet ratios unavailable in historical source data — data begins FY2021.</div>"
        "</div>"
    )
    st.markdown(ratio_tbl, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="nv-section-title">Margin trend · FY2020–2025 · FY2023 trough annotated</div>'
        '<div class="nv-section-sub">Gross margin vs EBITDA margin · historical actuals</div>',
        unsafe_allow_html=True,
    )
    yrs = sorted(_RATIO_HIST.keys())
    gm = [_RATIO_HIST[y]["gm"] * 100 for y in yrs]
    ebt = [_RATIO_HIST[y]["ebitda"] * 100 for y in yrs]
    x = [str(y) for y in yrs]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=gm,
            name="Gross Margin",
            mode="lines+markers+text",
            line=dict(color="#3b82f6", width=2),
            marker=dict(size=6),
            text=[f"{v:.1f}%" for v in gm],
            textposition="top center",
            textfont=dict(color="#3b82f6", size=9),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ebt,
            name="EBITDA Margin",
            mode="lines+markers+text",
            line=dict(color="#10b981", width=2),
            marker=dict(size=6),
            text=[f"{v:.1f}%" for v in ebt],
            textposition="bottom center",
            textfont=dict(color="#10b981", size=9),
        )
    )
    fig.add_annotation(
        x="2023",
        y=21.4,
        text="FY2023 trough<br>inventory write-downs",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#f59e0b",
        font=dict(color="#f59e0b", size=9),
        bgcolor="#ffffff",
        bordercolor="#f59e0b",
        borderwidth=1,
        ax=40,
        ay=-40,
    )
    fig.update_layout(
        **_L,
        height=260,
        yaxis=dict(
            title="Margin %", gridcolor="#e2e8f0", zeroline=False, ticksuffix="%"
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.2, bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="nv-section-title">Working capital efficiency trend</div>'
        '<div class="nv-section-sub">DSO · DPO · CCC — lower DSO = faster collection · higher DPO = better float</div>',
        unsafe_allow_html=True,
    )
    wc_yrs = sorted(_WC_HIST.keys())
    dso = [_WC_HIST[y]["dso"] for y in wc_yrs]
    dpo = [_WC_HIST[y]["dpo"] for y in wc_yrs]
    ccc = [_WC_HIST[y]["ccc"] for y in wc_yrs]
    x_str = [str(y) for y in wc_yrs]

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=x_str,
            y=dso,
            name="DSO",
            mode="lines+markers",
            line=dict(color="#3b82f6", width=2),
            marker=dict(size=5),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=x_str,
            y=dpo,
            name="DPO",
            mode="lines+markers",
            line=dict(color="#10b981", width=2),
            marker=dict(size=5),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=x_str,
            y=ccc,
            name="CCC",
            mode="lines+markers",
            line=dict(color="#f59e0b", width=2, dash="dot"),
            marker=dict(size=5),
        )
    )
    fig2.update_layout(
        **_L,
        height=230,
        yaxis=dict(title="Days", gridcolor="#e2e8f0", zeroline=False),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", type="category"),
        legend=dict(orientation="h", y=-0.25, bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
