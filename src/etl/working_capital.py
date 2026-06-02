"""
src/etl/working_capital.py
===========================
Canonical Table 3 builder — working_capital (ETL version)

Produces the working capital canonical table from BS + IS data.
Computes NWC components, DSO, DIO, DPO, and CCC.

IMPORTANT: This is the ETL version (src/etl/).
There is a separate working_capital.py in src/modeling/ which uses
assumptions to PROJECT working capital for forecast years.
This file handles HISTORICAL data only.

Rules (canonical_schema.md Table 3):
  - 1 row per fiscal year per scenario
  - change_in_nwc positive = NWC increase = cash outflow in FCFF
  - AR days = (AR / Revenue) × 365
  - Inventory days = (Inventory / COGS) × 365
  - AP days = (AP / COGS) × 365
  - CCC = DSO + DIO - DPO

Architecture slot: transformer.py calls this builder.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_working_capital(
    bs_df: pd.DataFrame,
    is_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build canonical working_capital table from BS and IS DataFrames.

    Args:
        bs_df: Cleaned, transformed BS DataFrame (canonical column names)
        is_df: Cleaned, transformed IS DataFrame (canonical column names)
               Needed for revenue_usdm and cogs_usdm references

    Returns:
        working_capital DataFrame sorted by fiscal_year ascending.
    """
    # ── 1. Start with key BS columns ───────────────────────────────────────
    wc_bs_cols = ["fiscal_year"]
    optional_bs = [
        "accounts_receivable_usdm",
        "inventory_usdm",
        "prepaid_expenses_usdm",
        "accounts_payable_usdm",
        "accrued_liabilities_usdm",
    ]
    for col in optional_bs:
        if col in bs_df.columns:
            wc_bs_cols.append(col)

    wc = bs_df[[c for c in wc_bs_cols if c in bs_df.columns]].copy()

    # ── 2. Merge IS reference columns (revenue + cogs for ratio calcs) ─────
    is_ref_cols = ["fiscal_year"]
    for col in ["revenue_usdm", "cogs_usdm"]:
        if col in is_df.columns:
            is_ref_cols.append(col)

    if len(is_ref_cols) > 1:
        wc = wc.merge(is_df[is_ref_cols], on="fiscal_year", how="left")

    # ── 3. Fill missing WC components with 0 (NVIDIA is fabless) ──────────
    ar = wc.get("accounts_receivable_usdm", pd.Series(float("nan"), index=wc.index))
    inv = wc.get("inventory_usdm", pd.Series(0.0, index=wc.index)).fillna(0)
    pre = wc.get("prepaid_expenses_usdm", pd.Series(0.0, index=wc.index)).fillna(0)
    ap = wc.get("accounts_payable_usdm", pd.Series(float("nan"), index=wc.index))
    acc = wc.get("accrued_liabilities_usdm", pd.Series(0.0, index=wc.index)).fillna(0)

    # ── 4. NWC aggregates ──────────────────────────────────────────────────
    wc["nwc_assets_usdm"] = ar.fillna(0) + inv + pre
    wc["nwc_liabilities_usdm"] = ap.fillna(0) + acc
    wc["net_working_capital_usdm"] = wc["nwc_assets_usdm"] - wc["nwc_liabilities_usdm"]

    # change_in_nwc = NWC(t) - NWC(t-1)
    # Positive = NWC increased = cash outflow (sign convention per data_contracts.md)
    wc["change_in_nwc_usdm"] = wc["net_working_capital_usdm"].diff()

    # ── 5. Turnover ratios ─────────────────────────────────────────────────
    rev = wc.get("revenue_usdm")
    cogs = wc.get("cogs_usdm")

    if rev is not None:
        rev_safe = rev.replace(0, float("nan"))
        wc["ar_days_dso"] = (ar / rev_safe * 365).round(1)
    else:
        wc["ar_days_dso"] = float("nan")

    if cogs is not None:
        cogs_safe = cogs.replace(0, float("nan"))
        wc["inventory_days_dio"] = (inv / cogs_safe * 365).round(1)
        wc["ap_days_dpo"] = (ap / cogs_safe * 365).round(1)
    else:
        wc["inventory_days_dio"] = float("nan")
        wc["ap_days_dpo"] = float("nan")

    # CCC = DSO + DIO - DPO
    dso = wc.get("ar_days_dso", pd.Series(float("nan"), index=wc.index))
    dio = wc.get("inventory_days_dio", pd.Series(float("nan"), index=wc.index))
    dpo = wc.get("ap_days_dpo", pd.Series(float("nan"), index=wc.index))
    wc["cash_conversion_cycle"] = dso + dio - dpo

    # ── 6. Metadata columns ────────────────────────────────────────────────
    if "ticker" not in wc.columns:
        wc.insert(1, "ticker", "NVDA")
    wc["is_forecast"] = False
    wc["scenario"] = "base"
    wc["source"] = "10-K (EDGAR)"

    # ── 7. Sort and reset ──────────────────────────────────────────────────
    wc = wc.sort_values("fiscal_year").reset_index(drop=True)

    logger.info(
        "[working_capital] Final table: %d rows × %d cols | FY%s–FY%s",
        len(wc),
        len(wc.columns),
        wc["fiscal_year"].min(),
        wc["fiscal_year"].max(),
    )
    return wc
