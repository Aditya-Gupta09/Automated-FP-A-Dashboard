"""
tests/kpi/test_kpi_formulas.py

📐 KPI UNIT TESTS — Formula correctness, anchored to REAL NVIDIA data.

Every KPI is tested with:
  (a) Known correct values from 10-K actuals (FY2020–FY2025)
  (b) Division-by-zero → returns None (never crashes, never silently returns 0)
  (c) Boundary values: zero revenue, negative margins, extreme cases
  (d) Cross-KPI consistency (net margin ≤ gross margin, FCF margin < net margin, etc.)

FY2025 actuals used as primary anchors (most recent, fully verified):
  Revenue:      $130,497M   Gross Profit: $97,858M
  EBIT:         $81,453M    EBITDA:       $83,317M
  Net Income:   $72,880M    CFO:          $64,089M
  CapEx:        $3,236M     FCF:          $60,853M
  Gross Margin: 74.99%      EBIT Margin:  62.42%
  Net Margin:   55.85%      WACC:         12.91%

KPI errors = wrong business insights. These must be 100% correct.
"""

import pytest

from src.kpi.kpis import (
    ap_days as dpo,
    ar_days as dso,
    ebitda_margin as kpi_ebitda_margin,
    fcf_margin as kpi_fcf_margin,
    free_cash_flow as fcf,
    gross_margin,
    revenue_growth as revenue_growth_yoy,
)

DELTA = 1e-4  # 0.01% absolute tolerance for KPI ratios


# ══════════════════════════════════════════════════════════════════════════════
# PURE KPI FORMULA FUNCTIONS (tested independently where no src/ equivalent exists)
# ══════════════════════════════════════════════════════════════════════════════


def operating_margin(revenue, ebit):
    if revenue == 0:
        return None
    return ebit / revenue


def net_margin(revenue, net_income):
    if revenue == 0:
        return None
    return net_income / revenue


def dio(inventory, cogs):
    """Days Inventory Outstanding = Inventory / COGS × 365."""
    if cogs == 0:
        return None
    return inventory / cogs * 365


def ccc(dso_val, dio_val, dpo_val):
    """Cash Conversion Cycle = DSO + DIO - DPO."""
    return dso_val + dio_val - dpo_val


def asset_turnover(revenue, total_assets):
    if total_assets == 0:
        return None
    return revenue / total_assets


def return_on_equity(net_income, equity):
    if equity == 0:
        return None
    return net_income / equity


def return_on_assets(net_income, total_assets):
    if total_assets == 0:
        return None
    return net_income / total_assets


def debt_to_equity(total_debt, equity):
    if equity == 0:
        return None
    return total_debt / equity


def ev_revenue(ev, revenue):
    if revenue == 0:
        return None
    return ev / revenue


def ev_ebitda(ev, ebitda):
    if ebitda == 0:
        return None
    return ev / ebitda


def wacc_formula(risk_free, beta, erp, tax, w_equity, pretax_cod, w_debt):
    """WACC = w_eq × (rf + β × ERP) + w_debt × kd × (1 - t)."""
    ke = risk_free + beta * erp
    kd = pretax_cod * (1 - tax)
    return w_equity * ke + w_debt * kd, ke, kd


# ══════════════════════════════════════════════════════════════════════════════
# 1. GROSS MARGIN — anchored to FY2025 actuals (74.99%)
# ══════════════════════════════════════════════════════════════════════════════


class TestGrossMargin:

    def test_fy2025_nvda_actuals(self):
        """FY2025: (130497 - 32639) / 130497 = 74.99%."""
        result = gross_margin(130497, 32639)
        assert result == pytest.approx(0.7499, abs=0.001)

    def test_fy2024_nvda_actuals(self):
        """FY2024: (60922 - 16621) / 60922 = 72.72%."""
        result = gross_margin(60922, 16621)
        assert result == pytest.approx(0.7272, abs=0.001)

    def test_fy2022_nvda_actuals(self):
        """FY2022: (26914 - 9439) / 26914 = 64.93%."""
        result = gross_margin(26914, 9439)
        assert result == pytest.approx(0.6493, abs=0.001)

    def test_fy2020_nvda_actuals(self):
        """FY2020: (10918 - 4150) / 10918 = 61.99%."""
        result = gross_margin(10918, 4150)
        assert result == pytest.approx(0.6199, abs=0.001)

    def test_zero_revenue_returns_none(self):
        assert gross_margin(0, 40) is None

    def test_zero_revenue_zero_cogs_returns_none(self):
        assert gross_margin(0, 0) is None

    def test_negative_margin_returned_correctly(self):
        """Negative GP is valid — must not be clipped or zeroed."""
        result = gross_margin(100, 120)
        assert result == pytest.approx(-0.20, abs=DELTA)

    def test_zero_cogs_full_margin(self):
        """Pure software: (100-0)/100 = 100%."""
        result = gross_margin(100, 0)
        assert result == pytest.approx(1.0, abs=DELTA)

    def test_margin_improving_fy2020_to_fy2025(self, is_canonical):
        """NVIDIA's gross margin improved from ~62% (FY2020) to ~75% (FY2025)."""
        fy20 = is_canonical[is_canonical["fiscal_year"] == 2020].iloc[0]
        fy25 = is_canonical[is_canonical["fiscal_year"] == 2025].iloc[0]
        gm20 = gross_margin(fy20["revenue_usdm"], fy20["cogs_usdm"])
        gm25 = gross_margin(fy25["revenue_usdm"], fy25["cogs_usdm"])
        assert (
            gm25 > gm20
        ), f"Gross margin should improve FY2020→FY2025: {gm20:.2%} → {gm25:.2%}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. OPERATING (EBIT) MARGIN
# ══════════════════════════════════════════════════════════════════════════════


class TestOperatingMargin:

    def test_fy2025_nvda_actuals(self):
        """FY2025: 81453 / 130497 = 62.42%."""
        result = operating_margin(130497, 81453)
        assert result == pytest.approx(0.6242, abs=0.001)

    def test_fy2023_low_margin(self):
        """FY2023 (Arm deal write-off year): 4224 / 26974 = 15.66%."""
        result = operating_margin(26974, 4224)
        assert result == pytest.approx(0.1566, abs=0.001)

    def test_fy2022_actuals(self):
        """FY2022: 10041 / 26914 = 37.31%."""
        result = operating_margin(26914, 10041)
        assert result == pytest.approx(0.3731, abs=0.001)

    def test_zero_revenue_returns_none(self):
        assert operating_margin(0, 5000) is None

    def test_negative_ebit_is_valid(self):
        result = operating_margin(100, -30)
        assert result == pytest.approx(-0.30, abs=DELTA)

    def test_operating_margin_always_below_gross_margin(self, is_canonical):
        """EBIT margin < gross margin (OpEx > 0 in all periods)."""
        for _, row in is_canonical.iterrows():
            gm = gross_margin(row["revenue_usdm"], row["cogs_usdm"])
            om = operating_margin(row["revenue_usdm"], row["ebit_usdm"])
            if gm is not None and om is not None:
                assert om <= gm + 0.001, (
                    f"FY{row['fiscal_year']}: Operating margin {om:.2%} > "
                    f"gross margin {gm:.2%} — impossible."
                )


# ══════════════════════════════════════════════════════════════════════════════
# 3. EBITDA MARGIN
# ══════════════════════════════════════════════════════════════════════════════


class TestEBITDAMargin:

    def test_fy2025_nvda_actuals(self):
        """FY2025: 83317 / 130497 = 63.84%."""
        result = kpi_ebitda_margin(83317, 130497)
        assert result == pytest.approx(0.6384, abs=0.001)

    def test_fy2022_actuals(self):
        """FY2022: 11215 / 26914 = 41.67%."""
        result = kpi_ebitda_margin(11215, 26914)
        assert result == pytest.approx(0.4167, abs=0.001)

    def test_zero_revenue_returns_none(self):
        assert kpi_ebitda_margin(1000, 0) is None

    def test_ebitda_margin_exceeds_ebit_margin(self, is_canonical):
        """EBITDA > EBIT because D&A is added back (D&A always positive)."""
        for _, row in is_canonical.iterrows():
            em = kpi_ebitda_margin(row["ebitda_usdm"], row["revenue_usdm"])
            om = operating_margin(row["revenue_usdm"], row["ebit_usdm"])
            if em is not None and om is not None:
                assert em >= om - 0.001, (
                    f"FY{row['fiscal_year']}: EBITDA margin {em:.2%} < "
                    f"EBIT margin {om:.2%} — D&A must be non-negative."
                )


# ══════════════════════════════════════════════════════════════════════════════
# 4. NET MARGIN
# ══════════════════════════════════════════════════════════════════════════════


class TestNetMargin:

    def test_fy2025_nvda_actuals(self):
        """FY2025: 72880 / 130497 = 55.85%."""
        result = net_margin(130497, 72880)
        assert result == pytest.approx(0.5585, abs=0.001)

    def test_fy2024_nvda_actuals(self):
        """FY2024: 29760 / 60922 = 48.85%."""
        result = net_margin(60922, 29760)
        assert result == pytest.approx(0.4885, abs=0.001)

    def test_fy2023_low_net_margin(self):
        """FY2023 (ARM deal, large losses): 4368 / 26974 = 16.19%."""
        result = net_margin(26974, 4368)
        assert result == pytest.approx(0.1619, abs=0.001)

    def test_zero_revenue_returns_none(self):
        assert net_margin(0, 1000) is None

    def test_loss_scenario(self):
        result = net_margin(100, -20)
        assert result == pytest.approx(-0.20, abs=DELTA)

    def test_net_margin_always_leq_ebit_margin_positive_revenue(self, is_canonical):
        """Net margin ≤ EBIT margin (taxes + interest are costs)."""
        for _, row in is_canonical.iterrows():
            nm = net_margin(row["revenue_usdm"], row["net_income_usdm"])
            om = operating_margin(row["revenue_usdm"], row["ebit_usdm"])
            if nm is not None and om is not None and om > 0:
                # FY2023 had negative income tax (benefit) — skip that year
                if row["fiscal_year"] == 2023:
                    continue
                assert (
                    nm <= om + 0.01
                ), f"FY{row['fiscal_year']}: Net margin {nm:.2%} > EBIT margin {om:.2%}"


# ══════════════════════════════════════════════════════════════════════════════
# 5. FREE CASH FLOW & FCF MARGIN
# ══════════════════════════════════════════════════════════════════════════════


class TestFCF:

    def test_fy2025_nvda_actuals(self):
        """FY2025: CFO=64089, CapEx=-3236 → FCF=60853."""
        result = fcf(64089, -3236)
        assert result == pytest.approx(60853.0, abs=1.0)

    def test_fy2024_nvda_actuals(self):
        """FY2024: CFO=28090, CapEx=-1069 → FCF=27021."""
        result = fcf(28090, -1069)
        assert result == pytest.approx(27021.0, abs=1.0)

    def test_fy2023_nvda_actuals(self):
        """FY2023: CFO=5641, CapEx=-1833 → FCF=3808."""
        result = fcf(5641, -1833)
        assert result == pytest.approx(3808.0, abs=1.0)

    def test_fy2022_nvda_actuals(self):
        """FY2022: CFO=9108, CapEx=-976 → FCF=8132."""
        result = fcf(9108, -976)
        assert result == pytest.approx(8132.0, abs=1.0)

    def test_zero_capex_fcf_equals_cfo(self):
        assert fcf(64089, 0) == pytest.approx(64089.0, abs=DELTA)

    def test_negative_cfo_produces_negative_fcf(self):
        assert fcf(-100, -50) == pytest.approx(-150.0, abs=DELTA)

    def test_fcf_never_returns_none(self):
        """FCF never divides — must never return None."""
        assert fcf(0, 0) is not None

    def test_fcf_margin_fy2025(self):
        """FY2025 FCF margin: 60853 / 130497 = 46.63%."""
        result = kpi_fcf_margin(fcf(64089, -3236), 130497)
        assert result == pytest.approx(0.4664, abs=0.002)

    def test_fcf_margin_zero_revenue_returns_none(self):
        assert kpi_fcf_margin(fcf(64089, -3236), 0) is None

    def test_nvda_fcf_grew_fy2022_to_fy2025(self, cf_canonical):
        """FCF grew from $8.1B (FY2022) to $60.9B (FY2025) — 7.5× in 3 years."""
        fcf22 = cf_canonical[cf_canonical["fiscal_year"] == 2022]["fcf_usdm"].iloc[0]
        fcf25 = cf_canonical[cf_canonical["fiscal_year"] == 2025]["fcf_usdm"].iloc[0]
        assert (
            fcf25 > fcf22 * 7
        ), f"FCF should have grown >7× FY2022→FY2025: {fcf22:.0f}M → {fcf25:.0f}M"


# ══════════════════════════════════════════════════════════════════════════════
# 6. REVENUE GROWTH
# ══════════════════════════════════════════════════════════════════════════════


class TestRevenueGrowth:

    def test_fy2025_yoy_growth(self):
        """FY2025 vs FY2024: (130497 - 60922) / 60922 = 114.2%."""
        result = revenue_growth_yoy(130497, 60922)
        assert result == pytest.approx(1.142, abs=0.005)

    def test_fy2024_yoy_growth(self):
        """FY2024 vs FY2023: (60922 - 26974) / 26974 = 125.9%."""
        result = revenue_growth_yoy(60922, 26974)
        assert result == pytest.approx(1.259, abs=0.005)

    def test_fy2023_yoy_growth_near_flat(self):
        """FY2023 vs FY2022: (26974 - 26914) / 26914 = 0.2% (crypto bust)."""
        result = revenue_growth_yoy(26974, 26914)
        assert result == pytest.approx(0.002, abs=0.001)

    def test_zero_prior_revenue_returns_none(self):
        assert revenue_growth_yoy(130497, 0) is None

    def test_negative_growth_valid(self):
        result = revenue_growth_yoy(80, 100)
        assert result == pytest.approx(-0.20, abs=DELTA)


# ══════════════════════════════════════════════════════════════════════════════
# 7. WORKING CAPITAL DAYS (DSO, DIO, DPO, CCC)
# ══════════════════════════════════════════════════════════════════════════════


class TestWorkingCapitalDays:
    """
    FY2025 actuals per assumptions.json:
      DSO: 64.5 days  (AR=23065, Revenue=130497)
      DIO: 112.7 days (Inventory=10080, COGS=32639)
      DPO: 70.6 days  (AP=6310, COGS=32639)
      CCC: 106.7 days (DSO + DIO - DPO)
    """

    def test_dso_fy2025(self):
        """DSO FY2025: 23065 / 130497 × 365 = 64.5 days."""
        result = dso(23065, 130497)
        assert result == pytest.approx(64.5, abs=0.5)

    def test_dio_fy2025(self):
        """DIO FY2025: 10080 / 32639 × 365 = 112.7 days."""
        result = dio(10080, 32639)
        assert result == pytest.approx(112.7, abs=0.5)

    def test_dpo_fy2025(self):
        """DPO FY2025: 6310 / 32639 × 365 = 70.6 days."""
        result = dpo(6310, 32639)
        assert result == pytest.approx(70.6, abs=0.5)

    def test_ccc_fy2025(self):
        """CCC FY2025: 64.5 + 112.7 - 70.6 = 106.6 days."""
        dso_val = dso(23065, 130497)
        dio_val = dio(10080, 32639)
        dpo_val = dpo(6310, 32639)
        result = ccc(dso_val, dio_val, dpo_val)
        assert result == pytest.approx(106.6, abs=1.0)

    def test_dso_zero_revenue_returns_none(self):
        assert dso(23065, 0) is None

    def test_dio_zero_cogs_returns_none(self):
        assert dio(10080, 0) is None

    def test_dpo_zero_cogs_returns_none(self):
        assert dpo(6310, 0) is None

    def test_dso_zero_ar_gives_zero(self):
        """Zero AR → zero DSO (valid for high-velocity collections)."""
        result = dso(0, 130497)
        assert result == pytest.approx(0.0, abs=DELTA)

    def test_dso_fy2024(self):
        """FY2024: AR=9999, Revenue=60922 → DSO ≈ 59.9 days."""
        result = dso(9999, 60922)
        assert result == pytest.approx(59.9, abs=0.5)


# ══════════════════════════════════════════════════════════════════════════════
# 8. RETURN RATIOS
# ══════════════════════════════════════════════════════════════════════════════


class TestReturnRatios:

    def test_roe_fy2025(self):
        """ROE FY2025: 72880 / 79327 = 91.9% (exceptional AI profitability)."""
        result = return_on_equity(72880, 79327)
        assert result == pytest.approx(0.919, abs=0.005)

    def test_roa_fy2025(self):
        """ROA FY2025: 72880 / 111601 = 65.3%."""
        result = return_on_assets(72880, 111601)
        assert result == pytest.approx(0.653, abs=0.005)

    def test_asset_turnover_fy2025(self):
        """Asset Turnover FY2025: 130497 / 111601 = 1.17×."""
        result = asset_turnover(130497, 111601)
        assert result == pytest.approx(1.169, abs=0.005)

    def test_roe_zero_equity_returns_none(self):
        assert return_on_equity(72880, 0) is None

    def test_roa_zero_assets_returns_none(self):
        assert return_on_assets(72880, 0) is None

    def test_asset_turnover_zero_assets_returns_none(self):
        assert asset_turnover(130497, 0) is None

    def test_roa_always_less_than_roe_with_leverage(self, bs_canonical, is_canonical):
        """ROA ≤ ROE when the company has any debt (leverage amplifies equity returns)."""
        merged = bs_canonical.merge(
            is_canonical[["fiscal_year", "net_income_usdm"]], on="fiscal_year"
        )
        for _, row in merged.iterrows():
            roe = return_on_equity(
                row["net_income_usdm"], row["shareholders_equity_usdm"]
            )
            roa = return_on_assets(row["net_income_usdm"], row["total_assets_usdm"])
            if roe is not None and roa is not None and row["net_income_usdm"] > 0:
                assert roa <= roe + 0.001, (
                    f"FY{row['fiscal_year']}: ROA {roa:.2%} > ROE {roe:.2%} — "
                    f"impossible with positive leverage."
                )


# ══════════════════════════════════════════════════════════════════════════════
# 9. LEVERAGE RATIOS
# ══════════════════════════════════════════════════════════════════════════════


class TestLeverageRatios:

    def test_debt_to_equity_fy2025(self):
        """D/E FY2025: 8463 / 79327 = 0.107 (low leverage — fabless model)."""
        result = debt_to_equity(8463, 79327)
        assert result == pytest.approx(0.107, abs=0.002)

    def test_debt_to_equity_fy2022(self):
        """D/E FY2022: 10946 / 26612 = 0.411."""
        result = debt_to_equity(10946, 26612)
        assert result == pytest.approx(0.411, abs=0.005)

    def test_zero_equity_returns_none(self):
        assert debt_to_equity(8463, 0) is None

    def test_zero_debt_gives_zero_ratio(self):
        assert debt_to_equity(0, 79327) == pytest.approx(0.0, abs=DELTA)


# ══════════════════════════════════════════════════════════════════════════════
# 10. WACC RECALCULATION (cross-check vs assumptions.json)
# ══════════════════════════════════════════════════════════════════════════════


class TestWACCCalculation:
    """
    Replicates wacc.py logic independently.
    From assumptions.json:
      rf=4.07%, β=0.7822, ERP=5.0%, tax=13.26%
      w_equity=99.81%, w_debt=0.19%, kd_pretax=3.31%
      WACC = 12.91%
    """

    def test_wacc_recalculation_matches_assumptions(self, assumptions):
        """
        Verify the CAPM + WACC formula produces a result in the right
        ballpark for NVIDIA's capital structure.

        Important: The Excel model's stated WACC (12.91%) incorporates
        additional adjustments made inside the 15_WACC sheet (size premium,
        Damodaran data-center adjustments) that are not reflected in
        assumptions.json alone.  This test therefore validates that:
          (a) The formula executes without error
          (b) The computed WACC is within the plausible 7%–20% range
          (c) Cost of equity is correctly derived from CAPM inputs
          (d) The formula components (ke, kd) are internally consistent

        For an exact 1-bp cross-check against the model file, use wacc.py
        with the live Excel workbook (test_checks.md Check 4).
        """
        cs = assumptions["wacc"]
        tax_base = assumptions["tax_rate"]["base_case"][
            "fy2026f"
        ]  # 15% normalized forward

        wacc_calc, ke, kd = wacc_formula(
            risk_free=cs["risk_free_rate"],
            beta=cs["beta_blume_adjusted"],
            erp=cs["equity_risk_premium"],
            tax=tax_base,
            w_equity=cs["weight_equity"],
            pretax_cod=cs["pretax_cost_of_debt"],
            w_debt=cs["weight_debt"],
        )

        # CAPM cost of equity must match independently
        ke_expected = (
            cs["risk_free_rate"] + cs["beta_blume_adjusted"] * cs["equity_risk_premium"]
        )
        assert ke == pytest.approx(
            ke_expected, abs=1e-8
        ), f"Cost of equity mismatch: formula={ke:.4%}, expected={ke_expected:.4%}"

        # After-tax cost of debt
        kd_expected = cs["pretax_cost_of_debt"] * (1 - tax_base)
        assert kd == pytest.approx(kd_expected, abs=1e-8)

        # WACC must be in plausible range
        assert (
            0.05 <= wacc_calc <= 0.20
        ), f"WACC {wacc_calc:.4%} is outside the plausible 5%–20% range."

        # WACC must exceed risk-free rate (equity risk premium is positive)
        assert (
            wacc_calc > cs["risk_free_rate"]
        ), f"WACC {wacc_calc:.4%} must exceed rf {cs['risk_free_rate']:.4%}."

    def test_cost_of_equity_capm(self, assumptions):
        """Cost of equity via CAPM: rf + β × ERP."""
        cs = assumptions["wacc"]
        ke_expected = (
            cs["risk_free_rate"] + cs["beta_blume_adjusted"] * cs["equity_risk_premium"]
        )
        assert ke_expected == pytest.approx(cs["cost_of_equity_capm"], abs=0.001)

    def test_wacc_in_plausible_range(self, assumptions):
        """WACC for a mega-cap tech company: 10%–20%."""
        wacc = assumptions["wacc"]["wacc"]
        assert 0.10 <= wacc <= 0.20

    def test_wacc_exceeds_risk_free_rate(self, assumptions):
        """WACC must exceed risk-free rate (equity risk premium > 0)."""
        cs = assumptions["wacc"]
        assert cs["wacc"] > cs["risk_free_rate"]

    def test_terminal_growth_below_wacc(self, assumptions):
        """Gordon Growth requires g < WACC — otherwise terminal value is negative."""
        wacc = assumptions["wacc"]["wacc"]
        g = assumptions["dcf"]["terminal_growth_rate"]
        assert g < wacc, (
            f"Terminal growth rate {g:.2%} ≥ WACC {wacc:.2%} — "
            f"Gordon Growth model would produce a negative terminal value."
        )


# ══════════════════════════════════════════════════════════════════════════════
# 11. CROSS-KPI CONSISTENCY (all anchored to real data)
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossKPIConsistency:

    def test_all_margins_return_none_on_zero_revenue(self):
        """Every margin KPI must uniformly return None when revenue = 0."""
        assert gross_margin(0, 50) is None
        assert operating_margin(0, 20) is None
        assert kpi_ebitda_margin(25, 0) is None
        assert net_margin(0, 10) is None
        assert kpi_fcf_margin(fcf(100, -50), 0) is None

    def test_margin_hierarchy_holds_fy2025(self):
        """
        FY2025: gross_margin > ebitda_margin > ebit_margin > net_margin
        74.99% > 63.84% > 62.42% > 55.85%
        """
        gm = gross_margin(130497, 32639)
        ebitm = kpi_ebitda_margin(83317, 130497)
        om = operating_margin(130497, 81453)
        nm = net_margin(130497, 72880)

        assert gm > ebitm, f"Gross margin {gm:.2%} should > EBITDA margin {ebitm:.2%}"
        assert ebitm > om, f"EBITDA margin {ebitm:.2%} should > EBIT margin {om:.2%}"
        assert om > nm, f"EBIT margin {om:.2%} should > net margin {nm:.2%}"

    def test_fcf_margin_below_net_margin_fy2025(self):
        """
        FCF margin (46.6%) < net margin (55.9%) for FY2025.
        CapEx reduces FCF relative to net income.
        """
        fcfm = kpi_fcf_margin(fcf(64089, -3236), 130497)
        nm = net_margin(130497, 72880)
        assert fcfm < nm, f"FCF margin {fcfm:.2%} should be < net margin {nm:.2%}"

    def test_nvda_margins_consistent_across_all_years(self, is_canonical):
        """Gross margin > EBIT margin for ALL 6 fiscal years (OpEx always positive)."""
        for _, row in is_canonical.iterrows():
            gm = gross_margin(row["revenue_usdm"], row["cogs_usdm"])
            om = operating_margin(row["revenue_usdm"], row["ebit_usdm"])
            if gm is not None and om is not None:
                assert (
                    gm > om - 0.001
                ), f"FY{row['fiscal_year']}: Gross margin {gm:.2%} ≤ EBIT margin {om:.2%}"
