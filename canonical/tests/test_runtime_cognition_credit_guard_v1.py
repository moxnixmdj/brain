from copy import deepcopy
from pathlib import Path
import json

from canonical.runtime.runtime_cognition_credit_guard_v1 import (
    evaluate_materials,
    evaluate_repository,
)

ROOT = Path(__file__).resolve().parents[2]


def _materials():
    pointer = json.loads((ROOT / "canonical/CANONICAL_POINTER.json").read_text(encoding="utf-8"))
    startup = (ROOT / "sitecustomize.py").read_text(encoding="utf-8")
    runtime = (ROOT / "canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")
    return pointer, startup, runtime


def test_current_repository_passes():
    out = evaluate_repository(ROOT)
    assert out["pass"] is True, out


def test_weakened_runtime_cognition_law_fails_closed():
    pointer, startup, runtime = _materials()
    mutated = deepcopy(pointer)
    mutated["boot_requirements"]["runtime_cognition_provider_forbidden_regardless_of_label_hosting_or_cost"] = False
    out = evaluate_materials(mutated, startup, runtime)
    assert out["pass"] is False
    assert any("runtime_cognition_provider_forbidden" in e for e in out["errors"])


def test_removed_startup_kill_switch_fails_closed():
    pointer, _startup, runtime = _materials()
    out = evaluate_materials(pointer, "import os\n", runtime)
    assert out["pass"] is False
    assert "STARTUP_MODEL_PLANNER_KILL_SWITCH_MISSING" in out["errors"]


def test_removed_runtime_kill_switch_check_fails_closed():
    pointer, startup, runtime = _materials()
    stripped = runtime.replace("ASTRA_DISABLE_MODEL_PLANNER", "ASTRA_DISABLED_FLAG_REMOVED")
    out = evaluate_materials(pointer, startup, stripped)
    assert out["pass"] is False
    assert "ASTRA_RUNTIME_KILL_SWITCH_CHECK_MISSING" in out["errors"]
