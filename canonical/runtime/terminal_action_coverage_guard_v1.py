"""Fail-closed completeness guard for the live Opus55 acceptance action hypergraph.

This guard proves only that every currently unproved atomic acceptance predicate
has at least one explicit declared discharge action. It does not optimize the
action set and does not grant execution, promotion, capability, or family credit.
The existing terminal_proof_supercompiler remains authoritative for minimum-cut
optimization.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TERMINAL_ACTION_COVERAGE_GUARD_V1"

def evaluate(registry: Mapping[str,Any], evidence: Mapping[str,Any], hypergraph: Mapping[str,Any]) -> dict[str,Any]:
    errors:list[str]=[]
    rows=registry.get("predicates")
    claims=evidence.get("claims")
    actions=hypergraph.get("actions")
    if not isinstance(rows,list): rows=[]; errors.append("PREDICATES_NOT_LIST")
    if not isinstance(claims,list): claims=[]; errors.append("CLAIMS_NOT_LIST")
    if not isinstance(actions,list): actions=[]; errors.append("ACTIONS_NOT_LIST")

    ids=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping) or not isinstance(row.get("id"),str) or not row.get("id"):
            errors.append(f"PREDICATE_INVALID:{i}"); continue
        ids.append(row["id"])
    if len(ids)!=len(set(ids)): errors.append("DUPLICATE_PREDICATE_ID")
    known=set(ids)

    proved={c.get("predicate_id") for c in claims if isinstance(c,Mapping) and c.get("state")=="PROVED"}
    proved={x for x in proved if isinstance(x,str)}
    for x in sorted(proved-known): errors.append("UNKNOWN_PROVED:"+x)
    unresolved=sorted(known-proved)

    coverage:dict[str,list[str]]={pid:[] for pid in unresolved}
    for i,action in enumerate(actions):
        if not isinstance(action,Mapping) or not isinstance(action.get("id"),str) or not action.get("id"):
            errors.append(f"ACTION_INVALID:{i}"); continue
        aid=action["id"]
        targets=action.get("target_predicates")
        if not isinstance(targets,list) or any(not isinstance(x,str) or not x for x in targets):
            errors.append("TARGETS_INVALID:"+aid); continue
        for pid in targets:
            if pid not in known:
                errors.append("UNKNOWN_TARGET:"+aid+":"+pid)
            elif pid in coverage:
                coverage[pid].append(aid)

    uncovered=sorted(pid for pid,aids in coverage.items() if not aids)
    represented=sorted(pid for pid,aids in coverage.items() if aids)
    return {
        "schema":SCHEMA,
        "status":"PASS" if not errors and not uncovered else "FAIL_CLOSED",
        "pass":not errors and not uncovered,
        "errors":sorted(set(errors)),
        "predicate_count":len(known),
        "proved_predicate_count":len(proved & known),
        "unresolved_predicate_count":len(unresolved),
        "represented_unresolved_predicate_count":len(represented),
        "uncovered_unresolved_predicates":uncovered,
        "coverage":{pid:sorted(aids) for pid,aids in sorted(coverage.items())},
        "rule":"EVERY_UNPROVED_ATOMIC_ACCEPTANCE_PREDICATE_MUST_HAVE_AT_LEAST_ONE_EXPLICIT_DISCHARGE_ACTION__MINIMUM_CUT_OPTIMIZATION_REMAINS_THE_AUTHORITY_OF_TERMINAL_PROOF_SUPERCOMPILER",
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
