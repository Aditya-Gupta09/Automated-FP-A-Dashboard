// ============================================================
// NVIDIA FP&A Platform — canonical model data layer
// Every value traces to config/assumptions.json (v1.0) or the
// Python modeling engine outputs (src/modeling/engine.py).
// Source: NVIDIA 10-K SEC filings FY2020–FY2025 + Company_Valuation_Model.xlsx
// ============================================================

export type Scenario = 'base' | 'upside' | 'downside'

export const SCENARIOS: Scenario[] = ['base', 'upside', 'downside']

export const SCENARIO_META: Record<
  Scenario,
  { label: string; short: string; color: string }
> = {
  base: { label: 'Base Case', short: 'BASE', color: '#60a5fa' },
  upside: { label: 'Upside · Bull', short: 'BULL', color: '#34d399' },
  downside: { label: 'Downside · Bear', short: 'BEAR', color: '#f87171' },
}

// ---- WACC (15_WACC sheet) ----
export const WACC = {
  riskFreeRate: 0.0407,
  equityRiskPremium: 0.05,
  betaRaw: 0.6749,
  betaBlumeAdjusted: 1.7728,
  costOfEquityCapm: 0.12934,
  pretaxCostOfDebt: 0.028285,
  weightEquity: 0.99810,
  weightDebt: 0.0018973,
  wacc: 0.12914245,
  marketCapEquityUsdm: 4452000,
  totalDebtUsdm: 8463,
}

// ---- DCF canonical engine outputs (05b_DCF, expected_outputs) ----
export const DCF_OUTPUTS: Record<
  Scenario,
  {
    wacc: number
    terminalGrowth: number
    sumPvFcfUsdm: number
    terminalValueUsdm: number
    pvTerminalValueUsdm: number
    enterpriseValueUsdm: number
    equityValueUsdm: number
    impliedSharePriceUsd: number
  }
> = {
  base: {
    wacc: 0.1291,
    terminalGrowth: 0.03675,
    sumPvFcfUsdm: 660851,
    terminalValueUsdm: 3595241,
    pvTerminalValueUsdm: 1958774,
    enterpriseValueUsdm: 2619625,
    equityValueUsdm: 2652565,
    impliedSharePriceUsd: 109.16,
  },
  upside: {
    wacc: 0.1191,
    terminalGrowth: 0.045,
    sumPvFcfUsdm: 1042654,
    terminalValueUsdm: 7902409,
    pvTerminalValueUsdm: 4502099,
    enterpriseValueUsdm: 5544753,
    equityValueUsdm: 5577693,
    impliedSharePriceUsd: 229.53,
  },
  downside: {
    wacc: 0.1391,
    terminalGrowth: 0.03,
    sumPvFcfUsdm: 268551,
    terminalValueUsdm: 948427,
    pvTerminalValueUsdm: 494532,
    enterpriseValueUsdm: 763083,
    equityValueUsdm: 796023,
    impliedSharePriceUsd: 32.76,
  },
}

export const MARKET_PRICE_USD = 183.22
export const DILUTED_SHARES_M = 24300
export const NET_CASH_USDM = 32940 // net debt is negative (net cash position)
export const VALUATION_DATE = 'Oct 17, 2025'

// ---- Scenario assumption summaries (sidebar) ----
export const SCENARIO_ASSUMPTIONS: Record<
  Scenario,
  { label: string; value: string; dir: 'up' | 'down' | 'flat' }[]
> = {
  base: [
    { label: 'WACC', value: '12.91%', dir: 'flat' },
    { label: 'Terminal g', value: '3.675%', dir: 'flat' },
    { label: 'DC growth FY26F', value: '+69%', dir: 'flat' },
    { label: 'Gross margin FY26F', value: '77.0%', dir: 'flat' },
    { label: 'CapEx % rev', value: '3.0%', dir: 'flat' },
  ],
  upside: [
    { label: 'WACC', value: '11.91%', dir: 'up' },
    { label: 'Terminal g', value: '4.50%', dir: 'up' },
    { label: 'DC growth FY26F', value: '+95%', dir: 'up' },
    { label: 'Gross margin FY26F', value: '82.0%', dir: 'up' },
    { label: 'CapEx % rev', value: '3.5%', dir: 'flat' },
  ],
  downside: [
    { label: 'WACC', value: '13.91%', dir: 'down' },
    { label: 'Terminal g', value: '3.00%', dir: 'down' },
    { label: 'DC growth FY26F', value: '+50%', dir: 'down' },
    { label: 'Gross margin FY26F', value: '66.0%', dir: 'down' },
    { label: 'CapEx % rev', value: '2.0%', dir: 'flat' },
  ],
}

// ---- Forecast income statement (engine output, base) ----
export const FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]

export const INCOME_STATEMENT: Record<
  Scenario,
  {
    year: number
    revenue: number
    grossProfit: number
    ebit: number
    netIncome: number
    grossMarginPct: number
    ebitMarginPct: number
  }[]
> = {
  base: [
    { year: 2026, revenue: 179500, grossProfit: 135675, ebit: 112000, netIncome: 100000, grossMarginPct: 0.756, ebitMarginPct: 0.624 },
    { year: 2027, revenue: 272000, grossProfit: 204000, ebit: 170000, netIncome: 152000, grossMarginPct: 0.75, ebitMarginPct: 0.625 },
    { year: 2028, revenue: 386000, grossProfit: 289500, ebit: 240000, netIncome: 215000, grossMarginPct: 0.75, ebitMarginPct: 0.621 },
    { year: 2029, revenue: 490000, grossProfit: 367500, ebit: 310000, netIncome: 280000, grossMarginPct: 0.75, ebitMarginPct: 0.633 },
    { year: 2030, revenue: 625000, grossProfit: 468750, ebit: 390000, netIncome: 350000, grossMarginPct: 0.75, ebitMarginPct: 0.624 },
  ],
  upside: [
    { year: 2026, revenue: 205000, grossProfit: 168100, ebit: 143500, netIncome: 130000, grossMarginPct: 0.82, ebitMarginPct: 0.7 },
    { year: 2027, revenue: 330000, grossProfit: 277200, ebit: 234300, netIncome: 210000, grossMarginPct: 0.84, ebitMarginPct: 0.71 },
    { year: 2028, revenue: 490000, grossProfit: 421400, ebit: 357700, netIncome: 320000, grossMarginPct: 0.86, ebitMarginPct: 0.73 },
    { year: 2029, revenue: 650000, grossProfit: 572000, ebit: 487500, netIncome: 435000, grossMarginPct: 0.88, ebitMarginPct: 0.75 },
    { year: 2030, revenue: 880000, grossProfit: 792000, ebit: 686400, netIncome: 610000, grossMarginPct: 0.9, ebitMarginPct: 0.78 },
  ],
  downside: [
    { year: 2026, revenue: 160000, grossProfit: 105600, ebit: 80000, netIncome: 68000, grossMarginPct: 0.66, ebitMarginPct: 0.5 },
    { year: 2027, revenue: 185000, grossProfit: 121175, ebit: 92500, netIncome: 77000, grossMarginPct: 0.655, ebitMarginPct: 0.5 },
    { year: 2028, revenue: 200000, grossProfit: 130000, ebit: 98000, netIncome: 81000, grossMarginPct: 0.65, ebitMarginPct: 0.49 },
    { year: 2029, revenue: 205000, grossProfit: 133250, ebit: 100450, netIncome: 82000, grossMarginPct: 0.65, ebitMarginPct: 0.49 },
    { year: 2030, revenue: 215000, grossProfit: 138675, ebit: 105350, netIncome: 85000, grossMarginPct: 0.645, ebitMarginPct: 0.49 },
  ],
}

// ---- FCFF projections (engine output) ----
export const FCFF: Record<Scenario, { year: number; fcff: number; revenue: number }[]> = {
  base: [
    { year: 2026, fcff: 99315, revenue: 179500 },
    { year: 2027, fcff: 149946, revenue: 272000 },
    { year: 2028, fcff: 200235, revenue: 386000 },
    { year: 2029, fcff: 246423, revenue: 490000 },
    { year: 2030, fcff: 308056, revenue: 625000 },
  ],
  upside: [
    { year: 2026, fcff: 128000, revenue: 205000 },
    { year: 2027, fcff: 208000, revenue: 330000 },
    { year: 2028, fcff: 318000, revenue: 490000 },
    { year: 2029, fcff: 430000, revenue: 650000 },
    { year: 2030, fcff: 590000, revenue: 880000 },
  ],
  downside: [
    { year: 2026, fcff: 62000, revenue: 160000 },
    { year: 2027, fcff: 71000, revenue: 185000 },
    { year: 2028, fcff: 76000, revenue: 200000 },
    { year: 2029, fcff: 78000, revenue: 205000 },
    { year: 2030, fcff: 81000, revenue: 215000 },
  ],
}

// Historical FCFF (05a_FCFF)
export const FCFF_HISTORICAL = [
  { year: 2023, fcff: 2650 },
  { year: 2024, fcff: 23329 },
  { year: 2025, fcff: 55932 },
]

// ---- FY2025 historical actuals (cleaned_financials.csv) ----
export const FY2025_ACTUALS = {
  revenue: 130497,
  cogs: 32639,
  grossProfit: 97858,
  ebit: 81453,
  ebitda: 83317,
  da: 1864,
  netIncome: 72880,
  cfo: 64089,
  capex: -3236,
  fcf: 60853,
  totalAssets: 111601,
  totalDebt: 10270,
  shareholdersEquity: 79327,
  accountsReceivable: 23065,
  inventory: 10080,
  accountsPayable: 6310,
  cashAndInvestments: 43210,
  nwc: 18869,
}

// ---- Segments (01_Historical_IS + 04a_Projection_IS) ----
export const SEGMENTS = [
  { key: 'data_center', label: 'Data Center', color: '#76b900' },
  { key: 'gaming', label: 'Gaming', color: '#60a5fa' },
  { key: 'professional_viz', label: 'Prof. Visualization', color: '#34d399' },
  { key: 'automotive', label: 'Automotive', color: '#fbbf24' },
  { key: 'oem_and_other', label: 'OEM & Other', color: '#64748b' },
] as const

export type SegmentKey = (typeof SEGMENTS)[number]['key']

export const SEGMENT_FY2025: Record<SegmentKey | 'total', number> = {
  data_center: 115186,
  gaming: 11350,
  professional_viz: 1878,
  automotive: 1694,
  oem_and_other: 389,
  total: 130497,
}

export const SEGMENT_HISTORY: Record<SegmentKey, Record<number, number>> = {
  data_center: { 2023: 15005, 2024: 47467, 2025: 115186 },
  gaming: { 2023: 9068, 2024: 10448, 2025: 11350 },
  professional_viz: { 2023: 1544, 2024: 1591, 2025: 1878 },
  automotive: { 2023: 903, 2024: 1090, 2025: 1694 },
  oem_and_other: { 2023: 454, 2024: 326, 2025: 389 },
}

// FY26F growth by scenario, and forward years for projection
export const SEGMENT_GROWTH_FY26: Record<SegmentKey, Record<Scenario, number>> = {
  data_center: { base: 0.69, upside: 0.95, downside: 0.5 },
  gaming: { base: 0.05, upside: 0.15, downside: -0.05 },
  professional_viz: { base: 0.06, upside: 0.15, downside: -0.02 },
  automotive: { base: 0.45, upside: 0.65, downside: 0.1 },
  oem_and_other: { base: 0.02, upside: 0.1, downside: -0.05 },
}

// Base-case forward growth path per segment (assumptions.json revenue_growth)
export const SEGMENT_GROWTH_PATH: Record<
  SegmentKey,
  Record<Scenario, number[]>
> = {
  data_center: {
    base: [0.69, 0.42, 0.27, 0.16, 0.22],
    upside: [0.95, 0.55, 0.35, 0.22, 0.42],
    downside: [0.5, 0.12, 0.04, -0.05, 0.02],
  },
  gaming: {
    base: [0.05, 0.03, 0.02, 0.02, 0.03],
    upside: [0.15, 0.1, 0.02, 0.02, 0.03],
    downside: [-0.05, -0.05, 0.02, 0.02, 0.03],
  },
  professional_viz: {
    base: [0.06, 0.07, 0.05, 0.04, 0.05],
    upside: [0.15, 0.07, 0.05, 0.04, 0.05],
    downside: [-0.02, 0.07, 0.05, 0.04, 0.05],
  },
  automotive: {
    base: [0.45, 0.5, 0.35, 0.26, 0.35],
    upside: [0.65, 1.0, 0.35, 0.26, 0.35],
    downside: [0.1, 0.05, 0.35, 0.26, 0.35],
  },
  oem_and_other: {
    base: [0.02, 0.03, 0.02, 0.02, 0.03],
    upside: [0.1, 0.03, 0.02, 0.02, 0.03],
    downside: [-0.05, 0.03, 0.02, 0.02, 0.03],
  },
}

// ---- Geographic revenue FY2025 (10_GrowthRates) ----
export const GEO_FY2025 = [
  { region: 'United States', rev: 61257, pct: 0.469, color: '#76b900' },
  { region: 'Singapore', rev: 23684, pct: 0.182, color: '#60a5fa' },
  { region: 'Taiwan', rev: 20573, pct: 0.158, color: '#34d399' },
  { region: 'China + HK', rev: 17108, pct: 0.131, color: '#fbbf24' },
  { region: 'Other', rev: 7875, pct: 0.06, color: '#64748b' },
]

// ---- KPI traffic-light signals FY2025 (src/kpi/ratios.py) ----
export const KPI_SIGNALS = [
  { name: 'Gross margin', display: '75.0%', signal: 'green', pct: 88 },
  { name: 'EBITDA margin', display: '63.8%', signal: 'green', pct: 80 },
  { name: 'FCF margin', display: '46.6%', signal: 'green', pct: 78 },
  { name: 'Revenue growth', display: '+114.2%', signal: 'green', pct: 76 },
  { name: 'AR days (DSO)', display: '64.5d', signal: 'amber', pct: 28 },
  { name: 'AP days (DPO)', display: '70.6d', signal: 'green', pct: 78 },
  { name: 'Current ratio', display: '4.44x', signal: 'green', pct: 63 },
  { name: 'Int. coverage', display: '329.8x', signal: 'green', pct: 82 },
] as const

// ---- Working capital history (09_WorkingCapital) ----
export const WC_HISTORY = [
  { year: 2021, dso: 53.2, dio: 106.1, dpo: 66.8, ccc: 92.5 },
  { year: 2022, dso: 63.1, dio: 100.7, dpo: 68.9, ccc: 94.8 },
  { year: 2023, dso: 51.8, dio: 162.1, dpo: 37.5, ccc: 176.4 },
  { year: 2024, dso: 59.9, dio: 116.0, dpo: 59.3, ccc: 116.6 },
  { year: 2025, dso: 64.5, dio: 112.7, dpo: 70.6, ccc: 106.7 },
]

// ---- Ratio history (08_RatioAnalysis) ----
export const RATIO_HISTORY = [
  { year: 2020, gm: 0.619, ebitda: 0.296, current: null, de: null },
  { year: 2021, gm: 0.623, ebitda: 0.338, current: 4.09, de: 0.7 },
  { year: 2022, gm: 0.649, ebitda: 0.417, current: 6.65, de: 0.66 },
  { year: 2023, gm: 0.569, ebitda: 0.214, current: 3.52, de: 0.86 },
  { year: 2024, gm: 0.727, ebitda: 0.566, current: 4.17, de: 0.53 },
  { year: 2025, gm: 0.75, ebitda: 0.638, current: 4.44, de: 0.41 },
]

// ---- Comparable companies (17_ComparableAnalysis, Oct 17 2025 LTM) ----
export const PEERS = [
  { ticker: 'NVDA', name: 'NVIDIA', evB: 4406.05, evEbitda: 44.83, pe: 52.2, evRev: 26.67, subject: true },
  { ticker: 'AVGO', name: 'Broadcom', evB: 1703.17, evEbitda: 52.01, pe: 89.11, evRev: 28.42, subject: false },
  { ticker: 'TSM', name: 'TSMC', evB: 1168.51, evEbitda: 14.29, pe: 29.69, evRev: 9.81, subject: false },
  { ticker: 'AMD', name: 'AMD', evB: 376.27, evEbitda: 68.29, pe: 134.73, evRev: 12.71, subject: false },
  { ticker: 'QCOM', name: 'Qualcomm', evB: 180.22, evEbitda: 12.99, pe: 15.78, evRev: 4.17, subject: false },
  { ticker: 'INTC', name: 'Intel', evB: 205.15, evEbitda: 22.3, pe: null, evRev: 3.87, subject: false },
]

export const PEER_MEDIAN = { evEbitda: 22.3, pe: 29.7, evRev: 9.8 }

export const COMPS_IMPLIED = { evEbitdaMedian: 56.24, evRevMedian: 131.5 }

export const EXIT_CROSSCHECK = {
  fy2030Ebitda: 387543,
  exitMultiple: 22.3,
  terminalEv: 8642198,
  pvTerminalEv: 4708478,
  sumPvFcf: 664085,
  totalEvExit: 5372563,
  gordonGrowthEv: 2622182,
  premiumExitVsGg: 2.05,
}

export const MULTIPLE_STATS = {
  high: 68.29,
  p75: 52.01,
  mean: 35.18,
  median: 22.3,
  p25: 13.64,
  low: 12.99,
}

// ---- Margin assumption paths per scenario (04a_Projection_IS) ----
export const GROSS_MARGIN_PATH: Record<Scenario, number[]> = {
  base: [0.7699, 0.7899, 0.8099, 0.8299, 0.8499],
  upside: [0.8199, 0.8399, 0.8599, 0.8799, 0.8999],
  downside: [0.66, 0.655, 0.65, 0.65, 0.645],
}

export const CAPEX_PCT_PATH: Record<Scenario, number[]> = {
  base: [0.03, 0.032, 0.033, 0.03, 0.028],
  upside: [0.035, 0.04, 0.045, 0.035, 0.045],
  downside: [0.02, 0.022, 0.023, 0.02, 0.025],
}

export const TAX_RATE_PATH: Record<Scenario, number[]> = {
  base: [0.15, 0.145, 0.145, 0.14, 0.14],
  upside: [0.13, 0.125, 0.125, 0.12, 0.12],
  downside: [0.16, 0.17, 0.17, 0.175, 0.18],
}
