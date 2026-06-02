"""
pipeline.py — ETL Orchestrator
================================
Runs the full ETL pipeline:
  data/raw → loader → validator → cleaner → transformer → data/canonical

Produces:
  data/canonical/actuals.parquet
  data/canonical/costs.parquet
  data/canonical/working_capital.parquet
  data/processed/error_report.csv   ← ALWAYS generated (Task 5)

This is the single entry point for the ETL layer.
Call run_etl() from run_all.py or standalone.

SahilBuran concept applied: modular pipeline with clear stage separation.
Each stage receives a DataFrame and returns a DataFrame — no side effects
except error_logger accumulation and final file writes.
"""

import json
import logging
import os
from datetime import datetime

import pandas as pd

from src.etl.loader import load_historical_bs, load_historical_cf, load_historical_is
from src.etl.validator import (
    validate_is,
    validate_bs,
    validate_cf,
    validate_actuals,
    validate_revenue_crosscheck,
)
from src.etl.cleaner import clean_is, clean_bs, clean_cf
from src.etl.transformer import (
    transform_is,
    transform_bs,
    transform_cf,
    derive_is_ratios,
)
from src.utils.error_logger import (
    reset_errors,
    save_error_report,
    error_summary,
    log_error,
)

logger = logging.getLogger(__name__)

CANONICAL_DIR = "data/canonical"
PROCESSED_DIR = "data/processed"
OUTPUTS_DIR = "outputs"
LOGS_DIR = "logs"


def _ensure_dirs() -> None:
    os.makedirs(CANONICAL_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def _save_canonical(df: pd.DataFrame, name: str) -> str:
    """Save canonical table as parquet (type-safe) per canonical_schema.md."""
    path = os.path.join(CANONICAL_DIR, f"{name}.parquet")
    df.to_parquet(path, index=False)
    logger.info(
        "[pipeline] Saved canonical/%s.parquet (%d rows × %d cols)",
        name,
        len(df),
        len(df.columns),
    )
    return path


def _save_canonical_csv(df: pd.DataFrame, name: str) -> str:
    """Also save a CSV copy for human inspection."""
    path = os.path.join(CANONICAL_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    return path


def run_etl(save_parquet: bool = True, save_csv: bool = True) -> dict:
    """
    Execute the full ETL pipeline.

    Returns:
        dict with keys: actuals, costs, working_capital, error_report_path,
                        error_summary, duration_seconds, status
    """
    start = datetime.utcnow()
    reset_errors()  # Start fresh — clear any previous run errors
    _ensure_dirs()

    logger.info("=" * 60)
    logger.info("[pipeline] ETL run started at %s", start.isoformat())
    logger.info("=" * 60)

    status = "success"
    canonical_tables = {}

    try:
        # ══════════════════════════════════════════════════════════
        # STAGE 1 — LOAD
        # ══════════════════════════════════════════════════════════
        logger.info("[pipeline] Stage 1: Loading raw files...")
        raw_is = load_historical_is()
        raw_bs = load_historical_bs()
        raw_cf = load_historical_cf()
        raw_cf_has_cols = set(raw_cf.columns)

        # ══════════════════════════════════════════════════════════
        # STAGE 2 — TRANSFORM (column mapping first, before validation)
        # ══════════════════════════════════════════════════════════
        logger.info("[pipeline] Stage 2: Applying column mappings (transformer)...")
        mapped_is = transform_is(raw_is)
        mapped_bs = transform_bs(raw_bs)
        mapped_cf = transform_cf(raw_cf)

        # ══════════════════════════════════════════════════════════
        # STAGE 3 — VALIDATE
        # ══════════════════════════════════════════════════════════
        logger.info("[pipeline] Stage 3: Validating schema and duplicates...")
        validate_is(mapped_is)
        validate_bs(mapped_bs)
        validate_cf(mapped_cf)

        # ══════════════════════════════════════════════════════════
        # STAGE 4 — CLEAN (missing value policy)
        # ══════════════════════════════════════════════════════════
        logger.info("[pipeline] Stage 4: Applying missing value policy (cleaner)...")
        clean_is_df = clean_is(mapped_is)
        clean_bs_df = clean_bs(mapped_bs)
        clean_cf_df = clean_cf(mapped_cf)

        # ══════════════════════════════════════════════════════════
        # STAGE 5 — DERIVE RATIOS
        # ══════════════════════════════════════════════════════════
        logger.info("[pipeline] Stage 5: Deriving IS ratios...")
        clean_is_df = derive_is_ratios(clean_is_df)

        # ══════════════════════════════════════════════════════════
        # STAGE 6 — BUILD CANONICAL TABLES
        # ══════════════════════════════════════════════════════════
        logger.info("[pipeline] Stage 6: Building canonical tables...")

        # ── Table: costs (from IS) ────────────────────────────────
        costs = clean_is_df.copy()
        canonical_tables["costs"] = costs

        # ── Table: actuals (IS + BS + CF merged on fiscal_year) ──
        actuals = _build_actuals(clean_is_df, clean_bs_df, clean_cf_df)
        validate_actuals(actuals)
        canonical_tables["actuals"] = actuals

        # ── Table: working_capital (from BS) ─────────────────────
        wc = _build_working_capital(clean_bs_df, clean_is_df)
        canonical_tables["working_capital"] = wc

        # ── Cross-check revenue IS vs actuals ────────────────────
        validate_revenue_crosscheck(clean_is_df, actuals)

        # ══════════════════════════════════════════════════════════
        # STAGE 7 — PERSIST
        # ══════════════════════════════════════════════════════════
        logger.info("[pipeline] Stage 7: Persisting canonical tables...")
        output_paths = {}
        for name, df in canonical_tables.items():
            if save_parquet:
                output_paths[f"{name}_parquet"] = _save_canonical(df, name)
            if save_csv:
                output_paths[f"{name}_csv"] = _save_canonical_csv(df, name)

    except Exception as exc:
        status = "failed"
        log_error(
            row=None,
            col="pipeline",
            err="PIPELINE_EXCEPTION",
            val=str(exc),
            action="pipeline_aborted",
        )
        logger.error("[pipeline] ETL FAILED: %s", exc)
        raise

    finally:
        # ── ALWAYS write error_report.csv — even on failure ──────
        error_report_path = save_error_report(
            os.path.join(PROCESSED_DIR, "error_report.csv")
        )
        summary = error_summary()
        duration = (datetime.utcnow() - start).total_seconds()

        # Write pipeline summary
        pipeline_summary = {
            "run_timestamp": start.isoformat(),
            "status": status,
            "duration_seconds": round(duration, 2),
            "error_summary": summary,
            "tables_produced": list(canonical_tables.keys()),
            "error_report": error_report_path,
        }
        summary_path = os.path.join(PROCESSED_DIR, "etl_pipeline_summary.json")
        with open(summary_path, "w") as f:
            json.dump(pipeline_summary, f, indent=2)

        logger.info(
            "[pipeline] ETL %s in %.2fs | %d issue(s) logged",
            status.upper(),
            duration,
            summary["total"],
        )
        logger.info("[pipeline] error_report → %s", error_report_path)
        logger.info("[pipeline] summary      → %s", summary_path)

    return {
        **canonical_tables,
        "error_report_path": error_report_path,
        "error_summary": summary,
        "status": status,
        "duration_seconds": duration,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CANONICAL TABLE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════


def _build_actuals(
    is_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge IS + BS + CF into Table 4 (actuals) per canonical_schema.md.
    IS is the spine (all FY2020-2025). BS adds balance sheet cols.
    CF adds cash flow cols (NaN for FY2020-21 is valid per architecture.md).
    """
    # IS columns to keep
    is_cols = [
        c for c in is_df.columns if c not in ("is_forecast", "scenario", "source")
    ]
    actuals = is_df[is_cols].copy()

    # BS columns to merge in (drop dupes of IS cols except fiscal_year)
    bs_merge_cols = ["fiscal_year"] + [
        c
        for c in bs_df.columns
        if c not in actuals.columns
        and c not in ("is_forecast", "scenario", "source", "ticker")
    ]
    actuals = actuals.merge(bs_df[bs_merge_cols], on="fiscal_year", how="left")

    # CF columns to merge in
    cf_merge_cols = ["fiscal_year"] + [
        c
        for c in cf_df.columns
        if c not in actuals.columns
        and c not in ("is_forecast", "scenario", "source", "ticker")
    ]
    actuals = actuals.merge(cf_df[cf_merge_cols], on="fiscal_year", how="left")

    # Enforce canonical metadata
    actuals["is_forecast"] = False
    actuals["scenario"] = "base"
    actuals["source"] = "10-K (EDGAR)"
    actuals["ticker"] = "NVDA"

    actuals = actuals.sort_values("fiscal_year").reset_index(drop=True)
    return actuals


def _build_working_capital(bs_df: pd.DataFrame, is_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build Table 3 (working_capital) from BS + IS per canonical_schema.md.
    Computes NWC components, DSO, DIO, DPO, CCC.
    """
    wc_cols = [
        "fiscal_year",
        "accounts_receivable_usdm",
        "inventory_usdm",
        "accounts_payable_usdm",
    ]
    optional_bs = ["prepaid_expenses_usdm", "accrued_liabilities_usdm"]

    available = [c for c in wc_cols if c in bs_df.columns]
    for c in optional_bs:
        if c in bs_df.columns:
            available.append(c)

    wc = bs_df[available].copy()

    # Merge in IS for revenue and COGS (needed for DSO/DIO/DPO)
    is_needed = ["fiscal_year"] + [
        c for c in ["revenue_usdm", "cogs_usdm"] if c in is_df.columns
    ]
    wc = wc.merge(is_df[is_needed], on="fiscal_year", how="left")

    # NWC calculations
    ar = wc.get("accounts_receivable_usdm", pd.Series(0, index=wc.index))
    inv = wc.get("inventory_usdm", pd.Series(0, index=wc.index))
    pre = wc.get("prepaid_expenses_usdm", pd.Series(0, index=wc.index))
    ap = wc.get("accounts_payable_usdm", pd.Series(0, index=wc.index))
    acc = wc.get("accrued_liabilities_usdm", pd.Series(0, index=wc.index))

    wc["nwc_assets_usdm"] = ar + inv + pre
    wc["nwc_liabilities_usdm"] = ap + acc
    wc["net_working_capital_usdm"] = wc["nwc_assets_usdm"] - wc["nwc_liabilities_usdm"]
    wc["change_in_nwc_usdm"] = wc["net_working_capital_usdm"].diff()

    # Turnover ratios (DSO/DIO/DPO/CCC)
    rev = wc.get("revenue_usdm")
    cogs = wc.get("cogs_usdm")

    if rev is not None:
        wc["ar_days_dso"] = (ar / rev * 365).round(1)
    if cogs is not None:
        wc["inventory_days_dio"] = (inv / cogs * 365).round(1)
        wc["ap_days_dpo"] = (ap / cogs * 365).round(1)
    if (
        "ar_days_dso" in wc.columns
        and "inventory_days_dio" in wc.columns
        and "ap_days_dpo" in wc.columns
    ):
        wc["cash_conversion_cycle"] = (
            wc["ar_days_dso"] + wc["inventory_days_dio"] - wc["ap_days_dpo"]
        )

    wc["ticker"] = "NVDA"
    wc["is_forecast"] = False
    wc["scenario"] = "base"
    wc["source"] = "10-K (EDGAR)"
    wc = wc.sort_values("fiscal_year").reset_index(drop=True)
    return wc
