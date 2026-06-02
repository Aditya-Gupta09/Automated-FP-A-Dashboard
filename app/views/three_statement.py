"""
app/views/three_statement.py  v3.0
Light theme · waterfall with floating bars
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_L = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8fafc",
    font=dict(color="#475569", size=11),
    margin=dict(l=8, r=8, t=28, b=8),
)

_HIST = {
    2020: {"rev": 10918, "gm": 0.619, "ebit_m": 0.261, "net_m": 0.256},
    2021: {"rev": 16675, "gm": 0.623, "ebit_m": 0.272, "net_m": 0.260},
    2022: {"rev": 26914, "gm": 0.649, "ebit_m": 0.373, "net_m": 0.362},
    2023: {"rev": 26974, "gm": 0.569, "ebit_m": 0.157, "net_m": 0.162},
    2024: {"rev": 60922, "gm": 0.727, "ebit_m": 0.541, "net_m": 0.488},
    2025: {"rev": 130497, "gm": 0.750, "ebit_m": 0.624, "net_m": 0.559},
}

_FCFF_FALLBACK = {
    "base": {2026: 99315, 2027: 149946, 2028: 200235, 2029: 246423, 2030: 308056},
    "upside": {2026: 158824, 2027: 254183, 2028: 363097, 2029: 462430, 2030: 576121},
    "downside": {2026: 42456, 2027: 55893, 2028: 68241, 2029: 72309, 2030: 83415},
}
_HIST_FCFF = {2023: 2650, 2024: 23329, 2025: 55932}

_FCFF_BUILD = [
    ("NOPAT", 68443, "positive"),
    ("+ D&A", 1864, "relative"),
    ("− CapEx", 3236, "relative"),
    ("− ΔNWC", 11139, "relative"),
    ("= FCFF", 55932, "total"),
]


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except:
        return None


def _get_df(result, key):
    df = result.get(key)
    return df if isinstance(df, pd.DataFrame) and not df.empty else None


def render_three_statement_tab(results, scenario):
    result = results.get(scenario, {})
    is_df = _get_df(result, "income_statement")
    fcff_df = _get_df(result, "fcff")

    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        st.markdown(
            '<div class="nv-section-title">Revenue · FY2020–2025</div>'
            '<div class="nv-section-sub">Historical actuals ($M)</div>',
            unsafe_allow_html=True,
        )
        yrs = list(_HIST.keys())
        revs = [_HIST[y]["rev"] for y in yrs]
        bar_colors = [
            "rgba(59,130,246,0.25)",
            "rgba(59,130,246,0.31)",
            "rgba(59,130,246,0.38)",
            "rgba(59,130,246,0.44)",
            "rgba(59,130,246,0.56)",
            "rgba(59,130,246,1.00)",
        ]
        fig = go.Figure(
            go.Bar(
                x=[str(y) for y in yrs],
                y=revs,
                marker_color=bar_colors,
                text=[f"${r/1000:.0f}K" for r in revs],
                textposition="outside",
                textfont=dict(color="#3b82f6", size=9),
            )
        )
        fig.update_layout(
            **_L,
            height=210,
            showlegend=False,
            bargap=0.3,
            yaxis=dict(showticklabels=False, gridcolor="#e2e8f0", zeroline=False),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown(
            '<div class="nv-section-title">Margin progression · FY2020–2025</div>'
            '<div class="nv-section-sub">Gross · EBIT · Net margin</div>',
            unsafe_allow_html=True,
        )
        cm = {
            2020: "#64748b",
            2021: "#64748b",
            2022: "#64748b",
            2023: "#f59e0b",
            2024: "#10b981",
            2025: "#34d399",
        }
        r = (
            '<div class="nv-panel" style="padding:10px 12px">'
            '<table style="width:100%;font-size:10px;border-collapse:collapse">'
            '<tr style="border-bottom:1px solid #e2e8f0">'
            '<td style="padding:3px 0;color:#64748b;font-weight:600">Year</td>'
            '<td style="text-align:right;color:#64748b;font-weight:600">Gross</td>'
            '<td style="text-align:right;color:#64748b;font-weight:600">EBIT</td>'
            '<td style="text-align:right;color:#64748b;font-weight:600">Net</td></tr>'
        )
        for yr, d in _HIST.items():
            c = cm[yr]
            fw = "700" if yr == 2025 else "500"
            r += (
                f'<tr style="border-bottom:1px solid #e2e8f0">'
                f'<td style="padding:3px 0;color:{c};font-weight:{fw}">FY{yr}</td>'
                f'<td style="text-align:right;color:{c};font-weight:{fw};font-family:monospace">{d["gm"]*100:.1f}%</td>'
                f'<td style="text-align:right;color:{c};font-weight:{fw};font-family:monospace">{d["ebit_m"]*100:.1f}%</td>'
                f'<td style="text-align:right;color:{c};font-weight:{fw};font-family:monospace">{d["net_m"]*100:.1f}%</td>'
                f"</tr>"
            )
        r += "</table></div>"
        st.markdown(r, unsafe_allow_html=True)

    with c3:
        st.markdown(
            '<div class="nv-section-title">FCFF build-up · FY2025A</div>'
            '<div class="nv-section-sub">From 05a_FCFF · NOPAT = EBIT×(1−ETR)</div>',
            unsafe_allow_html=True,
        )
        wf_labels = ["NOPAT", "+ D&A", "− CapEx", "− ΔNWC", "= FCFF"]
        wf_values = [68443, 1864, -3236, -11139, 0]
        wf_measures = ["absolute", "relative", "relative", "relative", "total"]
        wf_text = ["$68,443M", "+$1,864M", "−$3,236M", "−$11,139M", "$55,932M"]
        wf_fig = go.Figure(
            go.Waterfall(
                orientation="h",
                measure=wf_measures,
                y=wf_labels,
                x=wf_values,
                text=wf_text,
                textposition="outside",
                connector=dict(line=dict(color="#e2e8f0", width=1)),
                increasing=dict(marker=dict(color="#3b82f6")),
                decreasing=dict(marker=dict(color="#ef4444")),
                totals=dict(marker=dict(color="#0891b2")),
                hovertemplate="<b>%{y}</b>: %{text}<extra></extra>",
            )
        )
        wf_fig.update_layout(
            **_L,
            height=210,
            showlegend=False,
            xaxis=dict(
                title=None,
                gridcolor="#e2e8f0",
                zeroline=False,
                tickprefix="$",
                ticksuffix="M",
            ),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", autorange="reversed"),
        )
        st.plotly_chart(
            wf_fig, use_container_width=True, config={"displayModeBar": False}
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="nv-section-title">FCFF projection FY2023–2030F · {scenario.title()}</div>'
        '<div class="nv-section-sub">$2.6K → $308K base (+116× over 7 years)</div>',
        unsafe_allow_html=True,
    )

    fcff_hist = [(yr, v, "hist") for yr, v in _HIST_FCFF.items()]
    fcff_proj = []
    if (
        fcff_df is not None
        and "fcff_usdm" in fcff_df.columns
        and "fiscal_year" in fcff_df.columns
    ):
        for _, row in fcff_df.iterrows():
            fcff_proj.append((int(row["fiscal_year"]), float(row["fcff_usdm"]), "proj"))
    else:
        for yr, v in _FCFF_FALLBACK.get(scenario, _FCFF_FALLBACK["base"]).items():
            fcff_proj.append((yr, v, "proj"))

    all_f = sorted(fcff_hist + fcff_proj, key=lambda x: x[0])
    xl = [f"FY{yr}A" if k == "hist" else f"FY{yr}F" for yr, _, k in all_f]
    yv = [v for _, v, _ in all_f]
    bc = ["rgba(107,114,128,0.40)" if k == "hist" else "#3b82f6" for _, _, k in all_f]

    fig3 = go.Figure(
        go.Bar(
            x=xl,
            y=yv,
            marker_color=bc,
            text=[f"${v/1000:.0f}K" for v in yv],
            textposition="outside",
            textfont=dict(color="#3b82f6", size=9),
        )
    )
    fig3.add_vline(
        x=2.5,
        line_dash="dot",
        line_color="#9ca3af",
        line_width=1,
        annotation_text="Forecast →",
        annotation_font_color="#64748b",
        annotation_font_size=9,
    )
    fig3.update_layout(
        **_L,
        height=250,
        showlegend=False,
        bargap=0.3,
        yaxis=dict(title="FCFF ($M)", gridcolor="#e2e8f0", zeroline=False),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="nv-section-title">Income statement projection · {scenario.title()}</div>'
        '<div class="nv-section-sub">FY2026F–2030F · key metrics · all figures $M</div>',
        unsafe_allow_html=True,
    )
    if is_df is not None:
        _render_is_table(is_df)
    else:
        st.markdown(
            '<div class="nv-panel" style="color:#64748b;font-size:11px;text-align:center;padding:20px">'
            "IS projection not available — run pipeline to generate.</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="nv-section-title">Margin trajectory · {scenario.title()}</div>'
        '<div class="nv-section-sub">FY2020–2025 actual + FY2026–2030F projected (dashed)</div>',
        unsafe_allow_html=True,
    )

    if is_df is None:
        st.info(
            "Projected margin lines unavailable — income statement not returned by pipeline. Historical lines shown only."
        )

    hy = list(_HIST.keys())
    hgm = [_HIST[y]["gm"] * 100 for y in hy]
    hem = [_HIST[y]["ebit_m"] * 100 for y in hy]
    xh = [str(y) for y in hy]
    pgm, pem, xp = [], [], []
    if is_df is not None and "fiscal_year" in is_df.columns:
        for _, row in is_df.iterrows():
            xp.append(f"{int(row['fiscal_year'])}F")
            pgm.append(float(row.get("gross_margin_pct", 0)) * 100)
            pem.append(float(row.get("ebit_margin_pct", 0)) * 100)

    fig4 = go.Figure()
    fig4.add_trace(
        go.Scatter(
            x=xh,
            y=hgm,
            name="Gross (hist)",
            mode="lines+markers",
            line=dict(color="#3b82f6", width=2),
            marker=dict(size=5),
        )
    )
    fig4.add_trace(
        go.Scatter(
            x=xh,
            y=hem,
            name="EBIT (hist)",
            mode="lines+markers",
            line=dict(color="#10b981", width=2),
            marker=dict(size=5),
        )
    )
    if pgm:
        fig4.add_trace(
            go.Scatter(
                x=[xh[-1]] + xp,
                y=[hgm[-1]] + pgm,
                name="Gross (proj)",
                mode="lines+markers",
                line=dict(color="#3b82f6", width=2, dash="dot"),
                marker=dict(size=4),
            )
        )
    if pem:
        fig4.add_trace(
            go.Scatter(
                x=[xh[-1]] + xp,
                y=[hem[-1]] + pem,
                name="EBIT (proj)",
                mode="lines+markers",
                line=dict(color="#10b981", width=2, dash="dot"),
                marker=dict(size=4),
            )
        )
    fig4.update_layout(
        **_L,
        height=260,
        yaxis=dict(
            title="Margin %", gridcolor="#e2e8f0", zeroline=False, ticksuffix="%"
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.2, bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})


def _render_is_table(is_df: pd.DataFrame) -> None:
    KEY_COLS = [
        ("fiscal_year", "Year"),
        ("revenue_usdm", "Revenue"),
        ("gross_profit_usdm", "Gross Profit"),
        ("ebit_usdm", "EBIT"),
        ("net_income_usdm", "Net Income"),
        ("gross_margin_pct", "GM%"),
        ("ebit_margin_pct", "EBIT%"),
    ]
    present = [(c, l) for c, l in KEY_COLS if c in is_df.columns]
    hdr = "".join(f"<th>{l}</th>" for _, l in present)
    body = ""
    pct_set = {"gross_margin_pct", "ebit_margin_pct", "net_margin_pct"}
    for _, row in is_df.iterrows():
        cells = ""
        for col, _ in present:
            v = row.get(col)
            if col == "fiscal_year":
                cells += f'<td style="color:#0f1419;font-weight:600">FY{int(v)}F</td>'
            elif col in pct_set:
                n = _num(v)
                cells += (
                    f'<td style="color:#475569;font-family:monospace">{n*100:.1f}%</td>'
                    if n is not None
                    else "<td>N/A</td>"
                )
            else:
                n = _num(v)
                cells += (
                    f'<td style="color:#475569;font-family:monospace">${n:,.0f}</td>'
                    if n is not None
                    else "<td>N/A</td>"
                )
        body += f"<tr>{cells}</tr>"
    st.markdown(
        f'<div class="nv-dcf-wrap"><table class="nv-dcf-tbl">'
        f"<thead><tr>{hdr}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )
