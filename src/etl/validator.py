"""
validator.py — Task 3: Duplicate Handling + Schema Validation
=============================================================
Three responsibilities:
  1. Schema validation — required columns present, correct dtypes
  2. Duplicate detection and resolution (Task 3)
  3. Business-rule validation — BS balance, CF reconciliation (from data_contracts.md)

All errors flow through error_logger → error_report.csv (Task 5).
Architecture slot: loader → [VALIDATOR] → cleaner → transformer → canonical
"""

import pandas as pd
import logging
from src.utils.error_logger import log_error

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — DUPLICATE HANDLING POLICY
# ══════════════════════════════════════════════════════════════════════════════
#
# Detection key: ("fiscal_year",) for annual statements
#                ("fiscal_year", "segment", "scenario") for segment revenue
# Resolution:   RAISE — duplicate rows in financial statements = data error,
#               not a noise problem. Silent drops would hide source issues.
#
# The only exception is if rows are byte-for-byte identical (exact duplicates
# from export bugs) — those are safely deduplicated after logging.
# ══════════════════════════════════════════════════════════════════════════════

DUPLICATE_KEY_IS = ["fiscal_year"]
DUPLICATE_KEY_BS = ["fiscal_year"]
DUPLICATE_KEY_CF = ["fiscal_year"]
DUPLICATE_KEY_SEG = ["fiscal_year", "segment", "scenario"]


def check_duplicates(
    df: pd.DataFrame,
    key_cols: list[str],
    source_label: str = "",
    raise_on_conflict: bool = True,
) -> pd.DataFrame:
    """
    Detect and handle duplicate rows.

    Strategy:
    - Exact duplicates (all columns identical): deduplicate silently + log
    - Conflicting duplicates (same key, different values): raise ValueError

    Args:
        df: DataFrame to check.
        key_cols: Columns that define uniqueness (e.g. ["fiscal_year"]).
        source_label: For log messages.
        raise_on_conflict: If True, raise on conflicting dupes. If False, keep_last.

    Returns:
        DataFrame with exact duplicates removed.

    Raises:
        ValueError: If conflicting duplicates found and raise_on_conflict=True.
    """
    # Guard: key columns must exist
    missing_keys = [k for k in key_cols if k not in df.columns]
    if missing_keys:
        raise ValueError(
            f"[validator] {source_label} — duplicate key column(s) not found: {missing_keys}"
        )

    # Step 1: Exact duplicates (all columns match) — safe to drop
    exact_dupes = df.duplicated(keep="first")
    if exact_dupes.any():
        count = exact_dupes.sum()
        dup_vals = df[exact_dupes][key_cols].to_dict(orient="records")
        log_error(
            row=str(dup_vals),
            col=str(key_cols),
            err="EXACT_DUPLICATE_ROWS",
            val=f"{count} exact duplicate row(s)",
            action="deduplicated_keep_first",
        )
        logger.warning(
            "[validator] %s — removed %d exact duplicate row(s) at keys: %s",
            source_label,
            count,
            dup_vals,
        )
        df = df[~exact_dupes].copy()

    # Step 2: Conflicting duplicates (same key, different values)
    conflict_mask = df.duplicated(subset=key_cols, keep=False)
    if conflict_mask.any():
        conflict_df = df[conflict_mask]
        dup_keys = df[df.duplicated(subset=key_cols, keep="first")][key_cols].to_dict(
            orient="records"
        )

        log_error(
            row=str(dup_keys),
            col=str(key_cols),
            err="CONFLICTING_DUPLICATE_ROWS",
            val=f"{len(dup_keys)} conflicting duplicate key(s)",
            action="raised_ValueError" if raise_on_conflict else "kept_last",
        )

        if raise_on_conflict:
            raise ValueError(
                f"[validator] DUPLICATE ERROR in {source_label}: "
                f"Conflicting rows found for key(s) {key_cols}. "
                f"Affected records: {dup_keys}. "
                f"Fix the source data — do NOT silently overwrite."
            )
        else:
            logger.warning(
                "[validator] %s — keeping last of %d conflicting duplicate(s) at: %s",
                source_label,
                len(dup_keys),
                dup_keys,
            )
            df = df.drop_duplicates(subset=key_cols, keep="last").copy()

    return df


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION
# Required columns per canonical_schema.md and model_input_schema.json
# ══════════════════════════════════════════════════════════════════════════════

REQUIRED_IS_COLS = [
    "fiscal_year",
    "ticker",
    "revenue_usdm",
    "cogs_usdm",
    "gross_profit_usdm",
    "rd_expense_usdm",
    "sga_expense_usdm",
    "total_opex_usdm",
    "ebit_usdm",
    "ebt_usdm",
    "net_income_usdm",
]

REQUIRED_BS_COLS = [
    "fiscal_year",
    "ticker",
    "total_assets_usdm",
    "total_liabilities_usdm",
    "shareholders_equity_usdm",
    "cash_and_investments_usdm",
    "accounts_receivable_usdm",
    "accounts_payable_usdm",
]

REQUIRED_CF_COLS = [
    "fiscal_year",
    "ticker",
    # cfo/cfi/cff intentionally NOT required here — FY2020-21 absent per architecture.md
]

REQUIRED_ACTUALS_COLS = [
    "fiscal_year",
    "ticker",
    "revenue_usdm",
    "cogs_usdm",
    "gross_profit_usdm",
    "ebit_usdm",
    "net_income_usdm",
    "total_assets_usdm",
    "total_liabilities_usdm",
    "shareholders_equity_usdm",
]


def validate_schema(
    df: pd.DataFrame, required_cols: list[str], source_label: str = ""
) -> None:
    """
    Assert all required columns are present.
    Raises ValueError with full list of missing columns.
    """
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        for col in missing:
            log_error(
                row=None,
                col=col,
                err="MISSING_REQUIRED_COLUMN",
                val="column absent from DataFrame",
                action="raised_ValueError",
            )
        raise ValueError(
            f"[validator] {source_label} — Missing required column(s): {missing}"
        )
    logger.info(
        "[validator] %s — schema OK (%d required cols present)",
        source_label,
        len(required_cols),
    )


def validate_dtypes(df: pd.DataFrame, source_label: str = "") -> None:
    """
    Verify numeric columns are actually numeric (not object/string).
    Logs a warning per offending column — does not raise.
    """
    skip = {"ticker", "is_forecast", "scenario", "source", "data_date", "notes"}
    for col in df.columns:
        if col in skip:
            continue
        if col == "fiscal_year":
            continue
        if df[col].dtype == object:
            log_error(
                row=None,
                col=col,
                err="WRONG_DTYPE",
                val=f"dtype={df[col].dtype}",
                action="warning_issued — coerce in cleaner",
            )
            logger.warning(
                "[validator] %s.%s — dtype is object, expected numeric",
                source_label,
                col,
            )


# ══════════════════════════════════════════════════════════════════════════════
# BUSINESS RULE VALIDATION (data_contracts.md rules)
# ══════════════════════════════════════════════════════════════════════════════

BS_TOLERANCE = 0.01  # $0.01M per data_contracts.md Rule 2
CF_TOLERANCE = 0.01  # $0.01M per data_contracts.md Rule 3


def validate_bs_balance(df: pd.DataFrame, source_label: str = "BS") -> None:
    """
    Rule 2 (data_contracts.md): Total Assets == Total Liabilities + Equity
    Tolerance: $0.01M.
    """
    needed = ["total_assets_usdm", "total_liabilities_usdm", "shareholders_equity_usdm"]
    if not set(needed).issubset(df.columns):
        logger.warning(
            "[validator] %s — cannot check BS balance, missing columns", source_label
        )
        return

    df = df.copy()
    df["_bs_check"] = (
        df["total_assets_usdm"]
        - df["total_liabilities_usdm"]
        - df["shareholders_equity_usdm"]
    ).abs()

    failures = df[df["_bs_check"] > BS_TOLERANCE]
    if not failures.empty:
        for _, row in failures.iterrows():
            log_error(
                row=str(row.get("fiscal_year", "?")),
                col="total_assets_usdm / total_liabilities_usdm / shareholders_equity_usdm",
                err="BS_BALANCE_FAIL",
                val=f"delta={row['_bs_check']:.4f}M",
                action="warning_issued",
            )
            logger.warning(
                "[validator] %s FY%s — BS out of balance by $%.2fM",
                source_label,
                row.get("fiscal_year", "?"),
                row["_bs_check"],
            )
    else:
        logger.info(
            "[validator] %s — BS balance check PASSED for all rows", source_label
        )


def validate_cf_reconciliation(df: pd.DataFrame, source_label: str = "CF") -> None:
    """
    Rule 3 (data_contracts.md): CFO + CFI + CFF == Net Change in Cash
    Tolerance: $0.01M. Skips rows where any component is NaN (FY2020-21).
    """
    needed = ["cfo_usdm", "cfi_usdm", "cff_usdm", "net_change_cash_usdm"]
    if not set(needed).issubset(df.columns):
        logger.warning(
            "[validator] %s — cannot check CF reconciliation, missing columns",
            source_label,
        )
        return

    check_df = df[needed].dropna()  # Skip rows with NaN (FY2020-21 by design)
    if check_df.empty:
        return

    delta = (
        check_df["cfo_usdm"]
        + check_df["cfi_usdm"]
        + check_df["cff_usdm"]
        - check_df["net_change_cash_usdm"]
    ).abs()

    failures = delta[delta > CF_TOLERANCE]
    if not failures.empty:
        for idx in failures.index:
            fy = df.loc[idx, "fiscal_year"] if "fiscal_year" in df.columns else idx
            log_error(
                row=str(fy),
                col="cfo_usdm + cfi_usdm + cff_usdm vs net_change_cash_usdm",
                err="CF_RECONCILIATION_FAIL",
                val=f"delta={failures[idx]:.4f}M",
                action="warning_issued",
            )
            logger.warning(
                "[validator] CF FY%s — reconciliation off by $%.2fM", fy, failures[idx]
            )
    else:
        logger.info(
            "[validator] %s — CF reconciliation PASSED for all non-null rows",
            source_label,
        )


def validate_revenue_crosscheck(is_df: pd.DataFrame, actuals_df: pd.DataFrame) -> None:
    """
    Rule 4 (data_contracts.md): Revenue in IS must match revenue in actuals/FCFF.
    """
    if "revenue_usdm" not in is_df.columns or "revenue_usdm" not in actuals_df.columns:
        return
    if "fiscal_year" not in is_df.columns or "fiscal_year" not in actuals_df.columns:
        return

    merged = is_df[["fiscal_year", "revenue_usdm"]].merge(
        actuals_df[["fiscal_year", "revenue_usdm"]],
        on="fiscal_year",
        suffixes=("_is", "_actuals"),
    )
    delta = (merged["revenue_usdm_is"] - merged["revenue_usdm_actuals"]).abs()
    fails = merged[delta > 0.01]
    if not fails.empty:
        for _, row in fails.iterrows():
            log_error(
                row=str(row["fiscal_year"]),
                col="revenue_usdm",
                err="REVENUE_CROSSCHECK_FAIL",
                val=f"IS={row['revenue_usdm_is']}, actuals={row['revenue_usdm_actuals']}",
                action="warning_issued",
            )
            logger.warning(
                "[validator] Revenue mismatch FY%s: IS=%.2f vs actuals=%.2f",
                row["fiscal_year"],
                row["revenue_usdm_is"],
                row["revenue_usdm_actuals"],
            )
    else:
        logger.info("[validator] Revenue cross-check PASSED")


# ── Convenience wrappers ──────────────────────────────────────────────────────


def validate_is(df: pd.DataFrame) -> pd.DataFrame:
    check_duplicates(df, DUPLICATE_KEY_IS, source_label="IS")
    validate_schema(df, REQUIRED_IS_COLS, source_label="IS")
    validate_dtypes(df, source_label="IS")
    return df


def validate_bs(df: pd.DataFrame) -> pd.DataFrame:
    check_duplicates(df, DUPLICATE_KEY_BS, source_label="BS")
    validate_schema(df, REQUIRED_BS_COLS, source_label="BS")
    validate_dtypes(df, source_label="BS")
    validate_bs_balance(df)
    return df


def validate_cf(df: pd.DataFrame) -> pd.DataFrame:
    check_duplicates(df, DUPLICATE_KEY_CF, source_label="CF")
    validate_schema(df, REQUIRED_CF_COLS, source_label="CF")
    validate_dtypes(df, source_label="CF")
    validate_cf_reconciliation(df)
    return df


def validate_actuals(df: pd.DataFrame) -> pd.DataFrame:
    check_duplicates(df, ["fiscal_year"], source_label="actuals")
    validate_schema(df, REQUIRED_ACTUALS_COLS, source_label="actuals")
    validate_dtypes(df, source_label="actuals")
    validate_bs_balance(df)
    return df
