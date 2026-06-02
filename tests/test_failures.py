import sys

import pytest

sys.path.insert(0, "src")

from src.modeling.engine import run_pipeline


def test_invalid_scenario_raises():
    with pytest.raises(ValueError):
        run_pipeline("invalid")


def test_missing_keys_fail_cleanly(monkeypatch):
    from src.modeling import engine

    def broken_apply(*args, **kwargs):
        return {}

    monkeypatch.setattr(engine, "_apply_scenario", broken_apply)

    with pytest.raises(Exception):
        run_pipeline("base")
