from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "canonical/runtime/universal_verified_adaptive_solver_v12.py":
        "e85b4127a7cf53124114db89c651a22cdc51ee53",
    "canonical/runtime/universal_verified_adaptive_solver_v4.py":
        "759c068ca122daf94cbc8a0ad2e8e08c3a4c6ea7",
    "canonical/runtime/capability_planner.py":
        "629766f8a1194fd298e0809b64a5e9c5a39fa3ea",
    "canonical/tests/test_universal_verified_adaptive_solver_v4.py":
        "a188853115cc1e2f46d889f59886b09775725f17",
}

def _blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def prove_route(
    *,
    initial_facts: Sequence[str],
    target_effects: Sequence[str],
    route: Sequence[Mapping[str, Any]],
    cycle_budget: int,
    target_effects_task_correctness_complete: bool,
    preterminal_information_admissible: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(route, Sequence) or isinstance(route, (str, bytes)) or not route:
        errors.append("ROUTE_INVALID_OR_EMPTY")
        route = []
    if not isinstance(cycle_budget, int) or isinstance(cycle_budget, bool) or cycle_budget < len(route) + 1:
        errors.append("CYCLE_BUDGET_INSUFFICIENT")
    if target_effects_task_correctness_complete is not True:
        errors.append("TARGET_EFFECTS_TASK_CORRECTNESS_NOT_COMPLETE")
    if preterminal_information_admissible is not True:
        errors.append("PRETERMINAL_INFORMATION_NOT_ADMISSIBLE")

    facts = set(initial_facts)
    for i, row in enumerate(route):
        if not isinstance(row, Mapping):
            errors.append(f"STEP_NOT_OBJECT:{i}")
            continue
        required = set(row.get("requires") or [])
        provides = set(row.get("provides") or [])
        if not required.issubset(facts):
            errors.append(f"STEP_REQUIREMENTS_UNSATISFIED:{i}")
        for key in (
            "planner_selected_plan_bound",
            "effect_semantics_authenticated",
            "verifier_total_sound_complete",
            "execution_total_success",
            "no_unresolved_irreversible_effect",
        ):
            if row.get(key) is not True:
                errors.append(f"STEP_PREMISE_UNPROVED:{i}:{key}")
        if not errors or not any(e.startswith(f"STEP_") and f":{i}" in e for e in errors):
            facts.update(provides)

    targets = set(target_effects)
    if not targets.issubset(facts):
        errors.append("TARGET_EFFECTS_NOT_REACHED")

    passed = not errors
    return {
        "schema": "PROJECT_BRAIN_STATIC_VERIFIED_CAPABILITY_ROUTE_THEOREM_REDUCTION_V1",
        "pass": passed,
        "errors": errors,
        "route_length": len(route),
        "verified_final_facts": sorted(facts),
        "targets_reached": targets.issubset(facts),
        "constructive_liveness_proved_for_bound_cell": passed,
        "task_correctness_entails_from_targets": passed,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

def verify_sources() -> dict[str, Any]:
    errors = []
    for rel, expected in EXPECTED.items():
        full = ROOT / rel
        if not full.is_file():
            errors.append("SOURCE_MISSING:" + rel)
        elif _blob(full) != expected:
            errors.append("SOURCE_DRIFT:" + rel)
    return {
        "pass": not errors,
        "errors": errors,
    }

if __name__ == "__main__":
    print(json.dumps(verify_sources(), indent=2, sort_keys=True))
