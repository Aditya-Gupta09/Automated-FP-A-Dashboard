"""
test_etl.py — Test Suite for All 5 ETL Tasks
=============================================
Tests:
  Task 1 — Column mapping completeness and correctness
  Task 2 — Missing value policy enforcement
  Task 3 — Duplicate detection and resolution
  Task 4 — SahilBuran pattern: modular pipeline stages work independently
  Task 5 — error_report.csv always generated, correct schema
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import tempfile

import pandas as pd
import pytest

from src.etl.cleaner import MISSING_VALUE_POLICY, handle_missing
from src.etl.transformer import (
    BS_COLUMN_MAPPING,
    CF_COLUMN_MAPPING,
    IS_COLUMN_MAPPING,
    apply_column_mapping,
    derive_is_ratios,
)
from src.etl.validator import (
    REQUIRED_IS_COLS,
    check_duplicates,
    validate_schema,
)
from src.utils.error_logger import (
    error_summary,
    get_errors,
    log_error,
    reset_errors,
    save_error_report,
)

# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 TESTS — Column Mapping
# ══════════════════════════════════════════════════════════════════════════════


class TestColumnMapping:

    def test_is_mapping_covers_raw_file_columns(self):
        """Every column in nvidia_historical_IS.csv must be in IS_COLUMN_MAPPING."""
        raw_cols = [
            "year",
            "ticker",
            "revenue",
            "cogs",
            "gross_profit",
            "rd_expense",
            "sga_expense",
            "acq_termination",
            "total_opex",
            "ebit",
            "da",
            "ebitda",
            "interest_income",
            "interest_expense",
            "other_net",
            "ebt",
            "income_tax",
            "net_income",
        ]
        for col in raw_cols:
            assert (
                col in IS_COLUMN_MAPPING
            ), f"IS raw column '{col}' missing from IS_COLUMN_MAPPING"

    def test_bs_mapping_covers_raw_file_columns(self):
        """Every column in nvidia_historical_BS.csv must be in BS_COLUMN_MAPPING."""
        raw_cols = [
            "year",
            "ticker",
            "cash_equivalents",
            "short_term_investments",
            "cash_and_st_investments",
            "receivables",
            "inventory",
            "prepaid_expenses",
            "total_current_assets",
            "ppe_net",
            "goodwill",
            "intangible_assets",
            "total_assets",
            "accounts_payable",
            "accrued_expenses",
            "short_term_debt",
            "total_current_liabilities",
            "long_term_debt",
            "total_liabilities",
            "shareholders_equity",
        ]
        for col in raw_cols:
            assert (
                col in BS_COLUMN_MAPPING
            ), f"BS raw column '{col}' missing from BS_COLUMN_MAPPING"

    def test_cf_mapping_covers_raw_file_columns(self):
        """Every column in nvidia_historical_CF.csv must be in CF_COLUMN_MAPPING."""
        raw_cols = [
            "year",
            "ticker",
            "net_income",
            "stock_comp",
            "depreciation_amortization",
            "cfo",
            "capex",
            "cfi",
            "cff",
            "net_change_cash",
            "fcf",
        ]
        for col in raw_cols:
            assert (
                col in CF_COLUMN_MAPPING
            ), f"CF raw column '{col}' missing from CF_COLUMN_MAPPING"

    def test_revenue_synonyms_all_map_to_revenue_usdm(self):
        """All revenue synonyms must map to the single canonical target."""
        synonyms = [
            "revenue",
            "total_revenue",
            "net_revenue",
            "net_sales",
            "sales",
            "revenues",
        ]
        for syn in synonyms:
            assert (
                IS_COLUMN_MAPPING.get(syn) == "revenue_usdm"
            ), f"Synonym '{syn}' does not map to 'revenue_usdm'"

    def test_apply_column_mapping_renames_correctly(self):
        df = pd.DataFrame({"year": [2025], "revenue": [130497], "cogs": [32639]})
        result = apply_column_mapping(df, IS_COLUMN_MAPPING, "test")
        assert "fiscal_year" in result.columns
        assert "revenue_usdm" in result.columns
        assert "cogs_usdm" in result.columns
        assert "year" not in result.columns

    def test_unmapped_columns_are_dropped(self):
        """Columns not in mapping must not silently pass through."""
        df = pd.DataFrame({"year": [2025], "revenue": [100], "unknown_col": [999]})
        result = apply_column_mapping(df, IS_COLUMN_MAPPING, "test")
        assert "unknown_col" not in result.columns

    def test_no_ambiguity_in_canonical_targets(self):
        """Within a single real raw file, no two columns should collide at the same
        canonical target. Synonyms across different source systems are intentional
        and safe — only one fires per real file."""
        real_IS_cols = [
            "year",
            "ticker",
            "revenue",
            "cogs",
            "gross_profit",
            "rd_expense",
            "sga_expense",
            "acq_termination",
            "total_opex",
            "ebit",
            "da",
            "ebitda",
            "interest_income",
            "interest_expense",
            "other_net",
            "ebt",
            "income_tax",
            "net_income",
        ]
        from collections import Counter

        rename_map = {
            c: IS_COLUMN_MAPPING[c] for c in real_IS_cols if c in IS_COLUMN_MAPPING
        }
        dupes = [v for v, cnt in Counter(rename_map.values()).items() if cnt > 1]
        assert dupes == [], f"Canonical collision in real IS file: {dupes}"


# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 TESTS — Missing Value Policy
# ══════════════════════════════════════════════════════════════════════════════


class TestMissingValuePolicy:

    def setup_method(self):
        reset_errors()

    def test_revenue_missing_raises_error(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "revenue_usdm": [None],
                "cogs_usdm": [32639],
            }
        )
        with pytest.raises(ValueError, match="revenue_usdm"):
            handle_missing(df, "IS")

    def test_cogs_missing_raises_error(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "revenue_usdm": [130497],
                "cogs_usdm": [None],
            }
        )
        with pytest.raises(ValueError, match="cogs_usdm"):
            handle_missing(df, "IS")

    def test_inventory_missing_fills_zero(self):
        """NVDA is fabless — inventory NaN → 0 is correct policy."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "inventory_usdm": [None],
            }
        )
        result = handle_missing(df, "BS")
        assert result["inventory_usdm"].iloc[0] == 0

    def test_acq_termination_fills_zero(self):
        """One-time items absent in normal years → 0."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "acq_termination_usdm": [None],
            }
        )
        result = handle_missing(df, "IS")
        assert result["acq_termination_usdm"].iloc[0] == 0

    def test_ar_forward_filled(self):
        """AR should forward-fill from prior year."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2025],
                "accounts_receivable_usdm": [9999.0, None],
            }
        )
        result = handle_missing(df, "BS")
        assert result["accounts_receivable_usdm"].iloc[1] == 9999.0

    def test_cfo_allows_nan(self):
        """CF FY2020-21 absent by design — policy=ignore, no error raised."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2020, 2021],
                "ticker": ["NVDA", "NVDA"],
                "cfo_usdm": [None, None],
            }
        )
        result = handle_missing(df, "CF")  # Should not raise
        assert result["cfo_usdm"].isnull().all()

    def test_every_canonical_column_has_a_policy(self):
        """All required IS columns must have an explicit policy defined."""
        for col in REQUIRED_IS_COLS:
            if col in ("ticker",):
                continue
            assert (
                col in MISSING_VALUE_POLICY
            ), f"Required column '{col}' has no entry in MISSING_VALUE_POLICY"


# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 TESTS — Duplicate Handling
# ══════════════════════════════════════════════════════════════════════════════


class TestDuplicateHandling:

    def setup_method(self):
        reset_errors()

    def test_exact_duplicates_removed_silently(self):
        """Byte-for-byte identical rows should be deduplicated without error."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2024],
                "revenue_usdm": [60922, 60922],
            }
        )
        result = check_duplicates(df, ["fiscal_year"], "IS")
        assert len(result) == 1

    def test_exact_duplicates_logged_to_error_report(self):
        """Exact duplicate removal must be recorded in error log."""
        reset_errors()
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2024],
                "revenue_usdm": [60922, 60922],
            }
        )
        check_duplicates(df, ["fiscal_year"], "IS")
        errors = get_errors()
        assert any(e["error_type"] == "EXACT_DUPLICATE_ROWS" for e in errors)

    def test_conflicting_duplicates_raise_error(self):
        """Different values for same fiscal_year = data corruption → must raise."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2024],
                "revenue_usdm": [60922, 99999],  # Different values — conflict
            }
        )
        with pytest.raises(ValueError, match="DUPLICATE ERROR"):
            check_duplicates(df, ["fiscal_year"], "IS", raise_on_conflict=True)

    def test_conflicting_duplicates_keep_last_when_not_raising(self):
        """When raise_on_conflict=False, keep last and log."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2024],
                "revenue_usdm": [60922, 99999],
            }
        )
        result = check_duplicates(df, ["fiscal_year"], "IS", raise_on_conflict=False)
        assert len(result) == 1
        assert result["revenue_usdm"].iloc[0] == 99999

    def test_no_duplicates_passes_cleanly(self):
        """Clean data with no duplicates should pass unchanged."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2020, 2021, 2022, 2023, 2024, 2025],
                "revenue_usdm": [10918, 16675, 26914, 26974, 60922, 130497],
            }
        )
        result = check_duplicates(df, ["fiscal_year"], "IS")
        assert len(result) == 6

    def test_duplicate_key_column_missing_raises(self):
        """If key column doesn't exist, must raise clearly — not silently skip."""
        df = pd.DataFrame({"some_other_col": [1, 2]})
        with pytest.raises(ValueError, match="duplicate key column"):
            check_duplicates(df, ["fiscal_year"], "IS")


# ══════════════════════════════════════════════════════════════════════════════
# TASK 4 TESTS — SahilBuran Pattern: Modular Independence
# ══════════════════════════════════════════════════════════════════════════════


class TestModularPipeline:

    def test_transformer_runs_without_validator(self):
        """transformer.py must work standalone — no validator import needed."""
        df = pd.DataFrame({"year": [2025], "revenue": [130497]})
        result = apply_column_mapping(df, IS_COLUMN_MAPPING)
        assert "revenue_usdm" in result.columns

    def test_cleaner_runs_without_transformer(self):
        """cleaner.py must work on already-mapped data independently."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "revenue_usdm": [130497.0],
                "inventory_usdm": [None],
            }
        )
        result = handle_missing(df, "test")
        assert result["inventory_usdm"].iloc[0] == 0

    def test_validator_runs_without_cleaner(self):
        """validator.py must work on raw mapped data without needing cleaner."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "revenue_usdm": [130497.0],
                "cogs_usdm": [32639.0],
                "gross_profit_usdm": [97858.0],
                "rd_expense_usdm": [12914.0],
                "sga_expense_usdm": [3491.0],
                "total_opex_usdm": [16405.0],
                "ebit_usdm": [81453.0],
                "ebt_usdm": [84026.0],
                "net_income_usdm": [72880.0],
            }
        )
        validate_schema(df, REQUIRED_IS_COLS, "IS")  # Should not raise

    def test_derive_ratios_works_after_transform(self):
        """derive_is_ratios must correctly compute from canonical column names."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "revenue_usdm": [130497.0],
                "gross_profit_usdm": [97858.0],
                "ebit_usdm": [81453.0],
                "ebitda_usdm": [83317.0],
                "net_income_usdm": [72880.0],
                "rd_expense_usdm": [12914.0],
                "income_tax_usdm": [11146.0],
                "ebt_usdm": [84026.0],
            }
        )
        result = derive_is_ratios(df)
        assert abs(result["gross_margin_pct"].iloc[0] - 0.7499) < 0.001
        assert abs(result["net_margin_pct"].iloc[0] - 0.5585) < 0.001


# ══════════════════════════════════════════════════════════════════════════════
# TASK 5 TESTS — error_report.csv
# ══════════════════════════════════════════════════════════════════════════════


class TestErrorReport:

    def setup_method(self):
        reset_errors()

    def test_error_report_always_generated_even_if_empty(self):
        """CRITICAL: error_report.csv must be written even on a clean run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            assert os.path.exists(path), "error_report.csv was not created on clean run"

    def test_error_report_has_correct_schema(self):
        """File must have exactly the 6 required columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            df = pd.read_csv(path)
            expected_cols = {
                "timestamp",
                "row_number",
                "column_name",
                "error_type",
                "raw_value",
                "action_taken",
            }
            assert expected_cols == set(df.columns), f"Wrong columns: {set(df.columns)}"

    def test_empty_report_has_zero_rows(self):
        """Clean run produces 0-row CSV with headers only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            df = pd.read_csv(path)
            assert len(df) == 0

    def test_errors_are_stored_not_printed(self):
        """Errors must accumulate in the list — not just printed to stdout."""
        reset_errors()
        log_error(
            row=1,
            col="revenue_usdm",
            err="TEST_ERROR",
            val="None",
            action="test_action",
        )
        errors = get_errors()
        assert len(errors) == 1
        assert errors[0]["error_type"] == "TEST_ERROR"

    def test_error_report_captures_all_fields(self):
        """All 6 schema fields must be populated per logged error."""
        reset_errors()
        log_error(
            row=5,
            col="cogs_usdm",
            err="MISSING_CRITICAL_FIELD",
            val="NaN",
            action="raised_ValueError",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            df = pd.read_csv(path)
            assert len(df) == 1
            assert df["column_name"].iloc[0] == "cogs_usdm"
            assert df["error_type"].iloc[0] == "MISSING_CRITICAL_FIELD"
            assert df["action_taken"].iloc[0] == "raised_ValueError"

    def test_error_summary_counts_by_type(self):
        """error_summary() must return counts broken down by error_type."""
        reset_errors()
        log_error(None, "revenue_usdm", "MISSING_CRITICAL_FIELD", "NaN", "raised")
        log_error(None, "cogs_usdm", "MISSING_CRITICAL_FIELD", "NaN", "raised")
        log_error(None, "inventory_usdm", "MISSING_FILLED_ZERO", "NaN", "filled_0")
        summary = error_summary()
        assert summary["total"] == 3
        assert summary["by_type"]["MISSING_CRITICAL_FIELD"] == 2
        assert summary["has_critical"] is True

    def test_reset_clears_error_list(self):
        """reset_errors() must wipe the accumulated list for a fresh run."""
        log_error(None, "col", "ERR", "val", "act")
        reset_errors()
        assert len(get_errors()) == 0


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TEST — Full pipeline on real raw files
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegration:

    def test_full_pipeline_runs_on_real_data(self):
        """End-to-end: load real CSVs, run all 5 pipeline stages, produce canonical tables."""
        original_dir = os.getcwd()
        try:
            os.chdir(os.path.join(os.path.dirname(__file__), ".."))
            from src.etl.pipeline import run_etl

            result = run_etl(save_parquet=False, save_csv=True)

            assert result["status"] == "success"
            assert "actuals" in result
            assert "costs" in result
            assert "working_capital" in result
            assert os.path.exists(result["error_report_path"])

            # Validate actuals shape
            actuals = result["actuals"]
            assert len(actuals) == 6  # FY2020–2025
            assert "revenue_usdm" in actuals.columns
            assert actuals["revenue_usdm"].iloc[-1] == 130497  # FY2025

            # Validate costs shape
            costs = result["costs"]
            assert "gross_margin_pct" in costs.columns

            # Validate error_report always exists
            error_df = pd.read_csv(result["error_report_path"])
            required_cols = {
                "timestamp",
                "row_number",
                "column_name",
                "error_type",
                "raw_value",
                "action_taken",
            }
            assert required_cols == set(error_df.columns)

        finally:
            os.chdir(original_dir)
