from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PROTOCOLS = ROOT / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
FRONTIER = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
HYPERGRAPH = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"
TOOLATHLON = ROOT / "canonical/governance/TOOLATHLON_VERIFIED_TOOL_DISCOVERY_ROUTE_FREEZE_V1.json"
CORRECTION = ROOT / "canonical/governance/TOOL_DISCOVERY_MATCHED_ROUTE_PROOF_GRAPH_CORRECTION_V1.json"

TARGET_FAMILY = "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
TARGET_PREDICATE = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
CERT_ID = "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"
ACTION_ID = "BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_by_key_value(obj: Any, key: str, value: str) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        if obj.get(key) == value:
            return obj
        for child in obj.values():
            found = _find_by_key_value(child, key, value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for child in obj:
            found = _find_by_key_value(child, key, value)
            if found is not None:
                return found
    return None


def evaluate(
    protocols: Any | None = None,
    frontier: Any | None = None,
    hypergraph: Any | None = None,
    toolathlon: Any | None = None,
    correction: Any | None = None,
) -> dict[str, Any]:
    protocols = _load(PROTOCOLS) if protocols is None else protocols
    frontier = _load(FRONTIER) if frontier is None else frontier
    hypergraph = _load(HYPERGRAPH) if hypergraph is None else hypergraph
    toolathlon = _load(TOOLATHLON) if toolathlon is None else toolathlon
    correction = _load(CORRECTION) if correction is None else correction

    protocol = _find_by_key_value(protocols, "family", TARGET_FAMILY)
    certificate = _find_by_key_value(frontier, "id", CERT_ID)
    action = _find_by_key_value(hypergraph, "id", ACTION_ID)

    errors: list[str] = []
    if protocol is None:
        errors.append("FROZEN_TOOL_DISCOVERY_PROTOCOL_NOT_FOUND")
    if certificate is None:
        errors.append("ACTIVE_TOOL_DISCOVERY_CERTIFICATE_NOT_FOUND")
    if action is None:
        errors.append("ACTIVE_TOOL_DISCOVERY_ACTION_NOT_FOUND")

    acceptance = str((protocol or {}).get("acceptance") or "")
    matched_semantics = (
        "Opus matched bounds" in acceptance
        and "Brain conservative terminal-success/valid-route bounds" in acceptance
    )
    if not matched_semantics:
        errors.append("MATCHED_NONINFERIORITY_SEMANTICS_NOT_PROVED_FROM_FROZEN_PROTOCOL")

    certificate_is_absolute_only = (
        (certificate or {}).get("certificate_class") == "ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS"
        and TARGET_PREDICATE in list((certificate or {}).get("target_predicates") or [])
        and len(list((certificate or {}).get("requires") or [])) == 1
        and "UNIVERSAL_FORMAL_SCOPE_PROOF" in str(list((certificate or {}).get("requires") or [None])[0])
    )
    if not certificate_is_absolute_only:
        errors.append("ACTIVE_CERTIFICATE_IS_NOT_THE_EXPECTED_ABSOLUTE_ONLY_ROUTE")

    note = str((action or {}).get("notes") or "")
    scheduler_preserves_later_target = "later valid frozen target instantiation" in note
    if not scheduler_preserves_later_target:
        errors.append("SCHEDULER_DOES_NOT_PRESERVE_LATER_FROZEN_TARGET_ROUTE")

    correction_routes = {
        row.get("route_id"): row
        for row in list((correction or {}).get("proof_routes") or [])
        if isinstance(row, dict)
    }
    route_preserved = "ABSOLUTE_DOMINANCE_SCOPE_ROUTE" in correction_routes
    route_restored = "MATCHED_FROZEN_TARGET_ROUTE" in correction_routes
    if not route_preserved:
        errors.append("CORRECTION_DROPS_EXISTING_ABSOLUTE_ROUTE")
    if not route_restored:
        errors.append("CORRECTION_DOES_NOT_ADD_MATCHED_ROUTE")

    candidate_freeze_bound = (
        (toolathlon or {}).get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
        and (toolathlon or {}).get("status", "").startswith("PRE_TASK_CONTENT_FREEZE")
        and int(((toolathlon or {}).get("benchmark_identity") or {}).get("task_count", 0)) > 0
    )
    unresolved = list((toolathlon or {}).get("unresolved_before_public_fixed_bar_admission") or [])

    graph_correction_proved = not errors
    matched_route_satisfied = False

    return {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_MATCHED_ROUTE_GRAPH_VERDICT_V1",
        "target_family": TARGET_FAMILY,
        "target_predicate": TARGET_PREDICATE,
        "matched_noninferiority_semantics_proved": matched_semantics,
        "active_graph_absolute_route_only": certificate_is_absolute_only,
        "scheduler_note_preserves_later_frozen_target_instantiation": scheduler_preserves_later_target,
        "graph_correction_proved": graph_correction_proved,
        "matched_route_logically_available": graph_correction_proved,
        "matched_route_satisfied": matched_route_satisfied,
        "existing_candidate_frozen_target": {
            "path": str(TOOLATHLON.relative_to(ROOT)),
            "pre_task_freeze_bound": candidate_freeze_bound,
            "open_preconditions": unresolved,
            "open_precondition_count": len(unresolved),
        },
        "hard_nonclaims": [
            "NO_TOOL_DISCOVERY_ACCEPTANCE_CREDIT",
            "NO_CLAIM_THAT_TOOLATHLON_SCOPE_RELATION_IS_ALREADY_VALID",
            "NO_CLAIM_THAT_MATCHED_OPUS_BAR_IS_ALREADY_DURABLY_ADMISSIBLE",
            "NO_CLAIM_THAT_BRAIN_HAS_ALREADY_EXECUTED_THE_MATCHED_TARGET",
            "NO_FRESH_TERMINAL_REALITY",
        ],
        "errors": errors,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["graph_correction_proved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
