"""
app/components/summary.py  v3.0
Light theme · DCF summary table
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

_SCENARIO_ORDER = ("base", "upside", "downside")
_LABELS = {"base": "Base", "upside": "Upside", "downside": "Downside"}


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except:
        return None


def _fcff_sum(result: dict, col: str) -> float | None:
    fcff = result.get("fcff")
    if not isinstance(fcff, pd.DataFrame) or col not in fcff.columns:
        return None
    return _num(fcff[col].sum())


def _dcf(result: dict, key: str) -> float | None:
    return _num(result.get("dcf_valuation", {}).get(key))


def _fmt_usdm(v: float | None) -> str:
    return "N/A" if v is None else f"${v:,.0f}M"


def _fmt_price(v: float | None) -> str:
    return "N/A" if v is None else f"${v:,.2f}"


def _fmt_net_debt(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"(${abs(v):,.0f}M net cash)" if v < 0 else f"${v:,.0f}M net debt"


def _cell(val: str, cls: str) -> str:
    return f'<td class="{cls}">{val}</td>'


def _build_rows(results: dict) -> list[tuple[str, dict]]:
    specs = [
        ("Revenue (sum FY26–30)", lambda r: _fmt_usdm(_fcff_sum(r, "revenue_usdm"))),
        ("EBIT (sum FY26–30)", lambda r: _fmt_usdm(_fcff_sum(r, "ebit_usdm"))),
        ("FCFF (sum FY26–30)", lambda r: _fmt_usdm(_fcff_sum(r, "fcff_usdm"))),
        ("Sum PV of FCFs", lambda r: _fmt_usdm(_dcf(r, "sum_pv_fcf_usdm"))),
        (
            "PV of Terminal Value",
            lambda r: _fmt_usdm(_dcf(r, "pv_terminal_value_usdm")),
        ),
        ("Enterprise Value", lambda r: _fmt_usdm(_dcf(r, "enterprise_value_usdm"))),
        ("Net Debt", lambda r: _fmt_net_debt(_dcf(r, "net_debt_usdm"))),
        (
            "Implied Share Price",
            lambda r: _fmt_price(_dcf(r, "implied_share_price_usd")),
        ),
    ]
    rows = []
    for label, getter in specs:
        vals = {s: getter(results.get(s, {})) for s in _SCENARIO_ORDER}
        rows.append((label, vals))
    return rows


def render_dcf_summary(results: dict) -> None:
    st.markdown(
        '<div class="nv-section-title">DCF summary · all scenarios</div>'
        '<div class="nv-section-sub">Forecast-period totals · EV bridge · implied price</div>',
        unsafe_allow_html=True,
    )
    rows = _build_rows(results)
    header = "".join(
        f"<th>{'Metric' if i == 0 else _LABELS[s]}</th>"
        for i, s in enumerate([""] + list(_SCENARIO_ORDER))
    )
    body = ""
    for i, (label, vals) in enumerate(rows):
        is_last = i == len(rows) - 1
        metric_td = f'<td style="color:#0f1419;font-weight:{700 if is_last else 600}">{label}</td>'
        val_cells = (
            _cell(vals["base"], "td-base")
            + _cell(vals["upside"], "td-up")
            + _cell(vals["downside"], "td-dn")
        )
        body += f"<tr>{metric_td}{val_cells}</tr>"
    st.markdown(
        f'<div class="nv-dcf-wrap"><table class="nv-dcf-tbl">'
        f"<thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )
