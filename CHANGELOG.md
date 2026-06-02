# 📋 Changelog — NVIDIA FP&A Dashboard

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html): `MAJOR.MINOR.PATCH`.

---

## [v1.0.0] — October 2025

**Initial production release.**

### Added — Data Layer
- 13 raw NVIDIA data files: annual IS, BS, CF (FY2020–2025), quarterly IS/BS/CF, segment revenue, working capital, comps, market data
- `nvda_data_dictionary.csv` — full column-level data dictionary for all raw files
- `cleaned_financials.csv` — pre-merged IS + BS + CF with derived ratios

### Added — ETL Pipeline
- `loader.py` — CSV ingestion with whitespace stripping and clear FileNotFoundError messages
- `transformer.py` — column mapping from raw file headers to canonical schema names
- `validator.py` — schema validation, two-tier duplicate detection (exact vs conflicting), BS balance check, CF reconciliation check, revenue cross-check
- `cleaner.py` — explicit per-column missing value policy (`error`, `zero`, `ffill`, `bfill`, `median`, `warn`, `ignore`) for ~60 columns
- `pipeline.py` — 7-stage ETL orchestrator producing `actuals`, `costs`, `working_capital` canonical Parquet tables
- `error_logger.py` — accumulator that guarantees `error_report.csv` on every run, including failures
- Canonical tables stored as Parquet (type-safe) with CSV copies for human inspection
- `etl_pipeline_summary.json` — machine-readable run status, duration, and error counts

### Added — KPI Engine
- `kpis.py` — 8 pure KPI functions: `gross_margin`, `ebitda_margin`, `free_cash_flow`, `fcf_margin`, `revenue_growth`, `ar_days`, `ap_days`, `current_ratio`
- `safe_divide()` — single division gateway; returns `None` (not NaN, not exception) on invalid inputs
- `calculate_kpis()` — single-period composite calculator
- `calculate_kpis_timeseries()` — multi-period calculator with automatic revenue growth carry-forward
- `ratios.py` — NVIDIA-calibrated traffic-light signals (green/amber/red/grey) per KPI
- `evaluate_all()` — composite signal evaluator over full KPI dict
- `signal_to_color()` and `signal_to_emoji()` — UI rendering helpers
- All thresholds documented with NVIDIA FY2020–2025 historical ranges and semiconductor sector cross-validation

### Added — DCF Valuation Layer
- `wacc.py` — WACC calculator (CAPM Ke + Kd with tax shield)
- `dcf_valuation.py` — FCFF-based DCF model: 5-year projection (FY2026F–FY2030F), WACC discounting, Gordon Growth terminal value, equity bridge
- Base scenario: WACC 12.91%, terminal growth 4.0%, implied price $109.26 vs market $183.22

### Added — Scenario Engine
- `scenarios.json` — delta-only overrides for upside and downside scenarios
- `assumptions.json` — base model assumptions (revenue growth, margins, WACC inputs, working capital drivers)
- `scenario_engine.py` — deep-merge logic; base assumptions are never mutated
- 3 scenarios: `base`, `upside` (AI acceleration), `downside` (AI slowdown / margin compression)

### Added — UI Layer
- `app.py` — Streamlit dashboard with file uploader, KPI selector, margin selector, fiscal year range slider
- `kpi_tile.py` — reusable KPI card component with signal-colored border, delta display, and help text
- `render_kpi_row()` — distributes tiles across configurable column grid
- Plotly line charts for KPI and margin trends over time

### Added — Configuration
- `config/settings.yaml` — company identity, fiscal year convention, currency/formatting, file paths, scenario and logging config, validation tolerances
- `config/canonical_schema.md` — complete schema definition for all 4 canonical tables
- `config/data_contracts.md` — module interface contracts (6 contracts: ETL output, scenario engine, model input, model output, DCF scalars, KPI output)
- `config/model_input_schema.json` + `config/model_output_schema.json` — JSON Schema for runtime validation

### Added — Testing
- `test_etl_validation.py` — schema validation, duplicate detection, missing value policy, business rule tests
- `test_kpi_formulas.py` — all 8 KPI formulas with NVIDIA FY2025 ground-truth values, edge cases, signal tests
- `test_financial_invariants.py` — BS balance, CF reconciliation, revenue cross-check, segment aggregation
- `test_golden_output.py` — regression tests on canonical table structure and key values
- `conftest.py` — shared pytest fixtures (NVDA FY2025 actuals, sample DataFrames)
- `pyproject.toml` — pytest config with `PytestUnraisableExceptionWarning` promoted to error

### Added — Infrastructure
- `Dockerfile` — multi-stage build (builder with gcc/g++ → lean runtime Python 3.11-slim)
- Non-root `appuser` for container security
- Streamlit health check on `/_stcore/health`
- `requirements.txt` — production dependencies, major-version pinned
- `requirements-dev.txt` — dev/CI dependencies (black, isort, flake8, mypy, pytest-cov)
- `Makefile` — `install`, `install-dev`, `etl`, `run`, `test`, `lint`, `format`, `docker-build`, `docker-run`, `clean`
- `.flake8` — linter config
- `ci.yaml` — GitHub Actions CI (lint → test → coverage)

---

## Planned — v1.1.0

### In Progress
- PDF export of KPI summary and DCF output
- Quarterly data support in the dashboard (quarterly IS/BS/CF files already exist)

### Planned
- `test_etl_validation.py` — complete missing-value policy coverage for all 60 columns
- `test_golden_output.py` — extend with segment revenue row count and value assertions
- Peer comps panel in the dashboard (`comps_data.csv` is loaded but not yet rendered)

---

## Planned — v2.0.0

### Breaking Changes (anticipated)
- Multi-company support: `ticker` becomes a required filter parameter throughout
- Canonical schema version bump to support additional company-specific fields
- REST API layer (`GET /kpis/{ticker}/{fiscal_year}`, `GET /dcf/{ticker}`) — see `API.md`

### Planned Features
- PostgreSQL or DuckDB backend replacing Parquet file storage
- Streamlit Cloud deployment with authentication
- Automated data refresh via SEC EDGAR API integration
- Email delivery of weekly KPI summary report
- Scenario sensitivity table (WACC × terminal growth rate matrix)
