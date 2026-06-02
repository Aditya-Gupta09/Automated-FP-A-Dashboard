import pytest
import sys

sys.path.insert(0, "src")

from src.modeling.engine import run_pipeline


@pytest.mark.parametrize("scenario", ["base", "upside", "downside"])
def test_scenario_runs_and_reconciles(scenario):
    r = run_pipeline(scenario)

    assert "dcf_valuation" in r
    assert "reconciliation" in r

    status = r["reconciliation"]["summary"]["status"]
    assert status == "PASS"
