# Data Dictionary

All 91 columns in the canonical `actuals.parquet` table. Sourced from NVIDIA 10-K filings (SEC EDGAR).

**Units:** USD millions unless noted. Percentages as decimals (0.75 = 75%).  
**Convention:** Costs and expenses are positive values. Net debt negative = net cash.  
**Q4 Note:** The model uses annual fiscal years only (no quarterly breakdown). Q4 = FY total − FY first three quarters.

---

## Identifier Columns

| Column | Type | Description |
|---|---|---|
| `fiscal_year` | str | e.g., "FY2025". NVIDIA fiscal year ends late January. |
| `period_end_date` | date | Actual fiscal year-end date (e.g., 2025-01-26) |
| `filing_date` | date | Date 10-K filed with SEC |

---

## Income Statement

### Revenue & Segmentation

| Column | Type | Source | Formula / Notes |
|---|---|---|---|
| `revenue_usdm` | float | IS, top line | Total net revenue. All revenue is product revenue (no services). |
| `dc_revenue_usdm` | float | IS segment note | Data Center segment. Largest and fastest-growing. Includes cloud and enterprise hyperscalers. |
| `gaming_revenue_usdm` | float | IS segment note | Gaming segment. Consumer GPUs and gaming platforms. Cyclical. |
| `pro_viz_revenue_usdm` | float | IS segment note | Professional Visualization. Enterprise workstations and CAD/design rendering. Stable. |
| `automotive_revenue_usdm` | float | IS segment note | Automotive. Autonomous vehicles, self-driving platforms. New/growing segment. |
| `oem_other_revenue_usdm` | float | IS segment note | OEM & Other. Original equipment manufacturers and miscellaneous revenue. |

**Segment accounting:** Segments must sum to total revenue ± rounding error. If DC + Gaming + ProViz + Auto + OEM ≠ Total, data quality issue. The model validates this in `src/etl/validator.py`.

### Cost of Goods Sold & Gross Profit

| Column | Type | Source | Formula / Notes |
|---|---|---|---|
| `cogs_usdm` | float | IS | Cost of revenue. Includes wafer costs, memory, assembly, test. Fabless model: NVIDIA designs but TSMC manufactures. |
| `gross_profit_usdm` | float | Derived | Revenue − COGS. Raw margin before OpEx. |
| `gross_margin_pct` | float | Derived | Gross profit / Revenue. FY2025: 75.0%. Semiconductors typically 60–80%. NVIDIA is at high end due to premium positioning. |

**Accounting notes:**
- COGS is expensed when products are sold (not when manufactured). This is revenue recognition policy per ASC 606.
- COGS includes depreciation of manufacturing equipment (though NVIDIA doesn't manufacture directly — costs are contracted to TSMC).
- Changes in inventory flow through COGS via cost of goods sold formula: COGS = Beginning inventory + Purchases − Ending inventory.

### Operating Expenses

| Column | Type | Source | Formula / Notes |
|---|---|---|---|
| `rd_expense_usdm` | float | IS | Research & development. All R&D is expensed immediately (not capitalized). Includes GPU architecture, CUDA software, AI algorithm development. |
| `sga_expense_usdm` | float | IS | Selling, general & administrative. Sales force, marketing, finance, legal, HR. |
| `total_opex_usdm` | float | Derived | R&D + SG&A. Operating expenses (not including COGS). |

**Accounting notes:**
- R&D is expensed because semiconductor design is inherently risky and benefits may not materialize. Capitalization is rare.
- SG&A includes stock-based compensation (SBC). See `sbc_usdm` column.
- OpEx scales with revenue but doesn't increase proportionally (operating leverage).

### Operating Income (EBIT)

| Column | Type | Source | Formula / Notes |
|---|---|---|---|
| `ebit_usdm` | float | Derived | Gross profit − Total OpEx. Earnings before interest and taxes. This is operating profit from the business itself. |
| `ebit_margin_pct` | float | Derived | EBIT / Revenue. FY2025: 62.1%. Shows operating leverage. |

**EBIT vs EBITDA:** This model uses EBIT (not EBITDA) for DCF because D&A is a non-cash item that MUST be added back in FCFF. EBITDA would double-count D&A.

### Interest, Taxes, and Net Income

| Column | Type | Source | Formula / Notes |
|---|---|---|---|
| `interest_income_usdm` | float | IS | Interest earned on cash / short-term investments. NVIDIA has large cash balance (>$30B), so interest income is substantial ($1–2B annually). |
| `interest_expense_usdm` | float | IS | Interest on debt. NVIDIA has minimal debt, so this is small (< $0.1B). |
| `other_income_usdm` | float | IS | Non-operating other income/(expense). Includes gains/losses on equity investments, foreign exchange, etc. Usually small. |
| `ebt_usdm` | float | Derived | EBIT + Interest income − Interest expense + Other. Earnings before taxes. This is the profit subject to income tax. |
| `income_tax_usdm` | float | IS | Provision for income taxes. Includes federal, state, and international taxes. |
| `effective_tax_rate` | float | Derived | Income tax / EBT. NVIDIA's effective rate is ~12.65% (lower than 21% statutory due to R&D tax credits, global income allocation). |
| `net_income_usdm` | float | IS | Net income attributable to NVIDIA. Bottom-line profit. FY2025: $72,880M. This is what flows into retained earnings. |
| `net_margin_pct` | float | Derived | Net income / Revenue. FY2025: 55.9%. Exceptional for a semiconductor company. |

**Tax accounting:**
- Effective tax rate = Income tax / EBT. Not the statutory 21% federal rate because:
  - R&D tax credits (federal and state)
  - Foreign earnings (Singapore, Taiwan) taxed at lower rates
  - Tax deferral strategies (legal and legitimate)
- The model uses historical ETR from 10-K Note 8 (income taxes).

### Depreciation & Amortization and Stock-Based Compensation

| Column | Type | Source | Formula / Notes |
|---|---|---|---|
| `da_usdm` | float | CF or Notes | Depreciation & amortization. Non-cash expense. Includes depreciation of facilities, servers, and amortization of intangible assets (acquired R&D, patents). |
| `sbc_usdm` | float | CF | Stock-based compensation. Non-cash expense. Includes employee stock options, RSUs, and ESPP contributions. NVIDIA's SBC is large (>$2B annually) due to high stock price and competitive talent market. |

**Why D&A and SBC matter:**
- D&A reduces net income but doesn't reduce cash (it's non-cash).
- SBC reduces net income (dilutes shareholders) but doesn't reduce cash.
- In FCFF, both are added back: FCFF = EBIT×(1−t) + D&A + SBC − CapEx − ΔNWC

---

## Balance Sheet — Assets

### Current Assets

| Column | Type | Source | Notes |
|---|---|---|---|
| `cash_usdm` | float | BS | Cash and cash equivalents. NVIDIA's cash management policy is conservative. Large balance (>$30B) provides financial flexibility and offsets debt for net cash calculation. |
| `st_investments_usdm` | float | BS | Short-term investments / marketable securities. Highly liquid, < 1 year maturity. Part of net cash calculation. |
| `accounts_receivable_usdm` | float | BS | Net accounts receivable. Revenue is recognized when shipped (ASC 606). AR is the outstanding receivables from customers. FY2025: $23,065M. |
| `inventory_usdm` | float | BS | Inventories. NVIDIA holds finished goods and work-in-process. Inventory days = Inventory / (COGS/365). FY2025: ~45 days. |
| `prepaid_other_ca_usdm` | float | BS | Prepaid expenses and other current assets. Prepaid software licenses, insurance, utilities. Immaterial to model. |
| `total_current_assets_usdm` | float | BS | Sum of current assets. Cash + ST Investments + AR + Inventory + Prepaid. |

**Working capital management:**
- Days Sales Outstanding (DSO) = AR / (Revenue/365). FY2025: ~64 days. Customers (cloud hyperscalers) have payment terms of 30–60 days. DSO of 64 days is typical and healthy.
- Days Inventory Outstanding (DIO) = Inventory / (COGS/365). FY2025: ~88 days. Reflects supply chain complexities (wafer lead times from TSMC).
- Days Payable Outstanding (DPO) = AP / (COGS/365). FY2025: ~71 days. NVIDIA pays suppliers (TSMC, memory vendors, assembly partners) on net-60 or net-90 terms.
- Cash Conversion Cycle (CCC) = DSO + DIO − DPO. FY2025: 64 + 88 − 71 = 81 days. Positive CCC means NVIDIA finances inventory/AR. This is normal for high-growth companies.

### Non-Current Assets

| Column | Type | Source | Notes |
|---|---|---|---|
| `ppe_gross_usdm` | float | BS Notes | Property, plant & equipment, gross. Includes facilities (design centers, offices), servers, test equipment. Capital-intensive operations require on-going investment. |
| `accumulated_depreciation_usdm` | float | BS Notes | Accumulated depreciation. Historical depreciation of all PP&E over useful lives (3–7 years for equipment, 15–20 for buildings). |
| `ppe_net_usdm` | float | BS | PP&E, net = Gross − Accumulated depreciation. Net book value. |
| `operating_lease_rou_usdm` | float | BS | Operating lease right-of-use assets. Under ASC 842 (adopted 2019), operating leases are capitalized. ROU = present value of remaining lease payments. NVIDIA leases facilities and equipment. |
| `intangibles_usdm` | float | BS | Intangible assets, net. Includes acquisition-related intangibles (purchased patents, technology, customer relationships) and capitalized software. Amortized over 3–15 years. |
| `goodwill_usdm` | float | BS | Goodwill. Excess purchase price paid over fair value of assets in acquisitions (e.g., Arm attempted acquisition, past acquisitions). Tested annually for impairment. |
| `lt_investments_usdm` | float | BS | Long-term investments. Strategic stakes in other companies, joint ventures, or long-term securities. Usually < 5% of total assets. |
| `other_lt_assets_usdm` | float | BS | Other non-current assets. Deferred tax assets, pension assets (if any), long-term prepaid items. Immaterial. |
| `total_assets_usdm` | float | BS | Total assets. Must equal Total Liabilities + Total Equity (balance sheet identity). FY2025: $111,601M. |

---

## Balance Sheet — Liabilities & Equity

### Current Liabilities

| Column | Type | Source | Notes |
|---|---|---|---|
| `accounts_payable_usdm` | float | BS | Accounts payable. NVIDIA owes TSMC, memory suppliers, assembly partners for goods/services received but not paid. FY2025: $6,310M. |
| `accrued_liabilities_usdm` | float | BS | Accrued and other current liabilities. Includes accrued payroll (bonuses, salaries), accrued utilities, warranty accruals. Liabilities that will be paid within 12 months. |
| `deferred_revenue_current_usdm` | float | BS | Deferred revenue, current. Customer deposits or prepayments for goods to be delivered within 12 months. Under ASC 606, deferred revenue is a liability until goods are shipped. Usually immaterial for NVIDIA. |
| `total_current_liabilities_usdm` | float | BS | Sum of current liabilities. Must be paid or settled within 12 months. |

### Non-Current Liabilities

| Column | Type | Source | Notes |
|---|---|---|---|
| `lt_debt_usdm` | float | BS | Long-term debt, net of current portion. Bonds and term loans due > 1 year. NVIDIA issued debt occasionally but prefers equity financing due to strong cash flow and stock valuation. FY2025: $1,891M (very low). |
| `operating_lease_lt_usdm` | float | BS | Operating lease liability, non-current. Portion of capitalized lease obligations due > 1 year. Matching ROU asset above. |
| `deferred_tax_lt_usdm` | float | BS | Deferred tax liabilities, non-current. Timing differences between GAAP tax and book tax. Usually immaterial. |
| `other_lt_liabilities_usdm` | float | BS | Other non-current liabilities. Pension obligations (if any), warranty reserves (if any), long-term accruals. Immaterial. |
| `total_lt_liabilities_usdm` | float | Derived | Sum of non-current liabilities. Liabilities due > 1 year. |
| `total_liabilities_usdm` | float | BS | Total liabilities = Current + Non-current. |

### Shareholders' Equity

| Column | Type | Source | Notes |
|---|---|---|---|
| `common_stock_usdm` | float | BS | Common stock and APIC (additional paid-in capital). Represents par value of common stock issued + premiums received from issuance above par. NVIDIA has ~2.4B diluted shares outstanding at ~$183/share. |
| `retained_earnings_usdm` | float | BS | Accumulated retained earnings. Cumulative net income since inception minus cumulative dividends paid. The "plug" in the balance sheet for the model (solved via RE = prior RE + NI − Dividends). |
| `aoci_usdm` | float | BS | Accumulated other comprehensive income/(loss). Unrealized gains/losses on available-for-sale securities, foreign currency translation adjustments, pension remeasurements. Usually < ±$500M for NVIDIA. |
| `total_equity_usdm` | float | BS | Total stockholders' equity = Common stock + APIC + Retained earnings + AOCI. Owners' claim on assets. FY2025: $65,728M. |
| `total_liabilities_equity_usdm` | float | Derived | Must equal total_assets (balance sheet identity check). |

**Balance sheet identity:** Assets = Liabilities + Equity. This is fundamental accounting. If it doesn't hold, there's a data error or model bug.

---

## Cash Flow Statement

| Column | Type | Source | Notes |
|---|---|---|---|
| `cfo_usdm` | float | CF | Net cash from operating activities. Cash generated by the business through normal operations. NVIDIA's CFO is ~49% of revenue (very high). Calculated using indirect method (start with NI, add back non-cash items, adjust for working capital changes). |
| `capex_usdm` | float | CF | Capital expenditures (purchases of PP&E). **Positive convention** (unlike some texts that show it negative). Represents cash outflow for new facilities, equipment, technology. Fabless companies like NVIDIA have lower CapEx (<5% of revenue) vs foundries (>20%). |
| `cfi_usdm` | float | CF | Net cash from investing activities. Includes CapEx (cash outflow), acquisitions (outflow), and investment in securities (variable). |
| `cff_usdm` | float | CF | Net cash from financing activities. Includes debt issuance/repayment, stock buybacks (large for NVIDIA), and dividend payments (small). |
| `net_change_cash_usdm` | float | Derived | CFO + CFI + CFF. Net change in cash balance from beginning to end of year. |
| `buybacks_usdm` | float | CF | Share repurchases. NVIDIA aggressively buys back stock (reduces share count, increases EPS). Reflects confidence in business and excess cash generation. FY2025: >$10B. |
| `dividends_usdm` | float | CF | Dividends paid. NVIDIA pays a small dividend (< 0.1% yield). Most cash returned via buybacks, not dividends. FY2025: ~$0.5B. |

**Cash flow analysis:**
- Strong CFO (free cash generation) is a hallmark of quality companies.
- NVIDIA's CFO > Net Income because D&A and SBC are added back (non-cash), and working capital is efficient.
- Low CapEx (fabless model) allows cash return to shareholders (buybacks).
- CFF is often negative (more cash returned than debt issued).

---

## Derived & KPI Columns

| Column | Type | Formula | Benchmark | Signal |
|---|---|---|---|---|
| `fcf_usdm` | float | CFO − CapEx | N/A | None (absolute $, not thresholded) |
| `fcf_margin_pct` | float | FCF / Revenue | ≥ 25% → GREEN | Green if ≥ 25%; grey otherwise |
| `roic_pct` | float | NOPAT / (Equity + LT Debt) | ≥ 15% → GREEN | Green if ≥ 15%; amber 5–15%; red < 5% |
| `net_debt_usdm` | float | LT Debt − Cash − ST Inv | Negative (net cash) | None |
| `nwc_usdm` | float | AR + Inv − AP | Minimize | None |
| `ar_days` | float | AR / (Revenue/365) | ≤ 45d → GREEN | Green ≤ 45d; amber 45–70d; red > 70d |
| `inventory_days` | float | Inv / (COGS/365) | ≤ 45d → GREEN | Green ≤ 45d; amber 45–60d; red > 60d |
| `ap_days` | float | AP / (COGS/365) | ≥ 60d → GREEN | Green ≥ 60d; amber 30–60d; red < 30d |
| `capex_pct_revenue` | float | CapEx / Revenue | ≤ 5% → GREEN | Green ≤ 5%; amber 5–10%; red > 10% |
| `revenue_growth_yoy` | float | (Revenue_t − Revenue_{t−1}) / Revenue_{t−1} | ≥ 15% → GREEN | Green ≥ 15%; amber 0–15%; red < 0% |
| `ebitda_usdm` | float | EBIT + D&A | N/A | None |
| `net_debt_ebitda` | float | Net Debt / EBITDA | ≤ 1.5× → GREEN | Green ≤ 1.5×; amber 1.5–3×; red > 3× |

**Ratio explanations:**

- **AR Days (DSO):** How long it takes to collect cash after a sale. Lower is better (cash in faster). NVIDIA's 45-day benchmark reflects hyperscaler payment terms.
- **Inventory Days (DIO):** How long inventory sits before being sold. Lower is better (capital tied up). Semiconductor supply chains are long; 45 days is typical.
- **AP Days (DPO):** How long NVIDIA takes to pay suppliers. Higher is better (delays cash outflow). 60+ days shows strong supplier relationships and pricing power.
- **FCF Margin:** Free cash generated as % of revenue. > 25% is exceptional; indicates pricing power and operational efficiency.
- **ROIC:** Return on invested capital. How efficiently the company deploys capital. > 15% signals competitive advantage. NVIDIA's ROIC is >100% (extraordinary).
- **CapEx intensity:** CapEx as % of revenue. Fabless (NVIDIA) ≤ 3%; foundry (TSMC) ≥ 20%; IDM (Intel) 20–30%.

---

## DCF Model Parameters

Stored in `config/assumptions.json`:

| Parameter | Value | Source |
|---|---|---|
| Valuation date | 2025-10-17 | Snapshot date |
| Market price | $183.22/share | Yahoo Finance Oct 17 2025 |
| WACC (base) | 12.91% | CAPM: Rf + β × ERP |
| Terminal growth (base) | 3.675% | US nominal GDP + AI premium |
| Diluted shares | 24,300M | 10-K FY2025 Note 14 |
| Implied price (base) | $109.16 | DCF output |
| Upside/downside vs market | −40.3% | (Implied − Market) / Market |
| Forecast horizon | FY2026–FY2030 | 5 years |

---

## Configuration Reference

See `config/assumptions.json` for:
- WACC inputs (Rf, β, ERP, cost of equity)
- Revenue growth by segment
- Margin assumptions (gross, OpEx %)
- CapEx % of revenue
- Working capital metrics (AR/Inv/AP days)
- DCF parameters (terminal growth, discounting)

All inputs are documented with sources and rationales.
