"""
app/views/comps.py  v3.0
Light theme · comparable analysis · EV multiples
"""

from __future__ import annotations
import math
from typing import Any
import plotly.graph_objects as go
import streamlit as st

_L = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(color="#475569", size=11),
    margin=dict(l=8, r=8, t=28, b=8),
)

_PEERS = [
    {
        "ticker": "NVDA",
        "name": "NVIDIA",
        "ev_b": 4406.05,
        "ev_ebitda": 44.83,
        "pe": 52.20,
        "ev_rev": 26.67,
        "subject": True,
    },
    {
        "ticker": "AVGO",
        "name": "Broadcom",
        "ev_b": 1703.17,
        "ev_ebitda": 52.01,
        "pe": 89.11,
        "ev_rev": 28.42,
        "subject": False,
    },
    {
        "ticker": "TSM",
        "name": "TSMC",
        "ev_b": 1168.51,
        "ev_ebitda": 14.29,
        "pe": 29.69,
        "ev_rev": 9.81,
        "subject": False,
    },
    {
        "ticker": "AMD",
        "name": "AMD",
        "ev_b": 376.27,
        "ev_ebitda": 68.29,
        "pe": 134.73,
        "ev_rev": 12.71,
        "subject": False,
    },
    {
        "ticker": "QCOM",
        "name": "Qualcomm",
        "ev_b": 180.22,
        "ev_ebitda": 12.99,
        "pe": 15.78,
        "ev_rev": 4.17,
        "subject": False,
    },
    {
        "ticker": "INTC",
        "name": "Intel",
        "ev_b": 205.15,
        "ev_ebitda": 22.30,
        "pe": None,
        "ev_rev": 3.87,
        "subject": False,
    },
]
_EXIT = {
    "fy2030_ebitda_usdm": 387543,
    "exit_multiple": 22.3,
    "terminal_ev_usdm": 8642198,
    "pv_terminal_ev_usdm": 4708478,
    "sum_pv_fcf_usdm": 664085,
    "total_ev_exit_usdm": 5372563,
    "gordon_growth_ev_usdm": 2622182,
    "premium_exit_vs_gg": 2.05,
}
_STATS = {
    "ev_ebitda": {
        "high": 68.29,
        "p75": 52.01,
        "mean": 35.18,
        "median": 22.30,
        "p25": 13.64,
        "low": 12.99,
    }
}

_DCF_FALLBACK = {"base": 109.16, "upside": 229.53, "downside": 32.76}
_COMPS_IMPLIED = {"ev_ebitda_median": 56.24, "ev_rev_median": 131.50}


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except:
        return None


def render_comps_tab(results: dict, scenario: str) -> None:
    result = results.get(scenario, {})
    dcf_price = _num(result.get("dcf_valuation", {}).get("implied_share_price_usd"))
    if dcf_price is None:
        dcf_price = _DCF_FALLBACK.get(scenario, 109.16)

    st.markdown(
        '<div class="nv-section-title">Comparable companies · peer trading multiples</div>'
        '<div class="nv-section-sub">From 17_ComparableAnalysis & comps_data.csv · Oct 17 2025 · LTM figures</div>',
        unsafe_allow_html=True,
    )

    max_ev = max(p["ev_b"] for p in _PEERS)
    log_max = math.log10(max_ev)

    hdr = (
        '<div class="nv-comps-hdr"><div>Company</div><div>EV ($B)</div>'
        '<div style="text-align:right">EV/EBITDA</div>'
        '<div style="text-align:right">P/E</div>'
        '<div style="text-align:right">EV/Rev</div></div>'
    )
    rows = ""
    for p in _PEERS:
        tc = "#0891b2" if p["subject"] else "#475569"
        fw = "700" if p["subject"] else "500"
        log_w = math.log10(max(p["ev_b"], 1))
        bp = log_w / log_max * 100
        bc = "rgba(8,145,178,0.45)" if p["subject"] else "rgba(59,130,246,0.38)"
        pe = f"{p['pe']:.1f}×" if p["pe"] else "n/m"
        rows += (
            f'<div class="nv-comps-row">'
            f'<div style="color:{tc};font-weight:{fw}">{p["ticker"]} — {p["name"]}</div>'
            f"<div>"
            f'<div class="nv-ev-bar"><div class="nv-ev-fill" style="width:{bp:.0f}%;background:{bc}"></div></div>'
            f'<div style="font-size:9px;color:#64748b;font-family:monospace">${p["ev_b"]:,.0f}B</div>'
            f"</div>"
            f'<div style="text-align:right;color:{tc};font-weight:{fw};font-family:monospace">{p["ev_ebitda"]:.1f}×</div>'
            f'<div style="text-align:right;color:{tc};font-weight:{fw};font-family:monospace">{pe}</div>'
            f'<div style="text-align:right;color:{tc};font-weight:{fw};font-family:monospace">{p["ev_rev"]:.1f}×</div>'
            f"</div>"
        )
    rows += (
        '<div class="nv-comps-row" style="border-top:1px solid #e2e8f0;margin-top:4px;padding-top:6px">'
        '<div style="color:#f59e0b;font-size:10px;font-weight:700">Peer median (ex-NVDA)</div><div></div>'
        '<div style="text-align:right;color:#f59e0b;font-family:monospace;font-weight:700">22.3×</div>'
        '<div style="text-align:right;color:#f59e0b;font-family:monospace;font-weight:700">29.7×</div>'
        '<div style="text-align:right;color:#f59e0b;font-family:monospace;font-weight:700">9.8×</div></div>'
    )
    st.markdown(
        f'<div class="nv-panel">{hdr}{rows}'
        '<div style="font-size:9px;color:#64748b;margin-top:10px;line-height:1.6">'
        "NVIDIA 44.83× EV/EBITDA vs peer median 22.3× — 2.01× premium reflecting AI infrastructure leadership. "
        "Intel excluded from P/E (net loss FY2024). EV bars shown on log scale for readability.</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown(
            f'<div class="nv-section-title">NVDA price · DCF vs market vs comps · {scenario.title()}</div>'
            '<div class="nv-section-sub">Valuation date Oct 17 2025</div>',
            unsafe_allow_html=True,
        )

        labels = [
            "Market price",
            f"DCF implied\n({scenario.title()})",
            "EV/EBITDA\nmedian implied",
            "EV/Revenue\nmedian implied",
        ]
        vals = [
            183.22,
            dcf_price,
            _COMPS_IMPLIED["ev_ebitda_median"],
            _COMPS_IMPLIED["ev_rev_median"],
        ]
        colors = ["#94a3b8", "#0891b2", "#f59e0b", "#8b5cf6"]

        if scenario == "upside":
            colors[1] = "#10b981"
        elif scenario == "downside":
            colors[1] = "#ef4444"

        fig = go.Figure(
            go.Bar(
                x=labels,
                y=vals,
                marker_color=colors,
                text=[f"${v:.2f}" for v in vals],
                textposition="outside",
                textfont=dict(size=11, color="#0f1419"),
            )
        )
        fig.update_layout(
            **_L,
            height=270,
            showlegend=False,
            bargap=0.4,
            yaxis=dict(
                title="Implied Price ($)",
                gridcolor="#e2e8f0",
                zeroline=False,
                range=[0, max(vals) * 1.25],
            ),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown(
            '<div class="nv-section-title">Exit multiple crosscheck · secondary method</div>'
            '<div class="nv-section-sub">From 05b_DCF rows 41–45 · FY2030F EBITDA × peer median</div>',
            unsafe_allow_html=True,
        )
        em = _EXIT
        st.markdown(
            '<div class="nv-panel">'
            f'<div class="nv-assume-row"><span class="nv-alabel">FY2030F EBITDA</span><span class="nv-aval">${em["fy2030_ebitda_usdm"]:,.0f}M</span></div>'
            f'<div class="nv-assume-row"><span class="nv-alabel">Exit multiple</span><span class="nv-aval">{em["exit_multiple"]:.1f}×</span></div>'
            f'<div class="nv-assume-row"><span class="nv-alabel">Terminal EV</span><span class="nv-aval" style="color:#f59e0b;font-weight:700">${em["terminal_ev_usdm"]/1000:,.0f}B</span></div>'
            f'<div class="nv-assume-row"><span class="nv-alabel">PV of terminal EV</span><span class="nv-aval" style="color:#f59e0b;font-weight:700">${em["pv_terminal_ev_usdm"]/1000:,.0f}B</span></div>'
            f'<div class="nv-assume-row"><span class="nv-alabel">Total EV (exit method)</span><span class="nv-aval" style="color:#f59e0b;font-weight:700">${em["total_ev_exit_usdm"]/1000:,.0f}B</span></div>'
            f'<div class="nv-assume-row"><span class="nv-alabel">Gordon Growth EV</span><span class="nv-aval">${em["gordon_growth_ev_usdm"]/1000:,.0f}B</span></div>'
            f'<div class="nv-assume-row" style="border-top:1px solid #e2e8f0;padding-top:6px">'
            f'<span class="nv-alabel">Premium: exit vs GGM</span>'
            f'<span class="nv-aval" style="color:#f59e0b;font-weight:700">{em["premium_exit_vs_gg"]:.2f}×</span></div>'
            '<div style="font-size:9px;color:#64748b;margin-top:8px">'
            "Exit multiple method 2.05× higher EV than Gordon Growth — confirms base case is conservative. "
            "GGM used as primary method per 05b_DCF methodology.</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="nv-section-title">EV/EBITDA multiple distribution · peer universe</div>'
        '<div class="nv-section-sub">High / P75 / Mean / Median / P25 / Low · from comps.py compute_stats()</div>',
        unsafe_allow_html=True,
    )

    stat_labels = ["High", "P75", "Mean", "Median", "P25", "Low"]
    stat_keys = ["high", "p75", "mean", "median", "p25", "low"]
    ev_vals = [_STATS["ev_ebitda"][k] for k in stat_keys]
    bar_colors = [
        "rgba(59,130,246,0.56)",
        "rgba(59,130,246,0.44)",
        "rgba(59,130,246,0.31)",
        "#f59e0b",
        "rgba(59,130,246,0.19)",
        "rgba(59,130,246,0.19)",
    ]

    fig2 = go.Figure(
        go.Bar(
            x=stat_labels,
            y=ev_vals,
            marker_color=bar_colors,
            text=[f"{v:.1f}×" for v in ev_vals],
            textposition="outside",
            textfont=dict(color="#475569", size=10),
        )
    )

    fig2.add_hline(
        y=44.83,
        line_dash="dot",
        line_color="#0891b2",
        line_width=1.5,
        annotation_text="NVDA 44.83×",
        annotation_font_color="#0891b2",
        annotation_font_size=9,
        annotation_position="top right",
    )

    fig2.update_layout(
        **_L,
        height=250,
        showlegend=False,
        bargap=0.4,
        yaxis=dict(
            title="EV/EBITDA",
            gridcolor="#e2e8f0",
            zeroline=False,
            ticksuffix="×",
            range=[0, 80],
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
