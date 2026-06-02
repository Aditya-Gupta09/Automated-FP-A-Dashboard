"""
transformer.py — Task 1: Column Mapping Rules
==============================================
Converts raw CSV column names → canonical schema names defined in canonical_schema.md.

Design principles (from SahilBuran ETL study):
- Mapping is a top-level constant — NEVER hardcoded inside functions
- Covers every synonym seen across: nvidia_historical_IS, BS, CF, cleaned_financials,
  comps_data, SEC EDGAR exports, Bloomberg, FactSet, Compustat, and manual Excel exports
- Three mapping dicts by statement type + one unified dict for merged tables
- All canonical names match canonical_schema.md exactly (snake_case, _usdm suffix)

Architecture slot: data/raw → loader → validator → cleaner → [TRANSFORMER] → data/canonical
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 — COLUMN MAPPING DICTIONARIES
# These are the single source of truth for raw → canonical name conversion.
# Add synonyms here as new raw sources are encountered — never edit downstream.
# ══════════════════════════════════════════════════════════════════════════════

# ── Income Statement Mapping ──────────────────────────────────────────────────
IS_COLUMN_MAPPING: dict[str, str] = {
    # Period / Identity
    "year": "fiscal_year",
    "fy": "fiscal_year",
    "fiscal_year": "fiscal_year",
    "period": "fiscal_year",
    "ticker": "ticker",
    "symbol": "ticker",
    # Revenue
    "revenue": "revenue_usdm",
    "total_revenue": "revenue_usdm",
    "net_revenue": "revenue_usdm",
    "net_sales": "revenue_usdm",
    "sales": "revenue_usdm",
    "total_net_revenue": "revenue_usdm",
    "revenues": "revenue_usdm",
    "total revenues": "revenue_usdm",
    "net revenues": "revenue_usdm",
    # COGS
    "cogs": "cogs_usdm",
    "cost_of_revenue": "cogs_usdm",
    "cost_of_goods_sold": "cogs_usdm",
    "cost of revenue": "cogs_usdm",
    "cost of goods sold": "cogs_usdm",
    "cost_of_sales": "cogs_usdm",
    # Gross Profit
    "gross_profit": "gross_profit_usdm",
    "gross profit": "gross_profit_usdm",
    "gross_margin_usdm": "gross_profit_usdm",
    # R&D
    "rd_expense": "rd_expense_usdm",
    "r_and_d": "rd_expense_usdm",
    "research_and_development": "rd_expense_usdm",
    "research and development": "rd_expense_usdm",
    "r&d": "rd_expense_usdm",
    "r&d_expense": "rd_expense_usdm",
    # SG&A
    "sga_expense": "sga_expense_usdm",
    "sg_and_a": "sga_expense_usdm",
    "selling_general_administrative": "sga_expense_usdm",
    "sg&a": "sga_expense_usdm",
    "sga": "sga_expense_usdm",
    "selling general and administrative": "sga_expense_usdm",
    # One-time / Acquisition items
    "acq_termination": "acq_termination_usdm",
    "acquisition_termination": "acq_termination_usdm",
    "termination_charge": "acq_termination_usdm",
    # OpEx total
    "total_opex": "total_opex_usdm",
    "operating_expenses": "total_opex_usdm",
    "total operating expenses": "total_opex_usdm",
    # EBIT / Operating Income
    "ebit": "ebit_usdm",
    "operating_income": "ebit_usdm",
    "operating income": "ebit_usdm",
    "income_from_operations": "ebit_usdm",
    "operating_profit": "ebit_usdm",
    # D&A
    "da": "da_usdm",
    "depreciation_amortization": "da_usdm",
    "depreciation_and_amortization": "da_usdm",
    "d&a": "da_usdm",
    "depreciation & amortization": "da_usdm",
    "depreciation_amortization_usdm": "da_usdm",
    # EBITDA
    "ebitda": "ebitda_usdm",
    # Below-the-line
    "interest_income": "interest_income_usdm",
    "interest income": "interest_income_usdm",
    "interest_expense": "interest_expense_usdm",
    "interest expense": "interest_expense_usdm",
    "other_net": "other_net_usdm",
    "other income (expense), net": "other_net_usdm",
    "other_income_expense": "other_net_usdm",
    # EBT
    "ebt": "ebt_usdm",
    "pretax_income": "ebt_usdm",
    "pre_tax_income": "ebt_usdm",
    "income before tax": "ebt_usdm",
    "income_before_taxes": "ebt_usdm",
    # Tax
    "income_tax": "income_tax_usdm",
    "income tax provision": "income_tax_usdm",
    "provision_for_income_taxes": "income_tax_usdm",
    "tax_provision": "income_tax_usdm",
    # Net Income
    "net_income": "net_income_usdm",
    "net income": "net_income_usdm",
    "net_earnings": "net_income_usdm",
    "earnings": "net_income_usdm",
    # Derived ratios (cleaned_financials carries these)
    "gross_margin": "gross_margin_pct",
    "ebit_margin": "ebit_margin_pct",
    "net_margin": "net_margin_pct",
    "rd_pct_revenue": "rd_pct_revenue",
    "capex_pct_revenue": "capex_pct_revenue",
}

# ── Balance Sheet Mapping ─────────────────────────────────────────────────────
BS_COLUMN_MAPPING: dict[str, str] = {
    "year": "fiscal_year",
    "fy": "fiscal_year",
    "fiscal_year": "fiscal_year",
    "ticker": "ticker",
    # Cash & investments
    "cash_equivalents": "cash_only_usdm",  # component only
    "cash_and_equivalents": "cash_and_investments_usdm",
    "cash_and_st_investments": "cash_and_investments_usdm",
    "cash": "cash_and_investments_usdm",
    "cash and cash equivalents": "cash_and_investments_usdm",
    "cash_and_investments": "cash_and_investments_usdm",
    "short_term_investments": "short_term_investments_usdm",
    # AR
    "receivables": "accounts_receivable_usdm",
    "accounts_receivable": "accounts_receivable_usdm",
    "trade_receivables": "accounts_receivable_usdm",
    "net receivables": "accounts_receivable_usdm",
    # Inventory
    "inventory": "inventory_usdm",
    "inventories": "inventory_usdm",
    # Other current
    "prepaid_expenses": "prepaid_expenses_usdm",
    "prepaid_and_other": "prepaid_expenses_usdm",
    "other_current_assets": "prepaid_expenses_usdm",
    # Total current assets
    "total_current_assets": "total_current_assets_usdm",
    # PP&E
    "ppe_net": "ppe_net_usdm",
    "property_plant_equipment": "ppe_net_usdm",
    "net_ppe": "ppe_net_usdm",
    "net pp&e": "ppe_net_usdm",
    "property plant and equipment net": "ppe_net_usdm",
    # Intangibles / Goodwill
    "goodwill": "goodwill_usdm",
    "intangible_assets": "intangible_assets_usdm",
    "intangibles": "intangible_assets_usdm",
    # Other assets
    "lt_deferred_tax_assets": "lt_deferred_tax_assets_usdm",
    "operating_lease_assets": "operating_lease_assets_usdm",
    "other_assets": "other_assets_usdm",
    # Total assets
    "total_assets": "total_assets_usdm",
    "total assets": "total_assets_usdm",
    # AP
    "accounts_payable": "accounts_payable_usdm",
    "trade payables": "accounts_payable_usdm",
    "trade_payables": "accounts_payable_usdm",
    # Accrued liabilities
    "accrued_expenses": "accrued_liabilities_usdm",
    "accrued_liabilities": "accrued_liabilities_usdm",
    "accrued and other liabilities": "accrued_liabilities_usdm",
    # Debt
    "short_term_debt": "short_term_debt_usdm",
    "current_portion_debt": "short_term_debt_usdm",
    "long_term_debt": "long_term_debt_usdm",
    "lt_debt": "long_term_debt_usdm",
    "total_debt": "total_debt_usdm",
    # Other liabilities
    "current_portion_leases": "current_lease_liabilities_usdm",
    "long_term_leases": "lt_lease_liabilities_usdm",
    "income_taxes_payable": "income_taxes_payable_usdm",
    "current_unearned_revenue": "current_deferred_revenue_usdm",
    "lt_unearned_revenue": "lt_deferred_revenue_usdm",
    "lt_deferred_tax_liabilities": "lt_deferred_tax_liabilities_usdm",
    "other_lt_liabilities": "other_lt_liabilities_usdm",
    "other_current_liabilities": "other_current_liabilities_usdm",
    # Totals
    "total_current_liabilities": "total_current_liabilities_usdm",
    "total_liabilities": "total_liabilities_usdm",
    "total liabilities": "total_liabilities_usdm",
    # Equity
    "shareholders_equity": "shareholders_equity_usdm",
    "stockholders_equity": "shareholders_equity_usdm",
    "total_equity": "shareholders_equity_usdm",
    "common_stock": "common_stock_usdm",
    "apic": "apic_usdm",
    "retained_earnings": "retained_earnings_usdm",
    "treasury_stock": "treasury_stock_usdm",
    "comprehensive_income_other": "aoci_usdm",
    "total_liabilities_equity": "total_liabilities_equity_usdm",
}

# ── Cash Flow Mapping ─────────────────────────────────────────────────────────
CF_COLUMN_MAPPING: dict[str, str] = {
    "year": "fiscal_year",
    "fy": "fiscal_year",
    "fiscal_year": "fiscal_year",
    "ticker": "ticker",
    # Operating
    "net_income": "net_income_usdm",
    "stock_comp": "stock_based_comp_usdm",
    "stock_based_compensation": "stock_based_comp_usdm",
    "sbc": "stock_based_comp_usdm",
    "depreciation_amortization": "da_usdm",
    "da": "da_usdm",
    "deferred_taxes": "deferred_taxes_usdm",
    "gains_equity_sec": "gains_on_investments_usdm",
    "acq_termination": "acq_termination_usdm",
    "other_operating": "other_operating_usdm",
    "chg_accounts_receivable": "chg_accounts_receivable_usdm",
    "chg_inventory": "chg_inventory_usdm",
    "chg_prepaid_other": "chg_prepaid_other_usdm",
    "chg_accounts_payable": "chg_accounts_payable_usdm",
    "chg_accrued_liabilities": "chg_accrued_liabilities_usdm",
    "chg_other_lt_liabilities": "chg_other_lt_liabilities_usdm",
    "cfo": "cfo_usdm",
    "net_cash_from_operations": "cfo_usdm",
    "operating_cash_flow": "cfo_usdm",
    "cash from operations": "cfo_usdm",
    # Investing
    "proceeds_maturities_sec": "proceeds_maturities_securities_usdm",
    "proceeds_sales_sec": "proceeds_sales_securities_usdm",
    "proceeds_sales_equity_sec": "proceeds_sales_equity_securities_usdm",
    "purchases_securities": "purchases_securities_usdm",
    "capex": "capex_usdm",
    "capital_expenditures": "capex_usdm",
    "purchases_of_ppe": "capex_usdm",
    "capital expenditures": "capex_usdm",
    "purchases_equity_sec": "purchases_equity_securities_usdm",
    "acquisitions_net": "acquisitions_net_usdm",
    "other_investing": "other_investing_usdm",
    "cfi": "cfi_usdm",
    "net_cash_from_investing": "cfi_usdm",
    # Financing
    "proceeds_stock_plans": "proceeds_stock_plans_usdm",
    "share_repurchases": "share_repurchases_usdm",
    "buybacks": "share_repurchases_usdm",
    "tax_on_rsu": "tax_on_rsu_usdm",
    "debt_repayment": "debt_repayment_usdm",
    "dividends_paid": "dividends_paid_usdm",
    "dividends": "dividends_paid_usdm",
    "principal_lease_payments": "principal_lease_payments_usdm",
    "other_financing": "other_financing_usdm",
    "cff": "cff_usdm",
    "net_cash_from_financing": "cff_usdm",
    # Net cash
    "net_change_cash": "net_change_cash_usdm",
    "net change in cash": "net_change_cash_usdm",
    "cash_beginning": "cash_beginning_usdm",
    "cash_ending": "cash_ending_usdm",
    "cash_taxes_paid": "cash_taxes_paid_usdm",
    "cash_interest_paid": "cash_interest_paid_usdm",
    # Derived
    "fcf": "fcf_usdm",
    "free_cash_flow": "fcf_usdm",
}

# ── Unified mapping (cleaned_financials and merged tables) ────────────────────
UNIFIED_COLUMN_MAPPING: dict[str, str] = {
    **IS_COLUMN_MAPPING,
    **BS_COLUMN_MAPPING,
    **CF_COLUMN_MAPPING,
    # cleaned_financials-specific overrides
    "cash": "cash_and_investments_usdm",
    "change_in_nwc": "change_in_nwc_usdm",
    "fcf": "fcf_usdm",
    "gross_margin": "gross_margin_pct",
    "ebit_margin": "ebit_margin_pct",
    "net_margin": "net_margin_pct",
}

# ── Comps data mapping ────────────────────────────────────────────────────────
COMPS_COLUMN_MAPPING: dict[str, str] = {
    "ticker": "ticker",
    "company_name": "company_name",
    "market_cap": "market_cap_usdbn",
    "net_debt": "net_debt_usdbn",
    "ev": "ev_usdbn",
    "ltm_revenue": "ltm_revenue_usdbn",
    "ltm_ebitda": "ltm_ebitda_usdbn",
    "ltm_ebitda_adj": "ltm_ebitda_adj_usdbn",
    "ltm_net_income": "ltm_net_income_usdbn",
    "ev_ebitda": "ev_ebitda_x",
    "ev_ebitda_adj": "ev_ebitda_adj_x",
    "p_e": "pe_ratio_x",
    "ev_sales": "ev_sales_x",
    "ltm_price": "share_price_usd",
    "ltm_eps": "eps_usd",
    "data_date": "data_date",
    "notes": "notes",
}


# ══════════════════════════════════════════════════════════════════════════════
# TRANSFORMER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase + strip all column names before mapping."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def apply_column_mapping(
    df: pd.DataFrame, mapping: dict[str, str], source_label: str = ""
) -> pd.DataFrame:
    """
    Rename raw columns to canonical names using the provided mapping dict.
    Columns not in the mapping are dropped with a warning — they have no
    canonical target and must not silently pass through.

    Args:
        df: Raw DataFrame from loader.
        mapping: One of the MAPPING dicts above.
        source_label: Human-readable source name for log messages.

    Returns:
        DataFrame with canonical column names only.
    """
    df = _normalise_columns(df)

    # Build rename map: only rename columns that exist in df
    rename_map = {col: mapping[col] for col in df.columns if col in mapping}
    unmapped = [col for col in df.columns if col not in mapping]

    if unmapped:
        logger.warning(
            "[transformer] %s — %d unmapped column(s) dropped: %s",
            source_label,
            len(unmapped),
            unmapped,
        )

    df = df.rename(columns=rename_map)
    # Keep only canonical columns (drop everything unmapped)
    canonical_cols = list(rename_map.values())
    df = df[[c for c in canonical_cols if c in df.columns]]

    logger.info(
        "[transformer] %s — renamed %d columns to canonical schema",
        source_label,
        len(rename_map),
    )
    return df


def transform_is(df: pd.DataFrame) -> pd.DataFrame:
    """Apply IS mapping + enforce dtypes + add metadata columns."""
    df = apply_column_mapping(df, IS_COLUMN_MAPPING, source_label="IS")
    df = _enforce_is_dtypes(df)
    df = _add_metadata(df, is_forecast=False, scenario="base")
    return df


def transform_bs(df: pd.DataFrame) -> pd.DataFrame:
    """Apply BS mapping + enforce dtypes + add metadata columns."""
    df = apply_column_mapping(df, BS_COLUMN_MAPPING, source_label="BS")
    df = _enforce_numeric_cols(df, exclude=["ticker"])
    df = _add_metadata(df, is_forecast=False, scenario="base")
    return df


def transform_cf(df: pd.DataFrame) -> pd.DataFrame:
    """Apply CF mapping + enforce dtypes + add metadata columns."""
    df = apply_column_mapping(df, CF_COLUMN_MAPPING, source_label="CF")
    df = _enforce_numeric_cols(df, exclude=["ticker"])
    df = _add_metadata(df, is_forecast=False, scenario="base")
    return df


def transform_cleaned_financials(df: pd.DataFrame) -> pd.DataFrame:
    """Apply unified mapping to cleaned_financials (merged IS+BS+CF table)."""
    df = apply_column_mapping(
        df, UNIFIED_COLUMN_MAPPING, source_label="cleaned_financials"
    )
    df = _enforce_numeric_cols(df, exclude=["ticker"])
    df = _add_metadata(df, is_forecast=False, scenario="base")
    return df


def transform_comps(df: pd.DataFrame) -> pd.DataFrame:
    """Apply comps mapping."""
    df = apply_column_mapping(df, COMPS_COLUMN_MAPPING, source_label="comps")
    return df


# ── Private helpers ───────────────────────────────────────────────────────────


def _enforce_is_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="coerce").astype(
            "Int64"
        )
    numeric_cols = [
        c
        for c in df.columns
        if c not in ("fiscal_year", "ticker", "is_forecast", "scenario", "source")
    ]
    return _enforce_numeric_cols(
        df, exclude=["ticker", "is_forecast", "scenario", "source"]
    )


def _enforce_numeric_cols(df: pd.DataFrame, exclude: list[str]) -> pd.DataFrame:
    for col in df.columns:
        if col in exclude:
            continue
        if col == "fiscal_year":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _add_metadata(df: pd.DataFrame, is_forecast: bool, scenario: str) -> pd.DataFrame:
    """Add canonical metadata columns required by model_input_schema.json."""
    if "ticker" not in df.columns:
        df.insert(1, "ticker", "NVDA")
    if "is_forecast" not in df.columns:
        df["is_forecast"] = is_forecast
    if "scenario" not in df.columns:
        df["scenario"] = scenario
    if "source" not in df.columns:
        df["source"] = "10-K (EDGAR)"
    return df


def derive_is_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute canonical derived ratio columns from base IS columns.
    Called after transform_is() if ratios are not in the raw source.
    All ratio columns store decimal form (0.75 not 75%).
    """
    rev = df.get("revenue_usdm")
    if rev is None:
        return df

    def safe_div(num_col: str, den_col: str) -> pd.Series:
        num = df.get(num_col, pd.Series([None] * len(df)))
        den = df.get(den_col, pd.Series([None] * len(df)))
        return (num / den).where(den != 0)

    df["gross_margin_pct"] = safe_div("gross_profit_usdm", "revenue_usdm")
    df["ebit_margin_pct"] = safe_div("ebit_usdm", "revenue_usdm")
    df["ebitda_margin_pct"] = safe_div("ebitda_usdm", "revenue_usdm")
    df["net_margin_pct"] = safe_div("net_income_usdm", "revenue_usdm")
    df["rd_pct_revenue"] = safe_div("rd_expense_usdm", "revenue_usdm")
    df["effective_tax_rate_pct"] = safe_div("income_tax_usdm", "ebt_usdm")

    return df
