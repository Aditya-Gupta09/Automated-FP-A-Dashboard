"""
app/app.py  v3.0 FINAL
Light theme + filter bar + all features + DEMO DATA FALLBACK
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
for p in [str(SRC_DIR), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

st.set_page_config(
    page_title="NVIDIA FP&A Platform",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Import pipeline or use demo fallback
PIPELINE_AVAILABLE = False
run_pipeline = None
try:
    from src.modeling.engine import run_pipeline

    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False


# Demo data fallback
def _get_demo_results(scenario: str = "base") -> dict:
    """Fallback demo data when pipeline not available."""
    demo_prices = {
        "base": 109.16,
        "upside": 229.53,
        "downside": 32.76,
    }

    fcff_demo = pd.DataFrame(
        {
            "fiscal_year": [2026, 2027, 2028, 2029, 2030],
            "fcff_usdm": [99315, 149946, 200235, 246423, 308056],
            "revenue_usdm": [179500, 272000, 386000, 490000, 625000],
        }
    )

    is_demo = pd.DataFrame(
        {
            "fiscal_year": [2026, 2027, 2028, 2029, 2030],
            "revenue_usdm": [179500, 272000, 386000, 490000, 625000],
            "gross_profit_usdm": [135675, 204000, 289500, 367500, 468750],
            "ebit_usdm": [112000, 170000, 240000, 310000, 390000],
            "net_income_usdm": [100000, 152000, 215000, 280000, 350000],
            "gross_margin_pct": [0.756, 0.750, 0.750, 0.750, 0.750],
            "ebit_margin_pct": [0.624, 0.625, 0.621, 0.633, 0.624],
        }
    )

    return {
        "dcf_valuation": {
            "implied_share_price_usd": demo_prices[scenario],
            "wacc_used": (
                0.1291
                if scenario == "base"
                else (0.1191 if scenario == "upside" else 0.1391)
            ),
            "terminal_growth_rate": (
                0.03675
                if scenario == "base"
                else (0.045 if scenario == "upside" else 0.03)
            ),
            "pv_terminal_value_usdm": 2622182,
            "sum_pv_fcf_usdm": 664085,
            "net_debt_usdm": 32940,
            "enterprise_value_usdm": 3286267,
            "diluted_shares_millions": 24300,
            "sensitivity": {"implied_price": {}},
        },
        "fcff": fcff_demo,
        "income_statement": is_demo,
        "balance_sheet": pd.DataFrame(),
        "cash_flow_statement": pd.DataFrame(),
        "status": "DEMO",
    }


# Component imports
from components.drivers import build_driver_bridge, render_driver_bridge
from components.interactions import render_interactions
from components.kpi_tile import render_kpi_row
from components.narrative import render_narrative
from components.sensitivity import render_sensitivity_matrix
from components.summary import render_dcf_summary
from views.comps import render_comps_tab
from views.kpis import render_kpis_tab
from views.segments import render_segments_tab
from views.three_statement import render_three_statement_tab


def _apply_theme() -> None:
    css_path = APP_DIR / "style" / "theme.css"
    css = css_path.read_text() if css_path.exists() else ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _load_results() -> dict:
    """Load from pipeline or demo data. Store error message if it occurs."""
    if PIPELINE_AVAILABLE and run_pipeline:
        try:
            st.session_state.pipeline_error = None
            return {
                "base": run_pipeline("base"),
                "upside": run_pipeline("upside"),
                "downside": run_pipeline("downside"),
            }
        except Exception as e:
            # Store error but don't display here - display in main() instead
            st.session_state.pipeline_error = str(e)[:150]
            return {
                "base": _get_demo_results("base"),
                "upside": _get_demo_results("upside"),
                "downside": _get_demo_results("downside"),
            }
    else:
        st.session_state.pipeline_error = None
        return {
            "base": _get_demo_results("base"),
            "upside": _get_demo_results("upside"),
            "downside": _get_demo_results("downside"),
        }


_SCENARIO_META = {
    "base": {"label": "Base case", "price_color": "#3b82f6"},
    "upside": {"label": "Upside · bull", "price_color": "#10b981"},
    "downside": {"label": "Downside · bear", "price_color": "#ef4444"},
}
_ASSUME = {
    "base": [
        ("WACC", "12.91%", "—"),
        ("Terminal g", "3.675%", "—"),
        ("DC growth FY26F", "69%", "—"),
        ("Gross margin FY26F", "77.0%", "—"),
        ("CapEx % rev", "3.0%", "—"),
    ],
    "upside": [
        ("WACC", "11.91%", "▲"),
        ("Terminal g", "4.50%", "▲"),
        ("DC growth FY26F", "95%", "▲"),
        ("Gross margin FY26F", "82.0%", "▲"),
        ("CapEx % rev", "3.5%", "—"),
    ],
    "downside": [
        ("WACC", "13.91%", "▼"),
        ("Terminal g", "3.00%", "▼"),
        ("DC growth FY26F", "50%", "▼"),
        ("Gross margin FY26F", "66.0%", "▼"),
        ("CapEx % rev", "2.0%", "—"),
    ],
}
_BADGE = {"▲": "ab-up", "▼": "ab-dn", "—": "ab-n"}

_TABS = [
    ("valuation", "Valuation"),
    ("segments", "Revenue & Segments"),
    ("three_statement", "3-Statement"),
    ("kpis", "KPIs & Ratios"),
    ("comps", "Comps"),
]


def _price_str(result: dict) -> str:
    try:
        v = float(result.get("dcf_valuation", {}).get("implied_share_price_usd", 0))
        return f"${v:,.2f}"
    except Exception:
        return "N/A"


def _render_sidebar(results: dict) -> None:
    scenario = st.session_state.get("scenario", "base")

    with st.sidebar:
        # NVIDIA LOGO - ACTUAL LOGO IMAGE
        # NVIDIA LOGO - FULL WIDTH
        # NVIDIA LOGO - FULL WIDTH + NO TOP GAP
        logo_path = APP_DIR / "style" / "nvidia_logo.jpeg"

        st.markdown(
            """
            <style>

            /* REMOVE DEFAULT TOP SPACE */
            section[data-testid="stSidebar"] > div:first-child {
                padding-top: 0rem !important;
            }

            /* MOVE LOGO UP */
            [data-testid="stSidebar"] .stImage {
                margin-top: -18px !important;
                margin-bottom: 20px !important;
            }

            /* LOGO SIZE */
            [data-testid="stSidebar"] .stImage img {
                width: 100% !important;
                max-width: 92% !important;
                height: auto !important;
                display: block;
                margin: 0 auto;
            }

            </style>
            """,
            unsafe_allow_html=True,
        )

        st.image(str(logo_path), use_container_width=True)

        # HEADING - BOLD AND LARGER
        st.markdown(
            '<div style="text-align:center;padding:12px 0 8px;border-bottom:1px solid #e2e8f050">'
            '<div style="font-size:16px;font-weight:700;color:#000000;letter-spacing:-0.5px">NVIDIA FP&amp;A Platform</div>'
            '<div style="font-size:10px;color:#64748b;margin-top:4px">v3.0 · Light Theme</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="nv-slabel" style="margin-top:12px">Scenario</div>',
            unsafe_allow_html=True,
        )

        for key, meta in _SCENARIO_META.items():
            price = _price_str(results.get(key, {}))
            is_active = key == scenario
            bullet = "●" if is_active else "○"
            col_btn, col_price = st.columns([3, 1])
            with col_btn:
                if st.button(
                    f"{bullet} {meta['label']}",
                    key=f"sb_{key}",
                    use_container_width=True,
                ):
                    st.session_state.scenario = key
                    st.rerun()
            with col_price:
                st.markdown(
                    f'<div style="font-size:10px;color:{meta["price_color"]};'
                    f'font-family:monospace;text-align:right;padding-top:6px">{price}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            '<hr style="margin:10px 0"><div class="nv-slabel">Active assumptions</div>',
            unsafe_allow_html=True,
        )
        rows = "".join(
            f'<div class="nv-assume-row"><span class="nv-alabel">{lbl}</span>'
            f'<span class="nv-aval">{val}<span class="nv-abadge {_BADGE[badge]}">{badge}</span></span></div>'
            for lbl, val, badge in _ASSUME.get(scenario, _ASSUME["base"])
        )
        rows += '<div class="nv-assume-row"><span class="nv-alabel">Diluted shares</span><span class="nv-aval">24,300M</span></div>'
        st.markdown(rows, unsafe_allow_html=True)


def _render_topbar(active_page: str) -> None:
    st.markdown(
        '<div class="nv-topbar">'
        '<div style="display:flex;align-items:center;gap:12px;flex:1">'
        '<div><div style="font-size:13px;font-weight:700;letter-spacing:-.01em;color:#0f1419">'
        "FP&amp;A Platform</div>"
        '<div style="font-size:10px;color:#64748b">Light theme · institutional grade</div></div>'
        "</div>"
        '<div style="font-size:11px;color:#64748b;display:flex;align-items:center;gap:8px"><span class="nv-live-dot"></span>'
        "Ready · WACC 12.91% · g 3.675%</div></div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(_TABS))
    for col, (key, label) in zip(cols, _TABS):
        with col:
            is_active = key == active_page
            if is_active:
                st.markdown('<div class="nv-tab-active">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
            if is_active:
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:0 0 8px'>", unsafe_allow_html=True)


def _render_filter_bar() -> dict:
    """Render filter bar and return selected filters."""
    st.markdown('<div class="nv-filter-bar">', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([2, 2, 2, 2], gap="medium")

    filters = {}
    with col1:
        st.markdown(
            '<span class="nv-filter-label">Date Range</span>', unsafe_allow_html=True
        )
        filters["date_range"] = st.selectbox(
            "Date Range",
            ["FY2025", "FY2024–2025", "FY2023–2025"],
            label_visibility="collapsed",
            key="filter_date",
        )

    with col2:
        st.markdown(
            '<span class="nv-filter-label">Segments</span>', unsafe_allow_html=True
        )
        filters["segments"] = st.multiselect(
            "Segments",
            ["Data Center", "Gaming", "Professional Viz", "Automotive", "OEM & Other"],
            default=["Data Center"],
            label_visibility="collapsed",
            key="filter_seg",
        )

    with col3:
        st.markdown(
            '<span class="nv-filter-label">Metrics</span>', unsafe_allow_html=True
        )
        filters["metrics"] = st.selectbox(
            "Metrics",
            ["Revenue", "EBITDA", "FCF", "Margins"],
            label_visibility="collapsed",
            key="filter_metric",
        )

    with col4:
        st.markdown('<span class="nv-filter-label">View</span>', unsafe_allow_html=True)
        filters["view"] = st.selectbox(
            "View",
            ["Summary", "Detailed", "Comparative"],
            label_visibility="collapsed",
            key="filter_view",
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    return filters


def _render_valuation(
    results: dict, selected: dict, base: dict, scenario: str, filters: dict
) -> None:
    st.markdown(
        '<div class="nv-section-title">Valuation snapshot</div>'
        '<div class="nv-section-sub">Implied share price · Gordon Growth DCF · '
        "end-of-year discounting · WACC 12.91% base</div>",
        unsafe_allow_html=True,
    )
    render_kpi_row(results, active_scenario=scenario)
    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([1.4, 1], gap="large")
    driver_rows = build_driver_bridge(base, selected)
    with left:
        render_driver_bridge(driver_rows, selected, base, scenario)
    with right:
        render_interactions(selected, scenario)

    st.markdown("<br>", unsafe_allow_html=True)
    sum_col, narr_col = st.columns([1.3, 1], gap="large")
    with sum_col:
        render_dcf_summary(results)
    with narr_col:
        render_narrative(base, selected, scenario, driver_rows)

    st.markdown("<br>", unsafe_allow_html=True)
    render_sensitivity_matrix(selected, scenario=scenario)


def main() -> None:
    _apply_theme()

    if "page" not in st.session_state:
        st.session_state.page = "valuation"
    if "scenario" not in st.session_state:
        st.session_state.scenario = "base"

    with st.spinner("Loading financial model — please wait…"):
        results = _load_results()

    scenario = st.session_state.get("scenario", "base")
    selected = results[scenario]
    base = results["base"]
    page = st.session_state.get("page", "valuation")

    _render_sidebar(results)
    _render_topbar(page)
    filters = _render_filter_bar()

    # Display pipeline error warning if it occurred (RED, not yellow!)
    if st.session_state.get("pipeline_error"):
        st.markdown(
            f'<div style="background:#fee2e2;border:3px solid #dc2626;border-left:8px solid #dc2626;'
            f'padding:16px;border-radius:8px;margin-bottom:20px">'
            f'<div style="color:#991b1b;font-weight:700;font-size:13px;margin-bottom:8px">'
            f"⚠️ Pipeline Error - Using Demo Data</div>"
            f'<div style="color:#7f1d1d;font-size:12px;line-height:1.6">'
            f"<strong>Issue:</strong> {st.session_state.pipeline_error}<br><br>"
            f"<strong>Solution:</strong> Connect your financial modeling pipeline by adding "
            f'<code style="background:#f5f5f5;padding:2px 6px;border-radius:3px;'
            f'font-family:monospace">src/modeling/engine.py</code> to parent directory<br>'
            f"<strong>Currently:</strong> Showing sample NVIDIA data</div></div>",
            unsafe_allow_html=True,
        )

    if page == "valuation":
        _render_valuation(results, selected, base, scenario, filters)
    elif page == "segments":
        render_segments_tab(results, scenario)
    elif page == "three_statement":
        render_three_statement_tab(results, scenario)
    elif page == "kpis":
        render_kpis_tab(results, scenario)
    elif page == "comps":
        render_comps_tab(results, scenario)

    st.markdown(
        '<div class="nv-footer">'
        "<span>NVIDIA FP&A Platform v3.0 · Light Theme Edition · Demo Data Mode</span>"
        '<span style="color:#0891b2">Ready to connect to your pipeline</span>'
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
