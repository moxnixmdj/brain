from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

REQUIRED_TOP_LEVEL = {
    "COMPLETE_SELECTED_CONTEXT_ABC",
    "D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY",
}

DEFAULT_RESEARCH_ROOT = "U_NOT_PROVED_EMPTY"
POST_U_TRANSITION = "POST_U_SELECTED_COVER_PROMOTION_OR_ABC_RECOMPUTE_PENDING"
POST_ABC_FINALIZATION = "POST_ABC_FINALIZATION_PENDING"


def evaluate(pointer: dict) -> dict:
    live = pointer.get("live_truth", {})
    declared = set(live.get("independent_top_level_terminal_predicates", []))

    hard_failures = []
    if declared != REQUIRED_TOP_LEVEL:
        hard_failures.append("TOP_LEVEL_PREDICATE_SET_DRIFT")
    if live.get("fixed_authorized_target_trace_scope_closed") is not True:
        hard_failures.append("TARGET_TRACE_SCOPE_OPEN")
    if live.get("router_mechanical_core_implemented") is not True:
        hard_failures.append("ROUTER_CORE_NOT_IMPLEMENTED")
    if live.get("router_deployed_runtime_binding_closed") is not True:
        hard_failures.append("ROUTER_DEPLOYED_RUNTIME_BINDING_OPEN")

    u_closed = live.get("current_U_empty_proved") is True
    selected_cover_closed = live.get("router_registry_real_selected_cover_complete") is True
    abc_closed = live.get("complete_selected_context_ABC_closed") is True
    d_closed = live.get("D_finality_closed") is True
    declared_terminal = live.get("terminal") is True

    live_research_blockers = []
    derived_pending = []
    finalization_pending = []

    if not u_closed:
        live_research_blockers.append(
            live.get("current_terminal_root_predicate") or DEFAULT_RESEARCH_ROOT
        )
        if not selected_cover_closed:
            derived_pending.append("REAL_SELECTED_COVER_INCOMPLETE_DERIVED_FROM_OPEN_U")
        if not abc_closed:
            derived_pending.append("COMPLETE_SELECTED_CONTEXT_ABC_OPEN_DERIVED_FROM_OPEN_U")
        if not d_closed:
            finalization_pending.append("D_FINALITY_DEFERRED_UNTIL_ABC")
        phase = "RESEARCH_ROOT"
    elif not (selected_cover_closed and abc_closed):
        derived_pending.append(POST_U_TRANSITION)
        if not d_closed:
            finalization_pending.append("D_FINALITY_DEFERRED_UNTIL_ABC")
        phase = "POST_U_DERIVED_TRANSITION"
    elif not d_closed:
        finalization_pending.append(POST_ABC_FINALIZATION)
        phase = "POST_ABC_FINALIZATION"
    else:
        phase = "TERMINAL"

    predicates_satisfied = (
        not hard_failures
        and u_closed
        and selected_cover_closed
        and abc_closed
        and d_closed
    )
    terminal_real = predicates_satisfied

    declaration_warnings = []
    if declared_terminal and not predicates_satisfied:
        hard_failures.append("DECLARED_TERMINAL_INCONSISTENT_WITH_REQUIRED_PREDICATES")
        terminal_real = False
    elif predicates_satisfied and not declared_terminal:
        declaration_warnings.append(
            "DECLARED_TERMINAL_FALSE_BUT_DERIVED_TERMINAL_TRUE__METADATA_OUT_OF_SYNC"
        )

    # Only load-bearing work belongs in blockers. Derived state and the post-ABC
    # finalization tail are reported separately so one open root cannot multiply
    # into several fake parallel research programs.
    blockers = list(hard_failures)
    if live_research_blockers:
        blockers.extend(live_research_blockers)
    elif phase == "POST_U_DERIVED_TRANSITION":
        blockers.append(POST_U_TRANSITION)
    elif phase == "POST_ABC_FINALIZATION":
        blockers.append(POST_ABC_FINALIZATION)

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_REALITY_GATE_V2",
        "terminal_real": terminal_real,
        "declared_terminal": declared_terminal,
        "phase": phase,
        "blockers": blockers,
        "live_research_blockers": live_research_blockers,
        "derived_pending": derived_pending,
        "finalization_pending": finalization_pending,
        "declaration_warnings": declaration_warnings,
        "top_level_predicates": sorted(REQUIRED_TOP_LEVEL),
        "known_sound_D_B_certificate_record_count": live.get(
            "known_sound_D_B_certificate_record_count"
        ),
        "abc_normal_form": live.get("complete_selected_context_ABC_normal_form"),
        "anti_bureaucracy": {
            "u_open_implies_router_and_abc_are_not_independent_research_blockers": True,
            "d_finality_is_post_abc_not_parallel_research": True,
            "manual_terminal_declaration_is_not_an_extra_terminal_predicate": True,
        },
    }


def main() -> int:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    out = evaluate(pointer)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["terminal_real"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
