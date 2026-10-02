"""Fail closed when an action frontier targets already-terminal acceptance predicates.

This guard is scheduling-only. It never grants execution, family, capability, or
promotion credit. An action may target OPEN or EXTERNAL_BLOCKED predicates, but
must not keep PROVED or REFUTED predicates on the live work frontier.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_ACTION_HYPERGRAPH_OPEN_PREDICATE_GUARD_V1"
TERMINAL_STATES={"PROVED","REFUTED"}

def evaluate(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    actions_doc: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    rows=registry.get("predicates")
    claims=evidence.get("claims")
    actions=actions_doc.get("actions")
    if not isinstance(rows,list):
        errors.append("PREDICATE_REGISTRY_NOT_LIST")
        rows=[]
    if not isinstance(claims,list):
        errors.append("EVIDENCE_CLAIMS_NOT_LIST")
        claims=[]
    if not isinstance(actions,list):
        errors.append("ACTIONS_NOT_LIST")
        actions=[]

    predicate_ids:set[str]=set()
    for row in rows:
        if not isinstance(row,Mapping) or not isinstance(row.get("id"),str) or not row.get("id"):
            errors.append("INVALID_PREDICATE_ROW")
            continue
        pid=row["id"]
        if pid in predicate_ids:
            errors.append(f"DUPLICATE_PREDICATE:{pid}")
        predicate_ids.add(pid)

    states:dict[str,str]={}
    for claim in claims:
        if not isinstance(claim,Mapping):
            errors.append("INVALID_EVIDENCE_CLAIM")
            continue
        pid=claim.get("predicate_id")
        state=claim.get("state")
        if not isinstance(pid,str) or pid not in predicate_ids:
            errors.append(f"EVIDENCE_UNKNOWN_PREDICATE:{pid}")
            continue
        if pid in states:
            errors.append(f"DUPLICATE_EVIDENCE_CLAIM:{pid}")
            continue
        if state not in {"OPEN","PROVED","REFUTED","EXTERNAL_BLOCKED"}:
            errors.append(f"INVALID_EVIDENCE_STATE:{pid}")
            continue
        states[pid]=state

    checked=0
    terminal_targets:list[dict[str,str]]=[]
    for action in actions:
        if not isinstance(action,Mapping):
            errors.append("INVALID_ACTION_ROW")
            continue
        aid=str(action.get("id") or "UNKNOWN")
        targets=action.get("target_predicates",[])
        if not isinstance(targets,list):
            errors.append(f"TARGETS_NOT_LIST:{aid}")
            continue
        seen:set[str]=set()
        for pid in targets:
            checked+=1
            if not isinstance(pid,str) or pid not in predicate_ids:
                errors.append(f"UNKNOWN_TARGET_PREDICATE:{aid}:{pid}")
                continue
            if pid in seen:
                errors.append(f"DUPLICATE_TARGET_PREDICATE:{aid}:{pid}")
                continue
            seen.add(pid)
            state=states.get(pid,"OPEN")
            if state in TERMINAL_STATES:
                errors.append(f"STALE_TERMINAL_TARGET:{aid}:{pid}:{state}")
                terminal_targets.append({"action_id":aid,"predicate_id":pid,"state":state})

    errors=sorted(set(errors))
    return {
        "schema":SCHEMA,
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "checked_target_count":checked,
        "terminal_targets":terminal_targets,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "rule":"LIVE_ACTION_FRONTIER_MUST_NOT_TARGET_PROVED_OR_REFUTED_ACCEPTANCE_PREDICATES",
    }
