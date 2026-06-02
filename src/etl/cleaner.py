"""
cleaner.py — Task 2: Missing Value Policy
==========================================
Defines what to do when data is missing — field by field.
Every column has an explicit rule. No silent NaNs reach the model.

Policy rationale is documented inline for each decision.
Architecture slot: loader → validator → [CLEANER] → transformer → canonical
"""

import logging

import pandas as pd

from src.utils.error_logger import log_error

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — MISSING VALUE POLICY TABLE
# ══════════════════════════════════════════════════════════════════════════════
#
# Policy options:
#   "error"     → raise ValueError immediately — field is critical, no fallback
#   "zero"      → fill with 0 — field is structural zero for this business
#   "ffill"     → forward-fill from prior year — slowly changing balance items
#   "bfill"     → backward-fill — used for opening period values
#   "median"    → fill with column median — ratio/derived fields
#   "warn"      → allow NaN but emit warning — optional/supplemental fields
#   "ignore"    → NaN is valid (e.g. CF FY2020–2021 per architecture.md note)
#
# Format: { canonical_column_name: policy }
# ══════════════════════════════════════════════════════════════════════════════

MISSING_VALUE_POLICY: dict[str, str] = {
    # ── Identity columns — must always be present ──────────────────────────
    "fiscal_year": "error",  # No year = no row identity
    "ticker": "error",  # Must always be NVDA
    # ── IS: Critical P&L lines — model breaks without these ────────────────
    "revenue_usdm": "error",  # Core driver of entire model
    "cogs_usdm": "error",  # Required for gross profit
    "gross_profit_usdm": "error",  # Derived but validated
    "ebit_usdm": "error",  # Required for FCFF calculation
    "net_income_usdm": "error",  # Required for CF reconciliation
    # ── IS: OpEx lines — important but can warn if missing ─────────────────
    "rd_expense_usdm": "error",  # Key ratio for NVDA model
    "sga_expense_usdm": "error",  # Required for opex build
    "total_opex_usdm": "error",  # Sum of above two
    "acq_termination_usdm": "zero",  # One-time item; 0 in most years
    "ebitda_usdm": "warn",  # Derivable from ebit + da
    "da_usdm": "warn",  # Present FY2020+; warn if missing
    # ── IS: Below-the-line ─────────────────────────────────────────────────
    "interest_income_usdm": "zero",  # Not always disclosed separately
    "interest_expense_usdm": "zero",  # May be 0 in debt-free periods
    "other_net_usdm": "zero",  # Rounding / misc items
    "ebt_usdm": "error",  # Required for tax rate calc
    "income_tax_usdm": "warn",  # FY2023 tax was negative — allow
    "effective_tax_rate_pct": "warn",  # Derived; warn if suspicious
    # ── IS: Derived ratios ─────────────────────────────────────────────────
    "gross_margin_pct": "warn",  # Derivable
    "ebit_margin_pct": "warn",  # Derivable
    "ebitda_margin_pct": "warn",  # Derivable
    "net_margin_pct": "warn",  # Derivable
    "rd_pct_revenue": "warn",  # Derivable
    "capex_pct_revenue": "warn",  # Derivable
    # ── BS: Asset-side critical ────────────────────────────────────────────
    "total_assets_usdm": "error",  # Required for BS balance check
    "cash_and_investments_usdm": "error",  # Used in net debt calc
    "accounts_receivable_usdm": "ffill",  # Slowly-changing; ffill acceptable
    "inventory_usdm": "zero",  # NVDA is fabless — often minimal
    "prepaid_expenses_usdm": "ffill",  # Slowly-changing
    "ppe_net_usdm": "ffill",  # Changes gradually
    "goodwill_usdm": "ffill",  # Stable unless acquisition
    "intangible_assets_usdm": "ffill",  # Amortises; ffill then validate
    # ── BS: Liability-side critical ────────────────────────────────────────
    "total_liabilities_usdm": "error",  # Required for BS balance check
    "shareholders_equity_usdm": "error",  # Required for BS balance check
    "accounts_payable_usdm": "ffill",  # Slowly-changing
    "accrued_liabilities_usdm": "ffill",  # Slowly-changing
    "short_term_debt_usdm": "zero",  # May be 0 — valid for NVDA
    "long_term_debt_usdm": "ffill",  # Debt is stable year-to-year
    "total_debt_usdm": "warn",  # Derivable from STD + LTD
    # ── CF: Per architecture.md — FY2020/2021 CF is genuinely absent ───────
    "cfo_usdm": "ignore",  # FY2020–2021 absent by design
    "cfi_usdm": "ignore",  # FY2020–2021 absent by design
    "cff_usdm": "ignore",  # FY2020–2021 absent by design
    "capex_usdm": "warn",  # FY2022+ present; warn if missing
    "fcf_usdm": "warn",  # Derivable from cfo + capex
    "net_change_cash_usdm": "ignore",  # FY2020–2021 absent
    "da_usdm": "warn",  # Listed in CF too
    # ── CF: Working capital changes ────────────────────────────────────────
    "change_in_nwc_usdm": "warn",  # Used in FCFF — warn if missing
    "chg_accounts_receivable_usdm": "warn",
    "chg_inventory_usdm": "warn",
    "chg_accounts_payable_usdm": "warn",
    "chg_accrued_liabilities_usdm": "warn",
    "chg_prepaid_other_usdm": "warn",
    # ── CF: Additional line items ─────────────────────────────────────────
    "deferred_taxes_usdm": "warn",  # Non-cash item; may be 0
    "principal_lease_payments_usdm": "warn",  # Financing outflow
    "tax_on_rsu_usdm": "warn",  # RSU withholding tax
    "proceeds_maturities_securities_usdm": "warn",
    "proceeds_sales_securities_usdm": "warn",
    "proceeds_sales_equity_securities_usdm": "warn",
    "purchases_equity_securities_usdm": "warn",
    "cash_beginning_usdm": "ignore",  # Reference only
    "cash_ending_usdm": "ignore",  # Reference only
    # ── WC table ──────────────────────────────────────────────────────────
    "net_working_capital_usdm": "warn",  # Derivable
    "ar_days_dso": "warn",  # KPI — warn if missing
    "inventory_days_dio": "warn",
    "ap_days_dpo": "warn",
    "cash_conversion_cycle": "warn",
}


# ══════════════════════════════════════════════════════════════════════════════
# CLEANER IMPLEMENTATION
# ══════════════════════════════════════════════════════════════════════════════


def handle_missing(df: pd.DataFrame, source_label: str = "") -> pd.DataFrame:
    """
    Apply the MISSING_VALUE_POLICY to every column in the DataFrame.

    Raises ValueError for any "error" policy column with nulls.
    Fills silently for "zero" and "ffill"/"bfill" policies.
    Logs warnings for "warn" policy columns.
    Leaves "ignore" columns untouched.

    Args:
        df: DataFrame after transformer.apply_column_mapping()
        source_label: Label for error messages (e.g. "IS", "BS")

    Returns:
        Cleaned DataFrame with no unexpected NaNs.

    Raises:
        ValueError: If a critical column contains null values.
    """
    df = df.copy()

    for col in df.columns:
        if col not in MISSING_VALUE_POLICY:
            # Column exists but has no policy — warn and leave as-is
            if df[col].isnull().any():
                log_error(
                    row=None,
                    col=col,
                    err="UNMAPPED_MISSING_POLICY",
                    val=f"{df[col].isnull().sum()} nulls",
                    action="left_as_nan — add column to MISSING_VALUE_POLICY",
                )
            continue

        policy = MISSING_VALUE_POLICY[col]
        null_count = df[col].isnull().sum()

        if null_count == 0:
            continue  # Nothing to do

        if policy == "error":
            # Identify which fiscal years have the null
            bad_rows = (
                df[df[col].isnull()]["fiscal_year"].tolist()
                if "fiscal_year" in df.columns
                else "unknown"
            )
            log_error(
                row=str(bad_rows),
                col=col,
                err="MISSING_CRITICAL_FIELD",
                val=f"{null_count} nulls in fiscal_years={bad_rows}",
                action="raised_ValueError",
            )
            raise ValueError(
                f"[cleaner] CRITICAL: '{col}' has {null_count} null value(s) "
                f"in {source_label}. Fiscal years affected: {bad_rows}. "
                f"This field cannot be missing — check source data."
            )

        elif policy == "zero":
            df[col] = df[col].fillna(0)
            log_error(
                row=None,
                col=col,
                err="MISSING_FILLED_ZERO",
                val=f"{null_count} nulls",
                action="filled_with_0",
            )
            logger.info(
                "[cleaner] %s.%s — filled %d null(s) with 0",
                source_label,
                col,
                null_count,
            )

        elif policy == "ffill":
            df[col] = df[col].ffill()
            # If first row is still null after ffill, fall back to bfill
            remaining = df[col].isnull().sum()
            if remaining > 0:
                df[col] = df[col].bfill()
            log_error(
                row=None,
                col=col,
                err="MISSING_FILLED_FFILL",
                val=f"{null_count} nulls",
                action="forward_filled",
            )
            logger.info(
                "[cleaner] %s.%s — forward-filled %d null(s)",
                source_label,
                col,
                null_count,
            )

        elif policy == "bfill":
            df[col] = df[col].bfill()
            log_error(
                row=None,
                col=col,
                err="MISSING_FILLED_BFILL",
                val=f"{null_count} nulls",
                action="backward_filled",
            )

        elif policy == "median":
            fill_val = df[col].median()
            df[col] = df[col].fillna(fill_val)
            log_error(
                row=None,
                col=col,
                err="MISSING_FILLED_MEDIAN",
                val=f"{null_count} nulls",
                action=f"filled_with_median={fill_val:.4f}",
            )

        elif policy == "warn":
            log_error(
                row=None,
                col=col,
                err="MISSING_WARN",
                val=f"{null_count} nulls",
                action="left_as_nan — WARNING issued",
            )
            logger.warning(
                "[cleaner] WARNING: %s.%s has %d null(s). "
                "Downstream KPIs using this column may be NaN.",
                source_label,
                col,
                null_count,
            )

        elif policy == "ignore":
            # Expected absence (e.g. CF FY2020–2021 per architecture.md)
            logger.debug(
                "[cleaner] %s.%s — %d null(s) allowed by policy=ignore",
                source_label,
                col,
                null_count,
            )

    return df


def clean_is(df: pd.DataFrame) -> pd.DataFrame:
    """Apply missing value handling to IS canonical DataFrame."""
    return handle_missing(df, source_label="IS")


def clean_bs(df: pd.DataFrame) -> pd.DataFrame:
    """Apply missing value handling to BS canonical DataFrame."""
    return handle_missing(df, source_label="BS")


def clean_cf(df: pd.DataFrame) -> pd.DataFrame:
    """Apply missing value handling to CF canonical DataFrame."""
    return handle_missing(df, source_label="CF")


def clean_actuals(df: pd.DataFrame) -> pd.DataFrame:
    """Apply missing value handling to merged actuals table."""
    return handle_missing(df, source_label="actuals")
