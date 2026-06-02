# Complete Repo Setup Guide
# Every command to execute, in order

## Step 1 — Clone and clean your existing repo

git clone https://github.com/Aditya-Gupta09/Automated-FP-A-Dashboard.git
cd Automated-FP-A-Dashboard

# Remove placeholder README (you'll replace it)
rm README.md


## Step 2 — Set GitHub repo metadata (do this on GitHub.com)

Go to: https://github.com/Aditya-Gupta09/Automated-FP-A-Dashboard
Click the gear icon next to "About"

Description:
  Institutional-grade NVIDIA FP&A platform: FCFF DCF · 3-statement model ·
  scenario engine · Streamlit dashboard · pytest suite · Docker · CI/CD

Website: (leave blank or add Streamlit Cloud URL later)

Topics (add all):
  financial-modeling  fpa  dcf  valuation  nvidia  python
  streamlit  pandas  pytest  docker  equity-research  capm  wacc


## Step 3 — Create the full directory structure

mkdir -p .github/workflows
mkdir -p config
mkdir -p data/raw
mkdir -p data/processed
mkdir -p docs
mkdir -p src/etl
mkdir -p src/modeling
mkdir -p src/scenarios
mkdir -p src/kpi
mkdir -p src/output
mkdir -p src/utils
mkdir -p tests
mkdir -p app
mkdir -p assets

# Create __init__.py files (makes each src/ subfolder a package)
touch src/__init__.py
touch src/etl/__init__.py
touch src/modeling/__init__.py
touch src/scenarios/__init__.py
touch src/kpi/__init__.py
touch src/output/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py
touch app/__init__.py
touch data/processed/.gitkeep


## Step 4 — Copy all generated files into place

Copy these files (all provided in this repo build):

ROOT LEVEL:
  README.md             ← full analyst-grade README with badges, tables, diagrams
  .gitignore            ← comprehensive Python + Streamlit + data artifacts
  pyproject.toml        ← pytest config, coverage, ruff, pythonpath=src
  requirements.txt      ← pinned versions, all dependencies
  Makefile              ← install, etl, test, lint, format, run, docker-*
  Dockerfile            ← multi-stage, non-root, health check
  CONTRIBUTING.md       ← financial modeling standards for PRs
  LICENSE               ← MIT (already exists)

.github/workflows/:
  ci.yml                ← lint → test → invariants → docker (4 jobs)

config/:
  assumptions.json      ← master truth: all inputs with sources
  scenarios.json        ← delta overrides v1.2 (key paths verified)

docs/:
  ARCHITECTURE.md       ← layer diagram, design decisions, data flow
  FINANCIAL_MODEL.md    ← full FCFF/DCF/WACC methodology
  DATA_DICTIONARY.md    ← all 91 canonical columns documented
  TESTING.md            ← test strategy, invariant design
  DECISIONS.md          ← 7 ADRs explaining non-obvious choices
  ROADMAP.md            ← 4-phase plan, current status

data/raw/:
  README.md             ← source documentation, filing dates, EDGAR links
  [your CSV files]      ← copy your actual 10-K CSVs here


## Step 5 — Copy your existing source code

Your existing project code maps like this:

YOUR PROJECT                    → THIS REPO
────────────────────────────────────────────────────────────
app_final/app.py                → app/app.py
src/etl/pipeline.py             → src/etl/pipeline.py
src/etl/loader.py               → src/etl/loader.py
src/etl/transformer.py          → src/etl/transformer.py
src/etl/validator.py            → src/etl/validator.py
src/etl/cleaner.py              → src/etl/cleaner.py
src/etl/canonical_schema.py     → src/etl/canonical_schema.py
src/modeling/engine.py          → src/modeling/engine.py
src/modeling/wacc.py            → src/modeling/wacc.py
src/modeling/income_statement.py→ src/modeling/income_statement.py
src/modeling/balance_sheet.py   → src/modeling/balance_sheet.py
src/modeling/cash_flow.py       → src/modeling/cash_flow.py
src/modeling/fcff.py            → src/modeling/fcff.py
src/modeling/dcf_valuation.py   → src/modeling/dcf_valuation.py
src/kpi/kpis.py                 → src/kpi/kpis.py
src/kpi/ratios.py               → src/kpi/ratios.py
src/output/export_pdf.py        → src/output/export_pdf.py
src/output/export_ppt.py        → src/output/export_ppt.py
tests/*                         → tests/*
config/assumptions.json         → config/assumptions.json  (use new version)
config/scenarios.json           → config/scenarios.json    (use new v1.2)

REMOVE from your repo:
  check_nwc.py          (debug script — move to debug/ branch or delete)
  debug_dcf_gap.py      (same)
  tempCodeRunnerFile.python
  streamlit.err.log / streamlit.out.log
  src/ts/               (empty directory)


## Step 6 — Fix the balance_sheet.py indentation bug

FIND in src/modeling/balance_sheet.py:

    for year in FORECAST_YEARS:
        # ... revenue, ebit, etc computations ...

    # BUG: these lines are OUTSIDE the for loop (wrong indent level):
    retained_earnings = compute_retained_earnings(...)
    apic = compute_apic(...)
    # ... plug logic ...
    rows.append(...)
    prior_ending_cash = cash

FIX: indent all of those lines one level deeper so they're INSIDE the for loop.

Verify the fix:
  python -c "from src.modeling.balance_sheet import build_balance_sheet; \
             import json; a = json.load(open('config/assumptions.json')); \
             df = build_balance_sheet(a, {}); print(len(df), 'rows (expect 5)')"


## Step 7 — Run ETL and tests

# Verify environment
python --version   # should be 3.11+
make install

# Run ETL pipeline
make etl
# → Should create data/processed/actuals.parquet, costs.parquet, etc.
# → Check data/processed/error_report.csv — should be empty or have only warnings

# Run full test suite
make test
# → All 13 test files should pass
# → Financial invariant tests must PASS (BS balances, CF reconciles, RE rolls)

# Run dashboard
make run
# → http://localhost:8501


## Step 8 — Verify CI locally before pushing

# Run the same checks CI will run:
make lint       # ruff check
make format     # ruff format --check
make test       # pytest + coverage
make test-invariants   # invariant check only

# Optional: build and test Docker
make docker-build
make docker-run


## Step 9 — First commit

git add .
git commit -m "feat: complete analyst-grade repo restructure

- Full README with badges, architecture diagram, DCF output table, 
  sensitivity grid, scenario matrix, KPI benchmarks, data sources
- Comprehensive .gitignore (Python, Streamlit, data artifacts, IDE)
- pyproject.toml: pytest config with pythonpath=['src'], coverage targets
- requirements.txt: pinned dependencies
- Makefile: 15 targets (install, etl, test, lint, format, run, docker-*)
- Dockerfile: multi-stage, non-root user, health check
- GitHub Actions CI: 4 jobs (lint, test, invariants, docker)
- config/assumptions.json v3.0: all inputs with sources
- config/scenarios.json v1.2: key paths aligned
- docs/: ARCHITECTURE, FINANCIAL_MODEL, DATA_DICTIONARY, TESTING, 
         DECISIONS (7 ADRs), ROADMAP
- data/raw/README.md: filing dates, EDGAR links
- CONTRIBUTING.md: financial modeling PR standards
- Fix: balance_sheet.py indentation bug (RE/APIC/rows inside for loop)
- Remove: debug scripts, tempCodeRunnerFile, log files, empty src/ts/"

git push origin main


## Step 10 — Add GitHub repo enhancements

RELEASE TAG:
  git tag -a v3.0.0 -m "v3.0.0 — Production-grade FP&A platform"
  git push origin v3.0.0

PIN TOPICS on GitHub.com:
  financial-modeling, fpa, dcf, valuation, nvidia, python,
  streamlit, pandas, pytest, docker, equity-research

ADD SCREENSHOT:
  Take a full-page screenshot of your dashboard
  Save as assets/dashboard_screenshot.png
  Add to README.md: ![Dashboard](assets/dashboard_screenshot.png)

ENABLE CODECOV (optional):
  Sign up at codecov.io with GitHub
  The ci.yml already uploads coverage.xml


## Final repo checklist

[ ] README renders correctly on GitHub (check: badges, tables, code blocks)
[ ] .gitignore excludes: __pycache__, .venv, *.parquet, *.log, tempCodeRunner*
[ ] pyproject.toml: pythonpath = ["src"] present
[ ] CI passes all 4 jobs on first push
[ ] make etl runs without errors
[ ] make test: all pass, coverage report visible
[ ] make test-invariants: PASS for all 5 forecast years
[ ] make run: dashboard loads at localhost:8501
[ ] GitHub topics set (10 topics)
[ ] Release tag v3.0.0 created
[ ] data/raw/ has your actual CSV files committed
[ ] data/processed/ is in .gitignore (regenerated by ETL)
[ ] No debug scripts at root level
[ ] No tempCodeRunnerFile.python committed
[ ] No .log files committed
