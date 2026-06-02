# Financial Model Methodology

## Overview

This document describes the complete financial model methodology used in the NVIDIA FP&A Platform. The model is a 5-year FCFF-based DCF with a Gordon Growth terminal value, built on auditable SEC 10-K data.

---

## 1. Model Architecture (10-step engine)

The `src/modeling/engine.py` orchestrator runs these steps in strict order:

```
Step 1:  WACC computation        (wacc.py)
Step 2:  Income statement        (income_statement.py)
Step 3:  D&A schedule            (income_statement.py)
Step 4:  NWC schedule            (balance_sheet.py)
Step 5:  Balance sheet (pass 1)  (balance_sheet.py) — provisional, no RE plug
Step 6:  Cash flow statement     (cash_flow.py)
Step 7:  Balance sheet (pass 2)  (balance_sheet.py) — final with RE roll-forward plug
Step 8:  FCFF computation        (fcff.py)
Step 9:  DCF valuation           (dcf_valuation.py)
Step 10: Reconciliation check    (engine.py) — 3 invariants, ±$0.01M tolerance
```

---

## 2. WACC

### Formula
```
Ke  = Rf + β_adj × ERP           (CAPM)
WACC = Ke                         (100% equity — NVIDIA net cash positive)
```

### Blume Beta Adjustment
Raw 5-year monthly beta regresses toward 1.0 over time. Blume (1975) adjustment:
```
β_adj = (2/3) × β_raw + (1/3) × 1.0
β_adj = 0.6667 × 1.9157 + 0.3333 = 1.7728
```

### Inputs (as of Oct 2025)
| Input | Value | Source |
|---|---|---|
| Rf | 4.07% | US 10-yr Treasury, FRED, Jan 2025 |
| β_raw | 1.9157 | Yahoo Finance, 5-yr monthly vs S&P 500 |
| β_adj | 1.7728 | Blume-adjusted |
| ERP | 5.00% | Damodaran implied ERP, Jan 2025 |
| **Ke = WACC** | **12.91%** | |

---

## 3. Income Statement

Revenue is modelled by segment using growth rates from assumptions.json:

```
Revenue_t = Revenue_{t-1} × (1 + growth_rate_t)
```

Segment mix is maintained from FY2025 actuals (Data Center 87.7%, Gaming 8.0%, etc.), with growth rates differentiating segment trajectories.

**Gross profit:** Revenue × gross_margin_pct (steps down from peak 75.0% to long-run 74.0%)  
**Operating expense:** Revenue × opex_pct (scales with revenue at declining rate)  
**EBIT:** Gross profit − OpEx  
**Interest income:** Applied on average cash balance  
**EBT:** EBIT + Interest income − Interest expense  
**Net income:** EBT × (1 − Effective Tax Rate)

ETR: 12.65% (NVIDIA FY2025 10-K, Note 8 — income taxes)

---

## 4. Free Cash Flow to Firm (FCFF)

### Formula
```
FCFF  = NOPAT + D&A − |CapEx| − ΔNWC
NOPAT = EBIT × (1 − ETR)
```

**Why tax on EBIT, not EBT?** FCFF is an *unlevered* cash flow measure — it represents cash available to all capital providers before financing effects. Tax is applied to operating income (EBIT), not earnings before tax (EBT), to strip out the interest tax shield. This ensures FCFF is capital-structure neutral, consistent with discounting at WACC.

### ΔNWC (Change in Net Working Capital)
```
NWC   = Accounts Receivable + Inventory − Accounts Payable
ΔNWC  = NWC_t − NWC_{t-1}

AR   = Revenue × (AR_days / 365)
Inv  = COGS × (Inv_days / 365)
AP   = COGS × (AP_days / 365)
```

Positive ΔNWC = cash outflow (business growing, more capital tied up).  
Negative ΔNWC = cash inflow (shrinking or improving working capital efficiency).

---

## 5. DCF Valuation

### Present Value of Explicit Period FCFs
```
PV(FCF) = Σₜ₌₁⁵ [ FCFFₜ / (1 + WACC)ᵗ ]
```
End-of-year discounting convention. No mid-year adjustment.

### Terminal Value (Gordon Growth)
```
TV      = FCFF₅ × (1 + g) / (WACC − g)
PV(TV)  = TV / (1 + WACC)⁵
```
Terminal growth rate g = 3.675% (blend of US nominal GDP growth ~3.5% + modest AI platform premium).

### Equity Bridge
```
Enterprise Value = PV(FCFs) + PV(TV)
Equity Value     = EV − Net Debt
Implied Price    = Equity Value / Diluted Shares

Net Debt = Total Debt − Cash & Equivalents
         = $1,891M − $34,831M = −$32,940M  (net cash)
```
Negative net debt (net cash) *adds* to equity value.

---

## 6. Balance Sheet

The balance sheet is built as a roll-forward model:

- **Assets:** Cash (from CF statement), AR, Inventory, Prepaid, PP&E net, Intangibles, Investments
- **Liabilities:** AP, Accrued liabilities, Deferred revenue, Long-term debt
- **Equity:** Common stock, APIC (grows with SBC), Retained earnings (RE plug)

**RE plug:**
```
RE_end = RE_begin + Net Income − Dividends Paid
```
The balance sheet balances through RE. This is verified by the invariant checker at ±$0.01M tolerance.

---

## 7. Cash Flow Statement (Indirect Method)

```
CFO = Net Income
    + D&A (non-cash add-back)
    + SBC (non-cash add-back)
    − ΔNWC (working capital investment)
    ± Other operating adjustments

CFI = − CapEx
    ± Acquisitions / Divestitures
    ± Investments (net)

CFF = + Debt issuance / (repayment)
    − Share buybacks
    − Dividends paid

Net change in cash = CFO + CFI + CFF
Ending cash        = Beginning cash + Net change
```

---

## 8. Sensitivity Analysis

9×9 grid: WACC from 10.9% to 14.9% (step 0.5%) × terminal growth from 2.0% to 6.0% (step 0.5%).

**Key finding:** To justify the $183.22 market price requires simultaneously:
- WACC ≤ 10.9% (most aggressive; requires beta normalisation + rate cuts)
- g ≥ 5.5% (above long-run US nominal GDP — demands perpetual AI premium)

Neither condition alone is sufficient. Both must hold simultaneously — with no margin compression, no competitive erosion, and no capex cycle.

---

## 9. Scenario Design

Scenarios are defined as *delta overrides* in `config/scenarios.json` and applied via `deep_merge()` over the base assumptions. The base assumptions.json is **never mutated**.

```python
def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into a copy of base. Original untouched."""
    result = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result
```

---

## 10. Data Sources

| Data | Source | Filing / Date |
|---|---|---|
| IS, BS, CF actuals FY2020–FY2025 | SEC EDGAR | NVIDIA 10-K annual filings |
| Segment revenue | SEC EDGAR | NVIDIA 10-K, Note on Segment Information |
| Diluted shares | SEC EDGAR | NVIDIA 10-K FY2025, Note 14 |
| Effective tax rate | SEC EDGAR | NVIDIA 10-K FY2025, Note 8 |
| Beta (raw, 5-yr monthly) | Yahoo Finance | October 2025 |
| Equity risk premium | Damodaran online | January 2025 |
| Risk-free rate | FRED (Federal Reserve) | January 2025 |
| Market price | Yahoo Finance | October 17, 2025 |
