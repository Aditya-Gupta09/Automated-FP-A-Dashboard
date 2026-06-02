# Excel → Python Module Mapping
# NVIDIA DCF Financial Model
# Version: v1.0 | Source: Company_Valuation_Model.xlsx (24 tabs)
# ─────────────────────────────────────────────────────────────────────────────

## CANONICAL MAPPING TABLE

| Excel Tab(s)              | Python Module                          | Responsibility                                    |
|---------------------------|----------------------------------------|---------------------------------------------------|
| 01_Historical_IS          | src/modeling/income_statement.py       | Historical IS + all projected IS line items       |
| 04a_Projection_IS         | src/modeling/income_statement.py       | Revenue build + margins + ETR + net income        |
| 02_Historical_BS          | src/modeling/balance_sheet.py          | Historical BS + projected BS roll-forward         |
| 04b_Projection_BS         | src/modeling/balance_sheet.py          | BS projection driven by WC + DA + debt schedules  |
| 03_Historical_CF          | src/modeling/cashflow.py               | Historical CF + projected CF statement            |
| 04c_Projection_CF         | src/modeling/cashflow.py               | CFO/CFI/CFF projection + net change in cash       |
| 11_DA + 12_FixedAssets    | src/modeling/depreciation.py           | Straight-line D&A schedule + fixed asset roll     |
| 09_WorkingCapital         | src/modeling/working_capital.py        | NWC schedule: DSO/DIO/DPO → AR/Inv/AP/Prepaid     |
| 15_WACC + 14_Beta         | src/modeling/wacc.py                   | CAPM + WACC recalculation + cross-check           |
| 05a_FCFF                  | src/modeling/fcff.py                   | EBIT → NOPAT → FCFF unlevered free cash flow      |
| 05b_DCF + 06_Sensitivity  | src/modeling/dcf_valuation.py          | TV + PV + EV bridge + sensitivity grids           |
| 13_DebtSchedule           | src/modeling/balance_sheet.py          | Debt roll-forward (embedded in BS module)         |
| 17_ComparableAnalysis     | src/modeling/comps.py                  | Peer multiples + implied prices                   |
| 99_Validation             | src/modeling/reconciliation.py         | BS tie + CF recon + revenue cross-check           |
| 00_Assumptions            | config/assumptions.json                | All hardcoded inputs — NOT a Python module        |
| run_all.py (orchestrator) | src/modeling/engine.py                 | Pipeline orchestrator — calls all modules         |

---

## MODULE ARCHITECTURE

```
config/
  assumptions.json          ← All hardcoded numbers (Task 1)
  settings.yaml             ← App settings

src/
  modeling/
    engine.py               ← Orchestrator — calls all modules in order
    income_statement.py     ← IS: revenue build → gross profit → EBIT → net income
    balance_sheet.py        ← BS: assets / liabilities / equity roll-forward
    cashflow.py             ← CF: CFO / CFI / CFF projection
    depreciation.py         ← D&A: straight-line schedule + fixed asset roll
    working_capital.py      ← NWC: DSO/DIO/DPO → AR/Inv/AP
    fcff.py                 ← FCFF: NOPAT + DA - CapEx - ΔNWC
    dcf_valuation.py        ← DCF: Gordon Growth TV + EV bridge + sensitivity
    wacc.py                 ← WACC: CAPM recalc + named range read + cross-check
    comps.py                ← Comps: peer multiples → implied NVIDIA prices
    reconciliation.py       ← Invariants: BS tie / CF recon / revenue cross-check
```

---

## EXECUTION ORDER (CRITICAL)

```
engine.py execution sequence:

  1. wacc.py              → produces: wacc (scalar)
  2. income_statement.py  → produces: IS DataFrame (FY2026–2030)
  3. depreciation.py      → produces: DA schedule (feeds IS + BS + FCFF)
  4. working_capital.py   → produces: NWC schedule (feeds BS + FCFF)
  5. balance_sheet.py     → produces: BS DataFrame (FY2026–2030)
  6. cashflow.py          → produces: CF DataFrame (FY2026–2030)
  7. fcff.py              → produces: FCFF DataFrame (FY2026–2030)
  8. dcf_valuation.py     → produces: DCF valuation dict (scalar outputs)
  9. comps.py             → produces: comps_results.json
  10. reconciliation.py   → validates: BS tie / CF / revenue cross-checks
```

---

## DEPENDENCY GRAPH

```
assumptions.json
    │
    ├─→ wacc.py
    │       └─→ dcf_valuation.py (WACC input)
    │
    ├─→ income_statement.py
    │       ├── revenue build (segment × growth rates)
    │       ├── gross margin % × revenue = COGS / gross profit
    │       ├── R&D % + SG&A % = total opex
    │       ├── EBIT = gross profit - opex
    │       ├── interest income (cash × yield)
    │       ├── EBT = EBIT + interest income + interest expense + other
    │       └── net income = EBT × (1 - ETR)
    │                └─→ balance_sheet.py (retained earnings)
    │                └─→ fcff.py (EBIT input)
    │
    ├─→ depreciation.py
    │       ├── capex vintage roll-forward (straight line, 5yr)
    │       └── DA schedule
    │               └─→ income_statement.py (EBITDA)
    │               └─→ balance_sheet.py (PP&E net)
    │               └─→ fcff.py (DA add-back)
    │
    ├─→ working_capital.py
    │       ├── AR = (DSO/365) × Revenue
    │       ├── Inventory = (DIO/365) × COGS
    │       ├── Prepaid = prepaid_pct × opex
    │       ├── AP = (DPO/365) × COGS
    │       ├── Accrued = accrued_pct × (COGS + opex)
    │       └── NWC = assets - liabilities
    │               └─→ balance_sheet.py (current assets/liabilities)
    │               └─→ fcff.py (ΔNWC)
    │               └─→ cashflow.py (operating WC changes)
    │
    ├─→ balance_sheet.py
    │       ├── cash = revenue × cash_pct_of_revenue
    │       ├── current assets = cash + AR + inventory + prepaid
    │       ├── PP&E net = from depreciation.py
    │       ├── AP + accrued = from working_capital.py
    │       ├── debt = from debt schedule
    │       ├── equity = prior equity + net income - buybacks + SBC
    │       └── PLUG: retained_earnings = prior + net_income - dividends
    │               └─→ reconciliation.py (BS tie check)
    │
    ├─→ cashflow.py
    │       ├── CFO = net income + DA + Δworking capital items
    │       ├── CFI = -capex + other investing
    │       ├── CFF = debt issuance - repayment - dividends - buybacks
    │       └── net change = CFO + CFI + CFF
    │               └─→ reconciliation.py (CF recon check)
    │
    ├─→ fcff.py
    │       ├── NOPAT = EBIT × (1 - ETR)
    │       ├── FCFF = NOPAT + DA - |CapEx| - ΔNWC
    │       └── PV_FCFF = FCFF / (1 + WACC)^year
    │               └─→ dcf_valuation.py
    │
    ├─→ dcf_valuation.py
    │       ├── sum_pv_fcf = Σ PV_FCFF years 1–5
    │       ├── terminal_value = FCF5 × (1+g) / (WACC - g)
    │       ├── pv_tv = terminal_value / (1 + WACC)^5
    │       ├── enterprise_value = sum_pv_fcf + pv_tv
    │       ├── equity_value = EV - net_debt
    │       └── implied_price = equity_value / shares
    │
    └─→ comps.py (independent — reads comps_data.csv via canonical layer)
            ├── loads from: data/processed/comps_data.csv
            ├── computes: EV/Revenue, EV/EBITDA, P/E per peer
            ├── stats: high/p75/mean/median/p25/low
            └── implied_prices via EV bridge and P/E
```

---

## MODULE FUNCTION SIGNATURES

### engine.py
```python
def run_pipeline(scenario: str = "base", verbose: bool = False) -> dict
    """
    Master orchestrator. Runs all modules in dependency order.
    Returns full model output dict.
    """
```

### income_statement.py
```python
def build_revenue(assumptions: dict, scenario: str) -> pd.DataFrame
def build_income_statement(revenue: pd.DataFrame, assumptions: dict, scenario: str) -> pd.DataFrame
```

### balance_sheet.py
```python
def build_balance_sheet(is_df: pd.DataFrame, wc_df: pd.DataFrame,
                        da_df: pd.DataFrame, assumptions: dict, scenario: str) -> pd.DataFrame
def reconcile_balance_sheet(bs_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]
```

### cashflow.py
```python
def build_cashflow(is_df: pd.DataFrame, bs_df: pd.DataFrame,
                   wc_df: pd.DataFrame, da_df: pd.DataFrame,
                   assumptions: dict, scenario: str) -> pd.DataFrame
```

### depreciation.py
```python
def build_da_schedule(capex_series: pd.Series, assumptions: dict) -> pd.DataFrame
    """
    Straight-line D&A roll-forward.
    Each CapEx vintage depreciated over useful_life_years.
    Returns DataFrame with columns: fiscal_year, da_usdm, cumulative_da
    """
```

### working_capital.py
```python
def build_nwc_schedule(is_df: pd.DataFrame, assumptions: dict, scenario: str) -> pd.DataFrame
    """
    Computes AR, Inventory, Prepaid, AP, Accrued from DSO/DIO/DPO targets.
    Returns DataFrame including NWC and change_in_nwc per year.
    """
```

### wacc.py  (refactored — Task 5)
```python
def compute_wacc(assumptions: dict) -> dict
def read_wacc_from_model(model_path: str) -> dict
def cross_check_wacc(computed: float, model: float, tolerance_bps: float) -> bool
```

### fcff.py
```python
def build_fcff(is_df: pd.DataFrame, da_df: pd.DataFrame,
               wc_df: pd.DataFrame, assumptions: dict, scenario: str) -> pd.DataFrame
```

### dcf_valuation.py
```python
def discount_cash_flows(fcff: pd.Series, wacc: float) -> pd.Series
def compute_terminal_value(fcf_final: float, wacc: float, g: float) -> float
def compute_ev_bridge(sum_pv_fcf: float, pv_tv: float, net_debt: float,
                      shares: float) -> dict
def run_sensitivity(fcff_final: float, wacc_range: list, g_range: list) -> pd.DataFrame
```

### comps.py  (refactored — Task 6)
```python
def load_comps_from_canonical(comps_csv_path: str) -> pd.DataFrame
def compute_peer_multiples(comps_df: pd.DataFrame) -> pd.DataFrame
def compute_implied_prices(multiples_df: pd.DataFrame, subject: dict) -> dict
def run_comps(comps_csv_path: str, subject: dict) -> dict
```

### reconciliation.py
```python
def check_balance_sheet_tie(bs_df: pd.DataFrame, tolerance: float = 0.01) -> dict
def check_cashflow_reconciliation(cf_df: pd.DataFrame, tolerance: float = 0.01) -> dict
def check_revenue_crosscheck(is_df: pd.DataFrame, fcff_df: pd.DataFrame,
                             tolerance: float = 0.01) -> dict
def run_all_checks(is_df, bs_df, cf_df, fcff_df) -> dict
```

---

## RULE: ONE MODULE = ONE RESPONSIBILITY

- `income_statement.py` does NOT touch the balance sheet
- `balance_sheet.py` does NOT recalculate revenue
- `fcff.py` does NOT compute WACC
- `wacc.py` does NOT read historical financial data
- `reconciliation.py` does NOT produce outputs — only validates
- `comps.py` does NOT read from Excel directly — only from canonical CSV
- `engine.py` is the ONLY module that calls other modules
