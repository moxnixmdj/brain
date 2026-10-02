"""Reconcile reopened direct-objective gates against unresolved matched acceptance predicates.

This compiler identifies comparator-deletion candidates but never promotes prewave
bindings. It consumes the current atomic evidence ledger so already-proved matched
predicates are removed from the action frontier rather than scheduled again.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_REOPENED_OBJECTIVE_ROUTE_VERDICT_V1"
MATCHED_KINDS={"MATCHED_NONINFERIORITY","MATCHED_SCOPE_AUDIT"}

def evaluate(
    registry: Mapping[str,Any],
    spec: Mapping[str,Any],
    gate: Mapping[str,Any],
    evidence: Mapping[str,Any],
) -> dict[str,Any]:
    errors:list[str]=[]
    rows=registry.get("predicates")
    routes=spec.get("routes")
    claims=evidence.get("claims")
    if not isinstance(rows,list): rows=[]; errors.append("PREDICATES_NOT_LIST")
    if not isinstance(routes,list): routes=[]; errors.append("ROUTES_NOT_LIST")
    if not isinstance(claims,list): claims=[]; errors.append("CLAIMS_NOT_LIST")

    kinds={r.get("id"):r.get("kind") for r in rows if isinstance(r,Mapping) and isinstance(r.get("id"),str)}
    proved={
        c.get("predicate_id")
        for c in claims
        if isinstance(c,Mapping) and c.get("state")=="PROVED" and isinstance(c.get("predicate_id"),str)
    }
    expected=spec.get("required_gate_status")
    gate_pass=isinstance(expected,str) and gate.get("status")==expected
    if not gate_pass: errors.append("GATE_RECEIPT_STATUS_MISMATCH")

    result=[]
    candidate_targets=set()
    already_proved_targets=set()
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
        nonmatched=[x for x in targets if x in kinds and kinds[x] not in MATCHED_KINDS]
        errors.extend("TARGET_NOT_MATCHED:"+rid+":"+x for x in nonmatched)
        valid=[x for x in targets if x in kinds and x not in nonmatched]
        proved_valid=sorted(x for x in valid if x in proved)
        unresolved_valid=sorted(x for x in valid if x not in proved)

        if scope=="FULL_PROTOCOL_REPLACEMENT_CANDIDATE":
            already_proved_targets.update(proved_valid)
            if unresolved_valid and gate_pass:
                state="TERMINAL_EVIDENCE_REQUIRED"
                candidate_targets.update(unresolved_valid)
            elif unresolved_valid:
                state="FAIL_CLOSED"
            elif valid and proved_valid:
                state="ALREADY_PROVED_NO_ACTION"
            else:
                state="FAIL_CLOSED"
        elif scope in {"PARTIAL_ONLY","ROUTE_ENABLER_ONLY"}:
            state="NONCLOSING_ROUTE_ENABLEMENT"
        else:
            state="FAIL_CLOSED"
            errors.append("INVALID_SCOPE_RELATION:"+rid)

        result.append({
            "id":rid,
            "behavior_id":route.get("behavior_id"),
            "scope_relation":scope,
            "target_predicates":valid,
            "proved_target_predicates":proved_valid,
            "unresolved_target_predicates":unresolved_valid,
            "state":state,
            "terminal_evidence_required":state=="TERMINAL_EVIDENCE_REQUIRED",
            "acceptance_credit_delta":0,
        })

    matched=set(pid for pid,k in kinds.items() if k in MATCHED_KINDS)
    proved_matched=matched & proved
    unresolved_matched=matched-proved_matched
    residual=sorted(unresolved_matched-candidate_targets)

    return {
        "schema":SCHEMA,
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "gate_pass":gate_pass,
        "matched_predicate_count":len(matched),
        "proved_matched_predicate_count":len(proved_matched),
        "unresolved_matched_predicate_count":len(unresolved_matched),
        "full_protocol_replacement_candidate_count":len(candidate_targets),
        "candidate_predicates":sorted(candidate_targets),
        "already_proved_matched_predicates":sorted(proved_matched),
        "reopened_route_targets_already_proved":sorted(already_proved_targets),
        "residual_matched_predicates":residual,
        "routes":result,
        "rule":"ALREADY_PROVED_TARGETS_ARE_DELETED_FROM_ACTION_FRONTIER__PREWAVE_GATE_PASS_ONLY_REOPENS_UNRESOLVED_PROOF_ROUTES__TERMINAL_EVIDENCE_REQUIRED_BEFORE_A_REMAINING_COMPARATOR_DEPENDENCY_CAN_BE_DELETED",
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
