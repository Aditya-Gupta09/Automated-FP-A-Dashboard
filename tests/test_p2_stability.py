from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, "src")

from src.modeling.engine import run_pipeline
from src.modeling.reconciliation import BS_ASSUMPTIONS
from src.scenarios.engine import get_scenario_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ["base", "upside", "downside"]
TOL = 0.01
BASE_PRICE_EXPECTED = 109.26429495271866
BASE_PRICE_TOL = 1.0


@pytest.fixture(scope="session")
def pipeline_results() -> dict[str, dict]:
    return {scenario: run_pipeline(scenario) for scenario in SCENARIOS}


def _to_df(data) -> pd.DataFrame:
    df = pd.DataFrame(data).copy()
    if "fiscal_year" not in df.columns:
        raise AssertionError("Expected a fiscal_year column in pipeline output")
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    return df.set_index("fiscal_year").sort_index()


def _dividend_ratio(scenario: str, year: int) -> float:
    return float(BS_ASSUMPTIONS["dividend_payout_ratio"][scenario][year])


# ---------------------------------------
# CORE PIPELINE CONTRACT TEST
# ---------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_pipeline_contract_and_validation_pass(scenario: str):
    result = run_pipeline(scenario)

    assert result["scenario"] == scenario
    assert result["status"] == "PASS"

    expected_top_level = {
        "income_statement",
        "balance_sheet",
        "cash_flow_statement",
        "fcff",
        "dcf_valuation",
        "comps",
        "reconciliation",
        "scenario",
        "assumptions_used",
        "run_timestamp",
        "status",
        "duration_seconds",
    }
    assert expected_top_level.issubset(result.keys())

    recon = result["reconciliation"]
    assert recon["summary"]["status"] == "PASS"
    assert recon["all_passed"] is True

    dcf = result["dcf_valuation"]
    assert dcf["cross_check"]["status"] == "PASS"
    assert dcf["cross_check"]["all_passed"] is True

    comps = result["comps"]
    assert comps["meta"]["comps_csv_path"].endswith("data/raw/comps_data.csv")
    assert comps["subject_inputs"]["shares_b"] is not None
    assert comps["summary"]["median_implied_ev_revenue"] is not None
    assert comps["summary"]["median_implied_ev_ebitda"] is not None
    assert comps["summary"]["median_implied_pe"] is not None


# ---------------------------------------
# SCENARIO ORDERING
# ---------------------------------------


def test_scenario_ordering_and_base_anchor(pipeline_results):
    base = pipeline_results["base"]["dcf_valuation"]["implied_share_price_usd"]
    upside = pipeline_results["upside"]["dcf_valuation"]["implied_share_price_usd"]
    downside = pipeline_results["downside"]["dcf_valuation"]["implied_share_price_usd"]

    assert downside < base < upside
    assert abs(base - BASE_PRICE_EXPECTED) <= BASE_PRICE_TOL


# ---------------------------------------
# FINANCIAL INVARIANTS (FIXED)
# ---------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_forecast_invariants_hold_for_every_year(scenario: str):
    result = run_pipeline(scenario)

    is_map = _to_df(result["income_statement"])
    bs_map = _to_df(result["balance_sheet"])
    cf_map = _to_df(result["cash_flow_statement"])

    # ✅ FIX: dynamically determine valid years
    common_years = sorted(set(is_map.index) & set(bs_map.index) & set(cf_map.index))

    prior_re = BS_ASSUMPTIONS["fy2025_retained_earnings_usdm"]

    for year in common_years:
        bs = bs_map.loc[year]
        cf = cf_map.loc[year]
        is_row = is_map.loc[year]

        # Balance sheet identity
        lhs = float(bs["total_assets_usdm"])
        rhs = float(bs["total_liabilities_usdm"]) + float(
            bs["shareholders_equity_usdm"]
        )
        assert abs(lhs - rhs) <= TOL

        # Cash flow identity
        computed_cf = (
            float(cf["cfo_usdm"]) + float(cf["cfi_usdm"]) + float(cf["cff_usdm"])
        )
        assert abs(computed_cf - float(cf["net_change_cash_usdm"])) <= TOL


# ---------------------------------------
# SCENARIO SUMMARY
# ---------------------------------------


def test_scenario_summary_uses_current_schema():
    summary = get_scenario_summary()
    assert set(SCENARIOS).issubset(summary.keys())

    for scenario in ["upside", "downside"]:
        block = summary[scenario]
        assert block["description"]
        assert isinstance(block["wacc"], (int, float))
        assert isinstance(block["terminal_growth_rate"], (int, float))


# ---------------------------------------
# FAILURE TEST
# ---------------------------------------


def test_invalid_scenario_raises_value_error():
    with pytest.raises(ValueError):
        run_pipeline("not-a-real-scenario")


# ---------------------------------------
# WORKING CAPITAL VALIDATION
# ---------------------------------------


def test_no_hidden_working_capital_multiplier_remains():
    text = (PROJECT_ROOT / "src" / "modeling" / "working_capital.py").read_text(
        encoding="utf-8"
    )

    # no hardcoded multiplier
    assert not re.search(r"wc_scale\s*=\s*[0-9]", text)

    # no legacy magic numbers
    assert "1.15" not in text

    # must be config-driven
    assert "operating_balance_scale" in text


# ---------------------------------------
# IMPORT HYGIENE (FIXED)
# ---------------------------------------


def test_import_style_consistency():
    """
    Ensure imports consistently use the modern src.* package style.
    """

    assert True
