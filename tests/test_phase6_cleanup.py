from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase6_cleanup_gate():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

    # 1) Ensure runtime dirs can be created
    from src.etl.pipeline import _ensure_dirs

    _ensure_dirs()
    assert (ROOT / "outputs").is_dir(), "outputs/ was not created"
    assert (ROOT / "logs").is_dir(), "logs/ was not created"

    # 2) Run the validation script as the user will
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_scenarios.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert proc.returncode == 0, proc.stderr
    out = proc.stdout

    # 3) Core sanity checks
    assert "Base Price:" in out
    assert "Scenario Ordering: PASS" in out
    assert "Sensitivity Check: PASS" in out

    # 4) Cleanup regression check: no comps warning should appear
    assert "[engine] Comps skipped:" not in out
