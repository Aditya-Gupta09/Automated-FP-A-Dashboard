# src/utils/formatting.py
"""Formatting utilities for display."""

from typing import Optional


def format_currency(
    value: Optional[float], decimals: int = 0, currency: str = "$"
) -> str:
    """Format number as currency. $1234567.89 → $1,234,568 (decimals=0)."""
    if value is None:
        return "—"
    return f"{currency}{value:,.{decimals}f}".replace(f".{'0'*decimals}", "")


def format_percent(value: Optional[float], decimals: int = 1) -> str:
    """Format decimal as percentage. 0.757 → 75.7%."""
    if value is None:
        return "—"
    return f"{value*100:.{decimals}f}%"


def format_basis_points(value: Optional[float], decimals: int = 0) -> str:
    """Format percentage as basis points. 0.01 → 100 bps."""
    if value is None:
        return "—"
    return f"{value*10000:.{decimals}f} bps"


def format_number(value: Optional[float], decimals: int = 0) -> str:
    """Format with thousand separators. 1234567 → 1,234,567."""
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}".rstrip("0").rstrip(".")
