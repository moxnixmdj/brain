"""Professional step binding authority V2.

V2 preserves V1 authentication for every profile step and hardens the final
certificate-or-abstain step.

The final step MUST explicitly bind one of two outcomes:
  * ABSTAIN: authenticated abstention, no positive certificate authority.
  * POSITIVE_CERTIFICATE: requires a content-addressed, independently verified
    claim-scoped completeness certificate for the exact run context + evidence.

Unknown/missing outcome fails closed. A positive certificate can never inherit
authority from generic evidence_scope_verified=True alone.

This module authenticates mediation only. It grants no semantic, quality,
acceptance, promotion, or terminal authority by itself.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_step_binding_authority_v1 as base
from canonical.runtime import universal_scope_closure_compiler_v1 as scope_compiler

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_STEP_BINDING_AUTHORITY_V2"
TOTALITY_CERT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_FINAL_STEP_LOCAL_TOTALITY_CERTIFICATE_V1"
TOTALITY_VERIFY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_FINAL_STEP_LOCAL_TOTALITY_INDEPENDENT_VERIFY_V1"
FINAL_STEP="ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT"
OUTCOMES=frozenset({"ABSTAIN","POSITIVE_CERTIFICATE"})
SCOPE_COMPILER_PATH="canonical/runtime/universal_scope_closure_compiler_v1.py"
SCOPE_COMPILER_BLOB="b208255789b14e44e86c82c196e06b5c41b3d039"


def _sha(value:str)->str:
    return sha256(value.encode("utf-8")).hexdigest()


def target_scope_id(*,run_context_sha256:str,evidence_sha256:str)->str:
    material=json.dumps(
        {"run_context_sha256":run_context_sha256,"evidence_sha256":evidence_sha256},
        sort_keys=True,separators=(",",":"),
    )
    return "scope://professional-final-positive/"+_sha(material)


def _zero(step_id:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "step_id":step_id,
        "decision_outcome":None,
        "positive_certification_authorized":False,
        "material_totality_proved":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _fail(step_id:str,reason:str,**extra:Any)->dict[str,Any]:
    return {
        **_zero(step_id),
        "status":"FAIL_CLOSED__PROFESSIONAL_STEP_BINDING_V2_INVALID",
        "reason":reason,
        **extra,
    }


def authenticate_step_binding(
    binding:Any,
    *,
    behavior_id:str,
    subject_id:str,
    subject_sha256:str,
    step_id:str,
    run_context_sha256:str,
    repo_root:str|Path,
)->dict[str,Any]:
    prior=base.authenticate_step_binding(
        binding,
        behavior_id=behavior_id,
        subject_id=subject_id,
        subject_sha256=subject_sha256,
        step_id=step_id,
        run_context_sha256=run_context_sha256,
        repo_root=repo_root,
    )
    if prior.get("pass") is not True:
        return {
            **_zero(step_id),
            "status":prior.get("status"),
            "reason":prior.get("reason"),
            "v1_verdict":prior,
        }

    # Non-final profile steps preserve V1 semantics.
    if step_id!=FINAL_STEP:
        return {
            **prior,
            "schema":SCHEMA,
            "v1_authenticated":True,
            "decision_outcome":"NOT_APPLICABLE",
            "positive_certification_authorized":False,
            "material_totality_proved":False,
        }

    root=Path(repo_root).resolve(strict=True)
    try:
        receipt,_,receipt_blob=base._bound_json(
            binding.get("receipt"),repo_root=root,prefixes=base.ALLOWED_REF_PREFIXES
        )
        verification,_,_=base._bound_json(
            binding.get("verification"),repo_root=root,prefixes=("canonical/verification/",)
        )
        outcome=receipt.get("decision_outcome")
        if outcome not in OUTCOMES:
            raise base.StepBindingAuthorityError("FINAL_STEP_DECISION_OUTCOME_INVALID")
        if verification.get("decision_outcome")!=outcome:
            raise base.StepBindingAuthorityError("FINAL_STEP_VERIFY_OUTCOME_MISMATCH")

        if outcome=="ABSTAIN":
            return {
                **prior,
                "schema":SCHEMA,
                "v1_authenticated":True,
                "decision_outcome":"ABSTAIN",
                "positive_certification_authorized":False,
                "material_totality_proved":False,
                "status":"PASS__AUTHENTICATED_FINAL_STEP_ABSTENTION",
            }

        cert,cert_path,cert_blob=base._bound_json(
            binding.get("material_totality_certificate"),
            repo_root=root,
            prefixes=("canonical/governance/","canonical/evidence/","canonical/verification/"),
        )
        cert_verify,verify_path,verify_blob=base._bound_json(
            binding.get("material_totality_verification"),
            repo_root=root,
            prefixes=("canonical/verification/",),
        )
        if cert.get("schema")!=TOTALITY_CERT_SCHEMA:
            raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_CERT_SCHEMA_INVALID")

        expected_scope=target_scope_id(
            run_context_sha256=run_context_sha256,
            evidence_sha256=str(prior.get("evidence_sha256")),
        )
        required={
            "behavior_id":behavior_id,
            "subject_id":subject_id,
            "subject_sha256":subject_sha256,
            "step_id":FINAL_STEP,
            "run_context_sha256":run_context_sha256,
            "evidence_sha256":prior.get("evidence_sha256"),
            "decision_outcome":"POSITIVE_CERTIFICATE",
            "target_scope_id":expected_scope,
        }
        for field,expected in required.items():
            if cert.get(field)!=expected:
                raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_CERT_FIELD_MISMATCH:"+field)

        for field in (
            "semantic_truth_authority","quality_authority","acceptance_authority",
            "promotion_authority","terminal_authority",
        ):
            if cert.get(field) is not False:
                raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_CERT_AUTHORITY_OVERCLAIM:"+field)

        scope_cert=cert.get("scope_certificate")
        if not isinstance(scope_cert,Mapping):
            raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_SCOPE_CERT_REQUIRED")
        if scope_cert.get("target_scope_id")!=expected_scope:
            raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_SCOPE_TARGET_MISMATCH")
        scope_out=scope_compiler.evaluate(scope_cert)
        if scope_out.get("scope_complete") is not True:
            raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_SCOPE_NOT_COMPLETE")

        if cert_verify.get("schema")!=TOTALITY_VERIFY_SCHEMA:
            raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_VERIFY_SCHEMA_INVALID")
        expected_verify={
            "subject_git_blob_sha":cert_blob,
            "behavior_id":behavior_id,
            "subject_id":subject_id,
            "subject_sha256":subject_sha256,
            "step_id":FINAL_STEP,
            "run_context_sha256":run_context_sha256,
            "evidence_sha256":prior.get("evidence_sha256"),
            "decision_outcome":"POSITIVE_CERTIFICATE",
            "target_scope_id":expected_scope,
            "scope_compiler_git_blob_sha":SCOPE_COMPILER_BLOB,
            "scope_complete":True,
            "scope_basis":scope_out.get("basis"),
        }
        for field,expected in expected_verify.items():
            if cert_verify.get(field)!=expected:
                raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_VERIFY_FIELD_MISMATCH:"+field)
        for field in ("pass","independent_verified"):
            if cert_verify.get(field) is not True:
                raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_VERIFY_PREMISE_UNPROVED:"+field)
        independent_id=cert_verify.get("independent_verifier_id")
        if not isinstance(independent_id,str) or not independent_id.strip():
            raise base.StepBindingAuthorityError("MATERIAL_TOTALITY_INDEPENDENT_VERIFIER_REQUIRED")

        return {
            **prior,
            "schema":SCHEMA,
            "v1_authenticated":True,
            "decision_outcome":"POSITIVE_CERTIFICATE",
            "positive_certification_authorized":True,
            "material_totality_proved":True,
            "material_totality_basis":scope_out.get("basis"),
            "material_totality_target_scope_id":expected_scope,
            "material_totality_certificate_path":cert_path,
            "material_totality_certificate_git_blob_sha":cert_blob,
            "material_totality_verification_path":verify_path,
            "material_totality_verification_git_blob_sha":verify_blob,
            "status":"PASS__AUTHENTICATED_POSITIVE_CERTIFICATE_WITH_COMPLETE_LOCAL_TOTALITY",
        }
    except Exception as exc:
        return _fail(step_id,type(exc).__name__+":"+str(exc),v1_verdict=prior)
