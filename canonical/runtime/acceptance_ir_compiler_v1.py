"""Canonical zero-credit acceptance IR compiler.

Compiles the frozen atomic predicate registry, content-addressed evidence bindings,
and the active action hypergraph into one deterministic scheduling IR.

This module does not infer semantic equivalence, create acceptance evidence,
authorize benchmark execution, or grant capability/family credit.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_IR_V1"
PROVED = "PROVED"
BLOCKED_STATES = {"EXTERNAL_BLOCKED", "BLOCKED", "DEPENDENCY_BLOCKED"}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "predicates": [],
        "families": [],
        "actions": [],
        "proved_predicate_count": 0,
        "unresolved_predicate_count": 0,
        "closed_residual_family_count": 0,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def compile_ir(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    hypergraph: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    rows = registry.get("predicates")
    claims = evidence.get("claims")
    actions = hypergraph.get("actions")
    if not isinstance(rows, list):
        return _fail("PREDICATES_NOT_LIST")
    if not isinstance(claims, list):
        return _fail("CLAIMS_NOT_LIST")
    if not isinstance(actions, list):
        return _fail("ACTIONS_NOT_LIST")

    predicate_by_id: dict[str, Mapping[str, Any]] = {}
    family_to_predicates: dict[str, list[str]] = defaultdict(list)
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"PREDICATE_{i}_INVALID")
            continue
        pid = row.get("id")
        family = row.get("family")
        kind = row.get("kind")
        if not isinstance(pid, str) or not pid:
            errors.append(f"PREDICATE_{i}_ID_INVALID")
            continue
        if pid in predicate_by_id:
            errors.append(f"DUPLICATE_PREDICATE:{pid}")
            continue
        if not isinstance(family, str) or not family:
            errors.append(f"PREDICATE_FAMILY_INVALID:{pid}")
            continue
        if not isinstance(kind, str) or not kind:
            errors.append(f"PREDICATE_KIND_INVALID:{pid}")
            continue
        predicate_by_id[pid] = row
        family_to_predicates[family].append(pid)

    claim_by_id: dict[str, Mapping[str, Any]] = {}
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_{i}_INVALID")
            continue
        pid = claim.get("predicate_id")
        if not isinstance(pid, str) or pid not in predicate_by_id:
            errors.append(f"CLAIM_UNKNOWN_PREDICATE:{pid}")
            continue
        if pid in claim_by_id:
            errors.append(f"DUPLICATE_CLAIM:{pid}")
            continue
        claim_by_id[pid] = claim

    if errors:
        return _fail(*errors)

    predicate_out = []
    proved: set[str] = set()
    blocked: set[str] = set()
    for pid in sorted(predicate_by_id):
        row = predicate_by_id[pid]
        claim = claim_by_id.get(pid)
        claim_state = claim.get("state") if isinstance(claim, Mapping) else None
        if claim_state == PROVED:
            state = PROVED
            proved.add(pid)
        elif claim_state in BLOCKED_STATES:
            state = "BLOCKED"
            blocked.add(pid)
        else:
            state = "OPEN"
        predicate_out.append({
            "id": pid,
            "family": row["family"],
            "kind": row["kind"],
            "state": state,
            "claim_state": claim_state,
            "claim_source_path": claim.get("source_path") if isinstance(claim, Mapping) else None,
            "claim_source_sha": claim.get("source_sha") if isinstance(claim, Mapping) else None,
        })

    family_out = []
    for family in sorted(family_to_predicates):
        required = sorted(family_to_predicates[family])
        p = sorted(set(required) & proved)
        b = sorted(set(required) & blocked)
        o = sorted(set(required) - proved)
        family_out.append({
            "family": family,
            "required_predicates": required,
            "proved_predicates": p,
            "blocked_predicates": b,
            "unresolved_predicates": o,
            "acceptance_closed_by_atomic_registry": len(o) == 0,
        })

    action_out = []
    target_coverage: dict[str, list[str]] = defaultdict(list)
    for i, action in enumerate(actions):
        if not isinstance(action, Mapping):
            return _fail(f"ACTION_{i}_INVALID")
        aid = action.get("id")
        targets = action.get("target_predicates", [])
        preconditions = action.get("preconditions", [])
        if not isinstance(aid, str) or not aid:
            return _fail(f"ACTION_{i}_ID_INVALID")
        if not isinstance(targets, list) or any(t not in predicate_by_id for t in targets):
            return _fail(f"ACTION_TARGET_INVALID:{aid}")
        if not isinstance(preconditions, list):
            return _fail(f"ACTION_PRECONDITIONS_INVALID:{aid}")
        unsatisfied = []
        for p in preconditions:
            if not isinstance(p, Mapping) or not isinstance(p.get("id"), str):
                return _fail(f"ACTION_PRECONDITION_INVALID:{aid}")
            if p.get("satisfied") is False:
                unsatisfied.append(p["id"])
        unresolved_targets = sorted(set(targets) - proved)
        for pid in unresolved_targets:
            target_coverage[pid].append(aid)
        action_out.append({
            "id": aid,
            "action_class": action.get("action_class"),
            "critical_path": action.get("critical_path") is True,
            "new_reality_units": action.get("new_reality_units", 0),
            "target_predicates": sorted(set(targets)),
            "unresolved_target_predicates": unresolved_targets,
            "available_now": len(unsatisfied) == 0,
            "unsatisfied_preconditions": sorted(unsatisfied),
        })

    uncovered = sorted(
        pid for pid in predicate_by_id
        if pid not in proved and not target_coverage.get(pid)
    )

    return {
        "schema": SCHEMA,
        "status": "PASS" if not uncovered else "PASS_WITH_UNCOVERED_ACTION_TARGETS",
        "errors": [],
        "predicate_count": len(predicate_by_id),
        "proved_predicate_count": len(proved),
        "unresolved_predicate_count": len(predicate_by_id) - len(proved),
        "blocked_predicate_count": len(blocked),
        "predicates": predicate_out,
        "families": family_out,
        "residual_family_count": len(family_out),
        "closed_residual_family_count": sum(
            x["acceptance_closed_by_atomic_registry"] for x in family_out
        ),
        "actions": sorted(action_out, key=lambda x: x["id"]),
        "uncovered_unresolved_predicates": uncovered,
        "rule": (
            "IR_IS_A_DETERMINISTIC_PROJECTION_ONLY__NO_SEMANTIC_EQUIVALENCE_"
            "NO_NEW_EVIDENCE_NO_ACCEPTANCE_PROMOTION"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
