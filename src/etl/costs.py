"""
src/etl/costs.py
=================
Canonical Table 2 builder — costs

Produces the IS cost structure canonical table from the transformed
income statement DataFrame.

Rules (canonical_schema.md Table 2):
  - 1 row per fiscal year per scenario
  - No aggregation — direct pass-through of IS line items
  - Constraints enforced here:
      gross_profit = revenue - cogs
      ebit = gross_profit - total_opex
      ebitda = ebit + da

Architecture slot: transformer.py calls this builder.
No projection logic — historical actuals only.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Canonical columns for the costs table (canonical_schema.md Table 2)
_COSTS_COLS = [
    "fiscal_year",
    "ticker",
    "revenue_usdm",
    "cogs_usdm",
    "gross_profit_usdm",
    "gross_margin_pct",
    "rd_expense_usdm",
    "sga_expense_usdm",
    "acq_termination_usdm",
    "total_opex_usdm",
    "ebit_usdm",
    "ebit_margin_pct",
    "da_usdm",
    "ebitda_usdm",
    "ebitda_margin_pct",
    "interest_income_usdm",
    "interest_expense_usdm",
    "other_net_usdm",
    "ebt_usdm",
    "income_tax_usdm",
    "effective_tax_rate_pct",
    "net_income_usdm",
    "net_margin_pct",
    "is_forecast",
    "scenario",
    "source",
]


def build_costs(is_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the canonical costs table from a transformed IS DataFrame.

    Selects the relevant IS columns, enforces arithmetic constraints
    where columns are derivable, and validates metadata.

    Args:
        is_df: Cleaned, transformed IS DataFrame with canonical column names.

    Returns:
        costs DataFrame sorted by fiscal_year ascending.
    """
    # ── 1. Select available canonical columns ──────────────────────────────
    keep = [c for c in _COSTS_COLS if c in is_df.columns]
    costs = is_df[keep].copy()

    # ── 2. Derive missing columns where possible ───────────────────────────

    # gross_profit = revenue - cogs
    if "gross_profit_usdm" not in costs.columns:
        if "revenue_usdm" in costs.columns and "cogs_usdm" in costs.columns:
            costs["gross_profit_usdm"] = costs["revenue_usdm"] - costs["cogs_usdm"]
            logger.info("[costs] Derived gross_profit_usdm from revenue - cogs")

    # total_opex = rd + sga + acq_termination
    if "total_opex_usdm" not in costs.columns:
        rd = costs.get("rd_expense_usdm", pd.Series(0, index=costs.index)).fillna(0)
        sga = costs.get("sga_expense_usdm", pd.Series(0, index=costs.index)).fillna(0)
        acq = costs.get("acq_termination_usdm", pd.Series(0, index=costs.index)).fillna(
            0
        )
        costs["total_opex_usdm"] = rd + sga + acq
        logger.info("[costs] Derived total_opex_usdm from rd + sga + acq_termination")

    # ebit = gross_profit - total_opex
    if "ebit_usdm" not in costs.columns:
        if "gross_profit_usdm" in costs.columns and "total_opex_usdm" in costs.columns:
            costs["ebit_usdm"] = costs["gross_profit_usdm"] - costs["total_opex_usdm"]
            logger.info("[costs] Derived ebit_usdm from gross_profit - total_opex")

    # ebitda = ebit + da
    if "ebitda_usdm" not in costs.columns:
        if "ebit_usdm" in costs.columns and "da_usdm" in costs.columns:
            costs["ebitda_usdm"] = costs["ebit_usdm"] + costs["da_usdm"].fillna(0)
            logger.info("[costs] Derived ebitda_usdm from ebit + da")

    # Derived margin ratios
    rev = costs.get("revenue_usdm")
    if rev is not None:
        _zero_safe = rev.replace(0, float("nan"))
        if (
            "gross_margin_pct" not in costs.columns
            and "gross_profit_usdm" in costs.columns
        ):
            costs["gross_margin_pct"] = costs["gross_profit_usdm"] / _zero_safe
        if "ebit_margin_pct" not in costs.columns and "ebit_usdm" in costs.columns:
            costs["ebit_margin_pct"] = costs["ebit_usdm"] / _zero_safe
        if "ebitda_margin_pct" not in costs.columns and "ebitda_usdm" in costs.columns:
            costs["ebitda_margin_pct"] = costs["ebitda_usdm"] / _zero_safe
        if "net_margin_pct" not in costs.columns and "net_income_usdm" in costs.columns:
            costs["net_margin_pct"] = costs["net_income_usdm"] / _zero_safe
        if "rd_pct_revenue" not in costs.columns and "rd_expense_usdm" in costs.columns:
            costs["rd_pct_revenue"] = costs["rd_expense_usdm"] / _zero_safe

    # effective_tax_rate = income_tax / ebt
    if "effective_tax_rate_pct" not in costs.columns:
        if "income_tax_usdm" in costs.columns and "ebt_usdm" in costs.columns:
            ebt_safe = costs["ebt_usdm"].replace(0, float("nan"))
            costs["effective_tax_rate_pct"] = costs["income_tax_usdm"] / ebt_safe

    # ── 3. Ensure metadata columns ─────────────────────────────────────────
    if "ticker" not in costs.columns:
        costs.insert(1, "ticker", "NVDA")
    if "is_forecast" not in costs.columns:
        costs["is_forecast"] = False
    if "scenario" not in costs.columns:
        costs["scenario"] = "base"
    if "source" not in costs.columns:
        costs["source"] = "10-K (EDGAR)"

    # ── 4. Sort and reset ──────────────────────────────────────────────────
    costs = costs.sort_values("fiscal_year").reset_index(drop=True)

    logger.info(
        "[costs] Final table: %d rows × %d cols | FY%s–FY%s",
        len(costs),
        len(costs.columns),
        costs["fiscal_year"].min(),
        costs["fiscal_year"].max(),
    )
    return costs
