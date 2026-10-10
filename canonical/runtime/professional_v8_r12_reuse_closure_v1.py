"""V8 R12 reuse closure V1.

Reuses two independently verified Brain mechanisms:
1. V7->V8 positive-route refinement for preserved R12 C1-C7 structure.
2. Observable policy-cover totality for claim-scoped material-defeater totality.

The adapter deliberately does NOT treat a defeater catalog, a passing router
unit test, or a V7 positive route as a V8 totality witness. Positive CC_R3
requires an exact bound-state policy-relevant world set, independently verified
Brain-owned adequate policy regions, and truthful discriminators sufficient to
construct a total policy cover.

This module can reverify the preserved C1-C7 structure on the exact V8 subject.
It grants no C8, CC_R3, R4, quality, acceptance, promotion, or terminal credit
unless a real independently verified V8 cover instance is supplied.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_v7_to_v8_r12_positive_refinement_v1 as refinement
from canonical.runtime import observable_policy_cover_totality_gate_v1 as policy_cover
from canonical.runtime import professional_r12_material_defeater_generator_closure_v1 as generator_closure

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V8_R12_REUSE_CLOSURE_V1"
PROPERTY_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
OBLIGATION="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION"
TARGET_SCOPE_SEMANTICS="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_FOR_EXACT_RUN_CONTEXT_AND_EVIDENCE"

V8_SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V8_DECLARED_SYSTEM_SUBJECT_20261010_V7.json"
V8_SUBJECT_BLOB="21820105caab672440c76d051fecc16a562ae4cc"
V8_SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V8_TOTALITY_MEDIATED_SYSTEM_20261010_V7"
V8_SUBJECT_SHA256="f6a1752167c3e4972ac952b04e3298690088256fcaa65150743582e8e655e51c"
REFINE_VERIFY_PATH="canonical/verification/PROFESSIONAL_V7_TO_V8_R12_POSITIVE_REFINEMENT_INDEPENDENT_VERIFY_20261010_V1.json"
REFINE_VERIFY_BLOB="0a4bd655f6b6e2faeb23b39c6affe1b8187feba9"
R12_RECON_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
R12_RECON_BLOB="56a5f85e6133661dd7afbc8fc5041ad799f0736f"
COVER_VERIFY_PATH="canonical/verification/OBSERVABLE_POLICY_COVER_TOTALITY_TWO_SPRITE_VERIFICATION_20261008_V1.json"
COVER_VERIFY_BLOB="776f309139463ad6e143f86c133efba78ff15f26"
GENERATOR_VERIFY_PATH="canonical/verification/PROFESSIONAL_R12_MATERIAL_DEFEATER_GENERATOR_CLOSURE_INDEPENDENT_VERIFY_20261010_V1.json"
GENERATOR_VERIFY_BLOB="e72e29635038abbe8a4339b4fe77058040e93ffb"

PRESERVED_CLAUSES=(
    "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
    "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
    "R12C3_ABSTRACTION_SOUNDNESS",
    "R12C4_INDEPENDENT_DEFEATER_SEARCH",
    "R12C5_COVERAGE_ACCOUNTING",
    "R12C6_PROOF_SEARCH_HONESTY",
    "R12C7_META_CONTROLLER_FALSIFICATION",
)


def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _canonical_sha256(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _zero()->dict[str,Any]:
    return {
        "semantic_property_truth_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "preserved_c1_c7_v8_reverified":False,
        "v8_material_defeater_totality_proved":False,
        "v8_c8_nonvacuity_proved":False,
        "cc_r3_terminal_closure_proved":False,
        "r4_proof_realization_authority":False,
        **_zero(),**extra,
    }


def _load_bound_json(root:Path,rel:str,expected_blob:str)->dict[str,Any]:
    path=root/rel
    if not path.is_file() or path.is_symlink():
        raise ValueError("PIN_MISSING:"+rel)
    got=_blob(path)
    if got!=expected_blob:
        raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError("PIN_NOT_OBJECT:"+rel)
    return value


def verify_preserved_c1_c7(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        subject=_load_bound_json(root,V8_SUBJECT_PATH,V8_SUBJECT_BLOB)
        refine_verify=_load_bound_json(root,REFINE_VERIFY_PATH,REFINE_VERIFY_BLOB)
        r12=_load_bound_json(root,R12_RECON_PATH,R12_RECON_BLOB)
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))

    ref=refinement.verify(repo_root=root)
    if ref.get("pass") is not True or ref.get("positive_route_refinement_proved") is not True:
        return _fail("REFINEMENT_RUNTIME_NOT_PROVED",refinement=ref)
    if ref.get("preserved_clause_reverification_admissible") is not True:
        return _fail("PRESERVED_CLAUSE_REVERIFICATION_NOT_ADMISSIBLE")
    if tuple(ref.get("preserved_clause_ids") or ())!=PRESERVED_CLAUSES:
        return _fail("PRESERVED_CLAUSE_SET_DRIFT")

    if not str(refine_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
        return _fail("REFINEMENT_INDEPENDENT_VERIFY_NOT_PASS")
    truth=refine_verify.get("truth") or {}
    if truth.get("positive_route_refinement_proved") is not True:
        return _fail("REFINEMENT_VERIFY_MISSING_POSITIVE_ROUTE_REFINEMENT")
    if truth.get("preserved_clause_reverification_admissible") is not True:
        return _fail("REFINEMENT_VERIFY_MISSING_REUSE_AUTHORITY")
    if tuple(truth.get("preserved_clause_ids") or ())!=PRESERVED_CLAUSES:
        return _fail("REFINEMENT_VERIFY_CLAUSE_SET_DRIFT")
    if truth.get("cross_subject_property_authority_transport") is not False:
        return _fail("CROSS_SUBJECT_AUTHORITY_TRANSPORT_FORBIDDEN")

    if subject.get("subject_id")!=V8_SUBJECT_ID or subject.get("subject_sha256")!=V8_SUBJECT_SHA256:
        return _fail("V8_SUBJECT_IDENTITY_DRIFT")
    material=subject.get("system_material") or {}
    components=material.get("components") or []
    component_paths={row.get("path") for row in components if isinstance(row,Mapping)}
    for required in (
        "canonical/runtime/professional_quality_p1_router_v8.py",
        "canonical/runtime/professional_step_binding_authority_v2.py",
        "canonical/runtime/universal_scope_closure_compiler_v1.py",
    ):
        if required not in component_paths:
            return _fail("V8_REQUIRED_COMPONENT_MISSING:"+required)

    states={
        row.get("id"):row.get("state")
        for row in (r12.get("clause_state") or [])
        if isinstance(row,Mapping)
    }
    if any(states.get(cid)!="VERIFIED_CURRENT" for cid in PRESERVED_CLAUSES):
        return _fail("V7_PRESERVED_PREMISE_NOT_CURRENT",clause_states=states)

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__C1_TO_C7_REVERIFIED_ON_EXACT_V8_REFINEMENT_SUBJECT__NO_C8_OR_PROPERTY_CREDIT",
        "v8_subject_id":V8_SUBJECT_ID,
        "v8_subject_sha256":V8_SUBJECT_SHA256,
        "preserved_clause_ids":list(PRESERVED_CLAUSES),
        "preserved_clause_count":len(PRESERVED_CLAUSES),
        "preserved_c1_c7_v8_reverified":True,
        "proof_mode":"EXACT_SUBJECT_REFINEMENT_PLUS_INDEPENDENT_REPLAY_PLUS_CURRENT_CLAUSE_PREMISES",
        "cross_subject_property_authority_transport":False,
        "v8_c8_nonvacuity_proved":False,
        "v8_material_defeater_totality_proved":False,
        "cc_r3_terminal_closure_proved":False,
        "r4_proof_realization_authority":False,
        "exact_next":"BIND_ONE_REAL_V8_POLICY_RELEVANT_STATE_COVER__THEN_C8_CC_R3__THEN_R4",
        **_zero(),
    }


def evaluate_v8_totality_cover(
    problem:Mapping[str,Any],
    independent_verification:Mapping[str,Any],
    *,
    r12_reconciliation:Mapping[str,Any],
)->dict[str,Any]:
    """Adapt observable policy-cover totality into the exact R12 CC_R3 contract.

    This is a mechanism-level adapter. The supplied problem must represent one
    real exact V8 run/evidence state and the independent verification must bind
    those exact problem bytes.
    """
    if not all(isinstance(x,Mapping) for x in (problem,independent_verification,r12_reconciliation)):
        return _fail("INPUT_NOT_MAPPING")

    required_problem={
        "semantic_property_claim_id":PROPERTY_CLAIM_ID,
        "semantic_scope_claim_id":SCOPE_CLAIM_ID,
        "semantic_obligation":OBLIGATION,
        "target_scope_semantics":TARGET_SCOPE_SEMANTICS,
        "v8_subject_id":V8_SUBJECT_ID,
        "v8_subject_sha256":V8_SUBJECT_SHA256,
        "real_exact_run":True,
        "content_addressed":True,
    }
    for key,expected in required_problem.items():
        if problem.get(key)!=expected:
            return _fail("V8_COVER_BINDING_MISMATCH:"+key)

    cover_problem=problem.get("policy_cover_problem")
    if not isinstance(cover_problem,Mapping):
        return _fail("POLICY_COVER_PROBLEM_REQUIRED")
    cover_out=policy_cover.evaluate(cover_problem)
    if cover_out.get("pass") is not True or cover_out.get("bound_state_totality_proved") is not True:
        return _fail("POLICY_COVER_TOTALITY_NOT_PROVED",policy_cover_verdict=cover_out)

    digest=_canonical_sha256(problem)
    required_verify={
        "pass":True,
        "independent_verified":True,
        "problem_sha256":digest,
        "semantic_property_claim_id":PROPERTY_CLAIM_ID,
        "semantic_scope_claim_id":SCOPE_CLAIM_ID,
        "semantic_obligation":OBLIGATION,
        "v8_subject_id":V8_SUBJECT_ID,
        "v8_subject_sha256":V8_SUBJECT_SHA256,
        "policy_relevant_world_set_complete":True,
        "policy_cover_replay_pass":True,
        "positive_route_observed":True,
    }
    for key,expected in required_verify.items():
        if independent_verification.get(key)!=expected:
            return _fail("V8_COVER_INDEPENDENT_VERIFY_MISMATCH:"+key)
    verifier_id=independent_verification.get("independent_verifier_id")
    if not isinstance(verifier_id,str) or not verifier_id.strip():
        return _fail("INDEPENDENT_VERIFIER_ID_REQUIRED")

    cert={
        "schema":generator_closure.CERT_SCHEMA,
        "property_claim_id":PROPERTY_CLAIM_ID,
        "scope_claim_id":SCOPE_CLAIM_ID,
        "leaf_id":LEAF_ID,
        "obligation":OBLIGATION,
        "proof_basis":"LOSSLESS_DECOMPOSITION_OR_GENERATOR_CLOSURE",
        "scope_complete":True,
        "generator_or_universal_cover_complete":True,
        "all_material_defeaters_in_scope_covered":True,
        "uncovered_material_defeater_complement_empty":True,
        "decision_null_or_resolved_for_every_covered_defeater":True,
        "independent_verified":True,
        "independent_verifier_id":verifier_id,
        "content_addressed":True,
        "fail_closed_on_unknown":True,
        "finite_catalog_only":False,
        "eight_clause_count_only":False,
        "unknown_remainder":[],
    }
    close=generator_closure.evaluate(r12_reconciliation,cert)
    if close.get("pass") is not True or close.get("cc_r3_terminal_closure_proved") is not True:
        return _fail("GENERATOR_CLOSURE_ADAPTER_REJECTED",generator_closure_verdict=close)

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__REAL_V8_OBSERVABLE_POLICY_COVER_PROVES_MATERIAL_DEFEATER_TOTALITY__C8_AND_CC_R3_ONLY",
        "problem_sha256":digest,
        "v8_subject_id":V8_SUBJECT_ID,
        "v8_subject_sha256":V8_SUBJECT_SHA256,
        "policy_cover_verdict":cover_out,
        "v8_c8_nonvacuity_proved":True,
        "v8_material_defeater_totality_proved":True,
        "cc_r3_terminal_closure_proved":True,
        "preserved_c1_c7_v8_reverified":False,
        "r4_proof_realization_authority":False,
        "semantic_property_truth_authority":False,
        "exact_next":"BIND_R4_PROOF_REALIZATION_TO_THE_SAME_EXACT_V8_SUBJECT_AND_TOTALITY_WITNESS",
        **_zero(),
    }
