"""P3 real-context admission v8.

V8 preserves current V7 behavior only when no stronger explicit selection authority
is supplied. It adds one fail-closed authority ordering rule:

1. validate the declared P3 contract surface before every positive route;
2. explicit objective weights are binding when supplied;
3. an independently verified decision-dependency contract is binding when supplied;
4. if both are supplied, fail closed until a precedence/equivalence proof exists;
5. otherwise preserve V7/V6 behavior unchanged.

No source authorization, policy adequacy, DB admission, U-subtraction, or terminal
authority is minted.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p3_v3_contract_surface_guard_v1 import validate_v3_contract_surface
from canonical.runtime.p3_real_context_v3_admission_v7 import evaluate as evaluate_v7
from canonical.runtime.p3_explicit_weighted_salience_cell_v1 import evaluate as evaluate_weighted
from canonical.runtime.p3_exact_dependency_relevance_cell_v1 import evaluate as evaluate_dependency

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V8"
_ALLOWED_PAYLOAD_FIELDS={
    "context_id","v3_input","objective_weights","semantic_certificates",
    "decision_dependency_contract",
}

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "v3_admission_authorized":False,"p3_contract_cell_authorized":False,
      "top_law_eligible":False,"source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out

def _authority_zero(r:Mapping[str,Any])->bool:
    return (
      r.get("source_authorization_verified") is False
      and r.get("policy_adequacy_authority") is False
      and r.get("db_admission_authority") is False
      and r.get("u_subtraction_authority") is False
      and r.get("terminal_authority") is False
      and r.get("terminal_credit_delta")==0
    )

def _weighted_boundary_ok(r:Mapping[str,Any])->bool:
    return (
      r.get("pass") is True
      and r.get("v3_admission_authorized") is True
      and r.get("top_law_eligible") is True
      and r.get("policy_adequacy_authority") is False
      and r.get("db_admission_authority") is False
      and r.get("u_subtraction_authority") is False
      and r.get("terminal_authority") is False
      and r.get("terminal_credit_delta")==0
    )

def evaluate(payload:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    if set(payload)-_ALLOWED_PAYLOAD_FIELDS:
        return _fail("UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS")

    has_weights="objective_weights" in payload
    has_dependency="decision_dependency_contract" in payload

    context_id=payload.get("context_id")
    if context_id is not None and (not isinstance(context_id,str) or not context_id.strip()):
        return _fail("CONTEXT_ID_INVALID")
    if not has_dependency and context_id is None:
        return _fail("CONTEXT_ID_REQUIRED")

    public=payload.get("v3_input")
    if not isinstance(public,Mapping):
        return _fail("V3_INPUT_REQUIRED")
    contract_failure=validate_v3_contract_surface(public)
    if contract_failure is not None:
        return _fail(contract_failure)

    if has_weights and has_dependency:
        return _fail("MULTIPLE_EXPLICIT_SELECTION_AUTHORITIES_WITHOUT_PRECEDENCE_PROOF")

    if has_weights:
        weights=payload.get("objective_weights")
        if not isinstance(weights,Mapping):
            return _fail("OBJECTIVE_WEIGHTS_INVALID")
        weighted=evaluate_weighted({"v3_input":public,"objective_weights":weights})
        if weighted.get("pass") is not True:
            return _fail(
                "OBJECTIVE_WEIGHTS_UNSATISFIED",
                weighted_reason=weighted.get("reason") or weighted.get("status"),
            )
        if not _weighted_boundary_ok(weighted):
            return _fail("WEIGHTED_CELL_AUTHORITY_BOUNDARY_INVALID")
        return {
          "schema":SCHEMA,"pass":True,
          "status":"PASS__P3_REAL_CONTEXT_EXPLICIT_WEIGHT_FAST_PATH",
          "route":"EXPLICIT_WEIGHTED_SALIENCE_CELL_V1","context_id":context_id,
          "selected_claim_ids":list(weighted.get("selected_claim_ids") or []),
          "claim_order":list(weighted.get("claim_order") or []),
          "objective_value":weighted.get("objective_value"),
          "v3_admission_authorized":True,"p3_contract_cell_authorized":True,
          "top_law_eligible":True,"source_authorization_verified":False,
          "policy_adequacy_authority":False,"db_admission_authority":False,
          "u_subtraction_authority":False,"terminal_authority":False,
          "terminal_credit_delta":0,"route_receipt":weighted,
          "explicit_authority_consumed":"OBJECTIVE_WEIGHTS",
        }

    if has_dependency:
        contract=payload.get("decision_dependency_contract")
        if not isinstance(contract,Mapping):
            return _fail("DECISION_DEPENDENCY_CONTRACT_INVALID")
        root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
        dep=evaluate_dependency(payload,repo_root=root)
        if dep.get("pass") is not True:
            return _fail(
                "DECISION_DEPENDENCY_CONTRACT_UNSATISFIED",
                dependency_reason=dep.get("reason") or dep.get("status"),
            )
        if not _authority_zero(dep) or dep.get("p3_contract_cell_authorized") is not True:
            return _fail("DEPENDENCY_RELEVANCE_AUTHORITY_BOUNDARY_INVALID")
        out=dict(dep)
        out.update({
          "schema":SCHEMA,
          "status":"PASS__P3_REAL_CONTEXT_EXACT_DEPENDENCY_RELEVANCE_FAST_PATH",
          "route":"EXACT_COMPLETE_DECISION_DEPENDENCY_RELEVANCE_CELL_V1",
          "context_id":context_id,
          "explicit_authority_consumed":"DECISION_DEPENDENCY_CONTRACT",
        })
        return out

    prior=evaluate_v7(payload,repo_root=repo_root)
    if prior.get("pass") is True and not _authority_zero(prior):
        return _fail("V7_POSITIVE_ROUTE_AUTHORITY_BOUNDARY_INVALID")
    out=dict(prior)
    out["schema"]=SCHEMA
    out["v7_preserved_positive_route"]=prior.get("pass") is True
    out["explicit_authority_consumed"]=None
    return out

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {},repo_root=root)
