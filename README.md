# NVIDIA FP&A Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.2+-150458?style=flat-square&logo=pandas&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-8.1+-0A9EDC?style=flat-square&logo=pytest&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/Aditya-Gupta09/Automated-FP-A-Dashboard/ci.yml?style=flat-square&label=CI)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**An institutional-grade FP&A and valuation platform built on real NVIDIA 10-K filings.**

[Overview](#overview) · [Architecture](#architecture) · [Quickstart](#quickstart) · [Financial Model](#financial-model) · [Testing](#testing) · [Docs](#documentation)

</div>

---

## Overview

Most financial dashboards visualise historical outcomes. This platform models **financial causality**: how revenue drivers, margin structure, working capital mechanics, and CapEx dynamics interact to produce free cash flow — then discounts that cash flow to an intrinsic equity value.

**Key capabilities:**

- 7-stage ETL pipeline ingesting raw NVIDIA 10-K CSV/XLSX files (FY2020–FY2025)
- Deterministic 3-statement model (IS → BS → CF) with explicit driver linkages
- FCFF-based DCF with WACC, terminal value, equity bridge, and sensitivity grid
- Deep-merge JSON scenario engine (Base / Upside / Downside) — base assumptions never mutated
- 8 KPIs with traffic-light signals calibrated to semiconductor industry benchmarks
- Streamlit dashboard: 5 tabs, live scenario switching, PDF/PPTX export
- 13-file pytest suite validating financial invariants against known 10-K values
- Docker + GitHub Actions CI with `PYTHONPATH=src` consistency across all environments

**Implied share price (base case):** $109.16  
**Market price (Oct 17 2025):** $183.22 — a 67.7% premium to intrinsic value  
**WACC:** 12.91% · **Terminal growth:** 3.675% · **Forecast:** FY2026–FY2030

---

## Architecture

```
Automated-FP-A-Dashboard/
│
├── data/
│   ├── raw/                    # READ-ONLY: NVIDIA 10-K source files (SEC EDGAR)
│   │   ├── income_statement_fy2020_fy2025.csv
│   │   ├── balance_sheet_fy2020_fy2025.csv
│   │   ├── cash_flow_fy2020_fy2025.csv
│   │   ├── segment_revenue_fy2020_fy2025.csv
│   │   └── ...                 # 13 files total
│   └── processed/              # ETL outputs: Parquet canonical tables
│       ├── actuals.parquet
│       ├── costs.parquet
│       ├── working_capital.parquet
│       ├── error_report.csv    # Always written, even on failure
│       └── etl_summary.json
│
├── src/                        # All finance logic lives here — never in app/
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── loader.py           # Raw file ingestion, column normalisation
│   │   ├── transformer.py      # Unit conversion (thousands → millions), derived fields
│   │   ├── validator.py        # Schema checks, range assertions, duplicate detection
│   │   ├── cleaner.py          # MISSING_VALUE_POLICY dict, per-column decisions
│   │   ├── pipeline.py         # Orchestrates all 7 ETL stages
│   │   └── canonical_schema.py # 91-column canonical definition
│   │
│   ├── modeling/
│   │   ├── __init__.py
│   │   ├── engine.py           # 10-step orchestrator: WACC→IS→D&A→NWC→BS→CF→FCFF→DCF→Reconcile
│   │   ├── wacc.py             # CAPM + Blume β adjustment, WACC computation
│   │   ├── income_statement.py # Revenue segmentation, gross/op/net margin drivers
│   │   ├── balance_sheet.py    # Asset/liability roll-forward, RE plug, BS invariant check
│   │   ├── cash_flow.py        # Indirect method: NI→CFO→CFI→CFF, net cash reconciliation
│   │   ├── fcff.py             # NOPAT = EBIT×(1−ETR); FCFF = NOPAT+D&A−|CapEx|−ΔNWC
│   │   └── dcf_valuation.py    # PV of FCFs, terminal value, equity bridge, sensitivity grid
│   │
│   ├── scenarios/
│   │   ├── __init__.py
│   │   └── engine.py           # deep_merge() recursive override; scenario switcher
│   │
│   ├── kpi/
│   │   ├── __init__.py
│   │   ├── kpis.py             # 8 pure functions; safe_divide() single gateway
│   │   ├── ratios.py           # Traffic-light thresholds (semiconductor benchmarks)
│   │   └── timeseries.py       # KPI roll across fiscal years
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── export_pdf.py       # ReportLab: executive summary PDF
│   │   └── export_ppt.py       # python-pptx: board-ready slide deck
│   │
│   └── utils/
│       ├── __init__.py
│       ├── safe_math.py        # safe_divide, safe_percent, clip_to_bounds
│       └── formatting.py       # currency, percent, basis-point formatters
│
├── config/
│   ├── assumptions.json        # Master truth: all model inputs documented with sources
│   └── scenarios.json          # Delta overrides per scenario (v1.2 — keys aligned)
│
├── app/
│   ├── __init__.py
│   └── app.py                  # Streamlit entry point — ZERO finance logic here
│
├── tests/
│   ├── conftest.py             # Fixtures: raw→canonical column mapping, demo data
│   ├── test_etl_pipeline.py
│   ├── test_wacc.py
│   ├── test_income_statement.py
│   ├── test_balance_sheet.py
│   ├── test_cash_flow.py
│   ├── test_fcff.py
│   ├── test_dcf_valuation.py
│   ├── test_scenario_engine.py
│   ├── test_kpis.py
│   ├── test_financial_invariants.py  # BS balances, CF reconciles, RE rolls
│   ├── test_golden_output.py         # Regression: known 10-K values vs model
│   ├── test_safe_math.py
│   └── test_export.py
│
├── docs/
│   ├── ARCHITECTURE.md         # Layer diagram, design decisions, data flow
│   ├── DATA_DICTIONARY.md      # Every canonical column: source, unit, formula
│   ├── FINANCIAL_MODEL.md      # Full model methodology: FCFF, WACC, DCF, assumptions
│   ├── TESTING.md              # Test strategy, invariants, golden output approach
│   ├── DECISIONS.md            # ADRs: why Parquet, why deep_merge, why end-of-year discounting
│   └── ROADMAP.md              # Phased development plan
│
├── assets/
│   └── dashboard_screenshot.png
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .gitignore
├── Dockerfile
├── Makefile
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

**Core principle:** Zero finance logic in `app/`. The dashboard is a thin presentation layer. All computation lives in `src/`, is unit-tested, and produces deterministic outputs given fixed inputs.

---

## Quickstart

### Prerequisites

- Python 3.11+
- Docker (optional, for containerised run)

### Local setup

```bash
# Clone
git clone https://github.com/Aditya-Gupta09/Automated-FP-A-Dashboard.git
cd Automated-FP-A-Dashboard

# Install dependencies
make install

# Run ETL pipeline (builds canonical Parquet tables from raw 10-K CSVs)
make etl

# Run full test suite
make test

# Launch dashboard
make run
```

### Docker

```bash
make docker-build
make docker-run
# → http://localhost:8501
```

### One-line local run

```bash
pip install -r requirements.txt && python -m src.etl.pipeline && streamlit run app/app.py
```

---

## Financial Model

### WACC Computation

| Input | Value | Source |
|---|---|---|
| Risk-free rate (Rf) | 4.07% | US 10-year Treasury, Jan 2025 |
| Raw beta (β) | 1.9157 | Yahoo Finance, 5-yr monthly |
| Blume-adjusted β | 1.7728 | β_adj = 0.67×β + 0.33×1.0 |
| Equity risk premium (ERP) | 5.00% | Damodaran, Jan 2025 |
| Cost of equity (Ke) | 12.91% | CAPM: Rf + β×ERP |
| Target capital structure | 100% equity | NVIDIA net cash positive |
| **WACC** | **12.91%** | |

### DCF Output — Base Case

| Line | Value |
|---|---|
| Sum PV of FCFs (FY26–30) | $660,851M |
| PV of Terminal Value | $1,958,774M |
| Enterprise Value | $2,619,625M |
| (−) Net Debt | −$32,940M |
| Equity Value | $2,652,565M |
| Diluted shares | 24,300M |
| **Implied share price** | **$109.16** |
| Market price (Oct 17, 2025) | $183.22 |
| Premium to intrinsic | **67.7%** |

### FCFF Formula

```
FCFF  = NOPAT + D&A − |CapEx| − ΔNWC
NOPAT = EBIT × (1 − Effective Tax Rate)   ← unlevered; tax on operating income, not EBT
TV    = FCFF₅ × (1 + g) / (WACC − g)      ← Gordon Growth
PV    = Σ [ FCFFₜ / (1 + WACC)ᵗ ]         ← end-of-year discounting
```

### Scenario Matrix

| | Base | Upside · Bull | Downside · Bear |
|---|---|---|---|
| DC revenue growth FY26F | +62% | +75% | +35% |
| Gross margin FY26F | 77.0% | 79.0% | 68.0% |
| CapEx % revenue | 3.0% | 2.5% | 5.0% |
| WACC | 12.91% | 11.91% | 13.91% |
| Terminal growth | 3.675% | 4.50% | 3.00% |
| **Implied price** | **$109.16** | **$229.53** | **$32.76** |

### Sensitivity Grid (Base WACC × Terminal g)

```
         g:  2.0%   2.5%   3.0%   3.5%   4.0%   4.5%   5.0%   5.5%   6.0%
WACC 10.9%  115.3  120.9  127.2  134.4  142.6  152.1  163.2  176.3↑ 192.2↑
     11.4%  108.9  113.8  119.3  125.5  132.5  140.6  149.9  160.8  173.7↑
     11.9%  103.1  107.5  112.3  117.7  123.8  130.7  138.6  147.8  158.5
     12.4%   98.0  101.8  106.1  110.9  116.2  122.2  128.9  136.7  145.7
  ★  12.9%   93.4   96.8  100.6  104.8 [109.4] 114.7  120.5  127.2  134.9
     13.4%   89.2   92.3   95.6   99.4  103.5  108.1  113.2  119.0  125.5
     13.9%   85.4   88.1   91.2   94.5   98.2  102.2  106.7  111.7  117.4

↑ = approaches / exceeds $183 market price. Requires most aggressive assumptions simultaneously.
```

---

## Testing

```bash
make test                    # Full suite with coverage
make test-invariants         # Financial invariant checks only
make test-golden             # Regression vs known 10-K values
pytest tests/ -v --tb=short  # Verbose output
```

**Three invariants checked on every model run (tolerance ±$0.01M):**

1. **Balance sheet:** Total Assets = Total Liabilities + Shareholders' Equity (all forecast years)
2. **Cash flow reconciliation:** Ending cash = Beginning cash + Net change in cash
3. **Retained earnings roll-forward:** RE_end = RE_begin + Net Income − Dividends

**Golden output tests** embed known NVIDIA 10-K values (FY2020–FY2025) directly in test assertions with inline citations to the filing page.

---

## KPIs & Benchmarks

| KPI | Formula | Green threshold | Semiconductor benchmark |
|---|---|---|---|
| Gross margin | Gross profit / Revenue | ≥ 60% | NVIDIA FY25: 75.0% |
| Operating margin | EBIT / Revenue | ≥ 30% | NVIDIA FY25: 62.1% |
| FCF margin | FCFF / Revenue | ≥ 20% | NVIDIA FY25: 48.7% |
| ROIC | NOPAT / Invested Capital | ≥ 20% | Fabless benchmark |
| Revenue growth YoY | ΔRevenue / Prior Revenue | ≥ 15% | Cycle-dependent |
| NWC days | (AR+Inv−AP) / (Rev/365) | ≤ 60 days | |
| CapEx intensity | CapEx / Revenue | ≤ 5% | Fabless model |
| Debt / EBITDA | Net debt / EBITDA | ≤ 1.5× | |

---

## Documentation

| Doc | Contents |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layer diagram, design decisions, data contracts |
| [FINANCIAL_MODEL.md](docs/FINANCIAL_MODEL.md) | Full FCFF/DCF/WACC methodology with sources |
| [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | All 91 canonical columns: source, unit, formula |
| [TESTING.md](docs/TESTING.md) | Test strategy, invariant design, golden output |
| [DECISIONS.md](docs/DECISIONS.md) | Architectural decision records (ADRs) |
| [ROADMAP.md](docs/ROADMAP.md) | Phased development plan |

---

## Data Sources

All actuals sourced directly from NVIDIA SEC filings. No synthetic data. No estimates.

| Filing | Period | Source |
|---|---|---|
| NVIDIA 10-K FY2025 | Jan 27, 2025 | SEC EDGAR |
| NVIDIA 10-K FY2024 | Jan 29, 2024 | SEC EDGAR |
| NVIDIA 10-K FY2023 | Feb 24, 2023 | SEC EDGAR |
| NVIDIA 10-K FY2022 | Feb 25, 2022 | SEC EDGAR |
| NVIDIA 10-K FY2021 | Feb 26, 2021 | SEC EDGAR |
| NVIDIA 10-K FY2020 | Feb 21, 2020 | SEC EDGAR |
| Beta source | 5-yr monthly | Yahoo Finance (as of Oct 2025) |
| ERP source | Jan 2025 | Damodaran online |
| Risk-free rate | Jan 2025 | US Treasury (FRED) |

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Data | pandas 2.2, pyarrow (Parquet) |
| Dashboard | Streamlit 1.32 |
| Testing | pytest 8.1, pytest-cov |
| Export | ReportLab (PDF), python-pptx |
| Containerisation | Docker (Python 3.11-slim) |
| CI | GitHub Actions |
| Config | JSON (assumptions + scenario delta files) |

---

## License

MIT — see [LICENSE](LICENSE). For educational and portfolio demonstration purposes.

---

<div align="center">
  <strong>Aditya Gupta</strong> · Financial Engineering · Python · Equity Research<br>
  <a href="https://github.com/Aditya-Gupta09">GitHub</a> · <a href="https://www.linkedin.com/in/aditya-gupta09/">LinkedIn</a>
</div>
