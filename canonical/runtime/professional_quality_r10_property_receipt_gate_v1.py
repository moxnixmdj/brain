"""Receipt-backed property-evidence gate for the R10 execution whole-leaf claim.

The upstream R10 proof-slot verifier establishes structural policy compliance.
That is necessary but not sufficient for property truth. This gate accepts a
property slot only when exact evidence bytes, an executable semantic verifier,
and an independent verification receipt are all content-addressed and the
verifier rerun matches the stored receipt.

A separate detection-completeness semantic receipt is mandatory. Known-defeater
enforcement alone is not detection completeness.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R10_PROPERTY_EVIDENCE_RECEIPT_V1"
PROTOCOL="PROFESSIONAL_R10_PROPERTY_EVIDENCE_VERIFIER_V1"
CLAIM_ID="205a864e7d7a56a14a46bb75923cc9b11126d479676d26d88803831da1197294"
LEAF_ID="PQ::R10_ANALYSIS_DECISION::EXECUTION"
DETECTION_SLOT="DEFEATER_DETECTION_COMPLETENESS"
REQUIRED_SLOTS=(
    "target_and_hard_constraints_frozen",
    "decision_state_lossless",
    "uncertainty_semantics_typed",
    "aggregation_and_risk_policy_precommitted",
    "veto_constraints_preserved",
    "model_or_analysis_multiplicity_resolved_or_escalated",
    "evidence_packet_complete",
    "stopping_rule_precommitted",
    "absolute_floor_not_inferred_from_weak_baseline",
)
ALLOWED_PROOF_MODES=frozenset({
    "KERNEL_CHECKED",
    "DECISION_PROCEDURE",
    "MODEL_CHECKED",
    "FORMAL_REDUCTION",
    "INDEPENDENT_REPLAY",
})

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _safe(root:Path,rel:Any)->Path|None:
    if not isinstance(rel,str) or not rel or rel.startswith("/"):
        return None
    p=Path(rel)
    if ".." in p.parts:
        return None
    out=(root/p).resolve()
    try:
        out.relative_to(root.resolve())
    except ValueError:
        return None
    return out

def _fail(*errors:str,**extra:Any)->dict[str,Any]:
    return {
        "pass":False,
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "whole_leaf_property_truth_proved":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }

def validate_property_slot(
    root:Path,
    slot:Mapping[str,Any],
    *,
    claim_id:str,
    expected_slot_id:str,
)->dict[str,Any]:
    root=root.resolve()
    errors:list[str]=[]
    if slot.get("status")!="PROVED_CURRENT":
        return _fail("SLOT_NOT_PROVED_CURRENT",slot_id=expected_slot_id)
    if slot.get("slot_id")!=expected_slot_id:
        return _fail("SLOT_ID_MISMATCH",slot_id=expected_slot_id)
    evidence=slot.get("evidence")
    verifier=slot.get("semantic_verifier")
    receipt_ref=slot.get("independent_verification")
    if not isinstance(evidence,Mapping):
        return _fail("EVIDENCE_REF_MISSING",slot_id=expected_slot_id)
    if not isinstance(verifier,Mapping):
        return _fail("SEMANTIC_VERIFIER_REF_MISSING",slot_id=expected_slot_id)
    if not isinstance(receipt_ref,Mapping):
        return _fail("INDEPENDENT_VERIFICATION_REF_MISSING",slot_id=expected_slot_id)

    refs={
        "evidence":evidence,
        "semantic_verifier":verifier,
        "independent_verification":receipt_ref,
    }
    resolved:dict[str,Path]={}
    for label,ref in refs.items():
        p=_safe(root,ref.get("path"))
        sha=ref.get("git_blob_sha")
        if p is None or not isinstance(sha,str) or not sha:
            errors.append(label.upper()+"_REF_INVALID")
            continue
        if not p.is_file():
            errors.append(label.upper()+"_FILE_MISSING")
            continue
        if _blob(p)!=sha:
            errors.append(label.upper()+"_BLOB_SHA_MISMATCH")
            continue
        resolved[label]=p
    if errors:
        return _fail(*errors,slot_id=expected_slot_id)

    try:
        spec=importlib.util.spec_from_file_location(
            "professional_r10_property_semantic_verifier_runtime",
            resolved["semantic_verifier"],
        )
        if spec is None or spec.loader is None:
            return _fail("SEMANTIC_VERIFIER_LOAD_SPEC_FAILED",slot_id=expected_slot_id)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verify_fn=getattr(module,"verify_property",None)
        if not callable(verify_fn):
            return _fail("SEMANTIC_VERIFIER_ENTRYPOINT_MISSING",slot_id=expected_slot_id)
        rerun=verify_fn(
            root=root,
            evidence_path=resolved["evidence"],
            claim_id=claim_id,
            leaf_id=LEAF_ID,
            slot_id=expected_slot_id,
        )
    except Exception as exc:
        return _fail("SEMANTIC_VERIFIER_EXCEPTION:"+type(exc).__name__,slot_id=expected_slot_id)

    if not isinstance(rerun,Mapping):
        return _fail("SEMANTIC_VERIFIER_RESULT_NOT_OBJECT",slot_id=expected_slot_id)
    if rerun.get("pass") is not True:
        return _fail("SEMANTIC_VERIFIER_REJECTED_EVIDENCE",slot_id=expected_slot_id)
    if rerun.get("claim_id")!=claim_id:
        errors.append("SEMANTIC_VERIFIER_CLAIM_MISMATCH")
    if rerun.get("leaf_id")!=LEAF_ID:
        errors.append("SEMANTIC_VERIFIER_LEAF_MISMATCH")
    if rerun.get("slot_id")!=expected_slot_id:
        errors.append("SEMANTIC_VERIFIER_SLOT_MISMATCH")
    if errors:
        return _fail(*errors,slot_id=expected_slot_id)

    result_sha=hashlib.sha256(
        json.dumps(rerun,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    ).hexdigest()
    try:
        receipt=json.loads(resolved["independent_verification"].read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        return _fail("INDEPENDENT_VERIFICATION_RECEIPT_INVALID_JSON",slot_id=expected_slot_id)
    if not isinstance(receipt,Mapping):
        return _fail("INDEPENDENT_VERIFICATION_RECEIPT_NOT_OBJECT",slot_id=expected_slot_id)

    checks=(
        (receipt.get("schema")==SCHEMA,"RECEIPT_SCHEMA_INVALID"),
        (receipt.get("verifier_protocol")==PROTOCOL,"RECEIPT_PROTOCOL_INVALID"),
        (receipt.get("pass") is True,"RECEIPT_PASS_NOT_TRUE"),
        (isinstance(receipt.get("status"),str) and receipt.get("status","").startswith("PASS"),"RECEIPT_STATUS_NOT_PASS"),
        (receipt.get("independent") is True,"RECEIPT_NOT_INDEPENDENT"),
        (receipt.get("property_claim_verified") is True,"RECEIPT_PROPERTY_CLAIM_NOT_VERIFIED"),
        (receipt.get("claim_id")==claim_id,"RECEIPT_CLAIM_MISMATCH"),
        (receipt.get("leaf_id")==LEAF_ID,"RECEIPT_LEAF_MISMATCH"),
        (receipt.get("slot_id")==expected_slot_id,"RECEIPT_SLOT_MISMATCH"),
        (receipt.get("proof_mode") in ALLOWED_PROOF_MODES,"RECEIPT_PROOF_MODE_INVALID"),
        (receipt.get("verifier_result_sha256")==result_sha,"RECEIPT_RERUN_RESULT_MISMATCH"),
        (receipt.get("errors")==[],"RECEIPT_ERRORS_NONEMPTY"),
        (receipt.get("terminal_credit_delta",0)==0,"RECEIPT_NONZERO_TERMINAL_CREDIT"),
    )
    for ok,error in checks:
        if not ok:
            errors.append(error)
    receipt_evidence=receipt.get("evidence") or {}
    if (
        receipt_evidence.get("path")!=evidence.get("path")
        or receipt_evidence.get("git_blob_sha")!=evidence.get("git_blob_sha")
    ):
        errors.append("RECEIPT_EVIDENCE_BINDING_MISMATCH")
    receipt_verifier=receipt.get("semantic_verifier") or {}
    if (
        receipt_verifier.get("path")!=verifier.get("path")
        or receipt_verifier.get("git_blob_sha")!=verifier.get("git_blob_sha")
    ):
        errors.append("RECEIPT_VERIFIER_BINDING_MISMATCH")
    if errors:
        return _fail(*errors,slot_id=expected_slot_id)

    return {
        "pass":True,
        "status":"PASS__EXECUTABLE_R10_PROPERTY_EVIDENCE_VERIFICATION",
        "claim_id":claim_id,
        "leaf_id":LEAF_ID,
        "slot_id":expected_slot_id,
        "verifier_result_sha256":result_sha,
        "proof_mode":receipt.get("proof_mode"),
        "whole_leaf_property_truth_proved":False,
        "terminal_credit_delta":0,
        "errors":[],
    }

def evaluate(
    *,
    repo_root:str|Path,
    claim_id:str,
    structural_verdict:Mapping[str,Any],
    property_slots:Mapping[str,Mapping[str,Any]],
    detection_completeness_slot:Mapping[str,Any]|None,
)->dict[str,Any]:
    root=Path(repo_root).resolve()
    if claim_id!=CLAIM_ID:
        return _fail("CLAIM_ID_MISMATCH",claim_id=claim_id)
    if not isinstance(structural_verdict,Mapping):
        return _fail("STRUCTURAL_VERDICT_INVALID",claim_id=claim_id)
    if structural_verdict.get("pass") is not True:
        return _fail("STRUCTURAL_POLICY_NOT_PASS",claim_id=claim_id)
    if structural_verdict.get("structural_policy_compliance_only") is not True:
        return _fail("STRUCTURAL_VERDICT_SCOPE_INVALID",claim_id=claim_id)
    if structural_verdict.get("underlying_fact_truth_authority") is not False:
        return _fail("STRUCTURAL_VERDICT_AUTHORITY_OVERCLAIM",claim_id=claim_id)
    if structural_verdict.get("whole_leaf_property_truth_proved") is not False:
        return _fail("STRUCTURAL_VERDICT_PROPERTY_OVERCLAIM",claim_id=claim_id)
    if structural_verdict.get("claim_id")!=claim_id or structural_verdict.get("leaf_id")!=LEAF_ID:
        return _fail("STRUCTURAL_VERDICT_SUBJECT_MISMATCH",claim_id=claim_id)
    structural_slots=structural_verdict.get("slot_results")
    if not isinstance(structural_slots,Mapping) or any(structural_slots.get(s) is not True for s in REQUIRED_SLOTS):
        return _fail("STRUCTURAL_SLOTS_INCOMPLETE",claim_id=claim_id)

    results:dict[str,Any]={}
    missing:list[str]=[]
    invalid:list[str]=[]
    for slot_id in REQUIRED_SLOTS:
        slot=property_slots.get(slot_id) if isinstance(property_slots,Mapping) else None
        if not isinstance(slot,Mapping):
            missing.append(slot_id)
            continue
        verdict=validate_property_slot(root,slot,claim_id=claim_id,expected_slot_id=slot_id)
        results[slot_id]=verdict
        if verdict.get("pass") is not True:
            invalid.append(slot_id)

    detection=None
    if isinstance(detection_completeness_slot,Mapping):
        detection=validate_property_slot(
            root,
            detection_completeness_slot,
            claim_id=claim_id,
            expected_slot_id=DETECTION_SLOT,
        )
    detection_ok=isinstance(detection,Mapping) and detection.get("pass") is True

    complete=not missing and not invalid and detection_ok
    if not complete:
        return {
            "pass":False,
            "status":"OPEN__R10_PROPERTY_EVIDENCE_OR_DETECTION_COMPLETENESS_REQUIRED",
            "claim_id":claim_id,
            "leaf_id":LEAF_ID,
            "property_slot_results":results,
            "missing_property_receipt_slots":missing,
            "invalid_property_receipt_slots":invalid,
            "detection_completeness_result":detection,
            "detection_completeness_proved":detection_ok,
            "whole_leaf_property_truth_proved":False,
            "execution_authority":False,
            "quality_authority":False,
            "acceptance_authority":False,
            "promotion_authority":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
            "incremental_spend_usd":0,
        }

    return {
        "pass":True,
        "status":"PASS__R10_WHOLE_LEAF_PROPERTY_TRUTH_RECEIPT_ENVELOPE_COMPLETE",
        "claim_id":claim_id,
        "leaf_id":LEAF_ID,
        "property_slot_results":results,
        "missing_property_receipt_slots":[],
        "invalid_property_receipt_slots":[],
        "detection_completeness_result":detection,
        "detection_completeness_proved":True,
        "whole_leaf_property_truth_proved":True,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }
