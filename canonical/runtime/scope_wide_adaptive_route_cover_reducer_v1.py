"""Scope-wide adaptive-route cover reducer v1.

This reducer encodes a proof algebra step only:

  independently verified concrete-scope adaptive policy totality
  + independently verified exact Brain-owned deployed implementation of that tree
  + universal TRUE admission predicate within the exact bound scope
  => candidate route adequacy on every scope context
  => candidate residual S_TRACE AND NOT TRUE is unsatisfiable.

It deliberately does NOT mint independent verification, selected-cover completion,
U-empty, ABC closure, acceptance, ownership finality, or terminal authority.
Those require the existing independent complement gate path.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SCOPE_WIDE_ADAPTIVE_ROUTE_COVER_REDUCER_V1"


def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _sha(x:Any)->str:
    return "sha256:"+sha256(_canon(x).encode("utf-8")).hexdigest()


def _hex40(x:Any)->bool:
    return isinstance(x,str) and len(x)==40 and all(c in "0123456789abcdef" for c in x)


def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "candidate_admission_implies_route_adequacy":False,
      "candidate_residual_complement_unsat":False,
      "independent_verified":False,
      "selected_cover_complete_authorized":False,
      "u_empty_authorized":False,
      "abc_closed_authorized":False,
      "terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def _receipt(value:Any,required:Mapping[str,Any])->tuple[bool,str|None]:
    if not isinstance(value,Mapping):
        return False,"RECEIPT_REQUIRED"
    for key,expected in {
      "independent_verified":True,
      "exact_byte_bound":True,
      "conclusion":"success",
      **dict(required),
    }.items():
        if value.get(key)!=expected:
            return False,"RECEIPT_BINDING_MISMATCH:"+key
    return True,None


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    scope_id=payload.get("scope_id")
    route_id=payload.get("route_id")
    cell_id=payload.get("cell_id")
    predicate_id=payload.get("admission_predicate_id")
    for label,value in (
      ("SCOPE_ID",scope_id),("ROUTE_ID",route_id),("CELL_ID",cell_id),
      ("ADMISSION_PREDICATE_ID",predicate_id),
    ):
        if not isinstance(value,str) or not value:
            return _fail(label+"_REQUIRED")

    predicate=payload.get("admission_predicate")
    if predicate!={"op":"TRUE"}:
        return _fail("UNIVERSAL_TRUE_ADMISSION_PREDICATE_REQUIRED")
    predicate_sha=_sha(predicate)

    lift=payload.get("concrete_lift_result")
    if not isinstance(lift,Mapping):
        return _fail("CONCRETE_LIFT_RESULT_REQUIRED")
    if (
      lift.get("pass") is not True
      or lift.get("concrete_scope_adaptive_policy_totality_proved") is not True
      or lift.get("scope_id")!=scope_id
      or lift.get("terminal_authority") is not False
      or lift.get("terminal_credit_delta")!=0
    ):
        return _fail("CONCRETE_LIFT_RESULT_NOT_POSITIVE_ZERO_AUTHORITY")
    lift_sha=_sha(lift)
    tree_sha=lift.get("decision_tree_sha256")
    if not isinstance(tree_sha,str) or not tree_sha.startswith("sha256:"):
        return _fail("LIFT_DECISION_TREE_SHA_REQUIRED")

    ok,reason=_receipt(payload.get("concrete_lift_verification_receipt"),{
      "scope_id":scope_id,
      "concrete_lift_result_sha256":lift_sha,
      "concrete_scope_adaptive_policy_totality_proved":True,
    })
    if not ok:
        return _fail("CONCRETE_LIFT_VERIFICATION_RECEIPT_INVALID",receipt_error=reason)

    ok,reason=_receipt(payload.get("route_binding_receipt"),{
      "scope_id":scope_id,
      "route_id":route_id,
      "brain_owned":True,
      "deployed_exact":True,
      "resource_bound_proved":True,
      "implements_exact_lifted_decision_tree":True,
      "decision_tree_sha256":tree_sha,
    })
    if not ok:
        return _fail("ROUTE_BINDING_RECEIPT_INVALID",receipt_error=reason)

    blobs=payload.get("route_blobs")
    if not isinstance(blobs,Mapping):
        return _fail("ROUTE_BLOBS_REQUIRED")
    for field in (
      "admission_predicate_blob_sha",
      "adequacy_certificate_blob_sha",
      "admission_soundness_receipt_blob_sha",
    ):
        if not _hex40(blobs.get(field)):
            return _fail("INVALID_GIT_BLOB_SHA",field=field)

    theorem_binding={
      "scope_id":scope_id,
      "cell_id":cell_id,
      "route_id":route_id,
      "admission_predicate_id":predicate_id,
      "admission_predicate_sha256":predicate_sha,
      "concrete_lift_result_sha256":lift_sha,
      "decision_tree_sha256":tree_sha,
      "route_blobs":dict(blobs),
    }
    theorem_sha=_sha(theorem_binding)

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__CANDIDATE_SCOPE_WIDE_TRUE_ADMISSION_REDUCES_COMPLEMENT_TO_FALSE",
      **theorem_binding,
      "theorem_binding_sha256":theorem_sha,
      "candidate_admission_implies_route_adequacy":True,
      "candidate_residual_complement_unsat":True,
      "candidate_residual_normal_form":"S_TRACE_AND_NOT_TRUE",
      "proof_rule":(
        "CONCRETE_LIFT_PROVES_EVERY_SCOPE_CONTEXT_REACHES_AN_ADEQUATE_POLICY__"
        "EXACT_DEPLOYED_BRAIN_ROUTE_IMPLEMENTS_THAT_LIFTED_TREE__"
        "TRUE_ADMISSION_SELECTS_THAT_ROUTE_FOR_EVERY_CONTEXT_IN_THE_EXACT_SCOPE__"
        "THEREFORE_TRUE_IMPLIES_ROUTE_ADEQUACY_ON_SCOPE_AND_S_TRACE_AND_NOT_TRUE_IS_UNSAT"
      ),
      "independent_verified":False,
      "selected_cover_complete_authorized":False,
      "u_empty_authorized":False,
      "abc_closed_authorized":False,
      "terminal_authority":False,"terminal_credit_delta":0,
      "next_required_authority":(
        "INDEPENDENT_EXACT_BYTE_VERIFICATION_OF_THIS_THEOREM_BINDING__THEN_BIND_THE_RESULT_AS_"
        "ADMISSION_SOUNDNESS_AND_PROVEN_SUPERSET_COVER_INPUT_TO_PREDICATE_SELECTED_COVER_COMPLEMENT_GATE_V1"
      ),
      "boundary":"CANDIDATE_PROOF_ALGEBRA_ONLY__NO_SELF_CERTIFIED_INDEPENDENCE_OR_GLOBAL_CREDIT",
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
