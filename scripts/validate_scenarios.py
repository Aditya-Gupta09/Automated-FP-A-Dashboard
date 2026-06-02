import os
import sys

sys.path.insert(0, os.path.abspath("src"))
from src.modeling.engine import run_pipeline

results = {s: run_pipeline(s) for s in ["base", "upside", "downside"]}

base = results["base"]["dcf_valuation"]["implied_share_price_usd"]
upside = results["upside"]["dcf_valuation"]["implied_share_price_usd"]
downside = results["downside"]["dcf_valuation"]["implied_share_price_usd"]

# -------------------------------
# 1. Base accuracy (absolute)
# -------------------------------
BASE_TARGET = 109.26
BASE_TOL = 1.0

base_pass = abs(base - BASE_TARGET) < BASE_TOL

# -------------------------------
# 2. Scenario ordering (relative)
# -------------------------------
ordering_pass = upside > base > downside

# -------------------------------
# 3. Sensitivity sanity (optional)
# -------------------------------
sensitivity_pass = (upside / base > 1.1) and (downside / base < 0.9)

# -------------------------------
# OUTPUT
# -------------------------------
print(
    f"Base Price:     ${base:.2f}  | {'PASS' if base_pass else 'FAIL'} (target ~ {BASE_TARGET})"
)
print(f"Upside Price:   ${upside:.2f} | (relative check)")
print(f"Downside Price: ${downside:.2f} | (relative check)")
print(
    f"Scenario Ordering: {'PASS' if ordering_pass else 'FAIL'} (upside > base > downside)"
)
print(f"Sensitivity Check: {'PASS' if sensitivity_pass else 'WARN'}")
