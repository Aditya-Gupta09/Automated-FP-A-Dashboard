# Raw Data

**DO NOT MODIFY THESE FILES.**

All files in this directory are sourced directly from NVIDIA SEC filings (EDGAR). They are the canonical source of truth. The ETL pipeline reads them and produces canonical Parquet tables in `data/processed/`.

## Files

| File | Content | Source |
|---|---|---|
| `income_statement_fy2020_fy2025.csv` | IS: Revenue, COGS, OpEx, EBIT, NI (FY2020–FY2025) | NVIDIA 10-K, Consolidated Statements of Income |
| `balance_sheet_fy2020_fy2025.csv` | BS: Assets, Liabilities, Equity (FY2020–FY2025) | NVIDIA 10-K, Consolidated Balance Sheets |
| `cash_flow_fy2020_fy2025.csv` | CF: CFO, CFI, CFF, CapEx (FY2020–FY2025) | NVIDIA 10-K, Consolidated Statements of Cash Flows |
| `segment_revenue_fy2020_fy2025.csv` | Revenue by segment (DC, Gaming, ProViz, Auto, OEM) | NVIDIA 10-K, Segment Information Note |
| `da_sbc_fy2020_fy2025.csv` | D&A and SBC (from CF statement) | NVIDIA 10-K, Supplemental Cash Flow |
| `working_capital_fy2020_fy2025.csv` | AR, Inventory, AP, Prepaid (FY2020–FY2025) | NVIDIA 10-K, Balance Sheets + Notes |

## Filing Dates

| Fiscal Year | Period End | Filed |
|---|---|---|
| FY2025 | Jan 26, 2025 | Jan 27, 2025 |
| FY2024 | Jan 28, 2024 | Jan 29, 2024 |
| FY2023 | Jan 29, 2023 | Feb 24, 2023 |
| FY2022 | Jan 30, 2022 | Feb 25, 2022 |
| FY2021 | Jan 31, 2021 | Feb 26, 2021 |
| FY2020 | Jan 26, 2020 | Feb 21, 2020 |

All filings available at: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=NVDA&type=10-K
