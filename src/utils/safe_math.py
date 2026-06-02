# src/utils/safe_math.py
"""Safe math operations for financial models."""



def safe_divide(
    numerator: float | None,
    denominator: float | None,
    default: float | None = None,
) -> float | None:
    """
    Safe division that never raises ZeroDivisionError or returns NaN.

    Returns:
        - float: result if both numerator and denominator are non-None and denominator != 0
        - None: if either input is None or denominator == 0
        - default: if provided and the condition above isn't met
    """
    if numerator is None or denominator is None:
        return default
    if denominator == 0:
        return default
    return numerator / denominator


def safe_percent(
    numerator: float | None, denominator: float | None
) -> float | None:
    """Safe division for percentages (returns 0–1 scale, not 0–100)."""
    result = safe_divide(numerator, denominator, default=None)
    return result if result is None else min(1.0, max(0.0, result))


def clip_to_bounds(
    value: float | None, min_val: float = 0.0, max_val: float = 1.0
) -> float | None:
    """Clip value to [min_val, max_val] range. Returns None if input is None."""
    if value is None:
        return None
    return max(min_val, min(max_val, value))
