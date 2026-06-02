# 📦 API Reference — NVIDIA FP&A Dashboard

**Version:** v1.0 | **Author:** Aditya Gupta | **Date:** October 2025

> **Current status:** This project does not yet expose HTTP endpoints. This document defines the internal Python function API of the core computation modules, and outlines the REST API design for the planned v2.0 API layer.

---

## Part 1: Internal Python API (Current)

These are the callable interfaces used by `app.py`, the DCF layer, and the test suite. All modules follow the data contracts defined in `data_contracts.md`.

---

### Module: `kpi/kpis.py`

#### `safe_divide(numerator, denominator) → float | None`

The single division gateway used by every KPI formula.

```python
safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]
```

| Parameter | Type | Description |
|---|---|---|
| `numerator` | `float \| None` | Dividend |
| `denominator` | `float \| None` | Divisor |

Returns `None` if either input is `None` or denominator is zero. Never raises `ZeroDivisionError`. Never returns `NaN` or `Infinity`.

---

#### `calculate_kpis(...) → dict`

Compute all 8 KPIs for a single financial period.

```python
calculate_kpis(
    revenue:             Optional[float] = None,
    cogs:                Optional[float] = None,
    ebitda:              Optional[float] = None,
    cfo:                 Optional[float] = None,
    capex:               Optional[float] = None,
    accounts_receivable: Optional[float] = None,
    accounts_payable:    Optional[float] = None,
    current_assets:      Optional[float] = None,
    current_liabilities: Optional[float] = None,
    revenue_prior:       Optional[float] = None,
) -> dict
```

All monetary inputs in USD millions. `capex` must be negative (cash outflow convention).

**Returns:** Dict with keys `gross_margin`, `ebitda_margin`, `fcf`, `fcf_margin`, `revenue_growth`, `ar_days`, `ap_days`, `current_ratio`. All values are `float | None`.

**Example:**
```python
from src.kpi.kpis import calculate_kpis

kpis = calculate_kpis(
    revenue=130497, cogs=32639, ebitda=83317,
    cfo=64089, capex=-3236,
    accounts_receivable=23065, accounts_payable=6310,
    current_assets=80126, current_liabilities=18047,
    revenue_prior=60922,
)
# kpis['gross_margin']    → 0.7499
# kpis['fcf']             → 60853.0
# kpis['revenue_growth']  → 1.1420
```

---

#### `calculate_kpis_timeseries(periods) → list[dict]`

Compute KPIs across a time-series of periods. Automatically handles `revenue_growth` by carrying the prior period revenue forward.

```python
calculate_kpis_timeseries(periods: list[dict]) -> list[dict]
```

`periods` must be sorted chronologically (oldest first). Each dict uses the same keys as `calculate_kpis()` arguments, plus optional metadata keys (e.g. `year`, `ticker`) which are passed through unchanged.

---

### Module: `kpi/ratios.py`

#### `evaluate_all(kpis) → dict`

Convert a KPI dict into traffic-light signal strings.

```python
evaluate_all(kpis: dict) -> dict
```

**Input:** Dict produced by `calculate_kpis()`.

**Returns:** Dict with same keys, values replaced by `"green"`, `"amber"`, `"red"`, or `"grey"`.

Note: `"fcf"` always returns `"grey"` — it is an absolute dollar value with no threshold signal. Use `"fcf_margin"` for the signal.

---

#### `signal_to_color(signal) → str`

```python
signal_to_color(signal: str) -> str
# "green"  → "#22C55E"
# "amber"  → "#F59E0B"
# "red"    → "#EF4444"
# "grey"   → "#9CA3AF"
```

#### `signal_to_emoji(signal) → str`

```python
signal_to_emoji(signal: str) -> str
# "green"  → "🟢"
# "amber"  → "🟡"
# "red"    → "🔴"
# "grey"   → "⚪"
```

---

### Module: `etl/pipeline.py`

#### `run_etl(save_parquet, save_csv) → dict`

Execute the full 7-stage ETL pipeline.

```python
run_etl(save_parquet: bool = True, save_csv: bool = True) -> dict
```

**Returns:**

| Key | Type | Description |
|---|---|---|
| `actuals` | `pd.DataFrame` | Merged IS + BS + CF canonical table |
| `costs` | `pd.DataFrame` | IS cost structure canonical table |
| `working_capital` | `pd.DataFrame` | NWC + DSO/DIO/DPO canonical table |
| `error_report_path` | `str` | Path to `data/processed/error_report.csv` |
| `error_summary` | `dict` | `{total, by_type}` error counts |
| `status` | `str` | `"success"` or `"failed"` |
| `duration_seconds` | `float` | Wall-clock pipeline duration |

Always writes `error_report.csv` and `etl_pipeline_summary.json` — even on failure.

---

### Module: `src/scenario_engine.py`

#### `get_assumptions(scenario) → dict`

Returns the fully merged assumption dict for the given scenario.

```python
get_assumptions(scenario: Literal["base", "upside", "downside"] = "base") -> dict
```

Loads `config/assumptions.json` (base) and `config/scenarios.json` (overrides) fresh on each call — no caching. Base assumptions are never mutated; a deep copy is produced before merging.

#### `get_scenario_summary() → dict`

Returns a lightweight summary of key override differences per scenario for UI display (WACC, terminal growth rate, gross margin assumption).

---

### Module: `app/components/kpi_tile.py`

#### `render_kpi_tile(...) → None`

Render a single KPI card in the Streamlit UI.

```python
render_kpi_tile(
    label:       str,
    value:       str,
    delta:       Optional[float] = None,
    signal:      Literal["green", "yellow", "red", "neutral"] = "neutral",
    help_text:   Optional[str] = None,
    delta_label: str = "vs prior year",
) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `label` | `str` | Metric name, e.g. `"Gross Margin"` |
| `value` | `str` | Pre-formatted display string, e.g. `"74.9%"` or `"$60.9B"` |
| `delta` | `float \| None` | Numeric delta in percentage points (sign determines direction) |
| `signal` | `str` | Traffic-light from src.kpi engine |
| `help_text` | `str \| None` | Optional footnote (e.g. formula or data source) |
| `delta_label` | `str` | Context string, default `"vs prior year"` |

**Note:** All business logic (signal computation, delta calculation) must happen upstream in the KPI engine. This component renders pre-computed values only.

#### `render_kpi_row(tiles, columns) → None`

```python
render_kpi_row(tiles: list[dict], columns: int = 4) -> None
```

Distributes a list of tile configuration dicts across a `columns`-wide Streamlit column grid. Each dict maps 1:1 to `render_kpi_tile` kwargs.

---

## Part 2: Planned REST API (v2.0)

When the dashboard is extended to support multi-user access or external integrations (e.g., embedding KPIs in a portfolio management system), the following REST API is planned.

**Base URL:** `https://api.fpa-dashboard.internal/v1`
**Authentication:** Bearer token (JWT)
**Content-Type:** `application/json`

---

### `GET /kpis/{ticker}/{fiscal_year}`

Returns computed KPIs for a given ticker and fiscal year.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `ticker` | string | Company ticker, e.g. `"NVDA"` |
| `fiscal_year` | integer | 4-digit fiscal year, e.g. `2025` |

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `scenario` | string | `"base"` | `"base"`, `"upside"`, or `"downside"` |
| `include_signals` | boolean | `true` | Include traffic-light signals in response |

**Response `200 OK`:**

```json
{
  "ticker": "NVDA",
  "fiscal_year": 2025,
  "scenario": "base",
  "kpis": {
    "gross_margin": 0.7499,
    "ebitda_margin": 0.6386,
    "fcf": 60853.0,
    "fcf_margin": 0.4665,
    "revenue_growth": 1.1420,
    "ar_days": 64.5,
    "ap_days": 70.6,
    "current_ratio": 4.44
  },
  "signals": {
    "gross_margin": "green",
    "ebitda_margin": "green",
    "fcf_margin": "green",
    "revenue_growth": "green",
    "ar_days": "amber",
    "ap_days": "green",
    "current_ratio": "green"
  }
}
```

**Error Responses:**

| Code | Meaning |
|---|---|
| `404` | Ticker or fiscal year not found |
| `400` | Invalid scenario value |
| `500` | ETL pipeline error |

---

### `GET /dcf/{ticker}`

Returns the DCF valuation output for the given ticker.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `ticker` | string | Company ticker |

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `scenario` | string | `"base"` | Scenario for assumptions |

**Response `200 OK`:**

```json
{
  "ticker": "NVDA",
  "scenario": "base",
  "valuation_date": "2025-10-17",
  "dcf": {
    "sum_pv_fcf_usdm": null,
    "terminal_value_usdm": null,
    "pv_terminal_value_usdm": null,
    "enterprise_value_usdm": null,
    "net_debt_usdm": null,
    "equity_value_usdm": null,
    "diluted_shares_millions": 24300,
    "implied_share_price_usd": 109.26,
    "market_price_usd": 183.22,
    "upside_downside_pct": -0.403,
    "wacc_used": 0.1291,
    "terminal_growth_rate_used": 0.04
  }
}
```

---

### `GET /etl/status`

Returns the status of the most recent ETL pipeline run.

**Response `200 OK`:**

```json
{
  "run_timestamp": "2025-10-17T14:23:01.123456",
  "status": "success",
  "duration_seconds": 4.72,
  "tables_produced": ["actuals", "costs", "working_capital"],
  "error_summary": {
    "total": 3,
    "by_type": {
      "MISSING_FILLED_FFILL": 2,
      "MISSING_FILLED_ZERO": 1
    }
  }
}
```

---

### `POST /etl/run`

Triggers a fresh ETL pipeline run.

**Request body:** Empty or `{"save_parquet": true, "save_csv": true}`

**Response `202 Accepted`:**

```json
{
  "job_id": "etl_20251017_142301",
  "status": "running",
  "poll_url": "/etl/jobs/etl_20251017_142301"
}
```

---

## Part 3: Error Response Format (v2.0)

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "TICKER_NOT_FOUND",
    "message": "No data found for ticker 'AMZN'. Available tickers: ['NVDA']",
    "request_id": "req_abc123"
  }
}
```
