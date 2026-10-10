"""Minimal content-addressed authority kernel for professional profile step results.

This kernel does not execute professional work and grants no semantic, quality,
acceptance, promotion, or terminal authority.  It authenticates that one
load-bearing profile step result is bound to the exact behavior, declared-system
subject, run context, and independent verification receipt.

A caller-supplied string such as {"STEP": "PASS"} has zero authority here.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_STEP_BINDING_AUTHORITY_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_STEP_RESULT_BINDING_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_STEP_RESULT_BINDING_INDEPENDENT_VERIFICATION_V1"

ALLOWED_REF_PREFIXES=(
    "canonical/governance/",
    "canonical/verification/",
    "canonical/evidence/",
)

class StepBindingAuthorityError(ValueError):
    pass

def canon(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def digest(value:Any)->str:
    return "sha256:"+sha256(canon(value).encode("utf-8")).hexdigest()

def git_blob_sha(path:Path)->str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _bound_json(ref:Any,*,repo_root:Path,prefixes:tuple[str,...])->tuple[dict[str,Any],str,str]:
    if not isinstance(ref,Mapping):
        raise StepBindingAuthorityError("BOUND_REF_REQUIRED")
    rel=str(ref.get("path") or "").strip()
    expected=str(ref.get("git_blob_sha") or "").strip()
    p=Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise StepBindingAuthorityError("BOUND_PATH_INVALID")
    if not any(rel.startswith(prefix) for prefix in prefixes):
        raise StepBindingAuthorityError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")
    base=repo_root.resolve(strict=True)
    full=base/p
    resolved=full.resolve(strict=False)
    if not any(resolved.is_relative_to((base/prefix).resolve(strict=False)) for prefix in prefixes):
        raise StepBindingAuthorityError("BOUND_RESOLVED_PATH_OUTSIDE_ALLOWED_SCOPE")
    if not full.is_file() or full.is_symlink():
        raise StepBindingAuthorityError("BOUND_FILE_INVALID:"+rel)
    actual=git_blob_sha(full)
    if actual!=expected:
        raise StepBindingAuthorityError("BOUND_BLOB_DRIFT:"+rel)
    try:
        doc=json.loads(full.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StepBindingAuthorityError("BOUND_JSON_INVALID:"+rel) from exc
    if not isinstance(doc,dict):
        raise StepBindingAuthorityError("BOUND_JSON_NOT_OBJECT:"+rel)
    return doc,rel,actual

def run_context_digest(*,goal:str,decision_payload:Mapping[str,Any],artifact_paths:Any,hard_defect_profile_id:Any,detected_triggers:Any)->str:
    """Bind step receipts to the externally supplied run inputs that survive target auth."""
    basis={
        "goal":goal,
        "decision_payload":dict(decision_payload),
        "artifact_paths":artifact_paths,
        "hard_defect_profile_id":hard_defect_profile_id,
        "detected_triggers":detected_triggers,
    }
    return digest(basis)

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
    base={
        "schema":SCHEMA,
        "pass":False,
        "step_id":step_id,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }
    if not isinstance(binding,Mapping):
        return {**base,"status":"OPEN__PROFESSIONAL_STEP_BINDING_REQUIRED"}
    try:
        root=Path(repo_root).resolve(strict=True)
        receipt,receipt_path,receipt_blob=_bound_json(
            binding.get("receipt"),repo_root=root,prefixes=ALLOWED_REF_PREFIXES
        )
        verification,verification_path,verification_blob=_bound_json(
            binding.get("verification"),repo_root=root,prefixes=("canonical/verification/",)
        )
        if receipt.get("schema")!=RECEIPT_SCHEMA:
            raise StepBindingAuthorityError("STEP_BINDING_SCHEMA_INVALID")
        required_receipt={
            "behavior_id":behavior_id,
            "subject_id":subject_id,
            "subject_sha256":subject_sha256,
            "step_id":step_id,
            "run_context_sha256":run_context_sha256,
            "result":"PASS",
        }
        for field,expected in required_receipt.items():
            if receipt.get(field)!=expected:
                raise StepBindingAuthorityError("STEP_BINDING_FIELD_MISMATCH:"+field)
        evidence_sha=receipt.get("evidence_sha256")
        if not isinstance(evidence_sha,str) or len(evidence_sha)!=64:
            raise StepBindingAuthorityError("STEP_BINDING_EVIDENCE_SHA256_INVALID")
        producer_id=receipt.get("producer_id")
        if not isinstance(producer_id,str) or not producer_id.strip():
            raise StepBindingAuthorityError("STEP_BINDING_PRODUCER_ID_REQUIRED")
        if receipt.get("binding_proved") is not True:
            raise StepBindingAuthorityError("STEP_BINDING_PROOF_MISSING")
        if verification.get("schema")!=VERIFY_SCHEMA:
            raise StepBindingAuthorityError("STEP_BINDING_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha")!=receipt_blob:
            raise StepBindingAuthorityError("STEP_BINDING_VERIFY_SUBJECT_MISMATCH")
        for field,expected in {
            "behavior_id":behavior_id,
            "subject_id":subject_id,
            "subject_sha256":subject_sha256,
            "step_id":step_id,
            "run_context_sha256":run_context_sha256,
            "result":"PASS",
            "evidence_sha256":evidence_sha,
        }.items():
            if verification.get(field)!=expected:
                raise StepBindingAuthorityError("STEP_BINDING_VERIFY_FIELD_MISMATCH:"+field)
        for field in ("pass","independent_verified","semantic_preservation_verified","evidence_scope_verified"):
            if verification.get(field) is not True:
                raise StepBindingAuthorityError("STEP_BINDING_VERIFY_PREMISE_UNPROVED:"+field)
        verifier_id=verification.get("independent_verifier_id")
        if not isinstance(verifier_id,str) or not verifier_id.strip():
            raise StepBindingAuthorityError("STEP_BINDING_VERIFIER_ID_REQUIRED")
        if verifier_id.strip()==producer_id.strip():
            raise StepBindingAuthorityError("STEP_BINDING_PRODUCER_VERIFIER_NOT_INDEPENDENT")
        return {
            **base,
            "pass":True,
            "status":"PASS__PROFESSIONAL_STEP_RESULT_AUTHENTICATED",
            "result":"PASS",
            "run_context_sha256":run_context_sha256,
            "evidence_sha256":evidence_sha,
            "producer_id":producer_id.strip(),
            "independent_verifier_id":verifier_id.strip(),
            "receipt_path":receipt_path,
            "receipt_git_blob_sha":receipt_blob,
            "verification_path":verification_path,
            "verification_git_blob_sha":verification_blob,
        }
    except Exception as exc:
        return {
            **base,
            "status":"FAIL_CLOSED__PROFESSIONAL_STEP_BINDING_INVALID",
            "reason":type(exc).__name__+":"+str(exc),
        }
