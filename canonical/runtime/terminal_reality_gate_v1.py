from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

REQUIRED_TOP_LEVEL = {
    "COMPLETE_SELECTED_CONTEXT_ABC",
    "D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY",
}

def evaluate(pointer: dict) -> dict:
    live = pointer.get("live_truth", {})
    declared = set(live.get("independent_top_level_terminal_predicates", []))
    blockers = []

    if declared != REQUIRED_TOP_LEVEL:
        blockers.append("TOP_LEVEL_PREDICATE_SET_DRIFT")
    if live.get("fixed_authorized_target_trace_scope_closed") is not True:
        blockers.append("TARGET_TRACE_SCOPE_OPEN")
    if live.get("router_mechanical_core_implemented") is not True:
        blockers.append("ROUTER_CORE_NOT_IMPLEMENTED")
    if live.get("router_deployed_runtime_binding_closed") is not True:
        blockers.append("ROUTER_DEPLOYED_RUNTIME_BINDING_OPEN")
    if live.get("current_U_empty_proved") is not True:
        blockers.append("U_NOT_PROVED_EMPTY")
    if live.get("router_registry_real_selected_cover_complete") is not True:
        blockers.append("ROUTER_REGISTRY_SELECTED_COVER_INCOMPLETE")
    if live.get("complete_selected_context_ABC_closed") is not True:
        blockers.append("COMPLETE_SELECTED_CONTEXT_ABC_OPEN")
    if live.get("D_finality_closed") is not True:
        blockers.append("D_FINALITY_OPEN")

    derived_terminal = not blockers
    declared_terminal = live.get("terminal") is True

    if declared_terminal != derived_terminal:
        blockers.append("DECLARED_TERMINAL_INCONSISTENT_WITH_REQUIRED_PREDICATES")
        derived_terminal = False

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_REALITY_GATE_V1",
        "terminal_real": derived_terminal,
        "declared_terminal": declared_terminal,
        "blockers": blockers,
        "top_level_predicates": sorted(REQUIRED_TOP_LEVEL),
        "known_sound_D_B_certificate_record_count": live.get(
            "known_sound_D_B_certificate_record_count"
        ),
        "abc_normal_form": live.get("complete_selected_context_ABC_normal_form"),
    }

def main() -> int:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    out = evaluate(pointer)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["terminal_real"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
