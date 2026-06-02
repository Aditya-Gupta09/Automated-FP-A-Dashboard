"""
src/kpi/kpis.py
===============
KPI engine for the NVIDIA DCF Valuation project.

Design rules (Tasks 1 & 2):
  - Pure functions only — no side effects, no global state
  - All KPIs return float or None (never NaN, never raise ZeroDivisionError)
  - Output is always a plain typed dict — no DataFrames
  - safe_divide() is the single gateway for every division operation
  - Formula definitions match standard FP&A / CFA conventions exactly

8 Core KPIs
-----------
1.  gross_margin       = (revenue - cogs) / revenue
2.  ebitda_margin      = ebitda / revenue
3.  fcf                = cfo + capex   [capex is negative in source data]
4.  fcf_margin         = fcf / revenue
5.  revenue_growth     = (rev_t - rev_t_1) / rev_t_1
6.  ar_days   (DSO)    = ar / (revenue / 365)
7.  ap_days   (DPO)    = ap / (cogs / 365)
8.  current_ratio      = current_assets / current_liabilities

Data assumptions (matched to cleaned_financials.csv + nvidia_historical_BS.csv):
  - All monetary values in USD millions
  - capex is stored as a negative number (cash outflow convention)
  - 365-day year used for all days-based KPIs
  - Missing inputs produce None output — not zero, not error
"""

from __future__ import annotations
from typing import Optional

# ── Primitive ─────────────────────────────────────────────────────────────────


def safe_divide(
    numerator: Optional[float], denominator: Optional[float]
) -> Optional[float]:
    """
    Safe division gateway used by every KPI formula.

    Returns:
        float  — quotient when both inputs are valid and denominator != 0
        None   — when either input is None, or denominator is zero

    Never raises ZeroDivisionError. Never returns NaN or Infinity.

    Examples:
        safe_divide(97858, 130497)  →  0.7499
        safe_divide(0, 0)           →  None
        safe_divide(None, 100)      →  None
        safe_divide(100, 0)         →  None
    """
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


# ── Individual KPI functions ───────────────────────────────────────────────────


def gross_margin(revenue: Optional[float], cogs: Optional[float]) -> Optional[float]:
    """
    Gross Margin = (Revenue - COGS) / Revenue

    Measures the proportion of revenue retained after direct production costs.
    Higher is better. NVIDIA FY2020–2025 range: 56.9% – 75.0%.

    Args:
        revenue: Total net revenue (USD millions)
        cogs:    Cost of goods sold (USD millions)

    Returns:
        float in [0, 1] representing the gross margin ratio, or None
    """
    if revenue is None or cogs is None:
        return None
    gross_profit = revenue - cogs
    return safe_divide(gross_profit, revenue)


def ebitda_margin(ebitda: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """
    EBITDA Margin = EBITDA / Revenue

    Measures operational efficiency before the effects of capital structure,
    taxes, and non-cash charges. Used for cross-company comparability.
    NVIDIA FY2020–2025 range: 21.4% – 63.8%.

    Args:
        ebitda:  Earnings before interest, taxes, depreciation & amortisation
        revenue: Total net revenue (USD millions)

    Returns:
        float in [0, 1] representing the EBITDA margin ratio, or None
    """
    return safe_divide(ebitda, revenue)


def free_cash_flow(cfo: Optional[float], capex: Optional[float]) -> Optional[float]:
    """
    Free Cash Flow (FCF) = CFO + CapEx

    Measures actual cash generated after capital investment.
    CapEx is stored as a negative number (cash outflow convention), so
    addition produces the correct FCF figure.

    Formula note: FCF = CFO - |CapEx|  ≡  CFO + capex  (capex < 0)

    Args:
        cfo:   Net cash from operating activities (USD millions, positive)
        capex: Capital expenditures (USD millions, negative in source data)

    Returns:
        float in USD millions, or None if either input is missing
    """
    if cfo is None or capex is None:
        return None
    return cfo + capex  # capex is already negative


def fcf_margin(fcf_value: Optional[float], revenue: Optional[float]) -> Optional[float]:
    """
    FCF Margin = FCF / Revenue

    Measures the proportion of revenue that converts to free cash flow.
    A key indicator of capital efficiency. NVIDIA FY2022–2025 range: 14.1% – 46.6%.

    Args:
        fcf_value: Free cash flow in USD millions
        revenue:   Total net revenue (USD millions)

    Returns:
        float in [0, 1] representing FCF margin ratio, or None
    """
    return safe_divide(fcf_value, revenue)


def revenue_growth(
    rev_current: Optional[float], rev_prior: Optional[float]
) -> Optional[float]:
    """
    Revenue Growth = (Rev_t - Rev_t-1) / Rev_t-1

    Year-over-year revenue growth rate. Returns None for the base year
    (no prior period) or when either input is missing.

    Args:
        rev_current: Revenue in the current period (USD millions)
        rev_prior:   Revenue in the prior period (USD millions)

    Returns:
        float representing YoY growth rate (e.g. 1.142 = 114.2% growth), or None
    """
    if rev_current is None or rev_prior is None:
        return None
    return safe_divide(rev_current - rev_prior, rev_prior)


def ar_days(
    accounts_receivable: Optional[float], revenue: Optional[float]
) -> Optional[float]:
    """
    AR Days (DSO) = Accounts Receivable / (Revenue / 365)

    Days Sales Outstanding — measures how quickly the company collects
    cash after a sale. Lower is better (faster collection).
    NVIDIA FY2021–2025 range: 51.8 – 64.5 days.

    Args:
        accounts_receivable: Period-end AR balance (USD millions)
        revenue:             Annual revenue (USD millions)

    Returns:
        float in days, or None
    """
    if accounts_receivable is None or revenue is None:
        return None
    daily_revenue = safe_divide(revenue, 365)
    return safe_divide(accounts_receivable, daily_revenue)


def ap_days(
    accounts_payable: Optional[float], cogs: Optional[float]
) -> Optional[float]:
    """
    AP Days (DPO) = Accounts Payable / (COGS / 365)

    Days Payable Outstanding — measures how long the company takes to
    pay its suppliers. Higher is generally better (longer float),
    but must be balanced against supplier relationships.
    NVIDIA FY2021–2025 range: 37.5 – 70.6 days.

    Args:
        accounts_payable: Period-end AP balance (USD millions)
        cogs:             Cost of goods sold (USD millions)

    Returns:
        float in days, or None
    """
    if accounts_payable is None or cogs is None:
        return None
    daily_cogs = safe_divide(cogs, 365)
    return safe_divide(accounts_payable, daily_cogs)


def current_ratio(
    current_assets: Optional[float], current_liabilities: Optional[float]
) -> Optional[float]:
    """
    Current Ratio = Current Assets / Current Liabilities

    Measures short-term liquidity. A ratio > 1 means current assets
    exceed current liabilities. Semiconductor companies typically run 3–6×.
    NVIDIA FY2021–2025 range: 3.5× – 6.7×.

    Args:
        current_assets:      Total current assets (USD millions)
        current_liabilities: Total current liabilities (USD millions)

    Returns:
        float (ratio), or None
    """
    return safe_divide(current_assets, current_liabilities)


# ── Composite KPI calculator ───────────────────────────────────────────────────


def calculate_kpis(
    revenue: Optional[float] = None,
    cogs: Optional[float] = None,
    ebitda: Optional[float] = None,
    cfo: Optional[float] = None,
    capex: Optional[float] = None,
    accounts_receivable: Optional[float] = None,
    accounts_payable: Optional[float] = None,
    current_assets: Optional[float] = None,
    current_liabilities: Optional[float] = None,
    revenue_prior: Optional[float] = None,
) -> dict:
    """
    Compute all 8 KPIs from a single period's financial inputs.

    Design rules (Task 2):
      - Pure function — no side effects, no I/O, no global reads
      - Always returns a dict with all 8 keys present
      - Missing/invalid inputs yield None values — never NaN, never crash
      - No DataFrames anywhere in this function

    Args:
        revenue:             Total net revenue (USD millions)
        cogs:                Cost of goods sold (USD millions)
        ebitda:              EBITDA (USD millions)
        cfo:                 Net cash from operations (USD millions)
        capex:               Capital expenditures (USD millions, negative)
        accounts_receivable: Period-end AR balance (USD millions)
        accounts_payable:    Period-end AP balance (USD millions)
        current_assets:      Total current assets (USD millions)
        current_liabilities: Total current liabilities (USD millions)
        revenue_prior:       Prior period revenue for growth calc (USD millions)

    Returns:
        dict with keys:
            gross_margin      float | None  — ratio [0, 1]
            ebitda_margin     float | None  — ratio [0, 1]
            fcf               float | None  — USD millions
            fcf_margin        float | None  — ratio [0, 1]
            revenue_growth    float | None  — ratio (e.g. 1.14 = +114%)
            ar_days           float | None  — days
            ap_days           float | None  — days
            current_ratio     float | None  — ratio (e.g. 4.4)

    Example:
        >>> kpis = calculate_kpis(
        ...     revenue=130497, cogs=32639, ebitda=83317,
        ...     cfo=64089, capex=-3236,
        ...     accounts_receivable=23065, accounts_payable=6310,
        ...     current_assets=80126, current_liabilities=18047,
        ...     revenue_prior=60922,
        ... )
        >>> kpis['gross_margin']    # 0.7499
        >>> kpis['fcf']             # 60853.0
        >>> kpis['revenue_growth']  # 1.1420
    """
    fcf_val = free_cash_flow(cfo, capex)

    return {
        "gross_margin": gross_margin(revenue, cogs),
        "ebitda_margin": ebitda_margin(ebitda, revenue),
        "fcf": fcf_val,
        "fcf_margin": fcf_margin(fcf_val, revenue),
        "revenue_growth": revenue_growth(revenue, revenue_prior),
        "ar_days": ar_days(accounts_receivable, revenue),
        "ap_days": ap_days(accounts_payable, cogs),
        "current_ratio": current_ratio(current_assets, current_liabilities),
    }


def calculate_kpis_timeseries(periods: list[dict]) -> list[dict]:
    """
    Compute KPIs across a time-series of financial periods.

    Each element in `periods` must be a dict with the same keys accepted
    by calculate_kpis(). The first period returns None for revenue_growth
    (no prior year). Periods must be sorted chronologically (oldest first).

    Args:
        periods: List of period dicts, each containing financial inputs.
                 Required keys: revenue, cogs, ebitda, cfo, capex,
                                accounts_receivable, accounts_payable,
                                current_assets, current_liabilities
                 Optional metadata keys (passed through): year, ticker, etc.

    Returns:
        List of dicts — one per period — each containing all 8 KPIs
        plus any metadata keys present in the input dict.

    Example:
        >>> results = calculate_kpis_timeseries([
        ...     {"year": 2024, "revenue": 60922, "cogs": 16621, ...},
        ...     {"year": 2025, "revenue": 130497, "cogs": 32639, ...},
        ... ])
        >>> results[0]['revenue_growth']  # None (base year)
        >>> results[1]['revenue_growth']  # 1.1420
    """
    results = []
    prev_revenue = None

    for period in periods:
        kpis = calculate_kpis(
            revenue=period.get("revenue"),
            cogs=period.get("cogs"),
            ebitda=period.get("ebitda"),
            cfo=period.get("cfo"),
            capex=period.get("capex"),
            accounts_receivable=period.get("accounts_receivable"),
            accounts_payable=period.get("accounts_payable"),
            current_assets=period.get("current_assets"),
            current_liabilities=period.get("current_liabilities"),
            revenue_prior=prev_revenue,
        )

        # Carry forward any metadata keys from the input period
        metadata_keys = [
            k
            for k in period
            if k
            not in (
                "revenue",
                "cogs",
                "ebitda",
                "cfo",
                "capex",
                "accounts_receivable",
                "accounts_payable",
                "current_assets",
                "current_liabilities",
            )
        ]
        result = {k: period[k] for k in metadata_keys}
        result.update(kpis)
        results.append(result)

        prev_revenue = period.get("revenue")

    return results
