"""
loader.py — ETL Entry Point
============================
Reads raw CSV files from data/raw/ and returns raw DataFrames.
Keeps I/O completely separate from transformation logic.

SahilBuran pattern applied: loader only reads and does minimal type coercion.
All cleaning/mapping happens downstream in validator → cleaner → transformer.

Architecture slot: [LOADER] → validator → cleaner → transformer → canonical
"""

import pandas as pd
import os
import logging
from src.utils.error_logger import log_error

logger = logging.getLogger(__name__)

RAW_DIR = "data/raw"


def _load_csv(filename: str, source_label: str) -> pd.DataFrame:
    """
    Load a CSV from data/raw/. Raises FileNotFoundError with clear message.
    Strips whitespace from column names on load.
    """
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[loader] Raw file not found: {path}. "
            f"Expected in {RAW_DIR}/. Run export step first."
        )
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    logger.info(
        "[loader] %s — loaded %d rows × %d cols from %s",
        source_label,
        len(df),
        len(df.columns),
        path,
    )
    return df


def load_historical_is() -> pd.DataFrame:
    """Load nvidia_historical_IS.csv — IS FY2020–2025."""
    return _load_csv("nvidia_historical_IS.csv", "IS")


def load_historical_bs() -> pd.DataFrame:
    """Load nvidia_historical_BS.csv — BS FY2021–2025."""
    return _load_csv("nvidia_historical_BS.csv", "BS")


def load_historical_cf() -> pd.DataFrame:
    """Load nvidia_historical_CF.csv — CF FY2022–2025 (FY2020-21 absent by design)."""
    return _load_csv("nvidia_historical_CF.csv", "CF")


def load_cleaned_financials() -> pd.DataFrame:
    """Load cleaned_financials.csv — merged IS+BS+CF with derived ratios."""
    return _load_csv("cleaned_financials.csv", "cleaned_financials")


def load_comps_data() -> pd.DataFrame:
    """Load comps_data.csv — peer comps table."""
    return _load_csv("comps_data.csv", "comps")
