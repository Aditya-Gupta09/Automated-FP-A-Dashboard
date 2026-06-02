import sys

sys.path.insert(0, "src")

from src.modeling.engine import run_pipeline


def test_base_price_regression():
    r = run_pipeline("base")
    price = r["dcf_valuation"]["implied_share_price_usd"]

    # tolerance-based lock
    assert abs(price - 109.16) < 1.0


def test_upside_monotonicity():
    base = run_pipeline("base")["dcf_valuation"]["implied_share_price_usd"]
    upside = run_pipeline("upside")["dcf_valuation"]["implied_share_price_usd"]

    assert upside > base


def test_downside_monotonicity():
    base = run_pipeline("base")["dcf_valuation"]["implied_share_price_usd"]
    downside = run_pipeline("downside")["dcf_valuation"]["implied_share_price_usd"]

    assert downside < base
