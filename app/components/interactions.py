"""
app/components/interactions.py  v3.0
Light theme · scenario-aware filtering
"""

from __future__ import annotations

from typing import Any

import streamlit as st

_BASE_PRICE = 109.26


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except:
        return None


def _extract_interactions(result: dict, scenario: str) -> list[dict]:
    sens = result.get("dcf_valuation", {}).get("sensitivity")
    base_price = (
        _num(result.get("dcf_valuation", {}).get("implied_share_price_usd"))
        or _BASE_PRICE
    )

    if isinstance(sens, dict) and sens.get("implied_price"):
        price_grid = sens["implied_price"]
        rows = []
        for w, g_dict in price_grid.items():
            if not isinstance(g_dict, dict):
                continue
            for g, price in g_dict.items():
                p = _num(price)
                if p is None:
                    continue
                impact = p - base_price
                rows.append(
                    {
                        "label": f"WACC {float(w)*100:.1f}% × g {float(g)*100:.1f}%",
                        "price": p,
                        "impact": impact,
                        "direction": "pos" if impact >= 0 else "neg",
                    }
                )
        if rows:
            return _filter_and_rank(rows, scenario)

    return _fallback_interactions(scenario, base_price)


def _filter_and_rank(rows: list[dict], scenario: str) -> list[dict]:
    if scenario == "upside":
        filtered = [r for r in rows if r["impact"] >= 0]
        filtered.sort(key=lambda r: r["impact"], reverse=True)
    elif scenario == "downside":
        filtered = [r for r in rows if r["impact"] <= 0]
        filtered.sort(key=lambda r: r["impact"])
    else:
        filtered = sorted(rows, key=lambda r: abs(r["impact"]), reverse=True)

    top5 = filtered[:5] if filtered else rows[:5]
    max_abs = max(abs(r["impact"]) for r in top5) or 1
    for r in top5:
        r["pct"] = min(abs(r["impact"]) / max_abs * 92, 92)
    return top5


def _fallback_interactions(scenario: str, base_price: float) -> list[dict]:
    if scenario == "upside":
        data = [
            ("WACC 10.9% × g 6.0%", 192.17, "pos"),
            ("WACC 10.9% × g 5.5%", 176.33, "pos"),
            ("WACC 11.4% × g 6.0%", 173.73, "pos"),
            ("WACC 10.9% × g 5.0%", 163.18, "pos"),
            ("WACC 11.4% × g 5.5%", 160.81, "pos"),
        ]
    elif scenario == "downside":
        data = [
            ("WACC 14.9% × g 2.0%", 22.74, "neg"),
            ("WACC 14.9% × g 2.5%", 23.51, "neg"),
            ("WACC 14.4% × g 2.0%", 26.95, "neg"),
            ("WACC 14.9% × g 3.0%", 27.80, "neg"),
            ("WACC 14.4% × g 2.5%", 32.76, "neg"),
        ]
    else:
        data = [
            ("WACC 10.9% × g 6.0%", 192.17, "pos"),
            ("WACC 11.4% × g 6.0%", 173.73, "pos"),
            ("WACC 10.9% × g 5.5%", 176.33, "pos"),
            ("WACC 11.4% × g 5.5%", 160.81, "pos"),
            ("WACC 10.9% × g 5.0%", 163.18, "pos"),
        ]

    rows = []
    for label, price, direction in data:
        impact = price - base_price if direction == "pos" else price - base_price
        rows.append(
            {"label": label, "price": price, "impact": impact, "direction": direction}
        )

    max_abs = max(abs(r["impact"]) for r in rows) or 1
    for r in rows:
        r["pct"] = min(abs(r["impact"]) / max_abs * 92, 92)
    return rows


def render_interactions(result: dict, scenario: str) -> None:
    direction_label = {
        "base": "Top WACC × g combinations by impact magnitude",
        "upside": "Best bull WACC × g combinations (low WACC + high g)",
        "downside": "Worst bear WACC × g combinations (high WACC + low g)",
    }.get(scenario, "Top-5 combinations")

    st.markdown(
        f'<div class="nv-section-title">Interaction effects · {scenario.title()}</div>'
        f'<div class="nv-section-sub">{direction_label} · from 06_Sensitivity grid</div>',
        unsafe_allow_html=True,
    )

    rows = _extract_interactions(result, scenario)
    html = '<div class="nv-panel">'
    for r in rows:
        cls_bar = "nv-ib-p" if r["direction"] == "pos" else "nv-ib-n"
        sign = "+" if r["impact"] >= 0 else ""
        val_str = f"{sign}${r['impact']:,.2f}"
        html += (
            f'<div class="nv-irow">'
            f'<span class="nv-ilabel">{r["label"]}</span>'
            f'<div class="nv-ibar"><div class="{cls_bar}" style="width:{r["pct"]:.0f}%"></div></div>'
            f'<span class="nv-ival">{val_str}</span>'
            f"</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
