"""Deterministic terminal next-action compiler v1.

This is a zero-credit scheduler over the canonical acceptance IR. It never
infers semantic equivalence, creates evidence, authorizes benchmark execution,
or promotes capability ownership.

Purpose: prevent stale prose pointers from naming blocked actions as runnable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVIDENCE = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
HYPERGRAPH = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json"

SCHEMA = "PROJECT_BRAIN_TERMINAL_NEXT_ACTION_COMPILED_V1"


def _rank_key(action: Mapping[str, Any]) -> tuple[int, int, int, str]:
    # Critical path first, then maximum unresolved predicate coverage,
    # then minimum reality cost, then deterministic lexical tie-break.
    return (
        0 if action.get("critical_path") is True else 1,
        -len(action.get("unresolved_target_predicates", [])),
        int(action.get("new_reality_units", 0) or 0),
        str(action.get("id", "")),
    )


def compile_next_frontier(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    hypergraph: Mapping[str, Any],
) -> dict[str, Any]:
    ir = compile_ir(registry, evidence, hypergraph)
    if ir.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ir.get("errors", []),
            "execution_authority": False,
            "promotion_authority": False,
            "new_reality_units_consumed": 0,
        }

    live = [a for a in ir["actions"] if a["unresolved_target_predicates"]]
    ranked = sorted(live, key=_rank_key)

    critical_blocked = [
        a for a in ranked
        if a["critical_path"] and not a["available_now"]
    ]
    critical_available_zero_reality = [
        a for a in ranked
        if a["critical_path"] and a["available_now"] and int(a.get("new_reality_units", 0) or 0) == 0
    ]
    available_zero_reality = [
        a for a in ranked
        if a["available_now"] and int(a.get("new_reality_units", 0) or 0) == 0
    ]

    if critical_blocked:
        primary = critical_blocked[0]
        primary_state = "BLOCKED_PRECONDITIONS"
    elif critical_available_zero_reality:
        primary = critical_available_zero_reality[0]
        primary_state = "AVAILABLE_ZERO_REALITY"
    elif ranked:
        primary = ranked[0]
        primary_state = "AVAILABLE" if primary["available_now"] else "BLOCKED_PRECONDITIONS"
    else:
        primary = None
        primary_state = "NO_RESIDUAL_ACTION"

    return {
        "schema": SCHEMA,
        "status": "PASS__DETERMINISTIC_FRONTIER__ZERO_CREDIT",
        "proved_predicate_count": ir["proved_predicate_count"],
        "unresolved_predicate_count": ir["unresolved_predicate_count"],
        "primary_action_id": primary["id"] if primary else None,
        "primary_action_state": primary_state,
        "primary_unresolved_target_count": len(primary["unresolved_target_predicates"]) if primary else 0,
        "primary_unresolved_targets": primary["unresolved_target_predicates"] if primary else [],
        "primary_unsatisfied_preconditions": primary["unsatisfied_preconditions"] if primary else [],
        "available_zero_reality_critical_actions": [a["id"] for a in critical_available_zero_reality],
        "available_zero_reality_actions": [a["id"] for a in available_zero_reality],
        "blocked_critical_actions": [
            {
                "id": a["id"],
                "unresolved_target_count": len(a["unresolved_target_predicates"]),
                "unsatisfied_preconditions": a["unsatisfied_preconditions"],
            }
            for a in critical_blocked
        ],
        "rule": (
            "PRIMARY_IS_HIGHEST_COVERAGE_CRITICAL_PATH_FRONTIER__"
            "BLOCKED_PRIMARY_MEANS_DISCHARGE_LISTED_PRECONDITIONS_NOT_RUN_ACTION__"
            "NO_SEMANTIC_INFERENCE_NO_NEW_EVIDENCE_NO_PROMOTION"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    hypergraph = json.loads(HYPERGRAPH.read_text(encoding="utf-8"))
    out = compile_next_frontier(registry, evidence, hypergraph)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
