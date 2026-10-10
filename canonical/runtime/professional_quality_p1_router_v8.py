"""Professional-quality P1 Router V8: proof-bound execution with totality-mediated final certification.

V7 proves that caller-supplied step results cannot authorize profile execution.
V8 preserves that rule and upgrades the final certificate-or-abstain step to
professional_step_binding_authority_v2.

Consequences:
* every non-final load-bearing step remains content-addressed and independently verified;
* an authenticated ABSTAIN at the final step terminates as abstention;
* a positive final result is admitted only when V2 authenticates an independently
  verified, exact-run/evidence-bound scope-completeness certificate;
* missing, forged, cross-context, incomplete, or generic PASS-only final evidence
  cannot become a positive final step.

This is mediation authority only. It grants no quality, acceptance, promotion,
or terminal authority by itself.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v6 as base
from canonical.runtime import professional_step_binding_authority_v2 as step_auth
from canonical.runtime import professional_quality_declared_system_subject_verify_v2 as subject_verify

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V8"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
SUBJECT_REF_KEY="declared_system_subject"
STEP_BINDINGS_KEY="professional_step_bindings"
FINAL_STEP=step_auth.FINAL_STEP
R12_PROPERTY_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
R12_SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
R12_MATERIAL_OBLIGATION="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION"
R12_SCOPE_SEMANTICS="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_FOR_EXACT_RUN_CONTEXT_AND_EVIDENCE"

AUTHENTICATED_STEPS=(
    "GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION",
    "RUN_DETERMINISTIC_FACT_STRUCTURE_FORMAT_AND_GROUNDING_CHECKS",
    "RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS",
    "RUN_CRITERION_SPECIFIC_PLUS_HOLISTIC_COMPARATIVE_EVALUATION",
    "ATTACK_FINALISTS_WITH_RELEVANT_INVARIANCE_DEFEATER_HIDDEN_CHANNEL_AND_COUNTEREXAMPLE_PROBES",
    "FREEZE_WINNER_AND_USE_FRESH_OR_SELECTION_AWARE_TERMINAL_EVIDENCE",
    FINAL_STEP,
)
REQUIRED_SUBJECT_COMPONENT_PATHS=frozenset({
    "canonical/runtime/professional_quality_p1_router_v8.py",
    "canonical/runtime/professional_step_binding_authority_v2.py",
    "canonical/runtime/universal_scope_closure_compiler_v1.py",
    "canonical/runtime/professional_quality_declared_system_subject_verify_v2.py",
})

def _base(status:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return _base("FAIL_CLOSED",reason=reason,**extra)

def _open(reason:str,**extra:Any)->dict[str,Any]:
    return _base(
        "ABSTAIN__P1_VERIFIED_STEP_BINDINGS_REQUIRED",
        route="ABSTAIN",
        positive_certification_authorized=False,
        blocking_reason=reason,
        **extra,
    )

def _load_subject(ref:Any,*,root:Path)->tuple[dict[str,Any]|None,dict[str,Any]]:
    if not isinstance(ref,Mapping):
        return None,_open("DECLARED_SYSTEM_SUBJECT_REFERENCE_REQUIRED")
    rel=ref.get("path")
    expected_blob=ref.get("git_blob_sha")
    if not isinstance(rel,str) or not rel.startswith("canonical/governance/"):
        return None,_fail("DECLARED_SYSTEM_SUBJECT_PATH_INVALID")
    if not isinstance(expected_blob,str) or not expected_blob:
        return None,_fail("DECLARED_SYSTEM_SUBJECT_BLOB_REQUIRED")
    verified=subject_verify.verify(rel,repo_root=root)
    if verified.get("pass") is not True:
        return None,_fail("DECLARED_SYSTEM_SUBJECT_VERIFICATION_FAILED",subject_verification=verified)
    if verified.get("subject_git_blob_sha")!=expected_blob:
        return None,_fail("DECLARED_SYSTEM_SUBJECT_REFERENCE_STALE",subject_verification=verified)
    try:
        doc=json.loads((root/rel).read_text(encoding="utf-8"))
    except Exception as exc:
        return None,_fail("DECLARED_SYSTEM_SUBJECT_LOAD_FAILED",subject_error=type(exc).__name__+":"+str(exc))
    components=(doc.get("system_material") or {}).get("components") or []
    paths={row.get("path") for row in components if isinstance(row,Mapping)}
    missing=sorted(REQUIRED_SUBJECT_COMPONENT_PATHS-paths)
    if missing:
        return None,_fail("V8_LOAD_BEARING_COMPONENTS_NOT_IN_SUBJECT",missing_component_paths=missing)
    return doc,verified

def _semantic_totality_documents_ok(cert:Any, verification:Any)->dict[str,Any]:
    if not isinstance(cert,Mapping) or not isinstance(verification,Mapping):
        return {"pass":False,"reason":"R12_TOTALITY_SEMANTIC_DOCUMENT_REQUIRED"}
    required={
        "semantic_property_claim_id":R12_PROPERTY_CLAIM_ID,
        "semantic_scope_claim_id":R12_SCOPE_CLAIM_ID,
        "semantic_obligation":R12_MATERIAL_OBLIGATION,
        "target_scope_semantics":R12_SCOPE_SEMANTICS,
    }
    for field,expected in required.items():
        if cert.get(field)!=expected:
            return {"pass":False,"reason":"R12_TOTALITY_CERT_SEMANTIC_BINDING_MISMATCH:"+field}
        if verification.get(field)!=expected:
            return {"pass":False,"reason":"R12_TOTALITY_VERIFY_SEMANTIC_BINDING_MISMATCH:"+field}
    if verification.get("semantic_binding_verified") is not True:
        return {"pass":False,"reason":"R12_TOTALITY_SEMANTIC_BINDING_NOT_INDEPENDENTLY_VERIFIED"}
    return {"pass":True,"status":"PASS__R12_TOTALITY_SEMANTICS_EXACTLY_BOUND"}

def _authenticate_r12_totality_semantics(binding:Any,*,root:Path)->dict[str,Any]:
    if not isinstance(binding,Mapping):
        return {"pass":False,"reason":"R12_FINAL_BINDING_REQUIRED"}
    try:
        cert,_,cert_blob=step_auth.base._bound_json(
            binding.get("material_totality_certificate"),
            repo_root=root,
            prefixes=("canonical/governance/","canonical/evidence/","canonical/verification/"),
        )
        verify,_,_=step_auth.base._bound_json(
            binding.get("material_totality_verification"),
            repo_root=root,
            prefixes=("canonical/verification/",),
        )
    except Exception as exc:
        return {"pass":False,"reason":"R12_TOTALITY_SEMANTIC_BINDING_LOAD_FAILED:"+type(exc).__name__+":"+str(exc)}
    out=_semantic_totality_documents_ok(cert,verify)
    if out.get("pass") is not True:
        return out
    if verify.get("subject_git_blob_sha")!=cert_blob:
        return {"pass":False,"reason":"R12_TOTALITY_SEMANTIC_VERIFY_SUBJECT_MISMATCH"}
    return {**out,"certificate_git_blob_sha":cert_blob}

def route(state:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(state,Mapping):
        return _fail("STATE_NOT_OBJECT")
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]

    supplied=state.get("step_results",{})
    if not isinstance(supplied,Mapping):
        return _fail("STEP_RESULTS_NOT_OBJECT")
    if supplied:
        return _fail("CALLER_STEP_RESULTS_FORBIDDEN",caller_supplied_step_ids=sorted(str(k) for k in supplied))

    subject_doc,subject_state=_load_subject(state.get(SUBJECT_REF_KEY),root=root)
    if subject_doc is None:
        return subject_state
    subject_id=subject_state.get("subject_id")
    subject_sha=subject_state.get("subject_sha256")

    bindings=state.get(STEP_BINDINGS_KEY)
    if not isinstance(bindings,Mapping):
        return _open("PROFESSIONAL_STEP_BINDINGS_REQUIRED",blocking_steps=list(AUTHENTICATED_STEPS),declared_system_subject=subject_state)
    unknown=sorted(set(bindings)-set(AUTHENTICATED_STEPS))
    if unknown:
        return _fail("UNKNOWN_PROFESSIONAL_STEP_BINDING",unknown_step_ids=unknown)
    missing=[step for step in AUTHENTICATED_STEPS if step not in bindings]
    if missing:
        return _open("MISSING_PROFESSIONAL_STEP_BINDINGS",blocking_steps=missing,declared_system_subject=subject_state)

    goal=state.get("goal")
    payload=state.get("decision_payload")
    if not isinstance(goal,str) or not goal.strip():
        return _open("RAW_GOAL_REQUIRED",blocking_steps=list(AUTHENTICATED_STEPS))
    if not isinstance(payload,Mapping):
        return _open("DECISION_PAYLOAD_REQUIRED",blocking_steps=list(AUTHENTICATED_STEPS))

    run_context=step_auth.base.run_context_digest(
        goal=goal.strip(),
        decision_payload=payload,
        artifact_paths=state.get("artifact_paths"),
        hard_defect_profile_id=state.get("hard_defect_profile_id"),
        detected_triggers=state.get("detected_triggers",[]),
    )

    authenticated={}
    for step in AUTHENTICATED_STEPS:
        result=step_auth.authenticate_step_binding(
            bindings.get(step),
            behavior_id=BEHAVIOR_ID,
            subject_id=str(subject_id),
            subject_sha256=str(subject_sha),
            step_id=step,
            run_context_sha256=run_context,
            repo_root=root,
        )
        if result.get("pass") is not True:
            if str(result.get("status") or "").startswith("OPEN__"):
                return _open(
                    "PROFESSIONAL_STEP_BINDING_OPEN",
                    blocking_steps=[step],
                    step_binding_result=result,
                    declared_system_subject=subject_state,
                )
            return _fail(
                "PROFESSIONAL_STEP_BINDING_INVALID",
                blocking_step=step,
                step_binding_result=result,
                declared_system_subject=subject_state,
            )
        authenticated[step]=result

        if step==FINAL_STEP:
            outcome=result.get("decision_outcome")
            if outcome=="ABSTAIN":
                return _base(
                    "ABSTAIN__P1_AUTHENTICATED_FINAL_DECISION",
                    route="ABSTAIN",
                    positive_certification_authorized=False,
                    material_totality_proved=False,
                    final_step_binding=result,
                    declared_system_subject=subject_state,
                    run_context_sha256=run_context,
                )
            if outcome!="POSITIVE_CERTIFICATE":
                return _fail("FINAL_STEP_OUTCOME_NOT_MEDIATED",final_step_binding=result)
            if result.get("positive_certification_authorized") is not True:
                return _fail("FINAL_POSITIVE_CERTIFICATION_NOT_AUTHORIZED",final_step_binding=result)
            if result.get("material_totality_proved") is not True:
                return _fail("FINAL_POSITIVE_MATERIAL_TOTALITY_NOT_PROVED",final_step_binding=result)
            semantic_binding=_authenticate_r12_totality_semantics(bindings.get(step),root=root)
            if semantic_binding.get("pass") is not True:
                return _fail(
                    "FINAL_POSITIVE_R12_TOTALITY_SEMANTICS_NOT_BOUND",
                    semantic_binding_result=semantic_binding,
                    final_step_binding=result,
                )
            result["r12_totality_semantic_binding"]=semantic_binding

    delegated=deepcopy(dict(state))
    delegated.pop(SUBJECT_REF_KEY,None)
    delegated.pop(STEP_BINDINGS_KEY,None)
    delegated["step_results"]={step:"PASS" for step in AUTHENTICATED_STEPS}

    out=base.route(delegated,repo_root=root)
    if not isinstance(out,Mapping):
        return _fail("V6_RESULT_NOT_OBJECT")
    result=deepcopy(dict(out))
    final=authenticated[FINAL_STEP]
    result["schema"]=SCHEMA
    result["declared_system_subject"]={
        "path":state[SUBJECT_REF_KEY].get("path"),
        "git_blob_sha":state[SUBJECT_REF_KEY].get("git_blob_sha"),
        "subject_id":subject_id,
        "subject_sha256":subject_sha,
    }
    result["professional_step_bindings_authenticated"]=True
    result["caller_step_results_allowed"]=False
    result["authenticated_step_ids"]=list(AUTHENTICATED_STEPS)
    result["run_context_sha256"]=run_context
    result["final_step_outcome"]="POSITIVE_CERTIFICATE"
    result["positive_certification_authorized"]=True
    result["material_totality_proved"]=True
    result["material_totality_basis"]=final.get("material_totality_basis")
    result["material_totality_target_scope_id"]=final.get("material_totality_target_scope_id")
    result["r12_totality_semantics_bound"]=True
    result["r12_property_claim_id"]=R12_PROPERTY_CLAIM_ID
    result["r12_scope_claim_id"]=R12_SCOPE_CLAIM_ID
    result["r12_material_obligation"]=R12_MATERIAL_OBLIGATION
    result["step_binding_receipts"]={
        step:{
            "receipt_path":row.get("receipt_path"),
            "receipt_git_blob_sha":row.get("receipt_git_blob_sha"),
            "verification_path":row.get("verification_path"),
            "verification_git_blob_sha":row.get("verification_git_blob_sha"),
            "evidence_sha256":row.get("evidence_sha256"),
            "decision_outcome":row.get("decision_outcome"),
        }
        for step,row in authenticated.items()
    }
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
