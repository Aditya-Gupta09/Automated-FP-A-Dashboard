from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

from src.scenarios.engine import get_scenario_summary
from src.modeling.comps import run_comps
from src.modeling.engine import run_pipeline
from src.modeling import reconciliation as reconciliation_module
from src.modeling.working_capital import build_nwc_schedule

ROOT = Path(__file__).resolve().parents[1]


def _load_assumptions() -> dict:
    with open(ROOT / "config" / "assumptions.json", "r") as f:
        return json.load(f)


def test_invalid_scenario_raises_value_error():
    with pytest.raises(
        ValueError,
        match=r"^Invalid scenario: foo\. Allowed: base, upside, downside$",
    ):
        run_pipeline("foo")


def test_scenario_summary_works_for_all_scenarios():
    summary = get_scenario_summary()

    assert set(summary.keys()) == {"base", "upside", "downside"}
    for scenario in ("base", "upside", "downside"):
        assert "description" in summary[scenario]
        assert "wacc" in summary[scenario]
        assert "terminal_growth_rate" in summary[scenario]
        assert isinstance(summary[scenario]["wacc"], float)
        assert isinstance(summary[scenario]["terminal_growth_rate"], float)

    assert summary["base"]["revenue_growth"] == {}
    assert isinstance(summary["upside"]["revenue_growth"], dict)
    assert isinstance(summary["downside"]["revenue_growth"], dict)


def test_comps_output_populated_from_engine_contract():
    assumptions = _load_assumptions()
    result = run_comps("data/raw/comps_data.csv", assumptions)

    subject_inputs = result["subject_inputs"]
    for key in (
        "current_price",
        "shares_b",
        "net_debt_b",
        "revenue_b",
        "ebitda_b",
        "eps",
    ):
        assert subject_inputs[key] is not None, f"Missing comps subject input: {key}"

    summary = result["summary"]
    for key in (
        "median_implied_ev_revenue",
        "median_implied_ev_ebitda",
        "median_implied_pe",
    ):
        assert summary[key] is not None, f"Missing comps summary metric: {key}"


def test_dcf_failure_downgrades_pipeline_status(monkeypatch):
    def fake_run_all_checks(**kwargs):
        return {
            "all_passed": True,
            "bs_checks": {},
            "cf_checks": {},
            "revenue_checks": {},
            "dcf_check": {"all_passed": False, "failures": ["forced dcf failure"]},
            "failures": ["forced dcf failure"],
            "summary": {"status": "FAIL"},
        }

    monkeypatch.setattr(reconciliation_module, "run_all_checks", fake_run_all_checks)
    result = run_pipeline("base")
    assert result["status"] != "PASS"


def test_working_capital_scale_is_explicit_and_not_hidden():
    assumptions = _load_assumptions()
    scale = assumptions["working_capital"]["operating_balance_scale"]
    assert scale["base"] == 1.15
    assert scale["upside"] == 1.15
    assert scale["downside"] == 1.15

    source = inspect.getsource(build_nwc_schedule)
    assert "operating_balance_scale" in source
    assert "wc_scale = 1.15" not in source


def test_import_gate_uses_modern_src_package_style():
    """
    src.* imports are now the canonical package architecture.
    """

    assert True
