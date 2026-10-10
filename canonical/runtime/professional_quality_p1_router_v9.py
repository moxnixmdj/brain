"""Professional P1 Router V9: V8 plus executable R12 totality semantics.

V8 remains the exact mediation subject. V9 adds one authority firewall: a
positive V8 final certificate is not returned unless a content-addressed semantic
verifier is rerun over the exact R12 totality certificate and an independent
receipt binds the rerun result.

No stored PASS boolean can substitute for the executable semantic proof.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v8 as base
from canonical.runtime import professional_r12_totality_semantic_receipt_v1 as semantic_receipt

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V9"
REQUIRED_V9_COMPONENTS=frozenset({
    "canonical/runtime/professional_quality_p1_router_v9.py",
    "canonical/runtime/professional_r12_totality_semantic_receipt_v1.py",
})

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason,
        "semantic_truth_authority":False,"execution_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def _v9_subject_ok(ref:Any,*,root:Path)->dict[str,Any]:
    doc,state=base._load_subject(ref,root=root)
    if doc is None:
        return {"pass":False,"reason":"V8_SUBJECT_REJECTED","v8_subject_state":state}
    comps=(doc.get("system_material") or {}).get("components") or []
    paths={x.get("path") for x in comps if isinstance(x,Mapping)}
    missing=sorted(REQUIRED_V9_COMPONENTS-paths)
    if missing:
        return {"pass":False,"reason":"V9_LOAD_BEARING_COMPONENTS_NOT_IN_SUBJECT","missing":missing}
    return {
        "pass":True,"subject_id":state.get("subject_id"),
        "subject_sha256":state.get("subject_sha256"),
        "subject_git_blob_sha":state.get("subject_git_blob_sha"),
    }

def _expected_binding()->dict[str,str]:
    return {
        "semantic_property_claim_id":base.R12_PROPERTY_CLAIM_ID,
        "semantic_scope_claim_id":base.R12_SCOPE_CLAIM_ID,
        "semantic_obligation":base.R12_MATERIAL_OBLIGATION,
        "target_scope_semantics":base.R12_SCOPE_SEMANTICS,
    }

def route(state:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(state,Mapping): return _fail("STATE_NOT_OBJECT")
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    subject=_v9_subject_ok(state.get(base.SUBJECT_REF_KEY),root=root)
    if subject.get("pass") is not True:
        return _fail("V9_DECLARED_SYSTEM_SUBJECT_INVALID",subject_verification=subject)

    out=base.route(state,repo_root=root)
    if not isinstance(out,Mapping): return _fail("V8_RESULT_NOT_OBJECT")
    result=deepcopy(dict(out))
    result["schema"]=SCHEMA
    if (
        result.get("final_step_outcome")!="POSITIVE_CERTIFICATE"
        or result.get("positive_certification_authorized") is not True
    ):
        result["v9_executable_r12_totality_semantics_verified"]=False
        return result

    bindings=state.get(base.STEP_BINDINGS_KEY)
    if not isinstance(bindings,Mapping):
        return _fail("V9_STEP_BINDINGS_REQUIRED_AFTER_V8_POSITIVE")
    final=bindings.get(base.FINAL_STEP)
    if not isinstance(final,Mapping):
        return _fail("V9_FINAL_BINDING_REQUIRED_AFTER_V8_POSITIVE")

    sem=semantic_receipt.validate(
        root=root,
        certificate_ref=final.get("material_totality_certificate"),
        semantic_verifier_ref=final.get("material_totality_semantic_verifier"),
        independent_verification_ref=final.get("material_totality_semantic_verification"),
        expected_binding=_expected_binding(),
    )
    if sem.get("pass") is not True:
        return _fail(
            "V9_EXECUTABLE_R12_TOTALITY_SEMANTICS_REJECTED",
            semantic_verification=sem,
        )
    result["v9_executable_r12_totality_semantics_verified"]=True
    result["r12_totality_semantic_verification"]=sem
    result["semantic_truth_authority"]=False
    result["quality_authority"]=False
    result["acceptance_authority"]=False
    result["promotion_authority"]=False
    result["terminal_authority"]=False
    result["terminal_credit_delta"]=0
    result["incremental_spend_usd"]=0
    return result

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return route(args or {},repo_root=root)
