"""Fail-closed bridge from complete-objective proof to D_B admission.

The bridge grants *cell-level* D_B admission only when:
1. a scope-equivalence gate proves the candidate cell is non-weaker and information-safe;
2. the objective is independently bound as complete for all load-bearing dimensions;
3. an actual Brain-owned procedure is independently proved globally optimal on the
   complete admissible action/output space within its resource bound; and
4. the deployed route is content-bound to that procedure.

It never grants U-empty or terminal credit.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.scope_equivalent_proof_gate_v2 import evaluate as scope_gate

SCHEMA="PROJECT_BRAIN_COMPLETE_OBJECTIVE_DB_ADMISSION_BRIDGE_V1"


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "db_admission_authorized":False,"u_empty_authorized":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    scope=payload.get("scope_equivalence")
    if not isinstance(scope,Mapping):
        return _fail("SCOPE_EQUIVALENCE_REQUIRED")
    scope_result=scope_gate(scope)
    if scope_result.get("admissible") is not True:
        return _fail("SCOPE_EQUIVALENCE_NOT_PROVED", scope_result=scope_result)

    required_true=(
        "objective_complete_independently_verified",
        "admissible_space_complete_independently_verified",
        "global_optimality_independently_verified",
        "authorized_resource_bound_proved",
        "brain_owned_procedure_proved",
        "deployed_route_exactly_realizes_procedure",
    )
    missing=[k for k in required_true if payload.get(k) is not True]
    if missing:
        return _fail("COMPARATOR_ERASURE_PREMISE_MISSING", missing=missing)

    cell_id=payload.get("cell_id")
    policy_id=payload.get("policy_id")
    objective_id=payload.get("objective_id")
    if not all(isinstance(x,str) and x.strip() for x in (cell_id,policy_id,objective_id)):
        return _fail("IDENTITY_BINDING_INVALID")

    bindings=payload.get("content_bindings")
    if not isinstance(bindings,Mapping) or not bindings:
        return _fail("CONTENT_BINDINGS_REQUIRED")
    for key,value in bindings.items():
        if not isinstance(key,str) or not key or not isinstance(value,str) or not value:
            return _fail("CONTENT_BINDING_INVALID")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__COMPLETE_OBJECTIVE_CELL_ADMISSIBLE_TO_D_B",
        "cell_id":cell_id,
        "policy_id":policy_id,
        "objective_id":objective_id,
        "scope_equivalence":scope_result,
        "db_admission_authorized":True,
        "comparator_required":False,
        "target_identity_required":False,
        "target_score_required":False,
        "u_empty_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"CELL_ONLY__GLOBAL_U_CLOSURE_REQUIRES_SCOPE_COMPLETE_COVER_OR_TARGET_NONOCCUPANCY_OF_ALL_REMAINING_ESCAPE",
    }
