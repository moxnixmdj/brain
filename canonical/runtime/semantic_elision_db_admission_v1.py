"""Unified fail-closed D_B admission over three semantic-elision routes.

A context may be admitted to D_B when exactly one of these routes reports success:
A) complete-objective global optimum;
B) robust common policy across every still-possible completion;
C) exact-candidate direct end-to-end raw-task acceptance.

Route C relies on the raw acceptance gate, which checks receipt consistency
but cannot authenticate caller-supplied verifier claims. It therefore remains
unresolved until an authenticated verification boundary is implemented. This
module grants cell-level D_B admission only; it never grants U-empty or
terminal credit. Routes A and B have separate trust assumptions.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.complete_objective_db_admission_bridge_v1 import evaluate as eval_objective
from canonical.runtime.robust_common_policy_db_admission_v1 import evaluate as eval_robust
from canonical.runtime.lossless_raw_task_acceptance_gate_v1 import evaluate as eval_raw

SCHEMA="PROJECT_BRAIN_SEMANTIC_ELISION_DB_ADMISSION_V1"

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "db_admission_authorized":False,"u_empty_authorized":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail:
        out["detail"]=detail
    return out

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    route=payload.get("route")
    body=payload.get("payload")
    if route not in {"A_COMPLETE_OBJECTIVE","B_ROBUST_COMMON_POLICY","C_DIRECT_END_TO_END_ACCEPTANCE"}:
        return _fail("ROUTE_INVALID")
    if not isinstance(body,Mapping):
        return _fail("ROUTE_PAYLOAD_MAPPING_REQUIRED")

    if route=="A_COMPLETE_OBJECTIVE":
        result=eval_objective(body)
    elif route=="B_ROBUST_COMMON_POLICY":
        result=eval_robust(body)
    else:
        required={"task_contract","candidate_sha256","obligation_receipts","repo_root"}
        if set(body)!=required:
            return _fail("DIRECT_ACCEPTANCE_PAYLOAD_FIELDS_INVALID",missing=sorted(required-set(body)),extra=sorted(set(body)-required))
        result=eval_raw(
            body["task_contract"],
            candidate_sha256=body["candidate_sha256"],
            obligation_receipts=body["obligation_receipts"],
            repo_root=body["repo_root"],
        )

    if result.get("pass") is not True:
        return {
            "schema":SCHEMA,
            "pass":False,
            "status":"UNRESOLVED__SELECTED_ADMISSION_ROUTE_NOT_PROVED",
            "route":route,
            "route_result":result,
            "db_admission_authorized":False,
            "u_empty_authorized":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
        }

    if route=="C_DIRECT_END_TO_END_ACCEPTANCE":
        cell_id=payload.get("cell_id")
        policy_id=payload.get("policy_id")
        if not all(isinstance(x,str) and x.strip() for x in (cell_id,policy_id)):
            return _fail("DIRECT_ACCEPTANCE_IDENTITY_BINDING_INVALID")
        if payload.get("brain_owned_candidate_proved") is not True:
            return _fail("DIRECT_ACCEPTANCE_BRAIN_OWNERSHIP_UNPROVED")
        if payload.get("deployed_route_exactly_realizes_candidate") is not True:
            return _fail("DIRECT_ACCEPTANCE_DEPLOYED_REALIZATION_UNPROVED")
        if payload.get("authorized_resource_bound_proved") is not True:
            return _fail("DIRECT_ACCEPTANCE_RESOURCE_BOUND_UNPROVED")
    else:
        cell_id=result.get("cell_id")
        policy_id=result.get("policy_id")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__CELL_ADMISSIBLE_TO_D_B_VIA_"+route,
        "route":route,
        "cell_id":cell_id,
        "policy_id":policy_id,
        "route_result":result,
        "db_admission_authorized":True,
        "semantic_world_reconstruction_required":False,
        "target_identity_required":False,
        "u_empty_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"CELL_ONLY__GLOBAL_U_CLOSURE_REQUIRES_SCOPE_COMPLETE_UNION_OF_SOUND_D_B_ADMISSIONS",
    }
