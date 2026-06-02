# Architectural Decision Records (ADRs)

A log of non-obvious decisions made during development, with context and rationale.

---

## ADR-001: Streamlit over Dash/Flask/React

**Date:** 2025-08  
**Status:** Accepted  
**Batch 1 Deep Dive**

**Context:** A financial dashboard needs to:
- Display live KPIs and financial models
- Allow scenario switching (Base / Upside / Downside)
- Export results (PDF, PPTX)
- Require zero frontend/backend architecture overhead
- Be deployable by a single finance engineer (not a full-stack team)

**Decision:** Use Streamlit for the UI layer.

**Rationale:**

**Reactivity without serialization boundary:** Streamlit re-executes the entire Python script on user interaction (button click, slider drag, checkbox). This eliminates the need for a REST API boundary between frontend and backend. A financial model change (e.g., updating an assumption in `assumptions.json`) is instantly reflected in the UI without any JSON serialization/deserialization. The model and the UI share the same Python namespace.

**Non-engineered development:** Streamlit is procedural — you write `st.metric()`, `st.slider()`, `st.dataframe()` in sequential order and the UI builds itself. No React components, no Webpack bundling, no Node.js. A finance engineer who knows Python can ship a dashboard in hours.

**Auditability:** Every model output is printed or displayed directly. There's no hidden API server transforming data. The entire computation flow is visible in `app/app.py` — nothing is hidden in a microservice.

**Rejected alternatives:**
- **Dash (Plotly):** More enterprise-grade, but requires understanding of callbacks, state management, and component trees. Steeper learning curve for finance engineers.
- **Flask/FastAPI + React:** Introduces a full frontend/backend separation, requires Node.js tooling, Webpack, Redux or similar state management. Too much infrastructure for a single analyst to maintain.
- **Custom HTML/JS:** Impossible to maintain without a dedicated frontend engineer.

---

## ADR-002: Pandas over Spark/Polars/DuckDB

**Date:** 2025-08  
**Status:** Accepted  
**Batch 1 Deep Dive**

**Context:** The NVIDIA FP&A dataset is small:
- 6 annual fiscal years (FY2020–FY2025) = 6 rows in core tables
- ~200 columns per table
- Fits entirely in RAM (< 50 MB)

Evaluating data processing libraries:

**Decision:** Pandas for all data manipulation and modeling.

**Rationale:**

**Dataset is small.** Spark, Polars, DuckDB are optimized for multi-terabyte distributed workloads. NVIDIA's historical financials (6 years) are a few KB. Pandas is optimized for in-memory DataFrames up to ~1 GB. This is a perfect fit.

**Ecosystem maturity:** Pandas has 15 years of adoption in finance. Every quantitative finance library (numpy, scipy, matplotlib, statsmodels) integrates seamlessly with pandas. The alternative libraries (Polars, DuckDB) are newer and have smaller financial-specific ecosystems.

**Developer familiarity:** Finance engineers, quantitative analysts, and data scientists all know Pandas. It's the default language for financial analysis. Requiring someone to learn Polars or DuckDB is a hiring/team capability burden.

**Parquet upgrade path:** If the model later needs to scale (multi-company, multi-year quarterly data), the architecture allows upgrading to Polars or DuckDB later. Switching from Pandas DataFrames to `polars.DataFrame` is a mostly-mechanical refactor because the logic is separated from the I/O layer.

**Rejected alternatives:**
- **Spark:** Overhead and cluster management kill development velocity for a 50 MB dataset.
- **Polars:** Faster than Pandas but immature for finance workflows. Fewer downstream integrations.
- **DuckDB:** Excellent for analytical SQL. Overkill for a model that's mostly procedural Python logic.

---

## ADR-003: Parquet over CSV for canonical tables

**Date:** 2025-08  
**Status:** Accepted

**Context:** ETL output needs to be read by the modeling engine, tests, and dashboard. Options: CSV, SQLite, Parquet.

**Decision:** Parquet via PyArrow.

**Rationale:**
- Typed columns enforced at write time. Downstream never re-validates types.
- Column-store format: reads only needed columns, fast for pandas.
- Native nullable integers and floats — no silent float/string coercion like CSV.
- Human-unreadable, but that's acceptable: canonical tables are code output, not config.

**Rejected:** CSV — no type enforcement, floats round-trip incorrectly for large dollar values. SQLite — adds operational complexity with no benefit for this read-mostly workload.

---

## ADR-004: Pure Functions for KPIs (no classes, no DataFrames inside)

**Date:** 2025-09  
**Status:** Accepted  
**Batch 1 Deep Dive**

**Context:** KPIs (Gross Margin, FCF, ROIC, etc.) are computed from model outputs. Key question: should KPI computation be object-oriented or functional?

**Decision:** All KPI functions are pure functions. Signature: `fn(inputs: scalar/dict) → scalar`.

**Rationale:**

**Testability:** Pure functions have zero side effects. `gross_margin(revenue=100, cogs=25)` always returns 0.75. No hidden state, no mocking required. Test coverage is trivial.

**No DataFrame leakage:** A common mistake in financial models: passing an entire DataFrame into a KPI function, which then:
- Silently drops rows with NaN
- Silently casts columns
- Returns an array instead of a scalar
- Becomes impossible to debug later

By enforcing `scalar in → scalar out`, we prevent this anti-pattern entirely.

**Type safety:** The Streamlit dashboard renders KPIs in cards (one metric per card). A DataFrame or array doesn't fit. Pure scalar-returning functions force the right shape.

**`safe_divide()` as the single division gateway:**
```python
def safe_divide(numerator, denominator, default=None):
    """Return None if denominator is zero, else numerator/denominator."""
    if denominator == 0 or denominator is None:
        return default  # returns None, not NaN, not exception
    return numerator / denominator
```
Every division in every KPI function uses `safe_divide()`. This ensures consistent null handling (missing KPIs are `None`, not `NaN` or exceptions).

**Rejected alternatives:**
- **Class-based KPIs:** `class GrossMargin: def compute(self, df) → float` introduces unnecessary state and makes testing harder.
- **Vectorized (NumPy):** Faster for large datasets, unnecessary for 6-row annual data.

---

## ADR-005: Raise on Conflicting Duplicates

**Date:** 2025-09  
**Status:** Accepted  
**Batch 1 Deep Dive**

**Context:** Raw 10-K data is loaded. Question: if the same fiscal_year appears twice with different revenue values, what should happen?

**Decision:** Raise immediately with a detailed error message. Do NOT silently pick one, average, or overwrite.

**Rationale:**

**Silent data loss is catastrophic in finance.** If FY2025 revenue appears as both $100M and $150M in the raw files and the model silently picks $100M, the error may not be discovered for weeks/months. By then, analyses built on the wrong number may have been shared externally.

**Explicit failure is the right behavior** because:
- Duplicates signal a data quality problem (e.g., 10-K restatement, typo in source data, accidental row duplication)
- A human must investigate and resolve (not the code)
- The error message should show BOTH conflicting values, so the analyst knows exactly what to fix

**Example error:**
```
ValueError: Duplicate fiscal_year='FY2025' with conflicting revenue_usdm:
  Row 1: revenue_usdm=130497 (from income_statement.csv, line 45)
  Row 2: revenue_usdm=130500 (from segment_revenue.csv, line 22)
  Action: Check SEC filing and resolve discrepancy in source CSV.
```

**Rejected alternatives:**
- **Silent overwrite (last row wins):** Introduces undetected bias. The order of file processing becomes a hidden dependency.
- **Average:** Non-sensical for a true/false fact like revenue. You can't average $100M and $150M — one is correct, one is wrong.
- **Log warning and continue:** Creates a time bomb. The model runs successfully but on wrong data.

---

## ADR-006: Per-Column Missing-Value Policy

**Date:** 2025-08  
**Status:** Accepted

**Context:** Raw 10-K data has missing values (e.g., segment revenue not disclosed pre-FY2022, some balance sheet line items).

**Decision:** Explicit per-column policy dict. Policy options: `error`, `zero`, `ffill`, `bfill`, `median`, `warn`, `ignore`.

**Rationale:**
- Silently filling or dropping missing values is a financial modeling error. The decision must be documented and deliberate.
- `error`: use for values where missing = data problem (e.g., revenue, net income).
- `zero`: use for line items that genuinely didn't exist (e.g., automotive revenue FY2020).
- `ffill`: use for balance sheet items where prior year is best proxy.
- Each column's policy is reviewable and testable.

---

## ADR-007: Delta-Only Scenarios (never mutate base)

**Date:** 2025-08  
**Status:** Accepted

**Context:** Need to express Base / Upside / Downside scenarios without duplicating the full assumptions file.

**Decision:** Scenarios are delta files. `deep_merge(base, override)` produces a new dict; base is never mutated.

**Rationale:**
- Scenarios are small: 5–10 key changes from base. Full duplication creates drift.
- Code review of a scenario file shows exactly what changed (diff-friendly).
- Immutability of base assumptions is guaranteed — accidental mutation is a financial modeling bug.
- Recursive merge handles nested structures (e.g., wacc.wacc, margins.gross_margin_fy26f).

---

## ADR-008: Always-Write error_report.csv

**Date:** 2025-09  
**Status:** Accepted

**Context:** ETL pipeline can fail in various places (load, transform, validate, clean). When it fails, how much context should be available?

**Decision:** `error_report.csv` is written unconditionally, even on failure. It's written in a `finally` block.

**Rationale:**
- If ETL fails, the analyst needs to know WHY. The error report documents every validation failure, missing value decision, and data quality issue encountered.
- `finally` block ensures the report is written regardless of when the pipeline fails.
- The report is both a debugging tool and an audit trail.

---

## ADR-009: Version-Pin Dependencies

**Date:** 2025-09  
**Status:** Accepted

**Context:** Python dependencies (pandas, numpy, streamlit) release updates frequently. Should `requirements.txt` pin major versions or allow flexibility?

**Decision:** Major-version pinning. Example: `pandas>=2.0,<3.0` (allows security patches, blocks breaking changes).

**Rationale:**
- Financial models are sensitive to small changes in numerical libraries. A minor version bump in numpy could change rounding behavior.
- Version pinning ensures reproducibility: `pip install -r requirements.txt` produces the same environment every time.
- Security patches (e.g., 2.0.1 → 2.0.2) are safe. Breaking changes (e.g., 2.0 → 3.0) are not.

---

## ADR-010: Multi-Stage Docker Build

**Date:** 2025-10  
**Status:** Accepted

**Context:** Containerizing a Python financial app. How to minimize image size and attack surface?

**Decision:** Multi-stage build:
1. **Stage 1 (builder):** Includes gcc, g++, libatlas (dependencies for compiled packages like numpy)
2. **Stage 2 (runtime):** Only python:3.11-slim + copied packages. No build tools.

**Rationale:**
- Build-time dependencies (gcc, build-essential) are only needed to compile numpy/scipy. They're not needed at runtime.
- Multi-stage build discards Stage 1 after compilation. Stage 2 image is lean (~500 MB instead of ~1.5 GB).
- Attack surface is smaller (no compiler toolchain in production image).
- Non-root user (`appuser`) for security.

---

## Cross-Cutting Design Philosophy

All decisions above follow one principle: **Fail explicitly, never silently.** In financial modeling:
- Silent data loss → career risk
- Duplicate data with no error → audit failure
- Missing values silently filled → wrong valuation
- Type coercion → rounding errors

This repo prioritizes auditability and correctness over convenience.
