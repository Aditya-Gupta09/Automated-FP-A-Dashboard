# Roadmap

## Phase 1 — Core model (complete ✅)

- [x] ETL pipeline: 7-stage, canonical Parquet output, error report
- [x] WACC: CAPM + Blume adjustment, net debt computation
- [x] 3-statement model: IS → BS → CF, RE roll-forward plug
- [x] FCFF: NOPAT on EBIT, unlevered cash flow
- [x] DCF: PV explicit FCFs, Gordon Growth terminal value, equity bridge
- [x] Scenario engine: deep_merge(), 3 scenarios, immutable base
- [x] KPI engine: 8 pure functions, safe_divide, traffic-light signals
- [x] 3-invariant reconciliation: BS, CF, RE at ±$0.01M
- [x] Streamlit dashboard: 5 tabs, scenario switcher, filter bar

## Phase 2 — Production hardening (in progress 🔄)

- [x] Docker: multi-stage build, non-root user, health check
- [x] GitHub Actions CI: lint → test → invariants → docker
- [x] pytest suite: 13 files, golden output, integration tests
- [ ] PDF export: executive summary (ReportLab)
- [ ] PPTX export: board deck (python-pptx)
- [ ] Streamlit Cloud deployment
- [ ] Codecov badge integration

## Phase 3 — Analytics extensions (planned 📋)

- [ ] Comps table: peer group (AMD, Intel, Broadcom, TSMC) vs NVIDIA multiples
- [ ] LTM (last twelve months) rolling computation
- [ ] Segment revenue decomposition: Data Center by end-market (cloud, enterprise, sovereign)
- [ ] Regression analysis: NVDA revenue vs hyperscaler CapEx (MSFT, AMZN, GOOG, META)
- [ ] Monte Carlo DCF: distribution of implied prices from probabilistic assumptions

## Phase 4 — Automation (planned 📋)

- [ ] SEC EDGAR API integration: auto-pull 10-K filings on release
- [ ] Data validation against XBRL tags: machine-readable financial data
- [ ] Scheduled CI run: quarterly (post-10-K/10-Q filing)
- [ ] Email alert: model output delta vs prior quarter
