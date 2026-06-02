# Architecture

## Core Principle

**Zero finance logic in `app/`.** The Streamlit dashboard is a thin presentation layer that calls `src/` functions and renders results. All computation is unit-tested, deterministic, and reproducible.

---

## Layer Diagram

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 0 — Raw Data (data/raw/)                        │
│  13 CSV/XLSX files · SEC EDGAR · READ-ONLY              │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 1 — ETL Pipeline (src/etl/)                     │
│  7 stages: load→transform→validate→clean→derive→build   │
│  Output: Parquet canonical tables in data/processed/    │
│  Always writes error_report.csv + etl_summary.json      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 2 — Data Model / Contracts (src/etl/)           │
│  canonical_schema.py: 91-column definition              │
│  MISSING_VALUE_POLICY: per-column documented decisions   │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 3 — Assumptions & Scenarios (config/)           │
│  assumptions.json: master truth, all inputs with sources│
│  scenarios.json: delta overrides via deep_merge()        │
│  src/scenarios/engine.py: scenario switcher             │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 4 — Financial Modeling Engine (src/modeling/)   │
│  10-step orchestrator: WACC→IS→D&A→NWC→BS→CF→FCFF→DCF │
│  3-invariant reconciliation on every run (±$0.01M)      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 5 — KPI Engine (src/kpi/)                       │
│  8 pure functions · safe_divide() gateway               │
│  Traffic-light signals · semiconductor benchmarks       │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 6 — Dashboard (app/)                            │
│  Streamlit · 5 tabs · Scenario switcher · Filter bar   │
│  Exports: PDF (ReportLab) · PPTX (python-pptx)         │
└─────────────────────────────────────────────────────────┘
```

---

## ETL Pipeline — 7-Stage Philosophy

The ETL is **deterministic, auditable, and failure-transparent**. Each stage has a single responsibility.

### Stage 1: Load (`loader.py`)
Raw CSV/XLSX files are read into memory as pandas DataFrames. Column names are normalized to a canonical format (e.g., "Net Revenue" → "revenue_usdm"). No transformation yet — only intake and name alignment.

### Stage 2: Transform (`transformer.py`)
Unit conversion and column derivation. All NVIDIA 10-K figures arrive in thousands (e.g., "1,000" = $1 billion); these are converted to millions. Derived columns are computed (e.g., Gross Profit = Revenue − COGS). Fiscal year labels are standardized (e.g., "FY2025").

### Stage 3: Validate (`validator.py`)
Schema checks: each DataFrame must have expected columns with correct dtype. Range assertions: revenue cannot be negative, margin cannot exceed 100%. **Duplicate detection**: same fiscal_year with different values = immediate error. No silent overwrites.

### Stage 4: Clean (`cleaner.py`)
Missing-value handling via per-column policy. Seven policy types available:
- **`error`**: Missing value = pipeline failure (used for critical fields like revenue, net income)
- **`zero`**: Missing = replace with 0 (used for optional line items like SBC that genuinely didn't exist)
- **`ffill`**: Forward-fill with prior year (used for balance sheet items where prior is best proxy)
- **`bfill`**: Backward-fill
- **`median`**: Replace with column median
- **`warn`**: Log warning and continue
- **`ignore`**: Silently skip

Each column's policy is documented in `cleaner.py` with rationale.

### Stage 5: Derive (`transformer.py` continued)
Compute financial ratios and derived metrics: gross margin %, EBIT, working capital days, FCFF, etc. These derived columns are essential to downstream modules but are not raw — they're computed from raw + transformed data.

### Stage 6: Build (`canonical_schema.py`)
Construct the 4 canonical Parquet tables. Canonical ≠ raw. Raw = what came from 10-K. Canonical = what the model uses. Example: raw has quarterly revenue; canonical has annual revenue. Raw has many line items; canonical has 91 carefully selected columns with precise dtypes.

### Stage 7: Persist (`pipeline.py`)
Write Parquet tables to `data/processed/` . Unconditionally write `error_report.csv` (even if empty) and `etl_summary.json` for auditability.

---

## Duplicate Detection Strategy

If the ETL encounters the same `fiscal_year` with two different values for the same field:
1. **Raise immediately** with a detailed error message showing the conflict.
2. Do NOT silently pick the latest, average, or overwrite.
3. This signals a data problem that requires investigation (e.g., 10-K restatement, typo in source data).

The philosophy: **silent data loss is catastrophic in finance**. Explicit failure is correct.

---

## Missing-Value Policy Philosophy

Missing values in financial data fall into categories:
1. **Genuinely didn't exist** (e.g., automotive revenue FY2020 — NVIDIA didn't report this segment yet)
   - Policy: `zero` (treat as $0M)
   - Rationale: The segment generated zero revenue.

2. **Should exist but doesn't** (e.g., revenue for FY2025 is missing from 10-K)
   - Policy: `error` (fail the pipeline)
   - Rationale: Revenue is critical. Missing it signals a data problem.

3. **Optional accrual item** (e.g., stock-based compensation not separately disclosed in older 10-Ks)
   - Policy: `ffill` (use prior year) or `zero`
   - Rationale: SBC exists every year; if not disclosed, prior year is best proxy.

Each column's policy is explicit and reviewable. This is documented in `src/etl/cleaner.py` under `MISSING_VALUE_POLICY` dict.

---

## Error Accumulator Explanation

The ETL pipeline uses an **error accumulator** pattern:
- As data moves through stages, validation issues are collected in a list rather than raising immediately.
- At the end of a stage (or pipeline), all accumulated errors are written to `error_report.csv`.
- If errors exceed a threshold, the pipeline fails.
- If errors exist but are below threshold (e.g., warnings), the pipeline completes and the user is notified via the report.

This allows the pipeline to:
1. Process the entire dataset (not fail on the first issue).
2. Show all problems at once (not force iterative debugging).
3. Distinguish critical failures from non-blocking warnings.

---

## Canonical Tables Philosophy

Raw NVIDIA 10-K data has ~200 line items across quarterly and annual filings. The canonical schema **selects and standardizes 91 columns** into 4 Parquet tables:

1. **`actuals.parquet`** — Consolidated historical financials (FY2020–FY2025)
   - PK: `fiscal_year`
   - Purpose: Single source of truth for historical P&L, balance sheet, cash flow

2. **`costs.parquet`** — Full income statement cost structure (historical + forecast)
   - PK: `fiscal_year, scenario`
   - Purpose: Segment revenue, COGS, OpEx by fiscal year and scenario

3. **`working_capital.parquet`** — NWC schedule with drivers
   - PK: `fiscal_year, scenario`
   - Purpose: AR, Inventory, AP with DSO/DIO/DPO calculations

4. **`revenue.parquet`** — Segment-level revenue (annual, historical + forecast)
   - PK: `fiscal_year, segment, scenario`
   - Purpose: Data Center, Gaming, ProViz, Auto breakdown

**Why canonical matters:** Downstream modules (`modeling/`, `kpi/`, etc.) assume clean, typed, structured data. Canonical tables enforce schema at write time. Reading a Parquet file guarantees column types and prevents downstream type-coercion bugs.

---

## Design Decisions

### Why Parquet for canonical tables?
Typed columns, compressed storage, fast pandas read. Canonical types are enforced at write time — downstream consumers don't re-validate types. Error report and summary JSON are always written even on failure, so failed runs are diagnosable.

### Why JSON for assumptions?
Human-readable, version-controllable, diffable in PRs. Nested structure supports `deep_merge()` scenario overrides cleanly. YAML was considered but JSON's strictness (no implicit typing) reduces ambiguity in financial inputs.

### Why `deep_merge()` for scenarios?
Scenarios should express only what *changes*. A scenario file with 5 key overrides is readable and reviewable. Copying the full assumptions and editing creates drift and obscures what was changed. The deep_merge approach guarantees the base is immutable.

### Why end-of-year discounting?
Industry convention for corporate DCF. Mid-year convention (used in PE/LBO) assumes cash flows arrive at mid-year and produces higher valuations. End-of-year is more conservative and appropriate for a public equity context.

### Why NOPAT = EBIT × (1 − ETR) not (Net Income + Interest × (1 − t))?
The EBIT-based approach is cleaner and doesn't require isolating the interest tax shield. It produces the same result for an unlevered firm. For NVIDIA (net cash, minimal debt), both methods give equivalent NOPAT. The EBIT approach is preferred for consistency with how the income statement is modelled.

---

## Data Flow

```
data/raw/*.csv
    → src/etl/loader.py          (read, normalize columns)
    → src/etl/transformer.py     (units: $000s → $M, derived fields)
    → src/etl/validator.py       (schema, range assertions, duplicates)
    → src/etl/cleaner.py         (MISSING_VALUE_POLICY applied)
    → data/processed/actuals.parquet
    → data/processed/costs.parquet
    → data/processed/working_capital.parquet
    → data/processed/error_report.csv  [always written]
    → data/processed/etl_summary.json [always written]

config/assumptions.json + config/scenarios.json
    → src/scenarios/engine.py    (deep_merge → merged_assumptions)

data/processed/*.parquet + merged_assumptions
    → src/modeling/engine.py     (10-step orchestrator)
    → model_output dict          (IS, BS, CF, FCFF, DCF, KPIs per year)

model_output
    → app/app.py                 (Streamlit: render only)
    → src/output/export_pdf.py   (PDF: executive summary)
    → src/output/export_ppt.py   (PPTX: board deck)
```
