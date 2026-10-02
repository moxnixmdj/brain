"""Compile unresolved Opus55 predicates to a complete minimum declared action basis.

Scheduling/accounting only. Coverage does not imply executability, acceptance, or
capability ownership. The compiler fails closed on unknown targets or uncovered
unproved predicates.
"""
from __future__ import annotations
from itertools import combinations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TERMINAL_ACTION_BASIS_VERDICT_V1"

def _list(x: Any) -> list:
    return x if isinstance(x,list) else []

def evaluate(registry: Mapping[str,Any], evidence: Mapping[str,Any], hypergraph: Mapping[str,Any]) -> dict[str,Any]:
    errors:list[str]=[]
    rows=registry.get("predicates")
    actions=hypergraph.get("actions")
    claims=evidence.get("claims")
    if not isinstance(rows,list): errors.append("PREDICATES_NOT_LIST"); rows=[]
    if not isinstance(actions,list): errors.append("ACTIONS_NOT_LIST"); actions=[]
    if not isinstance(claims,list): errors.append("CLAIMS_NOT_LIST"); claims=[]

    ids=[]
    for row in rows:
        if not isinstance(row,Mapping) or not isinstance(row.get("id"),str):
            errors.append("MALFORMED_PREDICATE"); continue
        ids.append(row["id"])
    if len(ids)!=len(set(ids)): errors.append("DUPLICATE_PREDICATE_ID")
    known=set(ids)

    proved={c.get("predicate_id") for c in claims if isinstance(c,Mapping) and c.get("state")=="PROVED"}
    proved={x for x in proved if isinstance(x,str)}
    unknown_proved=sorted(proved-known)
    if unknown_proved: errors.extend("UNKNOWN_PROVED:"+x for x in unknown_proved)
    unresolved=sorted(known-proved)

    normalized=[]
    target_union=set()
    for action in actions:
        if not isinstance(action,Mapping) or not isinstance(action.get("id"),str):
            errors.append("MALFORMED_ACTION"); continue
        aid=action["id"]
        raw=action.get("target_predicates")
        if not isinstance(raw,list) or any(not isinstance(x,str) for x in raw):
            errors.append("INVALID_TARGETS:"+aid); continue
        targets=set(raw)
        for x in sorted(targets-known): errors.append("UNKNOWN_TARGET:"+aid+":"+x)
        targets &= known
        target_union |= targets
        normalized.append((aid,targets))
    unresolved_set=set(unresolved)
    covered=sorted(unresolved_set & target_union)
    uncovered=sorted(unresolved_set-target_union)

    minimum_basis=[]
    if not uncovered and normalized:
        indices=range(len(normalized))
        for size in range(1,len(normalized)+1):
            found=None
            for combo in combinations(indices,size):
                union=set()
                for i in combo: union |= normalized[i][1]
                if unresolved_set <= union:
                    found=[normalized[i][0] for i in combo]; break
            if found is not None:
                minimum_basis=sorted(found); break

    status="PASS" if not errors and not uncovered else "FAIL_CLOSED"
    return {
        "schema":SCHEMA,
        "status":status,
        "errors":sorted(set(errors)),
        "predicate_count":len(known),
        "proved_predicate_count":len(proved & known),
        "unresolved_predicate_count":len(unresolved),
        "represented_unresolved_predicate_count":len(covered),
        "uncovered_unresolved_predicates":uncovered,
        "declared_action_count":len(normalized),
        "minimum_declared_action_basis":minimum_basis,
        "minimum_declared_action_basis_size":len(minimum_basis),
        "coverage_complete":not uncovered,
        "rule":"EVERY_UNPROVED_PREDICATE_MUST_HAVE_A_DECLARED_DISCHARGE_ACTION__MINIMUM_BASIS_IS_STRUCTURAL_COVER_ONLY__PRECONDITIONS_AND_REALITY_GATES_STILL_APPLY",
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
