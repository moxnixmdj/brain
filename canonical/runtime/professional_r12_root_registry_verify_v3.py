"""Executable verifier for the stable R12 three-root candidate registry.

V3 advances the previously verified V2 registry state only if:
- the stable mission-authority registry guard accepts the exact registry;
- CC_R1, CC_R2, and CC_R3 are all PROVED_CURRENT;
- every proved slot reruns its content-addressed semantic verifier;
- every independent receipt binds the exact rerun result; and
- the exact frozen R12 claim remains unchanged.

This establishes R4 proof closure for this exact property claim only. It does
not by itself mint R12 semantic property truth or any quality/terminal credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import coverage_root_certificate_registry_guard_v2 as guard
from canonical.runtime.coverage_root_semantic_receipt_v1 import validate_semantic_root_slot

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_ROOT_REGISTRY_VERIFY_V3"
REGISTRY_PATH="canonical/governance/COVERAGE_ROOT_REGISTRY_PROFESSIONAL_R12_SEMANTIC_20261011_V3.json"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
MISSION_AUTHORITY_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_AUTHORITY_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
MISSION_POINTER_PATH="canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
EXPECTED_PROVED=[
    "CC_R1_REALITY_CONTAINMENT_V1",
    "CC_R2_MISSION_SOUNDNESS_V1",
    "CC_R3_TERMINAL_CLOSURE_V1",
]
EXPECTED_OPEN=[]


def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def _fail(*errors:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "proved_root_count":0,
        "open_root_count":3,
        "r4_proof_closure":False,
        "semantic_property_truth_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }


def evaluate(registry:Mapping[str,Any],*,repo_root:Path)->dict[str,Any]:
    root=repo_root.resolve()
    errors=[]
    try:
        pointer=json.loads((root/MISSION_POINTER_PATH).read_text(encoding="utf-8"))
        authority_path=root/MISSION_AUTHORITY_PATH
        authority=json.loads(authority_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail("MISSION_BINDING_LOAD_FAILED")

    if _blob(authority_path)!=MISSION_AUTHORITY_BLOB:
        return _fail("MISSION_AUTHORITY_BLOB_DRIFT")

    base=guard.validate(
        registry,
        current_mission_pointer=pointer,
        current_mission_authority=authority,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB,
    )
    if base.get("pass") is not True:
        errors.extend("REGISTRY:"+str(x) for x in base.get("errors") or ["INVALID"])

    active=registry.get("active_claim")
    if not isinstance(active,Mapping):
        errors.append("ACTIVE_CLAIM_MISSING")
        active={}
    if active.get("claim_id")!=CLAIM_ID:
        errors.append("ACTIVE_R12_CLAIM_ID_DRIFT")

    ref=active.get("claim_reference") or {}
    if not isinstance(ref,Mapping):
        errors.append("ACTIVE_CLAIM_REFERENCE_MISSING")
    else:
        p=root/str(ref.get("path") or "")
        if not p.is_file() or p.is_symlink():
            errors.append("ACTIVE_CLAIM_FILE_MISSING")
        elif _blob(p)!=ref.get("git_blob_sha"):
            errors.append("ACTIVE_CLAIM_BLOB_MISMATCH")
        else:
            try:
                frozen=json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                frozen={}
                errors.append("ACTIVE_CLAIM_JSON_INVALID")
            for key in (
                "claim_id","claim_kind","mission_blob_sha","scope_sha256",
                "target_predicate_sha256","semantics_sha256","epoch","authority_id",
            ):
                if frozen.get(key)!=active.get(key):
                    errors.append("ACTIVE_CLAIM_REFERENCE_MISMATCH:"+key)

    semantic_results={}
    for slot in registry.get("certificate_slots") or []:
        if not isinstance(slot,Mapping):
            continue
        if slot.get("status")=="PROVED_CURRENT":
            result=validate_semantic_root_slot(root,slot,active)
            rid=str(slot.get("root_id"))
            semantic_results[rid]=result
            if result.get("pass") is not True:
                errors.append("SEMANTIC_ROOT_REPLAY_FAILED:"+rid)

    proved=list(base.get("proved_root_ids") or [])
    opened=list(base.get("open_root_ids") or [])
    if proved!=EXPECTED_PROVED:
        errors.append("PROVED_ROOT_SET_DRIFT")
    if opened!=EXPECTED_OPEN:
        errors.append("OPEN_ROOT_SET_DRIFT")
    if base.get("r4_proof_closure") is not True:
        errors.append("R4_PROOF_CLOSURE_NOT_PROVED")
    if registry.get("currently_proved_root_certificates")!=3:
        errors.append("PROVED_ROOT_COUNT_DRIFT")
    if registry.get("currently_open_root_certificates")!=0:
        errors.append("OPEN_ROOT_COUNT_DRIFT")
    if registry.get("r4_proof_closure") is not True:
        errors.append("REGISTRY_R4_FLAG_NOT_TRUE")
    if registry.get("exact_remaining_root") is not None:
        errors.append("UNEXPECTED_REMAINING_ROOT")
    if registry.get("exact_remaining_obligation") is not None:
        errors.append("UNEXPECTED_REMAINING_OBLIGATION")

    if errors:
        return _fail(*errors,semantic_root_results=semantic_results)

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__STABLE_R12_ROOT_REGISTRY__ALL_THREE_ROOTS_EXECUTABLY_PROVED__R4_PROOF_CLOSURE_TRUE__ZERO_PROPERTY_CREDIT",
        "claim_id":CLAIM_ID,
        "proved_root_ids":proved,
        "open_root_ids":opened,
        "proved_root_count":3,
        "open_root_count":0,
        "r4_proof_closure":True,
        "semantic_root_results":semantic_results,
        "semantic_property_truth_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "errors":[],
    }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    p=root/REGISTRY_PATH
    if not p.is_file() or p.is_symlink():
        return _fail("REGISTRY_FILE_MISSING")
    try:
        registry=json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _fail("REGISTRY_JSON_INVALID")
    if not isinstance(registry,dict):
        return _fail("REGISTRY_NOT_OBJECT")
    return evaluate(registry,repo_root=root)
