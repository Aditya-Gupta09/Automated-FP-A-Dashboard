"""
error_logger.py — Task 5: error_report.csv Schema + Logger
============================================================
This module is the single place ALL ETL errors are recorded.

Design rules:
  - log_error() is called from validator.py, cleaner.py, loader.py
  - The error list accumulates in memory during the ETL run
  - save_error_report() writes data/processed/error_report.csv ALWAYS —
    even if the list is empty — to prove validation ran
  - Printing to stdout instead of storing is explicitly prohibited

Schema (per task specification):
  row_number   | column_name | error_type | raw_value | action_taken

Architecture slot: error_logger is imported by all ETL modules — it is
                   NOT in the pipeline chain, it is a cross-cutting concern.
"""

import logging
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# ── In-memory error accumulator ───────────────────────────────────────────────
# Module-level list — persists for the lifetime of the ETL run.
# Reset by calling reset_errors() at the start of each pipeline run.
_errors: list[dict] = []

# ── Error report output path (can be overridden by loader.py) ────────────────
ERROR_REPORT_PATH = "data/processed/error_report.csv"


def log_error(row, col: str, err: str, val: str, action: str) -> None:
    """
    Record one ETL issue into the in-memory error list.

    Args:
        row:    Row number or fiscal_year identifier. None if not row-specific.
        col:    Canonical column name where the issue occurred.
        err:    Error type string (e.g. "MISSING_CRITICAL_FIELD", "BS_BALANCE_FAIL").
        val:    The raw/actual value that triggered the issue.
        action: What the ETL did in response (e.g. "filled_with_0", "raised_ValueError").
    """
    _errors.append(
        {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "row_number": str(row) if row is not None else "",
            "column_name": col,
            "error_type": err,
            "raw_value": str(val),
            "action_taken": action,
        }
    )


def get_errors() -> list[dict]:
    """Return a copy of the current error list (read-only)."""
    return list(_errors)


def reset_errors() -> None:
    """Clear the error list. Call at the start of each pipeline run."""
    global _errors
    _errors = []
    logger.debug("[error_logger] Error list reset")


def save_error_report(output_path: str = None) -> str:
    """
    Write error_report.csv to disk.

    ALWAYS writes the file — even if _errors is empty.
    An empty file with only headers proves that validation ran and found nothing.

    Args:
        output_path: Override the default ERROR_REPORT_PATH.

    Returns:
        Absolute path to the written file.
    """
    path = output_path or ERROR_REPORT_PATH

    # Ensure output directory exists
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    columns = [
        "timestamp",
        "row_number",
        "column_name",
        "error_type",
        "raw_value",
        "action_taken",
    ]

    if _errors:
        df = pd.DataFrame(_errors, columns=columns)
    else:
        # Empty report — headers only — proves validation ran
        df = pd.DataFrame(columns=columns)

    df.to_csv(path, index=False)

    if _errors:
        logger.info(
            "[error_logger] error_report.csv written: %d issue(s) logged → %s",
            len(_errors),
            path,
        )
    else:
        logger.info(
            "[error_logger] error_report.csv written: 0 issues (clean run) → %s", path
        )

    return os.path.abspath(path)


def error_summary() -> dict:
    """
    Return a summary dict of error counts by error_type.
    Useful for pipeline_summary.json.
    """
    if not _errors:
        return {"total": 0, "by_type": {}}

    df = pd.DataFrame(_errors)
    by_type = df["error_type"].value_counts().to_dict()
    return {
        "total": len(_errors),
        "by_type": by_type,
        "has_critical": any(
            e["error_type"]
            in (
                "MISSING_CRITICAL_FIELD",
                "BS_BALANCE_FAIL",
                "CF_RECONCILIATION_FAIL",
                "CONFLICTING_DUPLICATE_ROWS",
            )
            for e in _errors
        ),
    }
