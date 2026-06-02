# Testing Strategy

## Philosophy

A financial model that isn't tested is a liability. **Two things must both be true:**
1. The code must be correct (unit tests catch code bugs)
2. The numbers must be correct (golden output tests catch financial errors)

### Known-Value Testing

Rather than synthetic test data, we embed actual NVIDIA FY2025 10-K figures directly in tests. This approach:
- Validates that the model reproduces historical reality
- Provides a regression baseline (if the model suddenly produces wrong numbers, the golden tests fail immediately)
- Creates an audit trail (the 10-K page number is cited in the test)

### Invariant Testing

Three mathematical identities must ALWAYS hold, regardless of scenario or assumptions:

1. **Balance Sheet Identity:** Total Assets = Total Liabilities + Shareholders' Equity
2. **Cash Flow Reconciliation:** Ending Cash = Beginning Cash + Net Change in Cash  
3. **Retained Earnings Roll-Forward:** RE_end = RE_begin + Net Income − Dividends

These aren't assumptions — they're mathematical definitions. A model that violates them is wrong by definition.

### Edge-Case Completeness

Financial models have many edge cases:
- Division by zero (e.g., FCF margin when revenue is zero in a downside scenario)
- Missing data (e.g., segment revenue for a division that didn't exist)
- Extreme assumptions (e.g., WACC of 5% or 20%)

Tests must verify that the model handles these gracefully (returns `None` for undefined metrics, not `NaN` or exceptions).

---

## Test Suite Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── test_etl_pipeline.py           # ETL: load, transform, validate, clean
├── test_wacc.py                   # WACC: CAPM, Blume adjustment, net debt
├── test_income_statement.py       # IS: revenue, gross profit, EBIT, NI
├── test_balance_sheet.py          # BS: roll-forward, RE plug, invariant
├── test_cash_flow.py              # CF: indirect method, net cash reconciliation
├── test_fcff.py                   # FCFF: NOPAT, formula, ΔNWC
├── test_dcf_valuation.py          # DCF: PV, TV, equity bridge, sensitivity grid
├── test_scenario_engine.py        # Scenario: deep_merge, immutability, ordering
├── test_kpis.py                   # KPIs: all 8 functions, safe_divide, None returns
├── test_financial_invariants.py   # ★ 3 invariants at ±$0.01M (all forecast years)
├── test_golden_output.py          # ★ Regression: known 10-K values vs model
├── test_safe_math.py              # safe_divide edge cases (zero, None, negative)
└── test_export.py                 # PDF/PPTX: file created, size > 0
```

---

## Running Tests

```bash
make test                    # Full suite + coverage report
make test-fast               # Exclude @pytest.mark.integration
make test-invariants         # test_financial_invariants.py only
make test-golden             # test_golden_output.py only
make test-modeling           # @pytest.mark.modeling only

pytest tests/ -v --tb=long   # Verbose, full traceback
pytest tests/test_wacc.py    # Single file
```

---

## Financial Invariant Tests

**File:** `tests/test_financial_invariants.py`  
**Marker:** `@pytest.mark.invariants`  
**Tolerance:** ±$0.01M ($10,000)  
**Frequency:** Run on every model execution

### The 3 Invariants

These must hold for **every forecast year (FY2026–FY2030)**:

#### Invariant 1: Balance Sheet Balances

```
Total Assets = Total Liabilities + Total Equity
```

The balance sheet is a fundamental accounting identity. If it doesn't balance, the model has a bug.

**Test Example:**
```python
def test_balance_sheet_balances_all_years():
    """BS must balance in every forecast year. Tolerance: ±$0.01M."""
    model_output = run_full_model(assumptions)
    bs = model_output['balance_sheet']
    
    for year in ['FY2026', 'FY2027', 'FY2028', 'FY2029', 'FY2030']:
        assets = bs[year]['total_assets']
        liabilities = bs[year]['total_liabilities']
        equity = bs[year]['total_equity']
        
        imbalance = assets - (liabilities + equity)
        assert abs(imbalance) <= 0.01, (
            f"BS out of balance in {year}: "
            f"Assets=${assets:.2f}M, L+E=${liabilities + equity:.2f}M, "
            f"gap=${imbalance:.4f}M"
        )
```

#### Invariant 2: Cash Flow Reconciliation

```
Ending Cash = Beginning Cash + Net Change in Cash
```

If the cash flow statement is computed correctly (CFO + CFI + CFF), the ending cash balance must match the beginning balance plus the net change.

**Test Example:**
```python
def test_cash_flow_reconciles_all_years():
    """CF must reconcile in every forecast year. Tolerance: ±$0.01M."""
    model_output = run_full_model(assumptions)
    cf = model_output['cash_flow']
    
    beginning_cash = model_output['balance_sheet']['FY2025']['cash']
    
    for year in ['FY2026', 'FY2027', 'FY2028', 'FY2029', 'FY2030']:
        net_change = cf[year]['net_change_cash']
        ending_cash = cf[year]['ending_cash']
        
        expected_ending = beginning_cash + net_change
        diff = ending_cash - expected_ending
        
        assert abs(diff) <= 0.01, (
            f"CF mismatch in {year}: "
            f"ending_cash=${ending_cash:.2f}M, "
            f"beginning+change=${expected_ending:.2f}M, "
            f"diff=${diff:.4f}M"
        )
        
        beginning_cash = ending_cash
```

#### Invariant 3: Retained Earnings Roll-Forward

```
RE_end = RE_begin + Net Income − Dividends
```

Retained earnings changes only by net income (added) and dividends (subtracted). This is the reconciliation between income statement and balance sheet.

**Test Example:**
```python
def test_retained_earnings_rolls_forward_correctly():
    """RE must roll forward consistently via NI − Dividends."""
    model_output = run_full_model(assumptions)
    
    re_beginning_fy26 = model_output['balance_sheet']['FY2025']['retained_earnings']
    
    for year in ['FY2026', 'FY2027', 'FY2028', 'FY2029', 'FY2030']:
        ni = model_output['income_statement'][year]['net_income']
        dividends = model_output['cash_flow'][year]['dividends_paid']
        re_ending = model_output['balance_sheet'][year]['retained_earnings']
        
        expected_re_ending = re_beginning_fy26 + ni - dividends
        diff = re_ending - expected_re_ending
        
        assert abs(diff) <= 0.01, (
            f"RE mismatch in {year}: "
            f"RE_end=${re_ending:.2f}M, "
            f"RE_begin+NI−Div=${expected_re_ending:.2f}M, "
            f"diff=${diff:.4f}M"
        )
        
        re_beginning_fy26 = re_ending
```

---

## Golden Output Tests (FY2025 Ground Truth)

**File:** `tests/test_golden_output.py`  
**Marker:** `@pytest.mark.golden`

Known NVIDIA 10-K values embedded as test assertions. Sources cited inline with filing page numbers.

### FY2025 Ground-Truth Fixture

```python
NVIDIA_FY2025_ACTUALS = {
    "revenue_usdm": 130497,          # 10-K p. F-4, Consolidated Statements of Income
    "cogs_usdm": 32639,              # 10-K p. F-4
    "gross_profit_usdm": 97858,      # Derived: Revenue - COGS
    "rd_expense_usdm": 8752,         # 10-K p. F-4
    "sga_expense_usdm": 9088,        # 10-K p. F-4
    "ebit_usdm": 80018,              # Derived: Gross profit - (R&D + SG&A)
    "net_income_usdm": 72880,        # 10-K p. F-4
    "cfo_usdm": 64089,               # 10-K p. F-7, Consolidated Statements of Cash Flows
    "capex_usdm": 1069,              # 10-K p. F-7, "Purchases of property and equipment"
    "fcf_usdm": 63020,               # Derived: CFO - CapEx
    "total_assets_usdm": 111601,     # 10-K p. F-5, Consolidated Balance Sheets
    "total_equity_usdm": 65728,      # 10-K p. F-5
    "cash_usdm": 34831,              # 10-K p. F-5
    "lt_debt_usdm": 1891,            # 10-K p. F-5
    "net_debt_usdm": -32940,         # Derived: LT Debt - Cash (negative = net cash)
    "accounts_receivable_usdm": 23065,  # 10-K p. F-5
    "inventory_usdm": 7932,          # 10-K p. F-5
    "accounts_payable_usdm": 6310,   # 10-K p. F-5
}
```

### Test Examples

```python
def test_fy2025_revenue_matches_10k():
    """Revenue FY2025 must match NVIDIA 10-K filing."""
    model_output = load_historical_actuals()
    
    assert abs(model_output['actuals']['FY2025']['revenue_usdm'] - 130497) <= 1.0, (
        "FY2025 revenue mismatch. "
        "Expected: $130,497M (10-K p. F-4). "
        "Check data/raw/income_statement_fy2020_fy2025.csv."
    )

def test_fy2025_gross_margin_matches_10k():
    """Gross margin FY2025 must match derived from 10-K."""
    model_output = load_historical_actuals()
    
    gm_actual = model_output['actuals']['FY2025']['gross_margin_pct']
    gm_expected = 97858 / 130497  # From 10-K: Gross profit / Revenue
    
    assert abs(gm_actual - gm_expected) <= 0.001, (
        "FY2025 gross margin mismatch. "
        "Expected: 75.0% (from 10-K). "
        "Actual: {:.2%}".format(gm_actual)
    )

def test_fy2025_fcf_matches_10k():
    """Free cash flow FY2025 must be CFO - CapEx."""
    model_output = load_historical_actuals()
    
    fcf_actual = model_output['actuals']['FY2025']['fcf_usdm']
    fcf_expected = 64089 - 1069  # CFO - CapEx from 10-K
    
    assert abs(fcf_actual - fcf_expected) <= 1.0, (
        "FY2025 FCF mismatch. "
        "Expected: $63,020M (CFO $64,089M - CapEx $1,069M). "
        "Actual: ${:.0f}M".format(fcf_actual)
    )

def test_wacc_computation_matches_capm():
    """WACC must be computed correctly via CAPM."""
    wacc_result = compute_wacc(
        risk_free_rate=0.0407,
        beta_adjusted=1.7728,
        equity_risk_premium=0.0500
    )
    
    expected_wacc = 0.0407 + 1.7728 * 0.0500  # Rf + β × ERP
    
    assert abs(wacc_result['wacc'] - expected_wacc) <= 0.0001, (
        "WACC CAPM formula error. "
        "Expected: {:.4%}. Actual: {:.4%}".format(expected_wacc, wacc_result['wacc'])
    )

def test_implied_share_price_base_case():
    """DCF implied price should be approximately $109.16 for base case."""
    dcf_result = run_dcf_valuation(
        assumptions=load_assumptions('base'),
        forecast_fcf=base_fcf_projections()
    )
    
    assert abs(dcf_result['implied_price'] - 109.16) <= 0.50, (
        "DCF implied price mismatch. "
        "Expected: $109.16. "
        "Actual: ${:.2f}".format(dcf_result['implied_price'])
    )
```

---

## KPI Validation Examples

All 8 KPI functions must:
1. Handle `None` inputs gracefully (return `None`, not exception)
2. Use `safe_divide()` for all divisions
3. Return exactly a scalar (not DataFrame, not array)
4. Match NVIDIA FY2025 benchmarks

```python
def test_safe_divide_handles_zero_denominator():
    """safe_divide(x, 0) must return None, never raise."""
    result = safe_divide(numerator=100, denominator=0)
    assert result is None, "Division by zero should return None"

def test_safe_divide_handles_none_inputs():
    """safe_divide(None, x) must return None."""
    result = safe_divide(numerator=None, denominator=50)
    assert result is None, "None input should return None"

def test_gross_margin_fy2025():
    """Gross margin FY2025 should be 75.0% (NVIDIA actual)."""
    gm = calculate_gross_margin(
        revenue_usdm=130497,
        cogs_usdm=32639
    )
    assert abs(gm - 0.750) <= 0.001, (
        f"Expected: 75.0%. Actual: {gm:.2%}"
    )

def test_fcf_margin_fy2025():
    """FCF margin FY2025 should be 48.3% (NVIDIA actual)."""
    fcf_margin = calculate_fcf_margin(
        fcf_usdm=63020,
        revenue_usdm=130497
    )
    assert abs(fcf_margin - 0.483) <= 0.001

def test_kpi_signal_traffic_lights():
    """KPI signals must map to correct traffic light."""
    # Gross margin 75% (NVIDIA FY25) → GREEN
    signal = get_signal('gross_margin', value=0.750)
    assert signal == 'green', f"Expected green, got {signal}"
    
    # Gross margin 45% → AMBER
    signal = get_signal('gross_margin', value=0.450)
    assert signal == 'amber', f"Expected amber, got {signal}"
    
    # Gross margin 30% → RED
    signal = get_signal('gross_margin', value=0.300)
    assert signal == 'red', f"Expected red, got {signal}"
```

---

## Coverage Targets

| Module | Target |
|---|---|
| `src/kpi/` | ≥ 95% |
| `src/modeling/` | ≥ 85% |
| `src/etl/` | ≥ 80% |
| `src/scenarios/` | ≥ 90% |
| `src/utils/` | ≥ 95% |
| `src/output/` | ≥ 70% |
| Overall | ≥ 70% |

Run `make test` to generate `htmlcov/index.html` coverage report.

---

## CI Integration

GitHub Actions runs the full test suite on every push:
1. Lint (ruff)
2. Test (pytest + coverage)
3. **Invariants** (±$0.01M checks — MUST PASS)
4. Docker build (main branch only)

If invariants fail, the PR is blocked. This ensures financial correctness at the repository level.
