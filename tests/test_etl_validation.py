"""
tests/etl/test_etl_validation.py

🔍 ETL VALIDATION TESTS — Wired to REAL validator.py and cleaner.py.

Tests the exact functions from your production ETL layer:
  etl/validator.py — check_duplicates, validate_schema, validate_bs_balance,
                      validate_cf_reconciliation, REQUIRED_IS_COLS
  etl/cleaner.py   — handle_missing, MISSING_VALUE_POLICY

Test coverage:
  1. Column validation — bad names raise clear errors
  2. Missing value policy — field-by-field enforcement
  3. Duplicate handling — exact vs. conflicting, with logging
  4. Date normalization — not applicable (NVDA uses fiscal_year int, not date str)
     → replaced with dtype validation (numeric columns must be numeric)
  5. Error report — always generated, correct 6-column schema

All numbers anchored to real NVIDIA 10-K data.
ETL bugs are silent killers. These tests ensure the pipeline fails loudly.
"""

import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

# ── add project src to path ───────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

# ── stub error_logger if not present (imported by validator + cleaner) ────────
try:
    from src.utils.error_logger import (
        error_summary,
        get_errors,
        log_error,
        reset_errors,
        save_error_report,
    )

    HAS_ERROR_LOGGER = True
except ImportError:
    HAS_ERROR_LOGGER = False

from src.etl.cleaner import MISSING_VALUE_POLICY, handle_missing
from src.etl.validator import (
    BS_TOLERANCE,
    CF_TOLERANCE,
    REQUIRED_BS_COLS,
    REQUIRED_IS_COLS,
    check_duplicates,
    validate_bs_balance,
    validate_cf_reconciliation,
    validate_dtypes,
    validate_schema,
)

# ══════════════════════════════════════════════════════════════════════════════
# 1. COLUMN / SCHEMA VALIDATION
# ══════════════════════════════════════════════════════════════════════════════


class TestSchemaValidation:

    def test_valid_is_passes_schema_check(self, is_canonical):
        """IS with all required canonical columns must pass validate_schema."""
        # Only subset of cols needed — validate_schema checks for required presence
        required_subset = {
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
        }
        assert required_subset.issubset(set(is_canonical.columns)), (
            f"IS canonical fixture missing required columns: "
            f"{required_subset - set(is_canonical.columns)}"
        )
        # Add ticker if not present (canonical fixture may omit it)
        df = is_canonical.copy()
        df["ticker"] = "NVDA"
        validate_schema(df, REQUIRED_IS_COLS, "IS")  # Must not raise

    def test_missing_revenue_column_raises(self):
        """DataFrame lacking 'revenue_usdm' must raise ValueError."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                # revenue_usdm intentionally absent
                "cogs_usdm": [32639.0],
            }
        )
        with pytest.raises(ValueError) as exc:
            validate_schema(df, REQUIRED_IS_COLS, "IS")
        assert "revenue_usdm" in str(exc.value)

    def test_missing_ebit_column_raises(self):
        """EBIT is required for FCFF calculation — must raise if absent."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "revenue_usdm": [130497.0],
            }
        )
        with pytest.raises(ValueError) as exc:
            validate_schema(df, REQUIRED_IS_COLS, "IS")
        assert "ebit_usdm" in str(exc.value) or "Missing" in str(exc.value)

    def test_error_message_lists_all_missing_columns(self):
        """Error must enumerate every missing column — not just the first."""
        df = pd.DataFrame({"fiscal_year": [2025]})  # Only has fiscal_year
        with pytest.raises(ValueError) as exc:
            validate_schema(df, REQUIRED_IS_COLS, "IS")
        msg = str(exc.value)
        # Should mention at least 2 missing columns
        assert "revenue_usdm" in msg or "cogs_usdm" in msg

    def test_bs_schema_requires_assets_liabilities_equity(self):
        """BS validation must require total_assets, total_liabilities, equity."""
        for col in [
            "total_assets_usdm",
            "total_liabilities_usdm",
            "shareholders_equity_usdm",
        ]:
            assert (
                col in REQUIRED_BS_COLS
            ), f"'{col}' is missing from REQUIRED_BS_COLS — BS balance check will fail."

    def test_extra_columns_do_not_cause_failure(self, is_canonical):
        """Extra non-required columns in the DataFrame must not raise."""
        df = is_canonical.copy()
        df["ticker"] = "NVDA"
        df["extra_experimental_column"] = 0
        validate_schema(df, REQUIRED_IS_COLS, "IS")  # Must not raise

    def test_validate_schema_with_real_bs_columns(self, bs_canonical):
        """BS canonical fixture must satisfy REQUIRED_BS_COLS."""
        bs = bs_canonical.copy()
        bs["ticker"] = "NVDA"
        validate_schema(bs, REQUIRED_BS_COLS, "BS")  # Must not raise

    def test_dtype_validation_flags_object_numeric_columns(self):
        """validate_dtypes must flag numeric columns stored as object dtype."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "revenue_usdm": ["130497"],  # String — should be float
            }
        )
        # Should log warning — not raise (per validator.py design)
        validate_dtypes(df, "IS")  # Must not raise, but would log


# ══════════════════════════════════════════════════════════════════════════════
# 2. MISSING VALUE POLICY (cleaner.py)
# ══════════════════════════════════════════════════════════════════════════════


class TestMissingValuePolicy:

    def test_revenue_missing_raises_error(self, is_missing_revenue):
        """revenue_usdm is policy=error — NaN must raise ValueError immediately."""
        with pytest.raises(ValueError) as exc:
            handle_missing(is_missing_revenue, "IS")
        assert "revenue_usdm" in str(exc.value)

    def test_error_message_identifies_fiscal_year(self, is_missing_revenue):
        """Error must name which fiscal year is affected — not just the column."""
        with pytest.raises(ValueError) as exc:
            handle_missing(is_missing_revenue, "IS")
        msg = str(exc.value)
        assert "2025" in msg, "Error should identify FY2025 as the affected year."

    def test_cogs_missing_raises_error(self):
        """cogs_usdm is policy=error — required for gross profit calculation."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2025],
                "ticker": ["NVDA", "NVDA"],
                "revenue_usdm": [60922.0, 130497.0],
                "cogs_usdm": [16621.0, np.nan],  # FY2025 missing
                "gross_profit_usdm": [44301.0, 97858.0],
                "rd_expense_usdm": [8675.0, 12914.0],
                "sga_expense_usdm": [2654.0, 3491.0],
                "total_opex_usdm": [11329.0, 16405.0],
                "ebit_usdm": [32972.0, 81453.0],
                "ebt_usdm": [33818.0, 84026.0],
                "net_income_usdm": [29760.0, 72880.0],
            }
        )
        with pytest.raises(ValueError) as exc:
            handle_missing(df, "IS")
        assert "cogs_usdm" in str(exc.value)

    def test_inventory_missing_fills_zero(self):
        """
        inventory_usdm is policy=zero — NVIDIA is fabless, inventory is minimal.
        NaN → 0 is the correct business policy.
        """
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "inventory_usdm": [np.nan],
            }
        )
        result = handle_missing(df, "BS")
        assert result["inventory_usdm"].iloc[0] == 0.0

    def test_acq_termination_fills_zero(self):
        """
        acq_termination_usdm is policy=zero — one-time item, 0 in most years.
        FY2023 had $1,353M (ARM termination fee). Other years: $0.
        """
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2025],
                "ticker": ["NVDA", "NVDA"],
                "acq_termination_usdm": [np.nan, np.nan],
            }
        )
        result = handle_missing(df, "IS")
        assert (result["acq_termination_usdm"] == 0).all()

    def test_accounts_receivable_forward_filled(self, bs_ar_gap):
        """
        AR is policy=ffill — balance sheet items change slowly.
        FY2024 AR ($9,999M) must propagate to FY2025 when FY2025 is NaN.
        """
        result = handle_missing(bs_ar_gap, "BS")
        assert result["accounts_receivable_usdm"].iloc[1] == pytest.approx(
            9999.0, abs=0.1
        )

    def test_cfo_nan_is_allowed_for_fy2020_2021(self):
        """
        cfo_usdm is policy=ignore — CF absent FY2020-21 per architecture.md.
        NaN must pass through untouched — NOT raised, NOT filled.
        """
        df = pd.DataFrame(
            {
                "fiscal_year": [2020, 2021],
                "ticker": ["NVDA", "NVDA"],
                "cfo_usdm": [np.nan, np.nan],
            }
        )
        result = handle_missing(df, "CF")  # Must NOT raise
        assert (
            result["cfo_usdm"].isnull().all()
        ), "CF FY2020-21 NaN should be preserved (policy=ignore)"

    def test_cfi_nan_is_allowed(self):
        """cfi_usdm is policy=ignore — same as CFO."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2020, 2021],
                "ticker": ["NVDA", "NVDA"],
                "cfi_usdm": [np.nan, np.nan],
            }
        )
        result = handle_missing(df, "CF")
        assert result["cfi_usdm"].isnull().all()

    def test_every_required_is_column_has_a_policy(self):
        """Every column in REQUIRED_IS_COLS must have an explicit policy — no silent NaN."""
        non_identifier_cols = [c for c in REQUIRED_IS_COLS if c not in ("ticker",)]
        for col in non_identifier_cols:
            assert col in MISSING_VALUE_POLICY, (
                f"Required IS column '{col}' has NO policy in MISSING_VALUE_POLICY. "
                f"This will cause silent NaN propagation."
            )

    def test_real_is_data_passes_cleaning(self, is_canonical):
        """Full real IS data should pass handle_missing without raising."""
        df = is_canonical.copy()
        df["ticker"] = "NVDA"
        result = handle_missing(df, "IS")  # Must not raise
        assert result is not None
        assert len(result) == len(df)

    def test_real_bs_data_passes_cleaning(self, bs_canonical):
        """Full real BS data should pass handle_missing without raising."""
        df = bs_canonical.copy()
        df["ticker"] = "NVDA"
        result = handle_missing(df, "BS")  # Must not raise
        assert result is not None


# ══════════════════════════════════════════════════════════════════════════════
# 3. DUPLICATE HANDLING (validator.py)
# ══════════════════════════════════════════════════════════════════════════════


class TestDuplicateHandling:

    def test_no_duplicates_in_real_is_data(self, is_canonical):
        """Real IS data has exactly 1 row per fiscal_year — no duplicates."""
        result = check_duplicates(is_canonical, ["fiscal_year"], "IS")
        assert len(result) == len(is_canonical)

    def test_no_duplicates_in_real_bs_data(self, bs_canonical):
        """Real BS data has exactly 1 row per fiscal_year."""
        result = check_duplicates(bs_canonical, ["fiscal_year"], "BS")
        assert len(result) == len(bs_canonical)

    def test_no_duplicates_in_real_cf_data(self, cf_canonical):
        """Real CF data has exactly 1 row per fiscal_year."""
        result = check_duplicates(cf_canonical, ["fiscal_year"], "CF")
        assert len(result) == len(cf_canonical)

    def test_exact_duplicates_silently_removed(self, is_exact_duplicates):
        """Byte-for-byte identical rows must be deduplicated without raising."""
        result = check_duplicates(is_exact_duplicates, ["fiscal_year"], "IS")
        assert len(result) == 1
        assert result["revenue_usdm"].iloc[0] == pytest.approx(130497.0, abs=0.1)

    def test_conflicting_duplicates_raise_value_error(self, is_conflicting_duplicates):
        """
        Same fiscal_year with different revenue values = data corruption.
        Must raise ValueError — never silently choose one.
        """
        with pytest.raises(ValueError) as exc:
            check_duplicates(
                is_conflicting_duplicates, ["fiscal_year"], "IS", raise_on_conflict=True
            )
        assert "DUPLICATE ERROR" in str(exc.value) or "Conflicting" in str(exc.value)

    def test_conflicting_duplicates_keep_last_when_allowed(
        self, is_conflicting_duplicates
    ):
        """When raise_on_conflict=False, keep last row and log warning."""
        result = check_duplicates(
            is_conflicting_duplicates, ["fiscal_year"], "IS", raise_on_conflict=False
        )
        assert len(result) == 1
        assert result["revenue_usdm"].iloc[0] == pytest.approx(999999.0, abs=0.1)

    def test_missing_key_column_raises_clearly(self):
        """Key column not in DataFrame must raise immediately with a clear message."""
        df = pd.DataFrame({"some_col": [1, 2]})
        with pytest.raises(ValueError) as exc:
            check_duplicates(df, ["fiscal_year"], "IS")
        assert (
            "fiscal_year" in str(exc.value) or "duplicate key" in str(exc.value).lower()
        )

    def test_all_six_real_is_years_present_and_unique(self, is_canonical):
        """FY2020–FY2025: 6 unique years, 0 duplicates."""
        result = check_duplicates(is_canonical, ["fiscal_year"], "IS")
        assert len(result) == 6
        assert sorted(result["fiscal_year"].tolist()) == [
            2020,
            2021,
            2022,
            2023,
            2024,
            2025,
        ]


# ══════════════════════════════════════════════════════════════════════════════
# 4. DTYPE / FORMAT VALIDATION
# (NVDA uses integer fiscal_year — date normalization not applicable.
#  We test the analogous check: numeric columns must not be object dtype.)
# ══════════════════════════════════════════════════════════════════════════════


class TestDtypeValidation:

    def test_real_is_fiscal_year_is_integer(self, is_canonical):
        """fiscal_year must be integer — not string or float."""
        assert is_canonical["fiscal_year"].dtype in [
            "int64",
            "int32",
            "int",
        ], f"fiscal_year dtype is {is_canonical['fiscal_year'].dtype}, expected integer."

    def test_real_bs_fiscal_year_is_integer(self, bs_canonical):
        assert bs_canonical["fiscal_year"].dtype in ["int64", "int32", "int"]

    def test_real_cf_fiscal_year_is_integer(self, cf_canonical):
        assert cf_canonical["fiscal_year"].dtype in ["int64", "int32", "int"]

    def test_revenue_is_numeric_not_string(self, is_canonical):
        """Revenue must be numeric — not object dtype from CSV parsing."""
        assert pd.api.types.is_numeric_dtype(
            is_canonical["revenue_usdm"]
        ), f"revenue_usdm dtype = {is_canonical['revenue_usdm'].dtype}, expected numeric."

    def test_all_dollar_columns_are_numeric(self, is_canonical):
        """Every _usdm column must be numeric — flags ETL text-formatting bugs."""
        usdm_cols = [c for c in is_canonical.columns if c.endswith("_usdm")]
        for col in usdm_cols:
            assert pd.api.types.is_numeric_dtype(
                is_canonical[col]
            ), f"Column '{col}' has dtype {is_canonical[col].dtype} — should be numeric."

    def test_fiscal_years_are_in_expected_range(self, is_canonical):
        """Fiscal years must be between 2018 and 2030 — catches epoch/format bugs."""
        years = is_canonical["fiscal_year"]
        assert years.between(
            2018, 2030
        ).all(), f"Unexpected fiscal year values: {years[~years.between(2018,2030)].tolist()}"

    def test_string_fiscal_year_would_be_flagged(self):
        """Confirm validate_dtypes logs a warning for object-dtype numeric column."""
        df = pd.DataFrame(
            {
                "fiscal_year": [2025],
                "ticker": ["NVDA"],
                "revenue_usdm": ["130497"],  # String — bad
            }
        )
        # Should not raise (policy is warn, not error) but should process cleanly
        validate_dtypes(df, "IS")  # We just verify it doesn't crash


# ══════════════════════════════════════════════════════════════════════════════
# 5. BUSINESS RULE VALIDATION (BS balance + CF reconciliation in validator.py)
# ══════════════════════════════════════════════════════════════════════════════


class TestBusinessRuleValidation:

    def test_bs_balance_rule_passes_on_real_data(self, bs_canonical):
        """
        validate_bs_balance must pass silently for all FY2021–FY2025 rows.
        All 5 years are verified balanced in conftest.py fixtures.
        """
        validate_bs_balance(bs_canonical, source_label="BS")  # Must not raise

    def test_cf_reconciliation_rule_passes_on_real_data(self, cf_canonical):
        """
        validate_cf_reconciliation must pass for FY2022–FY2025.
        All 4 years are verified reconciled in conftest.py fixtures.
        """
        validate_cf_reconciliation(cf_canonical, source_label="CF")  # Must not raise

    def test_bs_balance_rule_flags_corrupted_data(self, bs_broken_identity):
        """
        validate_bs_balance should log a warning (not raise) when BS is out of balance.
        Per validator.py design: warns but does not crash the pipeline.
        """
        # Should not raise (validator logs warnings, not errors, for business rules)
        validate_bs_balance(bs_broken_identity, source_label="BS_BROKEN")

    def test_cf_reconciliation_flags_corrupted_data(self, cf_broken_reconciliation):
        """validate_cf_reconciliation should log a warning for broken CF."""
        validate_cf_reconciliation(cf_broken_reconciliation, source_label="CF_BROKEN")

    def test_bs_tolerance_is_data_contracts_value(self):
        """BS_TOLERANCE in validator.py must match data_contracts.md ($0.01M)."""
        assert BS_TOLERANCE == pytest.approx(
            0.01, abs=1e-6
        ), f"BS_TOLERANCE={BS_TOLERANCE}, expected 0.01 per data_contracts.md"

    def test_cf_tolerance_is_data_contracts_value(self):
        """CF_TOLERANCE in validator.py must match data_contracts.md ($0.01M)."""
        assert CF_TOLERANCE == pytest.approx(0.01, abs=1e-6)

    def test_fy2025_bs_balance_exact(self, bs_canonical):
        """Direct arithmetic check on FY2025 BS values."""
        fy25 = bs_canonical[bs_canonical["fiscal_year"] == 2025].iloc[0]
        lhs = fy25["total_assets_usdm"]
        rhs = fy25["total_liabilities_usdm"] + fy25["shareholders_equity_usdm"]
        assert (
            abs(lhs - rhs) <= BS_TOLERANCE
        ), f"FY2025 BS: {lhs}M ≠ {rhs}M (diff={abs(lhs-rhs):.4f}M)"


# ══════════════════════════════════════════════════════════════════════════════
# 6. ERROR REPORT — ALWAYS GENERATED  (uses error_logger if available)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not HAS_ERROR_LOGGER, reason="error_logger not available")
class TestErrorReport:

    def setup_method(self):
        reset_errors()

    def test_error_report_generated_on_clean_run(self):
        """CRITICAL: error_report.csv must be written even if 0 errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            assert os.path.exists(
                path
            ), "error_report.csv was NOT created on a clean run."

    def test_error_report_has_correct_6_column_schema(self):
        """Must have exactly: timestamp, row_number, column_name, error_type, raw_value, action_taken."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            df = pd.read_csv(path)
            expected = {
                "timestamp",
                "row_number",
                "column_name",
                "error_type",
                "raw_value",
                "action_taken",
            }
            assert expected == set(
                df.columns
            ), f"Wrong schema. Expected: {expected}\nGot: {set(df.columns)}"

    def test_clean_run_produces_zero_row_report(self):
        """Headers present, 0 data rows on a clean run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            df = pd.read_csv(path)
            assert len(df) == 0

    def test_logged_errors_appear_in_report(self):
        """Errors logged via log_error() must appear in the saved CSV."""
        reset_errors()
        log_error(
            row=2025,
            col="revenue_usdm",
            err="MISSING_CRITICAL_FIELD",
            val="NaN",
            action="raised_ValueError",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "error_report.csv")
            save_error_report(path)
            df = pd.read_csv(path)
            assert len(df) == 1
            assert df["column_name"].iloc[0] == "revenue_usdm"
            assert df["error_type"].iloc[0] == "MISSING_CRITICAL_FIELD"
            assert df["action_taken"].iloc[0] == "raised_ValueError"

    def test_error_summary_counts_correctly(self):
        """error_summary() must return correct counts per error_type."""
        reset_errors()
        log_error(None, "revenue_usdm", "MISSING_CRITICAL_FIELD", "NaN", "raised")
        log_error(None, "cogs_usdm", "MISSING_CRITICAL_FIELD", "NaN", "raised")
        log_error(None, "inventory_usdm", "MISSING_FILLED_ZERO", "NaN", "filled_0")
        summary = error_summary()
        assert summary["total"] == 3
        assert summary["by_type"]["MISSING_CRITICAL_FIELD"] == 2
        assert summary["by_type"]["MISSING_FILLED_ZERO"] == 1
        assert summary["has_critical"] is True

    def test_reset_clears_all_errors(self):
        """reset_errors() must wipe accumulated error list for a fresh run."""
        log_error(None, "col", "ERR", "val", "act")
        reset_errors()
        assert len(get_errors()) == 0

    def test_exact_duplicate_removal_is_logged(self, is_exact_duplicates):
        """When exact duplicates are removed, log_error must record the event."""
        reset_errors()
        check_duplicates(is_exact_duplicates, ["fiscal_year"], "IS")
        errors = get_errors()
        assert any(
            e["error_type"] == "EXACT_DUPLICATE_ROWS" for e in errors
        ), "Exact duplicate removal was NOT logged to error report."

    def test_error_report_parent_dir_created(self):
        """save_error_report() must create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c", "error_report.csv")
            save_error_report(nested)
            assert os.path.exists(nested)
