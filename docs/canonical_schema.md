# NVIDIA FP&A Dashboard — Canonical Data Schema
**Version:** v1.0 | **Author:** Aditya Gupta | **Date:** Oct 2025  
**Source:** `nvda_data_dictionary.csv` + all historical CSV files + `Company_Valuation_Model.xlsx`

---

## Design Principle
> Raw data ≠ Canonical data.  
> ETL = Transform raw → canonical.  
> Every downstream module (modeling, KPI, UI) reads ONLY canonical tables.

---

## Table 1: `revenue`

**Purpose:** Segment-level annual revenue — historical and forecast  
**Source:** `nvda_segment_revenue`, `04a_Projection_IS` rows 3–35  
**Granularity:** 1 row per fiscal year per segment  
**Time Index:** `fiscal_year` (integer)

| Column | dtype | Unit | Format | Description |
|---|---|---|---|---|
| `fiscal_year` | `int64` | — | YYYY | NVIDIA fiscal year (ends ~Jan 31) |
| `ticker` | `str` | — | "NVDA" | Ticker symbol, always "NVDA" |
| `segment` | `str` | — | Enum | One of: `data_center`, `gaming`, `professional_viz`, `automotive`, `oem_other`, `total` |
| `revenue_usdm` | `float64` | USD $M | 0.00 | Net segment revenue in USD millions |
| `yoy_growth_rate` | `float64` | decimal | 0.0000 | YoY growth: (current/prior) - 1 |
| `revenue_mix_pct` | `float64` | decimal | 0.0000 | Segment % of total revenue |
| `is_forecast` | `bool` | — | True/False | False = historical, True = projected |
| `scenario` | `str` | — | Enum | One of: `base`, `upside`, `downside` |
| `source` | `str` | — | — | e.g. "10-K FY2025", "model_projection" |

**Primary Key:** `(fiscal_year, segment, scenario)`  
**Aggregation Logic:** `total` segment = SUM of all other segments for same `fiscal_year` and `scenario`  
**Date Range:** FY2020–FY2025 (historical), FY2026F–FY2030F (forecast)

---

## Table 2: `costs`

**Purpose:** Full income statement cost structure — historical and forecast  
**Source:** `nvidia_historical_IS.csv`, `cleaned_financials.csv`, `04a_Projection_IS`  
**Granularity:** 1 row per fiscal year  
**Time Index:** `fiscal_year` (integer)

| Column | dtype | Unit | Format | Description |
|---|---|---|---|---|
| `fiscal_year` | `int64` | — | YYYY | NVIDIA fiscal year |
| `ticker` | `str` | — | "NVDA" | Always "NVDA" |
| `revenue_usdm` | `float64` | USD $M | 0.00 | Total net revenue (reference, denormalized) |
| `cogs_usdm` | `float64` | USD $M | 0.00 | Cost of revenue (COGS) |
| `gross_profit_usdm` | `float64` | USD $M | 0.00 | Revenue minus COGS |
| `gross_margin_pct` | `float64` | decimal | 0.0000 | Gross profit / Revenue |
| `rd_expense_usdm` | `float64` | USD $M | 0.00 | R&D expense |
| `sga_expense_usdm` | `float64` | USD $M | 0.00 | SG&A expense |
| `acq_termination_usdm` | `float64` | USD $M | 0.00 | One-time acquisition termination (0 in forecasts) |
| `total_opex_usdm` | `float64` | USD $M | 0.00 | R&D + SG&A + one-time items |
| `ebit_usdm` | `float64` | USD $M | 0.00 | Gross profit minus total OpEx |
| `ebit_margin_pct` | `float64` | decimal | 0.0000 | EBIT / Revenue |
| `da_usdm` | `float64` | USD $M | 0.00 | Depreciation & amortization |
| `ebitda_usdm` | `float64` | USD $M | 0.00 | EBIT + D&A |
| `ebitda_margin_pct` | `float64` | decimal | 0.0000 | EBITDA / Revenue |
| `interest_income_usdm` | `float64` | USD $M | 0.00 | Interest income (positive) |
| `interest_expense_usdm` | `float64` | USD $M | 0.00 | Interest expense (negative convention) |
| `other_net_usdm` | `float64` | USD $M | 0.00 | Other income/expense, net |
| `ebt_usdm` | `float64` | USD $M | 0.00 | Earnings before tax |
| `income_tax_usdm` | `float64` | USD $M | 0.00 | Income tax provision |
| `effective_tax_rate_pct` | `float64` | decimal | 0.0000 | Tax / EBT |
| `net_income_usdm` | `float64` | USD $M | 0.00 | GAAP net income |
| `net_margin_pct` | `float64` | decimal | 0.0000 | Net income / Revenue |
| `is_forecast` | `bool` | — | True/False | False = historical, True = projected |
| `scenario` | `str` | — | Enum | `base`, `upside`, `downside` |
| `source` | `str` | — | — | Filing type or "model_projection" |

**Primary Key:** `(fiscal_year, scenario)`  
**Aggregation Logic:** No aggregation — 1 row per year per scenario  
**Constraint:** `gross_profit = revenue - cogs`, `ebit = gross_profit - total_opex`, `ebitda = ebit + da`

---

## Table 3: `working_capital`

**Purpose:** Balance sheet working capital drivers — historical and forecast  
**Source:** `working_capital.csv`, `09_WorkingCapital` sheet, `nvidia_historical_BS.csv`  
**Granularity:** 1 row per fiscal year  
**Time Index:** `fiscal_year` (integer)

| Column | dtype | Unit | Format | Description |
|---|---|---|---|---|
| `fiscal_year` | `int64` | — | YYYY | NVIDIA fiscal year |
| `ticker` | `str` | — | "NVDA" | Always "NVDA" |
| `accounts_receivable_usdm` | `float64` | USD $M | 0.00 | Trade receivables at year-end |
| `inventory_usdm` | `float64` | USD $M | 0.00 | Inventories at year-end |
| `prepaid_expenses_usdm` | `float64` | USD $M | 0.00 | Prepaid and other current assets |
| `accounts_payable_usdm` | `float64` | USD $M | 0.00 | Accounts payable at year-end |
| `accrued_liabilities_usdm` | `float64` | USD $M | 0.00 | Accrued and other current liabilities |
| `nwc_assets_usdm` | `float64` | USD $M | 0.00 | AR + Inventory + Prepaid |
| `nwc_liabilities_usdm` | `float64` | USD $M | 0.00 | AP + Accrued liabilities |
| `net_working_capital_usdm` | `float64` | USD $M | 0.00 | NWC assets minus NWC liabilities |
| `change_in_nwc_usdm` | `float64` | USD $M | 0.00 | Delta NWC vs prior year (used in FCFF) |
| `ar_days_dso` | `float64` | days | 0.00 | DSO = (AR / Revenue) × 365 |
| `inventory_days_dio` | `float64` | days | 0.00 | DIO = (Inventory / COGS) × 365 |
| `ap_days_dpo` | `float64` | days | 0.00 | DPO = (AP / COGS) × 365 |
| `cash_conversion_cycle` | `float64` | days | 0.00 | DSO + DIO - DPO |
| `revenue_usdm` | `float64` | USD $M | 0.00 | Reference revenue (denormalized) |
| `cogs_usdm` | `float64` | USD $M | 0.00 | Reference COGS (denormalized) |
| `is_forecast` | `bool` | — | True/False | False = historical, True = projected |
| `scenario` | `str` | — | Enum | `base`, `upside`, `downside` |
| `source` | `str` | — | — | "10-K (EDGAR)" or "model_projection" |

**Primary Key:** `(fiscal_year, scenario)`  
**Constraint:** `nwc_assets = ar + inventory + prepaid`, `net_working_capital = nwc_assets - nwc_liabilities`  
**Sign Convention:** `change_in_nwc` positive = NWC increase = cash outflow (reduces FCFF)

---

## Table 4: `actuals`

**Purpose:** Full consolidated historical financials — single source of truth for all actuals  
**Source:** `cleaned_financials.csv` + `nvidia_historical_BS.csv` + `nvidia_historical_CF.csv`  
**Granularity:** 1 row per fiscal year (annual only)  
**Time Index:** `fiscal_year` (integer)

| Column | dtype | Unit | Format | Description |
|---|---|---|---|---|
| `fiscal_year` | `int64` | — | YYYY | NVIDIA fiscal year |
| `ticker` | `str` | — | "NVDA" | Always "NVDA" |
| `revenue_usdm` | `float64` | USD $M | 0.00 | Total net revenue |
| `cogs_usdm` | `float64` | USD $M | 0.00 | Cost of goods sold |
| `gross_profit_usdm` | `float64` | USD $M | 0.00 | Revenue minus COGS |
| `ebit_usdm` | `float64` | USD $M | 0.00 | Operating income |
| `ebitda_usdm` | `float64` | USD $M | 0.00 | EBIT + D&A |
| `net_income_usdm` | `float64` | USD $M | 0.00 | GAAP net income |
| `rd_expense_usdm` | `float64` | USD $M | 0.00 | R&D expense |
| `sga_expense_usdm` | `float64` | USD $M | 0.00 | SG&A expense |
| `da_usdm` | `float64` | USD $M | 0.00 | Depreciation & amortization |
| `interest_income_usdm` | `float64` | USD $M | 0.00 | Interest income |
| `interest_expense_usdm` | `float64` | USD $M | 0.00 | Interest expense (negative) |
| `income_tax_usdm` | `float64` | USD $M | 0.00 | Income tax provision |
| `cfo_usdm` | `float64` | USD $M | 0.00 | Net cash from operations |
| `cfi_usdm` | `float64` | USD $M | 0.00 | Net cash from investing |
| `cff_usdm` | `float64` | USD $M | 0.00 | Net cash from financing |
| `capex_usdm` | `float64` | USD $M | 0.00 | Capital expenditures (negative = outflow) |
| `fcf_usdm` | `float64` | USD $M | 0.00 | Free cash flow (CFO + CapEx) |
| `change_in_nwc_usdm` | `float64` | USD $M | 0.00 | Change in net working capital |
| `total_assets_usdm` | `float64` | USD $M | 0.00 | Total assets at fiscal year-end |
| `total_liabilities_usdm` | `float64` | USD $M | 0.00 | Total liabilities at fiscal year-end |
| `shareholders_equity_usdm` | `float64` | USD $M | 0.00 | Stockholders equity at fiscal year-end |
| `cash_and_investments_usdm` | `float64` | USD $M | 0.00 | Cash + short-term investments |
| `short_term_debt_usdm` | `float64` | USD $M | 0.00 | Current portion of debt |
| `long_term_debt_usdm` | `float64` | USD $M | 0.00 | Long-term debt |
| `total_debt_usdm` | `float64` | USD $M | 0.00 | STD + LTD |
| `accounts_receivable_usdm` | `float64` | USD $M | 0.00 | Trade receivables |
| `inventory_usdm` | `float64` | USD $M | 0.00 | Inventories |
| `accounts_payable_usdm` | `float64` | USD $M | 0.00 | Accounts payable |
| `gross_margin_pct` | `float64` | decimal | 0.0000 | Gross profit / Revenue |
| `ebit_margin_pct` | `float64` | decimal | 0.0000 | EBIT / Revenue |
| `net_margin_pct` | `float64` | decimal | 0.0000 | Net income / Revenue |
| `rd_pct_revenue` | `float64` | decimal | 0.0000 | R&D / Revenue |
| `capex_pct_revenue` | `float64` | decimal | 0.0000 | |CapEx| / Revenue |
| `source` | `str` | — | — | "10-K (EDGAR)" |

**Primary Key:** `fiscal_year`  
**Date Range:** FY2020–FY2025 (no forecasts — actuals only)  
**Constraint:** `gross_profit = revenue - cogs`, `fcf = cfo + capex`, BS must balance  
**Notes:** NaN is acceptable for FY2020 in CF columns (CFO not available pre-FY2022)

---

## ETL Flow Summary

```
Raw Files                     ETL Transform              Canonical Tables
─────────────────────────     ─────────────────────      ────────────────────────
nvidia_historical_IS.csv  ─┐
cleaned_financials.csv    ─┤─→  load + clean + align  ─→  actuals
nvidia_historical_BS.csv  ─┤    fiscal year index         working_capital
nvidia_historical_CF.csv  ─┘

nvda_segment_revenue.csv  ──→  segment reshape       ─→  revenue (historical)
04a_Projection_IS (model) ──→  forecast injection    ─→  revenue (forecast)

working_capital.csv       ──→  column remap          ─→  working_capital (historical)
09_WorkingCapital (model) ──→  forecast injection    ─→  working_capital (forecast)

assumptions.json          ──→  cost pct × revenue   ─→  costs (forecast)
nvidia_historical_IS.csv  ──→  direct load           ─→  costs (historical)
```

---

## Schema Versioning & Change Policy

- Schema changes require version bump in `settings.yaml`
- ETL outputs must be validated against this schema before use
- Column additions are backward-compatible; column removals require migration script
- All canonical tables stored as `.parquet` (type-safe, efficient) — not CSV
