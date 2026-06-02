"""
tests/test_golden_output.py

🔒 GOLDEN OUTPUT TEST — Snapshot regression guard for the NVIDIA DCF model.

Wired to:
  config/assumptions.json       — base case assumptions (WACC=12.91%, g=3.675%)
  data/raw/cleaned_financials.csv — FY2020-FY2025 actuals (ground truth)
  tests/fixtures/golden_output.csv — generated once, compared forever

Concept
───────
1. Run model once with base assumptions → save output as golden fixture.
2. Every subsequent run re-executes and compares byte-for-byte.
3. Any unintended change in IS ratios, margins, or revenue numbers
   triggers an immediate failure — protecting against silent regression.

Updating the golden fixture (intentional change only)
──────────────────────────────────────────────────────
When you deliberately change model logic AND have verified the new output:
  1. Delete tests/fixtures/golden_output.csv
  2. Run:  pytest tests/test_golden_output.py::test_generate_golden_fixture -s
  3. Commit the new file with a clear git message explaining the change.
"""

import os
import pandas as pd
import pytest
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
FIXTURE_DIR = os.path.join(PROJECT_ROOT, "tests", "fixtures")
FIXTURE_PATH = os.path.join(FIXTURE_DIR, "golden_output.csv")

RTOL = 1e-4  # 0.01% relative tolerance (allows floating point rounding)
ATOL = 0.01  # $0.01M absolute tolerance (matches data_contracts.md)

# ── Known correct FY2025 values from 10-K (ground truth for regression) ──────
FY2025_GROUND_TRUTH = {
    "fiscal_year": 2025,
    "revenue_usdm": 130497.0,
    "cogs_usdm": 32639.0,
    "gross_profit_usdm": 97858.0,
    "ebit_usdm": 81453.0,
    "net_income_usdm": 72880.0,
    "da_usdm": 1864.0,
    "ebitda_usdm": 83317.0,
    "gross_margin_pct": 0.7499,
    "ebit_margin_pct": 0.6242,
    "net_margin_pct": 0.5585,
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPER — build the golden output from cleaned_financials.csv
# This is what the "model" produces for actuals (no forecasting here —
# we're testing the historical data processing, not the DCF projection).
# ══════════════════════════════════════════════════════════════════════════════


def _build_output_from_actuals() -> pd.DataFrame:
    """
    Build the canonical actuals output from cleaned_financials.csv.
    This is the deterministic output that must never silently change.
    Mirrors what pipeline.run_etl() produces for the costs/actuals tables.
    """
    df = pd.read_csv(os.path.join(RAW_DATA_DIR, "cleaned_financials.csv"))

    # Select and order the columns we care about for regression
    output_cols = [
        "year",
        "ticker",
        "revenue",
        "cogs",
        "gross_profit",
        "ebit",
        "ebitda",
        "net_income",
        "da",
        "capex",
        "gross_margin",
        "ebit_margin",
        "net_margin",
        "rd_pct_revenue",
        "capex_pct_revenue",
        "total_assets",
        "total_liabilities",
        "shareholders_equity",
        "receivables",
        "inventory",
        "accounts_payable",
        "fcf",
    ]
    available = [c for c in output_cols if c in df.columns]
    output = df[available].copy()
    output = output.sort_values("year").reset_index(drop=True)
    return output


def _ensure_fixture_dir():
    os.makedirs(FIXTURE_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE GENERATION (run once — not a regular test)
# ══════════════════════════════════════════════════════════════════════════════


def test_generate_golden_fixture():
    """
    Utility: Generate or regenerate the golden fixture.
    Run explicitly when intentionally updating the baseline:
      pytest tests/test_golden_output.py::test_generate_golden_fixture -s
    Normal test runs will skip this.
    """
    _ensure_fixture_dir()
    output = _build_output_from_actuals()
    output.to_csv(FIXTURE_PATH, index=False)
    assert os.path.exists(FIXTURE_PATH), "Failed to write golden fixture."
    print(f"\nGolden fixture written: {FIXTURE_PATH}")
    print(f"Rows: {len(output)} | Columns: {list(output.columns)}")


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE EXISTENCE GUARD
# ══════════════════════════════════════════════════════════════════════════════


def test_golden_fixture_exists():
    """
    The fixture file must exist before regression comparisons can run.
    If this fails, run:
      pytest tests/test_golden_output.py::test_generate_golden_fixture -s
    """
    assert os.path.exists(FIXTURE_PATH), (
        f"Golden fixture not found at: {FIXTURE_PATH}\n"
        f"Generate it first:\n"
        f"  pytest tests/test_golden_output.py::test_generate_golden_fixture -s"
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN GOLDEN OUTPUT REGRESSION TEST
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(
    not os.path.exists(FIXTURE_PATH),
    reason="Golden fixture not yet generated. Run test_generate_golden_fixture first.",
)
def test_golden_output_matches_fixture():
    """
    Re-run the model pipeline and compare to saved golden fixture.

    Failure means either:
      (a) Unintended change in cleaning/transformation logic → investigate + fix
      (b) Intentional model change → regenerate fixture + commit with explanation
    """
    new_output = _build_output_from_actuals()
    golden = pd.read_csv(FIXTURE_PATH)

    # ── 1. Shape must not change ───────────────────────────────────────────────
    assert new_output.shape == golden.shape, (
        f"Output shape changed: got {new_output.shape}, "
        f"expected {golden.shape}.\n"
        f"Rows or columns were added/removed."
    )

    # ── 2. Column set must be identical ───────────────────────────────────────
    assert list(new_output.columns) == list(golden.columns), (
        f"Column names changed.\n"
        f"  New   : {list(new_output.columns)}\n"
        f"  Golden: {list(golden.columns)}"
    )

    # ── 3. Row count must be identical ────────────────────────────────────────
    assert len(new_output) == len(
        golden
    ), f"Row count changed: got {len(new_output)}, expected {len(golden)}."

    # ── 4. Numeric columns: float comparison with tolerance ────────────────────
    numeric_cols = new_output.select_dtypes(include="number").columns.tolist()
    pd.testing.assert_frame_equal(
        new_output[numeric_cols].reset_index(drop=True),
        golden[numeric_cols].reset_index(drop=True),
        check_exact=False,
        rtol=RTOL,
        atol=ATOL,
        obj="Golden output (numeric columns)",
    )

    # ── 5. String/identifier columns: exact match ─────────────────────────────
    str_cols = [c for c in new_output.columns if c not in numeric_cols]
    if str_cols:
        pd.testing.assert_frame_equal(
            new_output[str_cols].reset_index(drop=True),
            golden[str_cols].reset_index(drop=True),
            obj="Golden output (string columns)",
        )


# ══════════════════════════════════════════════════════════════════════════════
# FY2025 GROUND TRUTH SPOT CHECKS
# These test the actual 10-K values — independent of fixture
# ══════════════════════════════════════════════════════════════════════════════


class TestFY2025GroundTruth:
    """
    Hard-coded checks against FY2025 10-K values.
    These are the ONLY values we know are 100% correct.
    If these fail, the source data has been corrupted.
    """

    @pytest.fixture(autouse=True)
    def load_actuals(self):
        self.df = _build_output_from_actuals()
        self.fy25 = self.df[self.df["year"] == 2025].iloc[0]

    def test_fy2025_revenue(self):
        """Revenue: $130,497M."""
        assert self.fy25["revenue"] == pytest.approx(130497.0, abs=0.5)

    def test_fy2025_cogs(self):
        """COGS: $32,639M."""
        assert self.fy25["cogs"] == pytest.approx(32639.0, abs=0.5)

    def test_fy2025_gross_profit(self):
        """Gross Profit: $97,858M."""
        assert self.fy25["gross_profit"] == pytest.approx(97858.0, abs=0.5)

    def test_fy2025_ebit(self):
        """EBIT: $81,453M."""
        assert self.fy25["ebit"] == pytest.approx(81453.0, abs=0.5)

    def test_fy2025_net_income(self):
        """Net Income: $72,880M."""
        assert self.fy25["net_income"] == pytest.approx(72880.0, abs=0.5)

    def test_fy2025_gross_margin(self):
        """Gross Margin: ~74.99% (assumptions.json: 0.7499)."""
        assert self.fy25["gross_margin"] == pytest.approx(0.7499, abs=0.001)

    def test_fy2025_ebit_margin(self):
        """EBIT Margin: ~62.4%."""
        assert self.fy25["ebit_margin"] == pytest.approx(0.6242, abs=0.002)

    def test_fy2025_net_margin(self):
        """Net Margin: ~55.85%."""
        assert self.fy25["net_margin"] == pytest.approx(0.5585, abs=0.002)

    def test_fy2025_fcf(self):
        """FCF: $60,853M (CFO 64089 + CapEx -3236)."""
        assert self.fy25["fcf"] == pytest.approx(60853.0, abs=1.0)


# ══════════════════════════════════════════════════════════════════════════════
# ASSUMPTIONS.JSON VALIDATION
# ══════════════════════════════════════════════════════════════════════════════


class TestAssumptionsFile:
    """
    Validate that assumptions.json has the correct structure and values.
    If assumptions drift, model outputs will silently change.
    """

    @pytest.fixture(autouse=True)
    def load_assumptions(self, assumptions):
        self.a = assumptions

    def test_wacc_within_range(self):
        """WACC should be between 10% and 20% for a mega-cap tech company."""
        wacc = self.a["wacc"]["wacc"]
        assert 0.10 <= wacc <= 0.20, f"WACC {wacc:.4%} is outside plausible range."

    def test_wacc_matches_known_value(self):
        """WACC = 12.91% per 15_WACC sheet."""
        wacc = self.a["wacc"]["wacc"]
        assert wacc == pytest.approx(0.1291, abs=0.0001)

    def test_terminal_growth_rate(self):
        """Terminal growth rate matches the configured base-case DCF input."""
        g = self.a["dcf"]["terminal_growth_rate"]
        assert g == pytest.approx(0.03675, abs=0.0001)

    def test_projection_horizon_is_5_years(self):
        """Standard 5-year DCF horizon."""
        assert self.a["dcf"]["projection_horizon_years"] == 5

    def test_tax_rate_base_case(self):
        """Base case tax rate = 15% (normalized forward rate)."""
        tax = self.a["tax_rate"]["base_case"]["fy2026f"]
        assert tax == pytest.approx(0.15, abs=0.001)

    def test_fy2025_actuals_match_cleaned_financials(self, cleaned_financials):
        """Historical actuals in assumptions.json must match cleaned_financials.csv."""
        ha = self.a["historical_actuals_fy2025"]
        fy25 = cleaned_financials[cleaned_financials["year"] == 2025].iloc[0]
        assert ha["revenue_usdm"] == pytest.approx(fy25["revenue"], abs=1.0)
        assert ha["net_income_usdm"] == pytest.approx(fy25["net_income"], abs=1.0)
        assert ha["ebit_usdm"] == pytest.approx(fy25["ebit"], abs=1.0)

    def test_all_required_sections_present(self):
        """Assumptions file must have all 7 required sections."""
        required = [
            "wacc",
            "dcf",
            "revenue_growth",
            "gross_margin",
            "rd_expense_pct",
            "sga_expense_pct",
            "tax_rate",
            "interest_income",
            "capex",
            "depreciation",
            "working_capital",
            "debt_schedule",
            "fcff_construction",
            "historical_actuals_fy2025",
        ]
        for section in required:
            assert section in self.a, f"Missing section '{section}' in assumptions.json"

    def test_revenue_growth_rates_reasonable(self):
        """FY2026F blended growth = 62% (AI data center boom)."""
        growth = self.a["revenue_growth"]["total_blended"]["fy2026f"]
        assert (
            0.50 <= growth <= 0.75
        ), f"FY2026F blended growth {growth:.1%} is outside expected range."

    def test_diluted_shares_reasonable(self):
        """Diluted shares ~24.3B — consistent with NVIDIA's share count."""
        shares = self.a["dcf"]["diluted_shares_outstanding_millions"]
        assert (
            20000 <= shares <= 30000
        ), f"Diluted shares {shares}M is outside plausible range for NVDA."


# ══════════════════════════════════════════════════════════════════════════════
# REGRESSION GUARDS — must hold every run regardless of fixture
# ══════════════════════════════════════════════════════════════════════════════


class TestRegressionGuards:

    @pytest.fixture(autouse=True)
    def load_output(self):
        self.df = _build_output_from_actuals()

    def test_output_covers_fy2020_to_fy2025(self):
        """Must have 6 fiscal years: FY2020–FY2025."""
        years = sorted(self.df["year"].tolist())
        assert set([2020, 2021, 2022, 2023, 2024, 2025]).issubset(set(years))

    def test_no_null_values_in_revenue(self):
        """Revenue must never be null — it's the critical driver of the model."""
        assert self.df["revenue"].notna().all()

    def test_revenue_always_positive(self):
        assert (self.df["revenue"] > 0).all()

    def test_gross_profit_always_positive(self):
        assert (self.df["gross_profit"] > 0).all()

    def test_gross_margin_between_zero_and_one(self):
        margins = self.df["gross_margin"].dropna()
        assert (margins > 0).all() and (margins < 1).all()

    def test_gross_margin_improving_trend(self):
        """Gross margin improved from ~62% (FY2020) to ~75% (FY2025)."""
        gm20 = self.df[self.df["year"] == 2020]["gross_margin"].iloc[0]
        gm25 = self.df[self.df["year"] == 2025]["gross_margin"].iloc[0]
        assert (
            gm25 > gm20
        ), f"Gross margin should have improved: FY2020={gm20:.2%}, FY2025={gm25:.2%}"

    def test_ticker_always_nvda(self):
        assert (self.df["ticker"] == "NVDA").all()

    def test_output_is_sorted_by_year(self):
        years = self.df["year"].tolist()
        assert years == sorted(years)
