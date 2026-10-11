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
    bindings = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "canonical/runtime/live_integrated_brain_v1.py",
            "canonical/runtime/autonomous_verified_self_improvement_v1.py",
            "canonical/runtime/terminal_closure_reducer.py",
            "canonical/runtime/ownership_promotion_compiler_v1.py",
            "canonical/runtime/final_terminal_cleanroom_gate_v1.py",
            "canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py",
            "canonical/runtime/terminal_kstar_promotion_bridge_v1.py",
        )
    }
    return pointer, startup, runtime, bindings


def test_current_repository_passes():
    out = evaluate_repository(ROOT)
    assert out["pass"] is True, out


def test_weakened_runtime_cognition_law_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    mutated = deepcopy(pointer)
    mutated["boot_requirements"]["runtime_cognition_provider_forbidden_regardless_of_label_hosting_or_cost"] = False
    out = evaluate_materials(mutated, startup, runtime, bindings)
    assert out["pass"] is False
    assert any("runtime_cognition_provider_forbidden" in e for e in out["errors"])


def test_removed_startup_kill_switch_fails_closed():
    pointer, _startup, runtime, bindings = _materials()
    out = evaluate_materials(pointer, "import os\n", runtime, bindings)
    assert out["pass"] is False
    assert "STARTUP_MODEL_PLANNER_KILL_SWITCH_MISSING" in out["errors"]


def test_removed_runtime_kill_switch_check_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    stripped = runtime.replace("ASTRA_DISABLE_MODEL_PLANNER", "ASTRA_DISABLED_FLAG_REMOVED")
    out = evaluate_materials(pointer, startup, stripped, bindings)
    assert out["pass"] is False
    assert "ASTRA_RUNTIME_KILL_SWITCH_CHECK_MISSING" in out["errors"]


def test_removed_live_guard_binding_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    mutated = dict(bindings)
    live = mutated["canonical/runtime/live_integrated_brain_v1.py"]
    mutated["canonical/runtime/live_integrated_brain_v1.py"] = live.replace(
        "assert_credit_path_cognition_governance(ROOT)",
        "pass  # removed cognition guard",
        1,
    )
    out = evaluate_materials(pointer, startup, runtime, mutated)
    assert out["pass"] is False
    assert any(
        e.startswith("COGNITION_GUARD_CALL_COUNT_WEAKENED:")
        for e in out["errors"]
    )


def test_removed_ownership_promotion_guard_binding_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    mutated = dict(bindings)
    path = "canonical/runtime/ownership_promotion_compiler_v1.py"
    mutated[path] = mutated[path].replace(
        "assert_credit_path_cognition_governance(root)",
        "pass  # removed cognition guard",
        1,
    )
    out = evaluate_materials(pointer, startup, runtime, mutated)
    assert out["pass"] is False
    assert any(path in e for e in out["errors"])


def test_removed_final_cleanroom_guard_binding_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    mutated = dict(bindings)
    path = "canonical/runtime/final_terminal_cleanroom_gate_v1.py"
    mutated[path] = mutated[path].replace(
        "assert_credit_path_cognition_governance(root)",
        "pass  # removed cognition guard",
        1,
    )
    out = evaluate_materials(pointer, startup, runtime, mutated)
    assert out["pass"] is False
    assert any(path in e for e in out["errors"])


def test_removed_kstar_guard_binding_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    mutated = dict(bindings)
    path = "canonical/runtime/terminal_kstar_promotion_bridge_v1.py"
    source = mutated[path]
    mutated[path] = source.replace(
        "assert_credit_path_cognition_governance(root)",
        "pass  # removed cognition guard",
        1,
    )
    out = evaluate_materials(pointer, startup, runtime, mutated)
    assert out["pass"] is False
    assert any(
        e == "COGNITION_GUARD_CALL_COUNT_WEAKENED:" + path
        for e in out["errors"]
    )


def test_removed_global_ownership_guard_binding_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    mutated = dict(bindings)
    path = "canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py"
    source = mutated[path]
    mutated[path] = source.replace(
        "assert_credit_path_cognition_governance(ROOT)",
        "pass  # removed cognition guard",
        1,
    )
    out = evaluate_materials(pointer, startup, runtime, mutated)
    assert out["pass"] is False
    assert any(
        e == "COGNITION_GUARD_CALL_COUNT_WEAKENED:" + path
        for e in out["errors"]
    )


def test_stale_model_permissive_pointer_authority_fails_closed():
    pointer, startup, runtime, bindings = _materials()
    mutated = deepcopy(pointer)
    mutated["mission_lock"]["authority_path"] = "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V9.md"
    mutated["mission_lock"]["model_substrate_law"] = "canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V3.md"
    mutated["execution_governance"]["frontier_comparison_rule"] = "THE_WINNING_ROUTE_MAY_BE_MODEL_BASED"
    out = evaluate_materials(mutated, startup, runtime, bindings)
    assert out["pass"] is False
    assert any(
        e.startswith("STALE_OR_CONTRADICTORY_POINTER_AUTHORITY:")
        or e == "STALE_MODEL_BASED_FRONTIER_COMPARISON_RULE"
        for e in out["errors"]
    )
