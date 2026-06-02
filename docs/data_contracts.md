# NVIDIA FP&A Dashboard — Data Contracts
**Version:** v1.0 | **Author:** Aditya Gupta | **Date:** Oct 2025

---

## What is a Data Contract?

A data contract is the **binding interface agreement** between modules. It specifies exactly what goes in and what comes out. If a module violates its contract, the entire pipeline breaks predictably — not silently.

---

## Module Map

```
┌─────────────────┐    ┌─────────────────┐    ┌────────────────────────┐
│  config/         │    │  etl/            │    │  modeling/             │
│  assumptions.json│─→ │  loader.py       │─→  │  income_statement.py   │─→ ┐
│  scenarios.json  │   │  transformer.py  │    │  cashflow.py           │   │
│  settings.yaml   │   │                  │    │  fcff.py               │   │
└─────────────────┘    └─────────────────┘    │  dcf.py                │   │
                                               │  working_capital.py    │   │
                                               └────────────────────────┘   │
                                                                             ↓
                                               ┌────────────────────────┐   │
                                               │  kpi/kpi_engine.py     │←──┘
                                               └────────────────────────┘
                                                             ↓
                                               ┌────────────────────────┐
                                               │  ui/dashboard.py       │
                                               └────────────────────────┘
```

---

## Contract 1 — ETL Output

**Produced by:** `etl/loader.py` → `etl/transformer.py`  
**Consumed by:** `modeling/`, `kpi/`, `ui/`

| Key | Type | Description |
|---|---|---|
| `revenue` | `pd.DataFrame` | Canonical revenue table (Table 1) |
| `costs` | `pd.DataFrame` | Canonical costs table (Table 2) |
| `working_capital` | `pd.DataFrame` | Canonical WC table (Table 3) |
| `actuals` | `pd.DataFrame` | Full historical actuals (Table 4) |

---

## Contract 2 — Scenario Engine

**Input:**

| Key | Type | Description |
|---|---|---|
| `base_assumptions` | `dict` | Full assumptions.json content |
| `scenario_overrides` | `dict` | Delta dict from src.scenarios.json[scenario] |
| `active_scenario` | `str` | `"base"` / `"upside"` / `"downside"` |

**Output:**

| Key | Type | Description |
|---|---|---|
| `final_assumptions` | `dict` | Deep-merged base + overrides |
| `active_scenario` | `str` | Label for tagging downstream outputs |

**Rule:** Use recursive deep merge — NOT shallow `.update()` — for nested keys.

---

## Contract 3 — Model Input

**Produced by:** ETL + Scenario Engine  
**Consumed by:** All projection modules

| Key | Type | Description |
|---|---|---|
| `revenue` | `pd.DataFrame` | Historical + forecast revenue |
| `costs` | `pd.DataFrame` | Historical + forecast costs |
| `working_capital` | `pd.DataFrame` | Historical + forecast WC schedule |
| `assumptions` | `dict` | Final merged assumptions |
| `scenario` | `str` | Active scenario name |

---

## Contract 4 — Model Output

**Produced by:** `modeling/run_model.py`  
**Consumed by:** `kpi/`, `ui/`

| Key | Type | Format | Description |
|---|---|---|---|
| `income_statement` | `pd.DataFrame` | 5 rows × IS columns | FY2026F–FY2030F |
| `cash_flow_statement` | `pd.DataFrame` | 5 rows × CF columns | FY2026F–FY2030F |
| `fcff` | `pd.DataFrame` | 5 rows × FCFF columns | Unlevered FCF |
| `dcf_valuation` | `dict` | Scalars only | EV → equity bridge |
| `scenario` | `str` | — | Active scenario |
| `assumptions_used` | `dict` | — | Snapshot at run time |

---

## Contract 5 — DCF Valuation (scalar dict)

All values USD millions except `implied_share_price_usd` (full USD):

| Key | Type | Unit | FY2025 Model Value |
|---|---|---|---|
| `sum_pv_fcf_usdm` | `float` | $M | From 05b_DCF |
| `terminal_value_usdm` | `float` | $M | Gordon Growth |
| `pv_terminal_value_usdm` | `float` | $M | Discounted at WACC |
| `enterprise_value_usdm` | `float` | $M | EV = PV FCF + PV TV |
| `net_debt_usdm` | `float` | $M | Debt - Cash |
| `equity_value_usdm` | `float` | $M | EV - Net Debt |
| `diluted_shares_millions` | `float` | M shares | 24,300M |
| `implied_share_price_usd` | `float` | USD/share | ~$109.26 |
| `market_price_usd` | `float` | USD/share | $183.22 |
| `upside_downside_pct` | `float` | decimal | ~-0.403 |
| `wacc_used` | `float` | decimal | 0.1291 |
| `terminal_growth_rate_used` | `float` | decimal | 0.04 |
| `scenario` | `str` | — | `"base"` |

---

## Contract 6 — KPI Output (ALL scalars — never DataFrame)

**Decision:** KPIs are point-in-time metrics → `dict` of floats, not DataFrame.

### Profitability KPIs
| Key | Unit | FY2025 Actual |
|---|---|---|
| `gross_margin_pct` | decimal | 0.7499 |
| `ebit_margin_pct` | decimal | 0.6242 |
| `ebitda_margin_pct` | decimal | 0.6386 |
| `net_margin_pct` | decimal | 0.5585 |
| `rd_pct_revenue` | decimal | 0.0990 |

### Cash Flow KPIs
| Key | Unit | FY2025 Actual |
|---|---|---|
| `fcf_margin_pct` | decimal | 0.4665 |
| `cfo_usdm` | $M | 64,089 |
| `capex_usdm` | $M | 3,236 |
| `capex_pct_revenue` | decimal | 0.0248 |
| `fcf_usdm` | $M | 60,853 |

### Working Capital KPIs
| Key | Unit | FY2025 Actual |
|---|---|---|
| `ar_days_dso` | days | 64.5 |
| `inventory_days_dio` | days | 112.7 |
| `ap_days_dpo` | days | 70.6 |
| `cash_conversion_cycle_days` | days | 106.7 |

### Valuation KPIs
| Key | Unit |
|---|---|
| `implied_share_price_usd` | USD/share |
| `enterprise_value_usdm` | $M |
| `ev_revenue_x` | x |
| `ev_ebitda_x` | x |
| `pe_ratio_x` | x |
| `upside_downside_pct` | decimal |

---

## Format Decision Table

| Use Case | Format | Rationale |
|---|---|---|
| Time-series financial data | `pd.DataFrame` | Vectorized ops, time indexing |
| Scalar model outputs (DCF) | `dict` of `float` | Point-in-time, no time axis |
| KPI metrics | `dict` of `float` | Point-in-time, UI rendering |
| Config parameters | `dict` | JSON-native, easy merge |
| App settings | YAML | Human-readable, env-agnostic |
| Scenario overrides | `dict` (delta only) | Memory-efficient, explicit |
| Canonical schemas | Markdown + TypedDict | Documentation + runtime enforcement |

---

## Validation Rules

1. **ETL** — All 4 canonical tables must pass column validation before modeling
2. **Balance Sheet** — `Total Assets == Total Liabilities + Equity` (tolerance $0.01M)
3. **Cash Flow** — `CFO + CFI + CFF == Net Change in Cash` (tolerance $0.01M)
4. **Revenue Cross-Check** — Revenue in IS must match revenue in FCFF sheet
5. **KPI** — All KPI values must be numeric; `scenario` key must be string
6. **Scenarios** — `final_assumptions` must never be the same object as `base_assumptions`
