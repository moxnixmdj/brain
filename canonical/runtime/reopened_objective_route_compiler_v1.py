"""Reconcile reopened direct-objective gates against matched acceptance predicates.

This compiler identifies comparator-deletion candidates but never promotes prewave
bindings. A full-protocol candidate remains blocked until fresh admissible terminal
evidence is bound.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_REOPENED_OBJECTIVE_ROUTE_VERDICT_V1"

def evaluate(registry: Mapping[str,Any], spec: Mapping[str,Any], gate: Mapping[str,Any]) -> dict[str,Any]:
    errors:list[str]=[]
    rows=registry.get("predicates")
    routes=spec.get("routes")
    if not isinstance(rows,list): rows=[]; errors.append("PREDICATES_NOT_LIST")
    if not isinstance(routes,list): routes=[]; errors.append("ROUTES_NOT_LIST")
    kinds={r.get("id"):r.get("kind") for r in rows if isinstance(r,Mapping) and isinstance(r.get("id"),str)}
    expected=spec.get("required_gate_status")
    gate_pass=isinstance(expected,str) and gate.get("status")==expected
    if not gate_pass: errors.append("GATE_RECEIPT_STATUS_MISMATCH")

    result=[]
    candidate_targets=set()
    for route in routes:
        if not isinstance(route,Mapping) or not isinstance(route.get("id"),str):
            errors.append("MALFORMED_ROUTE"); continue
        rid=route["id"]
        scope=route.get("scope_relation")
        targets=route.get("target_predicates",[])
        if not isinstance(targets,list) or any(not isinstance(x,str) for x in targets):
            errors.append("INVALID_TARGETS:"+rid); targets=[]
        unknown=[x for x in targets if x not in kinds]
        errors.extend("UNKNOWN_TARGET:"+rid+":"+x for x in unknown)
        nonmatched=[x for x in targets if x in kinds and kinds[x] not in {"MATCHED_NONINFERIORITY","MATCHED_SCOPE_AUDIT"}]
        errors.extend("TARGET_NOT_MATCHED:"+rid+":"+x for x in nonmatched)
        valid=[x for x in targets if x in kinds and x not in nonmatched]
        if scope=="FULL_PROTOCOL_REPLACEMENT_CANDIDATE" and gate_pass and valid:
            state="TERMINAL_EVIDENCE_REQUIRED"
            candidate_targets.update(valid)
        elif scope in {"PARTIAL_ONLY","ROUTE_ENABLER_ONLY"}:
            state="NONCLOSING_ROUTE_ENABLEMENT"
        else:
            state="FAIL_CLOSED"
            if scope not in {"FULL_PROTOCOL_REPLACEMENT_CANDIDATE","PARTIAL_ONLY","ROUTE_ENABLER_ONLY"}:
                errors.append("INVALID_SCOPE_RELATION:"+rid)
        result.append({
            "id":rid,
            "behavior_id":route.get("behavior_id"),
            "scope_relation":scope,
            "target_predicates":valid,
            "state":state,
            "terminal_evidence_required":state=="TERMINAL_EVIDENCE_REQUIRED",
            "acceptance_credit_delta":0,
        })

    matched=sorted(pid for pid,k in kinds.items() if k in {"MATCHED_NONINFERIORITY","MATCHED_SCOPE_AUDIT"})
    residual=sorted(set(matched)-candidate_targets)
    return {
        "schema":SCHEMA,
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "gate_pass":gate_pass,
        "matched_predicate_count":len(matched),
        "full_protocol_replacement_candidate_count":len(candidate_targets),
        "candidate_predicates":sorted(candidate_targets),
        "residual_matched_predicates":residual,
        "routes":result,
        "rule":"PREWAVE_GATE_PASS_ONLY_REOPENS_PROOF_ROUTE__TERMINAL_EVIDENCE_REQUIRED_BEFORE_COMPARATOR_DEPENDENCY_CAN_BE_DELETED",
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
