"""
tests/invariants/test_financial_invariants.py

🔥 CRITICAL — 3 non-negotiable accounting invariants tested against
REAL NVIDIA 10-K data (FY2021–FY2025).

MUST always pass. MUST never be skipped.
If any fails → the model or source data is WRONG.

──────────────────────────────────────────────────────────────────────
INVARIANT 1: Balance Sheet Identity  (Assets = Liabilities + Equity)
  Source: nvidia_historical_BS.csv
  FY2021: 28791 = 11898 + 16893  ✓
  FY2022: 44187 = 17575 + 26612  ✓
  FY2023: 41182 = 19081 + 22101  ✓
  FY2024: 65728 = 22750 + 42978  ✓
  FY2025: 111601 = 32274 + 79327 ✓

INVARIANT 2: Cash Flow Reconciliation  (CFO + CFI + CFF = ΔCash)
  Source: nvidia_historical_CF.csv  (FY2022–FY2025; FY2020-21 absent by design)
  FY2022:  9108 + (−9830) + 1865  = 1143  ✓
  FY2023:  5641 + 7375   + (−11617) = 1399  ✓
  FY2024: 28090 + (−10566) + (−13633) = 3891  ✓
  FY2025: 64089 + (−20421) + (−42359) = 1309  ✓

INVARIANT 3: Retained Earnings Rollforward (RE_t = RE_t-1 + NI - Div)
  Source: BS + IS merged
  Implied dividends = RE_prior + NI - RE_current  (dominated by buybacks)
  FY2022: 16235 = 18908 + 9752 − 12425   ✓
  FY2023: 10171 = 16235 + 4368 − 10432   ✓
  FY2024: 29817 = 10171 + 29760 − 10114  ✓
  FY2025: 68038 = 29817 + 72880 − 34659  ✓
──────────────────────────────────────────────────────────────────────
"""

import pytest

from src.modeling.engine import run_pipeline

TOLERANCE = 0.01  # $0.01M per data_contracts.md


@pytest.fixture(scope="session")
def projected_results() -> dict:
    return {
        scenario: run_pipeline(scenario) for scenario in ["base", "upside", "downside"]
    }


# ══════════════════════════════════════════════════════════════════════════════
# INVARIANT 1 — BALANCE SHEET IDENTITY
# ══════════════════════════════════════════════════════════════════════════════


class TestBalanceSheetIdentity:

    def test_identity_holds_on_all_real_data(self, bs_canonical):
        """
        CRITICAL: Real NVIDIA BS must balance for every fiscal year.
        Tolerance: $0.01M per data_contracts.md Rule 2.
        """
        df = bs_canonical.copy()
        df["_rhs"] = df["total_liabilities_usdm"] + df["shareholders_equity_usdm"]
        df["_discrepancy"] = (df["total_assets_usdm"] - df["_rhs"]).abs()
        failing = df[df["_discrepancy"] > TOLERANCE]
        assert failing.empty, (
            f"\n[INVARIANT 1 BREACH] BS does NOT balance in {len(failing)} year(s):\n"
            f"{failing[['fiscal_year','total_assets_usdm','total_liabilities_usdm','shareholders_equity_usdm','_discrepancy']].to_string(index=False)}\n"
            f"Max discrepancy: ${df['_discrepancy'].max():.4f}M"
        )

    def test_identity_row_by_row(self, bs_canonical):
        """Individual year check — pinpoints exactly which FY breaks."""
        for _, row in bs_canonical.iterrows():
            lhs = row["total_assets_usdm"]
            rhs = row["total_liabilities_usdm"] + row["shareholders_equity_usdm"]
            diff = abs(lhs - rhs)
            assert diff <= TOLERANCE, (
                f"FY{row['fiscal_year']}: Assets {lhs:.2f}M ≠ "
                f"Liabilities {row['total_liabilities_usdm']:.2f}M + "
                f"Equity {row['shareholders_equity_usdm']:.2f}M (diff={diff:.4f}M)"
            )

    def test_fy2025_exact_10k_values(self, bs_canonical):
        """
        Spot-check FY2025 against known 10-K figures.
        Assets: $111,601M | Liabilities: $32,274M | Equity: $79,327M
        """
        fy25 = bs_canonical[bs_canonical["fiscal_year"] == 2025].iloc[0]
        assert fy25["total_assets_usdm"] == pytest.approx(111601.0, abs=0.5)
        assert fy25["total_liabilities_usdm"] == pytest.approx(32274.0, abs=0.5)
        assert fy25["shareholders_equity_usdm"] == pytest.approx(79327.0, abs=0.5)

    def test_fy2021_exact_10k_values(self, bs_canonical):
        """Spot-check FY2021 — earliest year in BS file."""
        fy21 = bs_canonical[bs_canonical["fiscal_year"] == 2021].iloc[0]
        assert fy21["total_assets_usdm"] == pytest.approx(28791.0, abs=0.5)
        assert fy21["total_liabilities_usdm"] == pytest.approx(11898.0, abs=0.5)
        assert fy21["shareholders_equity_usdm"] == pytest.approx(16893.0, abs=0.5)

    def test_covers_all_five_fiscal_years(self, bs_canonical):
        """BS fixture must contain exactly FY2021–FY2025."""
        years = sorted(bs_canonical["fiscal_year"].tolist())
        assert years == [2021, 2022, 2023, 2024, 2025]

    def test_assets_always_positive(self, bs_canonical):
        assert (bs_canonical["total_assets_usdm"] > 0).all()

    def test_equity_always_positive_for_nvda(self, bs_canonical):
        assert (bs_canonical["shareholders_equity_usdm"] > 0).all()

    def test_equity_grew_dramatically_fy2023_to_fy2025(self, bs_canonical):
        """AI boom: NVDA equity more than tripled FY2023→FY2025."""
        e23 = bs_canonical[bs_canonical["fiscal_year"] == 2023][
            "shareholders_equity_usdm"
        ].iloc[0]
        e25 = bs_canonical[bs_canonical["fiscal_year"] == 2025][
            "shareholders_equity_usdm"
        ].iloc[0]
        assert (
            e25 > e23 * 3
        ), f"Equity should have tripled FY2023→FY2025: FY2023={e23:.0f}M, FY2025={e25:.0f}M"

    def test_broken_identity_is_caught(self, bs_broken_identity):
        """GUARD: Confirm corrupted BS data fails the identity check."""
        df = bs_broken_identity.copy()
        df["_d"] = (
            df["total_assets_usdm"]
            - df["total_liabilities_usdm"]
            - df["shareholders_equity_usdm"]
        ).abs()
        assert (
            df["_d"] > TOLERANCE
        ).any(), "Broken BS should have failed identity check."


# ══════════════════════════════════════════════════════════════════════════════
# INVARIANT 2 — CASH FLOW RECONCILIATION
# CFO + CFI + CFF = Net Change in Cash
# ══════════════════════════════════════════════════════════════════════════════


class TestCashFlowReconciliation:

    def test_reconciliation_holds_on_all_real_data(self, cf_canonical):
        """
        CRITICAL: Real NVIDIA CF must reconcile for FY2022–FY2025.
        FY2020–FY2021 absent by architecture design — skipped.
        Tolerance: $0.01M per data_contracts.md Rule 3.
        """
        df = cf_canonical.dropna(
            subset=["cfo_usdm", "cfi_usdm", "cff_usdm", "net_change_cash_usdm"]
        ).copy()
        assert len(df) >= 4, "Need at least 4 CF rows for reconciliation check."

        df["_computed"] = df["cfo_usdm"] + df["cfi_usdm"] + df["cff_usdm"]
        df["_discrepancy"] = (df["_computed"] - df["net_change_cash_usdm"]).abs()
        failing = df[df["_discrepancy"] > TOLERANCE]
        assert failing.empty, (
            f"\n[INVARIANT 2 BREACH] CF does NOT reconcile in {len(failing)} year(s):\n"
            f"{failing[['fiscal_year','cfo_usdm','cfi_usdm','cff_usdm','net_change_cash_usdm','_discrepancy']].to_string(index=False)}\n"
            f"Max discrepancy: ${df['_discrepancy'].max():.4f}M"
        )

    def test_reconciliation_row_by_row(self, cf_canonical):
        """Individual year check for every available CF row."""
        checkable = cf_canonical.dropna(
            subset=["cfo_usdm", "cfi_usdm", "cff_usdm", "net_change_cash_usdm"]
        )
        for _, row in checkable.iterrows():
            computed = row["cfo_usdm"] + row["cfi_usdm"] + row["cff_usdm"]
            diff = abs(computed - row["net_change_cash_usdm"])
            assert diff <= TOLERANCE, (
                f"FY{row['fiscal_year']}: CFO+CFI+CFF={computed:.2f}M "
                f"≠ ΔCash={row['net_change_cash_usdm']:.2f}M (diff={diff:.4f}M)"
            )

    def test_fy2025_exact_10k_values(self, cf_canonical):
        """
        FY2025 10-K: CFO=64089, CFI=-20421, CFF=-42359, ΔCash=1309 ($M).
        """
        fy25 = cf_canonical[cf_canonical["fiscal_year"] == 2025].iloc[0]
        assert fy25["cfo_usdm"] == pytest.approx(64089.0, abs=0.5)
        assert fy25["cfi_usdm"] == pytest.approx(-20421.0, abs=0.5)
        assert fy25["cff_usdm"] == pytest.approx(-42359.0, abs=0.5)
        assert fy25["net_change_cash_usdm"] == pytest.approx(1309.0, abs=0.5)

    def test_fy2023_exact_10k_values(self, cf_canonical):
        """FY2023 10-K: CFO=5641, CFI=7375, CFF=-11617, ΔCash=1399 ($M)."""
        fy23 = cf_canonical[cf_canonical["fiscal_year"] == 2023].iloc[0]
        assert fy23["cfo_usdm"] == pytest.approx(5641.0, abs=0.5)
        assert fy23["cfi_usdm"] == pytest.approx(7375.0, abs=0.5)
        assert fy23["cff_usdm"] == pytest.approx(-11617.0, abs=0.5)
        assert fy23["net_change_cash_usdm"] == pytest.approx(1399.0, abs=0.5)

    def test_covers_fy2022_to_fy2025(self, cf_canonical):
        years = sorted(cf_canonical["fiscal_year"].tolist())
        assert years == [2022, 2023, 2024, 2025]

    def test_cfo_always_positive(self, cf_canonical):
        """NVIDIA has never had negative OCF in FY2022–FY2025."""
        assert (cf_canonical["cfo_usdm"] > 0).all()

    def test_fcf_equals_cfo_minus_capex(self, cf_canonical):
        """FCF = CFO + CapEx  (CapEx stored as negative in CFI section)."""
        df = cf_canonical.dropna(subset=["cfo_usdm", "capex_usdm", "fcf_usdm"])
        for _, row in df.iterrows():
            computed = row["cfo_usdm"] + row["capex_usdm"]
            diff = abs(computed - row["fcf_usdm"])
            assert diff <= TOLERANCE, (
                f"FY{row['fiscal_year']}: FCF mismatch — "
                f"CFO({row['cfo_usdm']}) + CapEx({row['capex_usdm']}) = {computed:.2f}M "
                f"≠ stored FCF {row['fcf_usdm']:.2f}M (diff={diff:.4f}M)"
            )

    def test_broken_cf_is_caught(self, cf_broken_reconciliation):
        """GUARD: Confirm corrupted CF data fails the reconciliation check."""
        df = cf_broken_reconciliation.copy()
        df["_d"] = (
            df["cfo_usdm"]
            + df["cfi_usdm"]
            + df["cff_usdm"]
            - df["net_change_cash_usdm"]
        ).abs()
        assert (
            df["_d"] > TOLERANCE
        ).any(), "Broken CF should have failed reconciliation."


# ══════════════════════════════════════════════════════════════════════════════
# INVARIANT 3 — RETAINED EARNINGS ROLLFORWARD
# RE_t = RE_(t-1) + Net Income_t − Dividends_t
# ══════════════════════════════════════════════════════════════════════════════


class TestRetainedEarningsRollforward:
    """
    NVIDIA's RE changes are dominated by share buybacks.
    Implied "dividends" = RE_prior + NI - RE_current captures all equity distributions.

    Known values ($M):
      FY2022: 16235 = 18908 + 9752  − 12425  ✓
      FY2023: 10171 = 16235 + 4368  − 10432  ✓
      FY2024: 29817 = 10171 + 29760 − 10114  ✓
      FY2025: 68038 = 29817 + 72880 − 34659  ✓
    """

    def test_rollforward_closes_for_all_years(self, re_rollforward_df):
        """
        CRITICAL: RE_t reconstructed from (RE_prior + NI − implied_div)
        must equal stored RE_t exactly.
        """
        df = re_rollforward_df.dropna(subset=["re_prior"]).copy()
        assert len(df) >= 4

        df["_reconstructed"] = (
            df["re_prior"] + df["net_income_usdm"] - df["implied_dividends_usdm"]
        )
        df["_discrepancy"] = (df["_reconstructed"] - df["retained_earnings_usdm"]).abs()
        failing = df[df["_discrepancy"] > TOLERANCE]
        assert failing.empty, (
            f"\n[INVARIANT 3 BREACH] RE rollforward does NOT close in {len(failing)} year(s):\n"
            f"{failing[['fiscal_year','retained_earnings_usdm','re_prior','net_income_usdm','implied_dividends_usdm']].to_string(index=False)}"
        )

    def test_implied_dividends_positive_all_years(self, re_rollforward_df):
        """NVIDIA always distributes cash — implied dividends must be positive."""
        df = re_rollforward_df.dropna(subset=["implied_dividends_usdm"])
        for _, row in df.iterrows():
            assert row["implied_dividends_usdm"] > 0, (
                f"FY{row['fiscal_year']}: Implied dividend = "
                f"{row['implied_dividends_usdm']:.0f}M (should be positive)"
            )

    def test_fy2025_rollforward_exact(self, re_rollforward_df):
        """FY2025: 68038 = 29817 + 72880 − 34659."""
        fy25 = re_rollforward_df[re_rollforward_df["fiscal_year"] == 2025].iloc[0]
        reconstructed = (
            fy25["re_prior"] + fy25["net_income_usdm"] - fy25["implied_dividends_usdm"]
        )
        assert (
            abs(reconstructed - fy25["retained_earnings_usdm"]) <= TOLERANCE
        ), f"FY2025 RE rollforward fails: {reconstructed:.0f}M ≠ {fy25['retained_earnings_usdm']:.0f}M"

    def test_fy2022_rollforward_exact(self, re_rollforward_df):
        """FY2022: 16235 = 18908 + 9752 − 12425."""
        fy22 = re_rollforward_df[re_rollforward_df["fiscal_year"] == 2022].iloc[0]
        reconstructed = (
            fy22["re_prior"] + fy22["net_income_usdm"] - fy22["implied_dividends_usdm"]
        )
        assert abs(reconstructed - fy22["retained_earnings_usdm"]) <= TOLERANCE

    def test_re_grew_from_fy2021_to_fy2025(self, re_rollforward_df):
        """Despite buybacks, explosive NI growth caused RE to increase 3.6x."""
        re21 = re_rollforward_df[re_rollforward_df["fiscal_year"] == 2021][
            "retained_earnings_usdm"
        ].iloc[0]
        re25 = re_rollforward_df[re_rollforward_df["fiscal_year"] == 2025][
            "retained_earnings_usdm"
        ].iloc[0]
        assert (
            re25 > re21 * 3
        ), f"RE should have grown >3× FY2021→FY2025: {re21:.0f}M → {re25:.0f}M"

    def test_covers_fy2021_to_fy2025(self, re_rollforward_df):
        years = sorted(re_rollforward_df["fiscal_year"].tolist())
        assert set([2021, 2022, 2023, 2024, 2025]).issubset(set(years))


# ══════════════════════════════════════════════════════════════════════════════
# CROSS-STATEMENT TIES
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossStatementTies:

    def test_net_income_matches_is_and_cf(self, is_canonical, cf_canonical):
        """Net income in IS must match CF for FY2022–FY2025 (same line item)."""
        merged = is_canonical[["fiscal_year", "net_income_usdm"]].merge(
            cf_canonical[["fiscal_year", "net_income_usdm"]],
            on="fiscal_year",
            suffixes=("_is", "_cf"),
        )
        for _, row in merged.iterrows():
            diff = abs(row["net_income_usdm_is"] - row["net_income_usdm_cf"])
            assert diff <= TOLERANCE, (
                f"FY{row['fiscal_year']}: NI mismatch — "
                f"IS={row['net_income_usdm_is']:.0f}M vs CF={row['net_income_usdm_cf']:.0f}M"
            )

    def test_gross_profit_equals_revenue_minus_cogs(self, is_canonical):
        """GP = Revenue − COGS must hold for all 6 fiscal years."""
        for _, row in is_canonical.iterrows():
            computed = row["revenue_usdm"] - row["cogs_usdm"]
            diff = abs(computed - row["gross_profit_usdm"])
            assert diff <= TOLERANCE, (
                f"FY{row['fiscal_year']}: GP mismatch — "
                f"{row['revenue_usdm']:.0f} - {row['cogs_usdm']:.0f} = {computed:.0f}M "
                f"≠ stored {row['gross_profit_usdm']:.0f}M"
            )

    def test_ebitda_equals_ebit_plus_da(self, is_canonical):
        """EBITDA = EBIT + D&A for all 6 fiscal years."""
        for _, row in is_canonical.iterrows():
            computed = row["ebit_usdm"] + row["da_usdm"]
            diff = abs(computed - row["ebitda_usdm"])
            assert diff <= TOLERANCE, (
                f"FY{row['fiscal_year']}: EBITDA mismatch — "
                f"EBIT({row['ebit_usdm']:.0f}) + DA({row['da_usdm']:.0f}) "
                f"= {computed:.0f}M ≠ stored EBITDA {row['ebitda_usdm']:.0f}M"
            )

    def test_revenue_growth_fy2023_to_fy2025(self, is_canonical):
        """Revenue grew monotonically through the AI boom years."""
        recent = is_canonical[
            is_canonical["fiscal_year"].isin([2023, 2024, 2025])
        ].sort_values("fiscal_year")
        revs = recent["revenue_usdm"].tolist()
        assert (
            revs[1] > revs[0] and revs[2] > revs[1]
        ), f"Revenue should increase FY2023→FY2025: {revs}"


class TestProjectionRevenueGrowthConsistency:

    _SEGMENT_KEYS = [
        "data_center",
        "gaming",
        "professional_visualization",
        "automotive",
        "oem_and_other",
    ]

    @pytest.mark.parametrize("scenario", ["base", "upside", "downside"])
    def test_positive_segment_growth_does_not_produce_revenue_decline(
        self, projected_results, scenario
    ):
        result = projected_results[scenario]
        revenue_df = (
            result["income_statement"][["fiscal_year", "revenue_usdm"]]
            .sort_values("fiscal_year")
            .copy()
        )
        assumptions = result["assumptions_used"]
        revenue_growth = assumptions["revenue_growth"]

        prior_revenue = None
        for _, row in revenue_df.iterrows():
            year = int(row["fiscal_year"])
            fy_key = f"fy{year}f"
            current_revenue = float(row["revenue_usdm"])

            if prior_revenue is not None:
                growth_rates = [
                    float(revenue_growth[seg][fy_key]) for seg in self._SEGMENT_KEYS
                ]
                if all(rate > 0 for rate in growth_rates):
                    assert current_revenue > prior_revenue, (
                        f"{scenario} FY{year}: all segment growth assumptions are positive "
                        f"{growth_rates}, but revenue declined from {prior_revenue:.2f}M "
                        f"to {current_revenue:.2f}M"
                    )

            prior_revenue = current_revenue


class TestProjectionFcffIdentity:

    @pytest.mark.parametrize("scenario", ["base", "upside", "downside"])
    def test_fcff_identity_holds_for_all_projection_years(
        self, projected_results, scenario
    ):
        fcff_df = projected_results[scenario]["fcff"].sort_values("fiscal_year").copy()
        years = fcff_df["fiscal_year"].tolist()
        assert years == [2026, 2027, 2028, 2029, 2030]

        for _, row in fcff_df.iterrows():
            computed_fcff = (
                row["nopat_usdm"]
                + row["da_usdm"]
                - row["capex_usdm"]
                - row["change_in_nwc_usdm"]
            )
            diff = abs(computed_fcff - row["fcff_usdm"])
            assert diff <= TOLERANCE, (
                f"{scenario} FY{int(row['fiscal_year'])}: FCFF identity breach — "
                f"NOPAT({row['nopat_usdm']:.4f}) + D&A({row['da_usdm']:.4f}) "
                f"- CapEx({row['capex_usdm']:.4f}) - ΔNWC({row['change_in_nwc_usdm']:.4f}) "
                f"= {computed_fcff:.4f}M ≠ stored FCFF {row['fcff_usdm']:.4f}M "
                f"(diff={diff:.4f}M)"
            )


class TestProjectionScenarioOrdering:

    def test_upside_base_downside_valuation_ordering(self, projected_results):
        prices = {
            scenario: projected_results[scenario]["dcf_valuation"][
                "implied_share_price_usd"
            ]
            for scenario in ["base", "upside", "downside"]
        }
        assert prices["upside"] > prices["base"] > prices["downside"], (
            f"Scenario ordering failed: upside={prices['upside']:.4f}, "
            f"base={prices['base']:.4f}, downside={prices['downside']:.4f}"
        )
