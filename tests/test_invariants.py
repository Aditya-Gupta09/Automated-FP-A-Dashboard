import sys
import pandas as pd

sys.path.insert(0, "src")
from src.modeling.engine import run_pipeline

SCENARIOS = ["base", "upside", "downside"]
YEARS = None  # dynamic
TOL = 1e-3


def _to_df(data):
    return pd.DataFrame(data).set_index("fiscal_year")


def test_balance_sheet_identity():
    for scenario in SCENARIOS:
        r = run_pipeline(scenario)
        bs = _to_df(r["balance_sheet"])

        for year in bs.index:
            row = bs.loc[year]

            assets = row["total_assets_usdm"]
            liabilities = row["total_liabilities_usdm"]
            equity = row["shareholders_equity_usdm"]

            assert abs(assets - (liabilities + equity)) < TOL


def test_cash_flow_identity():
    for scenario in SCENARIOS:
        r = run_pipeline(scenario)
        cf = _to_df(r["cash_flow_statement"])

        for year in cf.index:
            row = cf.loc[year]

            calc = row["cfo_usdm"] + row["cfi_usdm"] + row["cff_usdm"]
            assert abs(calc - row["net_change_cash_usdm"]) < TOL


def test_dcf_consistency():
    for scenario in SCENARIOS:
        r = run_pipeline(scenario)
        dcf = r["dcf_valuation"]

        ev_calc = dcf["sum_pv_fcf_usdm"] + dcf["pv_terminal_value_usdm"]
        assert abs(ev_calc - dcf["enterprise_value_usdm"]) < TOL
