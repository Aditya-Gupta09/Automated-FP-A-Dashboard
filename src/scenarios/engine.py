"""
src/scenario_engine.py
───────────────────────
Merges base assumptions with scenario overrides.

CONTRACT (matches scenarios.json + assumptions.json):
  • Base assumptions are NEVER mutated.
  • Scenarios only carry delta keys (per scenarios.json _metadata.principle).
  • deep_merge handles nested dicts (revenue_growth, margin_and_cost, etc.)
  • Returns a plain dict — the model reads from this.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from src.etl.data_contracts import deep_merge

_CONFIG = Path(__file__).parent.parent.parent / "config"
_VALID_SCENARIOS = ("base", "upside", "downside")

ScenarioName = Literal["base", "upside", "downside"]


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _validate_scenario(scenario: str) -> str:
    if scenario not in _VALID_SCENARIOS:
        raise ValueError(
            f"Invalid scenario: {scenario}. Allowed: base, upside, downside"
        )
    return scenario


def _required(mapping: dict, *keys: str):
    current = mapping
    path = []
    for key in keys:
        path.append(key)
        if not isinstance(current, dict) or key not in current:
            joined = ".".join(path)
            raise KeyError(f"Missing scenario summary key: {joined}")
        current = current[key]
    return current


def get_assumptions(scenario: ScenarioName = "base") -> dict:
    """
    Returns final merged assumptions for the given scenario.
    Base config is loaded fresh each call — never mutated.
    """
    scenario = _validate_scenario(scenario)
    base = _load_json(_CONFIG / "assumptions.json")
    scenarios = _load_json(_CONFIG / "scenarios.json")

    # Strip metadata keys from base
    base_clean = {k: v for k, v in base.items() if not k.startswith("_")}

    if scenario == "base":
        return base_clean

    overrides = {k: v for k, v in scenarios[scenario].items() if not k.startswith("_")}

    return deep_merge(base_clean, overrides)


def get_scenario_summary() -> dict:
    """
    Returns a lightweight summary of key override differences per scenario,
    used by the UI to display the scenario badge.
    """
    base = _load_json(_CONFIG / "assumptions.json")
    scenarios = _load_json(_CONFIG / "scenarios.json")
    return {
        "base": {
            "description": "Central planning assumption — no overrides",
            "wacc": _required(base, "wacc", "wacc"),
            "terminal_growth_rate": _required(base, "dcf", "terminal_growth_rate"),
            "revenue_growth": {},
        },
        "upside": {
            "description": "AI acceleration, margin expansion, tighter WC",
            "wacc": _required(scenarios, "upside", "wacc", "wacc"),
            "terminal_growth_rate": _required(
                scenarios, "upside", "dcf", "terminal_growth_rate"
            ),
            "revenue_growth": _required(scenarios, "upside", "revenue_growth"),
        },
        "downside": {
            "description": "AI slowdown, margin compression, higher rates",
            "wacc": _required(scenarios, "downside", "wacc", "wacc"),
            "terminal_growth_rate": _required(
                scenarios, "downside", "dcf", "terminal_growth_rate"
            ),
            "revenue_growth": _required(scenarios, "downside", "revenue_growth"),
        },
    }
