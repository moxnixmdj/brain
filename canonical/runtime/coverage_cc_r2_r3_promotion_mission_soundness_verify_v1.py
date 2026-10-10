"""Executable formal reduction for CC_R2 mission soundness.

This proves only the active bounded PROPERTY_CERTIFICATE. It checks that the
five R3 promotion-safety requirements are consequences of exact authorized
mission rules requiring fail-closed sound verification and verified durable
capability compounding. It does not prove full mission optimality or completion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT_ID="CC_R2_MISSION_SOUNDNESS_V1"
CLAIM_ID="e1c519109c4b2c46a9225686fc2c5c5490564d1cc62d5c6ff3c6c436bfca4314"

MISSION_AXIOMS={
 "M_VERIFY":(
  "correctness_rule",
  "FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION",
 ),
 "M_COMPOUND":(
  "compounding_requirement",
  "SUCCESS_AND_FAILURE_EXPERIENCE_MUST_COMPOUND_INTO_DURABLE_VERIFIED_REUSABLE_CAPABILITY",
 ),
 "M_OPTIMIZE_VERIFIED":(
  "optimization_objective",
  "MAXIMIZE_REUSABLE_VERIFIED_CAPABILITY_GENERALIZATION_RELIABILITY_AND_EFFICIENCY_PER_AVAILABLE_RESOURCE_WHILE_PRESERVING_SEMANTIC_CAPABILITY_AND_FUTURE_OPTION_VALUE",
 ),
}
REQUIREMENTS=[
 "candidate_generation_and_external_provider_outputs_have_zero_verification_promotion_acceptance_terminal_authority",
 "skills_are_promoted_only_after_independent_skill_verification_and_authentication",
 "episodes_used_for_learning_are_independently_verified_or_remain_unpromoted",
 "verification_frontier_acquisition_cannot_rewrite_independent_verification_authority",
 "missing_distinguishing_evidence_or_adapter_coverage_does_not_self_certify_success",
]
EXPECTED_REDUCTION={
 REQUIREMENTS[0]:(
  ("M_VERIFY","M_COMPOUND"),
  "UNVERIFIED_CANDIDATE_OR_PROVIDER_OUTPUT_CANNOT_RECEIVE_DURABLE_LEARNING_OR_TERMINAL_PROGRESS_CREDIT",
 ),
 REQUIREMENTS[1]:(
  ("M_VERIFY","M_COMPOUND","M_OPTIMIZE_VERIFIED"),
  "PROMOTED_REUSABLE_SKILL_IS_VERIFIED_BEFORE_DURABLE_REUSE",
 ),
 REQUIREMENTS[2]:(
  ("M_VERIFY","M_COMPOUND"),
  "EXPERIENCE_ENTERING_DURABLE_LEARNING_IS_VERIFIED_OR_RECEIVES_NO_PROMOTION",
 ),
 REQUIREMENTS[3]:(
  ("M_VERIFY",),
  "ACQUISITION_CANNOT_SELF_DEFINE_THE_SOUND_VERIFICATION_STANDARD_THAT_GRANTS_ITS_OWN_PROGRESS_CREDIT",
 ),
 REQUIREMENTS[4]:(
  ("M_VERIFY",),
  "UNRESOLVED_EVIDENCE_GAPS_FAIL_CLOSED_WITH_ZERO_PROGRESS_CREDIT",
 ),
}
EXPECTED_TERMS={
 "G_minus":"IN_SCOPE_BEHAVIORS_THAT_SATISFY_ALL_FIVE_R3_PROMOTION_SAFETY_REQUIREMENTS_OF_THE_ACTIVE_PROPERTY_CERTIFICATE",
 "G_real":"IN_SCOPE_BEHAVIORS_ACCEPTED_BY_THE_AUTHORIZED_MISSION_WITH_RESPECT_TO_THE_VERIFICATION_AND_DURABLE_LEARNING_SAFETY_PROPERTY_CERTIFIED_BY_THIS_CLAIM",
 "progress_credit_binding":"PROMOTION_TO_DURABLE_LEARNED_SKILL_REUSE_OR_TERMINAL_TRUTH_IS_PROGRESS_CREDIT_FOR_THIS_PROPERTY",
 "sound_verification_binding":"THE_ACTIVE_CLAIM'S_INDEPENDENT_AUTHENTICATION_PATH_IS_THE_BOUND_IMPLEMENTATION_OF_SOUND_VERIFICATION_FOR_THIS_PROPERTY",
 "unresolved_binding":"MISSING_DISTINGUISHING_EVIDENCE_OR_ADAPTER_COVERAGE_HAS_NO_SOUND_VERIFICATION_AND_THEREFORE_MUST_NOT_RECEIVE_PROGRESS_CREDIT",
}


def _blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def _fail(root_id:str,claim_id:str,*errors:str)->dict[str,Any]:
    return {
      "pass":False,
      "status":"FAIL_CLOSED__CC_R2_MISSION_SOUNDNESS_UNPROVED",
      "root_id":root_id,
      "claim_id":claim_id,
      "semantic_claim_verified":False,
      "errors":sorted(set(errors)),
      "terminal_credit_delta":0,
    }


def verify_certificate(
 *,
 root:Path,
 certificate_path:Path,
 active_claim:Mapping[str,Any],
 root_id:str,
)->dict[str,Any]:
    root=root.resolve()
    claim_id=str(active_claim.get("claim_id") or "")
    errors:list[str]=[]
    if root_id!=ROOT_ID:
        return _fail(root_id,claim_id,"ROOT_ID_MISMATCH")
    if claim_id!=CLAIM_ID:
        return _fail(root_id,claim_id,"ACTIVE_CLAIM_ID_MISMATCH")
    if active_claim.get("claim_kind")!="PROPERTY_CERTIFICATE":
        return _fail(root_id,claim_id,"ACTIVE_CLAIM_NOT_PROPERTY_CERTIFICATE")

    try:
        cert=json.loads(certificate_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail(root_id,claim_id,"CERTIFICATE_INVALID_JSON")
    if cert.get("root_id")!=ROOT_ID: errors.append("CERTIFICATE_ROOT_MISMATCH")
    if cert.get("claim_id")!=CLAIM_ID: errors.append("CERTIFICATE_CLAIM_MISMATCH")
    if cert.get("terminal_authority") is not False: errors.append("CERTIFICATE_TERMINAL_AUTHORITY_NOT_FALSE")
    if (cert.get("accounting") or {}).get("terminal_credit_delta")!=0:
        errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")

    claim_ref=cert.get("active_claim") or {}
    claim_path=root/str(claim_ref.get("path") or "")
    if not claim_path.is_file():
        errors.append("ACTIVE_CLAIM_FILE_MISSING")
        frozen={}
    else:
        if _blob_sha(claim_path)!=claim_ref.get("git_blob_sha"):
            errors.append("ACTIVE_CLAIM_BLOB_MISMATCH")
        try: frozen=json.loads(claim_path.read_text(encoding="utf-8"))
        except Exception:
            frozen={}
            errors.append("ACTIVE_CLAIM_JSON_INVALID")
    if frozen.get("claim_id")!=CLAIM_ID:
        errors.append("FROZEN_CLAIM_ID_MISMATCH")
    if frozen.get("mission_blob_sha")!=active_claim.get("mission_blob_sha"):
        errors.append("FROZEN_CLAIM_MISSION_BINDING_MISMATCH")

    pointer_ref=cert.get("mission_pointer") or {}
    pointer_path=root/str(pointer_ref.get("path") or "")
    authority_ref=cert.get("mission_authority") or {}
    authority_path=root/str(authority_ref.get("path") or "")
    for label,path,ref in (
      ("MISSION_POINTER",pointer_path,pointer_ref),
      ("MISSION_AUTHORITY",authority_path,authority_ref),
    ):
        if not path.is_file():
            errors.append(label+"_FILE_MISSING")
        elif _blob_sha(path)!=ref.get("git_blob_sha"):
            errors.append(label+"_BLOB_MISMATCH")
    if errors:
        return _fail(root_id,claim_id,*errors)

    pointer=json.loads(pointer_path.read_text(encoding="utf-8"))
    authority=json.loads(authority_path.read_text(encoding="utf-8"))
    if _blob_sha(pointer_path)!=active_claim.get("mission_blob_sha"):
        errors.append("ACTIVE_CLAIM_CURRENT_MISSION_POINTER_DRIFT")
    source=(pointer.get("authoritative_source") or {}).get("path")
    if source!=authority_ref.get("path"):
        errors.append("MISSION_POINTER_AUTHORITY_PATH_MISMATCH")
    if pointer.get("real_objective")!=authority.get("real_objective"):
        errors.append("MISSION_OBJECTIVE_POINTER_AUTHORITY_MISMATCH")

    cert_axioms=cert.get("authorized_mission_axioms")
    if not isinstance(cert_axioms,Mapping):
        errors.append("CERTIFICATE_MISSION_AXIOMS_INVALID")
        cert_axioms={}
    for aid,(field,value) in MISSION_AXIOMS.items():
        if authority.get(field)!=value:
            errors.append("AUTHORIZED_MISSION_AXIOM_DRIFT:"+aid)
        row=cert_axioms.get(aid)
        if not isinstance(row,Mapping):
            errors.append("CERTIFICATE_MISSION_AXIOM_MISSING:"+aid)
        else:
            if row.get("field")!=field or row.get("exact_value")!=value:
                errors.append("CERTIFICATE_MISSION_AXIOM_BINDING_MISMATCH:"+aid)

    target=frozen.get("target_predicate") or {}
    if target.get("predicate_id")!="R3_PROMOTION_SAFETY_V1":
        errors.append("TARGET_PREDICATE_ID_DRIFT")
    if target.get("requires")!=REQUIREMENTS:
        errors.append("TARGET_REQUIREMENT_SET_OR_ORDER_DRIFT")
    if target.get("result")!="NO_UNVERIFIED_CANDIDATE_BECOMES_PROMOTED_LEARNED_OR_TERMINAL_TRUTH_WITHIN_SCOPE":
        errors.append("TARGET_RESULT_DRIFT")

    terms=cert.get("claim_scoped_terms")
    if not isinstance(terms,Mapping):
        errors.append("CLAIM_SCOPED_TERMS_INVALID")
    else:
        for key,value in EXPECTED_TERMS.items():
            if terms.get(key)!=value:
                errors.append("CLAIM_SCOPED_TERM_DRIFT:"+key)

    rows=cert.get("reduction")
    if not isinstance(rows,list) or len(rows)!=len(REQUIREMENTS):
        errors.append("REDUCTION_SHAPE_INVALID")
        rows=[]
    seen=set()
    for row in rows:
        if not isinstance(row,Mapping):
            errors.append("REDUCTION_ROW_INVALID")
            continue
        req=row.get("requirement")
        if req not in EXPECTED_REDUCTION:
            errors.append("REDUCTION_UNKNOWN_REQUIREMENT:"+str(req))
            continue
        if req in seen:
            errors.append("REDUCTION_DUPLICATE_REQUIREMENT:"+str(req))
            continue
        seen.add(req)
        expected_axioms,expected_consequence=EXPECTED_REDUCTION[req]
        if tuple(row.get("mission_axioms") or [])!=expected_axioms:
            errors.append("REDUCTION_AXIOM_SET_DRIFT:"+req)
        if row.get("consequence")!=expected_consequence:
            errors.append("REDUCTION_CONSEQUENCE_DRIFT:"+req)
        if any(aid not in MISSION_AXIOMS for aid in row.get("mission_axioms") or []):
            errors.append("REDUCTION_USES_UNAUTHORIZED_AXIOM:"+req)
    if seen!=set(REQUIREMENTS):
        errors.append("REDUCTION_REQUIREMENT_COVERAGE_INCOMPLETE")

    theorem=cert.get("theorem") or {}
    if theorem.get("proof_mode")!="FORMAL_REDUCTION":
        errors.append("THEOREM_PROOF_MODE_DRIFT")
    if theorem.get("full_mission_optimality_implied") is not False:
        errors.append("FULL_MISSION_OPTIMALITY_OVERCLAIM")
    if theorem.get("global_mission_completion_implied") is not False:
        errors.append("GLOBAL_MISSION_COMPLETION_OVERCLAIM")
    if theorem.get("opus_checkpoint_completion_implied") is not False:
        errors.append("CHECKPOINT_COMPLETION_OVERCLAIM")

    if errors:
        return _fail(root_id,claim_id,*errors)

    # Formal reduction: the exact G_minus predicate contains all five safety
    # requirements; each requirement is mapped only to exact authorized mission
    # axioms. For this claim-scoped property, satisfying G_minus therefore
    # satisfies the mission-authorized safety semantics G_real[C].
    return {
      "pass":True,
      "status":"PASS__CC_R2_R3_PROMOTION_MISSION_SOUNDNESS_FORMAL_REDUCTION",
      "root_id":ROOT_ID,
      "claim_id":CLAIM_ID,
      "semantic_claim_verified":True,
      "authorized_mission_axiom_count":len(MISSION_AXIOMS),
      "claim_requirement_count":len(REQUIREMENTS),
      "reduction_rows_verified":len(seen),
      "g_minus_subseteq_g_real":True,
      "claim_scoped_property_only":True,
      "full_mission_optimality_implied":False,
      "global_mission_completion_derivable":False,
      "terminal_credit_delta":0,
      "errors":[],
    }
