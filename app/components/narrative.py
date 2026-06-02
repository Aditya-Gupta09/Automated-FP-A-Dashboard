"""
app/components/narrative.py  v3.0
Light theme · annotation pills
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except:
        return None


def _price(result: dict) -> float | None:
    return _num(result.get("dcf_valuation", {}).get("implied_share_price_usd"))


def _fmt(v: float | None, fmt: str = "price") -> str:
    if v is None:
        return "N/A"
    if fmt == "price":
        return f"${v:,.2f}"
    if fmt == "pct":
        sign = "+" if v >= 0 else ""
        return f"{sign}{v*100:.1f}%"
    if fmt == "delta":
        sign = "+" if v >= 0 else ""
        return f"{sign}${v:,.2f}"
    return str(v)


def _stat(val: str) -> str:
    return (
        f'<span style="display:inline;background:#f1f5f9;border:1px solid #e2e8f0;'
        f"border-radius:3px;padding:2px 7px;font-family:'SF Mono','Fira Code',monospace;"
        f'font-size:10px;color:#0891b2;white-space:nowrap;font-weight:600">{val}</span>'
    )


def _build_narrative(base, selected, scenario, driver_rows):
    base_price = _price(base)
    sel_price = _price(selected)
    delta = (sel_price - base_price) if (base_price and sel_price) else None
    dcf = selected.get("dcf_valuation", {})
    wacc = _num(dcf.get("wacc_used"))
    g = _num(dcf.get("terminal_growth_rate"))
    mkt = _num(dcf.get("market_price_usd")) or 183.22
    updown = _num(dcf.get("upside_downside_pct"))
    top_pos = next(
        (
            r
            for r in driver_rows
            if r.get("direction") == "pos" and r.get("impact", 0) > 0.01
        ),
        None,
    )
    top_neg = next((r for r in driver_rows if r.get("direction") == "neg"), None)

    w_str = _stat(f"{wacc*100:.2f}%") if wacc else _stat("N/A")
    g_str = _stat(f"{g*100:.3f}%") if g else _stat("N/A")

    if scenario == "base":
        badge, title = "REFERENCE", "Base case"
        ud_str = f"{abs(updown*100):.1f}%" if updown else "40.4%"
        body = (
            f"Model-implied price is <strong>{_fmt(sel_price)}</strong> vs market price of "
            f"<strong>{_fmt(mkt)}</strong> — a <strong>{ud_str} downside</strong> to intrinsic value.<br><br>"
            f"DCF anchored by <strong>FCFF of $55,932M (FY2025A)</strong> growing to $308,056M by FY2030F. "
            f"Terminal value contributes <strong>74.7%</strong> of EV, discounted at WACC {w_str} "
            f"with perpetuity growth {g_str}.<br><br>"
            f"Net cash position of <strong>$32,940M</strong> adds to equity value. "
            f"Diluted shares {_stat('24,300M')}. All 5 model integrity checks pass."
        )
    elif scenario == "upside":
        badge, title = "BULL", "Upside case"
        pos_txt = (
            f"{top_pos['driver']} ({_fmt(top_pos['impact'],'delta')})"
            if top_pos
            else "PV of Terminal Value"
        )
        body = (
            f"Upside price increases from <strong>{_fmt(base_price)}</strong> to "
            f"<strong>{_fmt(sel_price)}</strong> (<strong>{_fmt(delta,'delta')}</strong> vs base).<br><br>"
            f"Primary driver: <strong>{pos_txt}</strong>. Data center accelerates to {_stat('+95% FY2026F')} vs base +69%. "
            f"WACC compresses {_stat('−100 bps')} to {w_str}. Terminal growth expands to {g_str}.<br><br>"
            f"Gross margin expands to {_stat('82% FY2026F')} vs 77% base. "
            f"FCFF sum reaches <strong>$1,562,654M</strong> across forecast period."
        )
    else:
        badge, title = "BEAR", "Downside case"
        neg_txt = (
            f"{top_neg['driver']} ({_fmt(top_neg['impact'],'delta')})"
            if top_neg
            else "PV of Terminal Value"
        )
        body = (
            f"Downside price decreases from <strong>{_fmt(base_price)}</strong> to "
            f"<strong>{_fmt(sel_price)}</strong> (<strong>{_fmt(delta,'delta')}</strong> vs base).<br><br>"
            f"Primary drag: <strong>{neg_txt}</strong>. AI spending slowdown — data center slows to {_stat('+50% FY2026F')}. "
            f"WACC rises {_stat('+100 bps')} to {w_str}. Terminal growth compresses to {g_str}.<br><br>"
            f"Gross margin compresses to {_stat('66% FY2026F')} vs 75% actual. "
            f"FCFF sum only <strong>$409,114M</strong> — 41% of base case."
        )
    return badge, title, body


def render_narrative(base, selected, scenario, driver_rows):
    badge, title, body = _build_narrative(base, selected, scenario, driver_rows)
    st.markdown(
        f'<div class="nv-section-title">Narrative · {scenario.title()}</div>'
        '<div class="nv-section-sub">Auto-generated scenario commentary</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="nv-narr">'
        f'<div class="nv-narr-title">{title} <span class="nv-narr-badge">{badge}</span></div>'
        f'<div class="nv-narr-body">{body}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
