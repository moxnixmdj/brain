from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


FORBIDDEN_ACTION_IDS = {
    "RERUN_POST_DELEGATION_V4_FULL_CORPUS_SCAN",
    "EXECUTE_CURRENT_TB4_SCORE_ROUTE",
    "EXECUTE_AUTOMATIONBENCH_PUBLIC_600_FOR_PRIVATE_BAR",
    "EXECUTE_TOOLATHLON_PUBLIC_SERVICE_AGAINST_INTERNAL_OPUS55_BAR",
    "RERUN_P1_ONE_USE_TERMINAL_ACTIVATION",
}


def _load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _proved_predicate_ids(predicate_bindings: Optional[Dict[str, Any]]) -> Set[str]:
    if not predicate_bindings:
        return set()
    return {
        str(c.get("predicate_id"))
        for c in (predicate_bindings.get("claims", []) or [])
        if c.get("state") == "PROVED" and c.get("predicate_id")
    }


def _available_zero_reality_actions(
    actions: Iterable[Dict[str, Any]],
    proved_predicates: Set[str],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for action in actions:
        if action.get("id") in FORBIDDEN_ACTION_IDS:
            continue
        if int(action.get("new_reality_units", 0) or 0) != 0:
            continue
        targets = {str(x) for x in (action.get("target_predicates", []) or [])}
        if targets and targets.issubset(proved_predicates):
            continue
        pre = action.get("preconditions", []) or []
        if any(p.get("satisfied") is False for p in pre):
            continue
        out.append(action)
    return sorted(out, key=lambda x: str(x.get("id", "")))


def compile_causal_depth_plan(
    authority: Dict[str, Any],
    action_hypergraph: Dict[str, Any],
    predicate_bindings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    atomic = authority.get("atomic_acceptance_frontier", {})
    proved = int(atomic.get("proved", 0))
    unresolved = int(atomic.get("unresolved", 0))
    total = int(atomic.get("total", proved + unresolved))
    proved_ids = _proved_predicate_ids(predicate_bindings)

    actions = action_hypergraph.get("actions", []) or []
    barrier1 = _available_zero_reality_actions(actions, proved_ids)

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CAUSAL_DEPTH_PLAN_V1",
        "truth_snapshot": {
            "proved_atomic_predicates": proved,
            "unresolved_atomic_predicates": unresolved,
            "total_atomic_predicates": total,
            "terminal_goal_achieved": bool(authority.get("truth", {}).get("achieved", False)),
        },
        "proved_predicate_ids_used_for_stale_action_subtraction": sorted(proved_ids),
        "objective_order": [
            "MINIMIZE_CAUSAL_BARRIER_DEPTH",
            "MINIMIZE_NEW_REALITY_UNITS",
            "MINIMIZE_WALL_CLOCK",
            "MINIMIZE_COMPUTE",
        ],
        "barriers": [
            {
                "id": "BARRIER_1_ZERO_REALITY_MEGABATCH",
                "parallel_actions": [a.get("id") for a in barrier1],
                "action_count": len(barrier1),
                "fresh_reality_authorized": False,
                "after_each_verified_fact": [
                    "RUN_SCOPE_SAFE_IMPLICATION",
                    "RUN_ACCEPTANCE_FIXED_POINT",
                    "DELETE_NEWLY_PROVED_OR_DOMINATED_ACTIONS",
                ],
            },
            {
                "id": "BARRIER_2_MINIMUM_REALITY_TRANSACTION",
                "enabled_only_if": "BARRIER_1_SATURATED_AND_UNRESOLVED_REMAIN",
                "solver": "EXACT_MINIMUM_SET_COVER_OVER_IRREDUCIBLE_INFORMATION_REQUIREMENTS",
                "fresh_reality_authority": "SEPARATE_EXISTING_MINIMUM_REALITY_GATE_REQUIRED",
                "concurrency": "RUN_CAUSALLY_INDEPENDENT_AUTHORIZED_OBSERVATIONS_CONCURRENTLY",
            },
            {
                "id": "BARRIER_3_ATOMIC_FINALITY",
                "enabled_only_if": "ALL_REQUIRED_ATOMIC_ACCEPTANCE_INPUTS_RESOLVED",
                "steps": [
                    "ACCEPTANCE_FIXED_POINT",
                    "FAMILY_REDUCTION",
                    "FINAL_PROOF_BUNDLE",
                    "GLOBAL_OWNERSHIP_POSTCONDITIONS",
                    "DONOR_DELETION_CLEANROOM",
                    "TERMINAL_CLOSURE_REDUCER",
                ],
                "manual_promotion": False,
            },
        ],
        "forbidden_action_ids": sorted(FORBIDDEN_ACTION_IDS),
        "credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    authority = _load(root / "governance" / "CURRENT_TERMINAL_AUTHORITY_V1.json")
    hypergraph = _load(root / "governance" / "OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
    bindings = _load(root / "governance" / "OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
    print(json.dumps(compile_causal_depth_plan(authority, hypergraph, bindings), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
