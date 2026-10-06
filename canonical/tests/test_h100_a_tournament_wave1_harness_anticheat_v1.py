import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HARNESS=ROOT/"canonical/runtime/h100_a_tournament_wave1_g0_harness_v1.py"
TASKS=ROOT/"canonical/governance/H100_A_TOURNAMENT_WAVE1_PUBLIC_TASKS_V1.json"

def test_harness_has_no_task_specific_literals():
    source=HARNESS.read_text(encoding="utf-8")
    doc=json.loads(TASKS.read_text(encoding="utf-8"))
    assert "W1_" not in source
    assert doc["derivation_seed_sha256"] not in source
    for task in doc["tasks"]:
        assert task["id"] not in source

def test_harness_imports_only_frozen_g0_runtime_components():
    source=HARNESS.read_text(encoding="utf-8")
    allowed={
        "h100_verified_capability_registry_v8",
        "h100_expression_tree_symbolic_regression_v1",
        "h100_typed_capability_planner_v1",
        "h100_verified_effect_tool_registry_v1",
        "h100_zero_learned_event_memory_v1",
        "h100_jit_lexical_role_v1",
        "h100_zero_learned_compositional_language_v1",
        "h100_zero_learned_tool_trace_normalizer_v1",
    }
    imports=set()
    for line in source.splitlines():
        line=line.strip()
        if line.startswith("from canonical.runtime import "):
            imports.add(line.split(" import ",1)[1].split(" as ",1)[0].strip())
    assert imports==allowed
