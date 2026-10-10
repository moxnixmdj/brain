"""Fail-closed verifier for one bounded V7 professional R3 realization witness.

This verifies evidence identity and scope only. It does not rerun LibreOffice/Poppler
and therefore requires a separately content-addressed independent public-runner
verification before any R3 root-subject binding can be promoted.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import professional_step_binding_authority_v1 as step_auth

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R3_V7_REALIZATION_WITNESS_VERIFY_V1"
WITNESS_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R3_V7_REALIZATION_WITNESS_V1"
SUBJECT_KIND="DECLARED_SYSTEM"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
PROFILE_BLOB="f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
STEP_ID="RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
CURRENT_RENDER_STACK={
    "libreoffice_core":"4:24.2.7-0ubuntu0.24.04.7",
    "poppler_utils":"24.02.0-1ubuntu9.10",
    "python-docx":"1.2.0",
    "openpyxl":"3.1.5",
    "python-pptx":"1.0.2",
    "pypdf":"6.19.0",
    "Pillow":"12.3.0",
}
PREDECESSOR_RENDER_STACK={
    "libreoffice_core":"4:24.2.7-0ubuntu0.24.04.6",
    "poppler_utils":"24.02.0-1ubuntu9.9",
}
B64_FIELDS=(
    ("source_artifact_b64","source_artifact_sha256"),
    ("output_artifact_b64","output_artifact_sha256"),
    ("source_audience_view_png_b64","source_audience_view_png_sha256"),
    ("output_audience_view_png_b64","output_audience_view_png_sha256"),
)

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def _hash(data:bytes)->str:
    return sha256(data).hexdigest()

def _base(status:str,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,
        "root_id":"R3_REALIZATION_OBSERVATION",
        "root_subject_binding_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return _base("FAIL_CLOSED",reason=reason,**extra)

def verify_witness(doc:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(doc,Mapping):
        return _fail("WITNESS_NOT_OBJECT")
    if doc.get("schema")!=WITNESS_SCHEMA:
        return _fail("WITNESS_SCHEMA_INVALID")
    if (doc.get("subject_kind"),doc.get("subject_id"),doc.get("subject_sha256")) != (
        SUBJECT_KIND,SUBJECT_ID,SUBJECT_SHA256
    ):
        return _fail("SUBJECT_TUPLE_MISMATCH")
    if doc.get("subject_git_blob_sha")!=SUBJECT_BLOB or doc.get("profile_git_blob_sha")!=PROFILE_BLOB:
        return _fail("SUBJECT_OR_PROFILE_BLOB_MISMATCH")
    if doc.get("behavior_id")!=BEHAVIOR_ID or doc.get("step_id")!=STEP_ID:
        return _fail("BEHAVIOR_OR_STEP_MISMATCH")
    if doc.get("format")!="pdf":
        return _fail("FORMAT_OUTSIDE_CURRENT_WITNESS_SCOPE")
    if not isinstance(doc.get("seed"),int) or isinstance(doc.get("seed"),bool):
        return _fail("SEED_INVALID")

    decoded={}
    for b64_field,sha_field in B64_FIELDS:
        raw=doc.get(b64_field)
        expected=doc.get(sha_field)
        if not isinstance(raw,str) or not isinstance(expected,str) or len(expected)!=64:
            return _fail("CONTENT_ADDRESS_FIELD_INVALID:"+b64_field)
        try:
            value=base64.b64decode(raw.encode("ascii"),validate=True)
        except Exception:
            return _fail("BASE64_INVALID:"+b64_field)
        if not value:
            return _fail("EMPTY_BOUND_BYTES:"+b64_field)
        if _hash(value)!=expected:
            return _fail("CONTENT_ADDRESS_MISMATCH:"+b64_field)
        decoded[b64_field]=value

    if decoded["source_artifact_b64"]==decoded["output_artifact_b64"]:
        return _fail("NO_ARTIFACT_CHANGE")
    if decoded["source_audience_view_png_b64"]==decoded["output_audience_view_png_b64"]:
        return _fail("NO_AUDIENCE_VIEW_CHANGE")

    structural=doc.get("structural_verdict")
    visual=doc.get("render_verdict")
    if not isinstance(structural,Mapping) or structural.get("pass") is not True:
        return _fail("STRUCTURAL_VERDICT_NOT_PASS")
    if not isinstance(visual,Mapping) or visual.get("pass") is not True or visual.get("reason")!="PASS":
        return _fail("RENDER_VERDICT_NOT_PASS")
    if visual.get("page_count")!=1 or not isinstance(visual.get("changed_page_count"),int) or visual.get("changed_page_count",0)<1:
        return _fail("RENDER_PAGE_EVIDENCE_INVALID")
    for field,limit in (("max_pixel_fraction",0.025),("max_bbox_fraction",0.10)):
        value=visual.get(field)
        if not isinstance(value,(int,float)) or isinstance(value,bool) or value<0 or value>limit:
            return _fail("RENDER_BOUND_EXCEEDED:"+field)

    stack=doc.get("render_stack")
    if not isinstance(stack,Mapping):
        return _fail("RENDER_STACK_INVALID")
    for key,value in CURRENT_RENDER_STACK.items():
        if stack.get(key)!=value:
            return _fail("CURRENT_RENDER_STACK_MISMATCH:"+key)
    if stack.get("predecessor_verified_libreoffice_core")!=PREDECESSOR_RENDER_STACK["libreoffice_core"]:
        return _fail("PREDECESSOR_LIBREOFFICE_IDENTITY_MISSING")
    if stack.get("predecessor_verified_poppler_utils")!=PREDECESSOR_RENDER_STACK["poppler_utils"]:
        return _fail("PREDECESSOR_POPPLER_IDENTITY_MISSING")
    if stack.get("version_transport_claimed") is not False or stack.get("current_stack_requires_fresh_replay") is not True:
        return _fail("VERSION_TRANSPORT_BOUNDARY_INVALID")

    scope=doc.get("scope")
    required_false=(
        "arbitrary_semantic_target_correctness",
        "whole_contract_scope_equivalence",
        "global_r3_root_closure",
        "quality_authority",
        "terminal_authority",
    )
    if not isinstance(scope,Mapping) or scope.get("bounded_generated_explicit_low_level_text_edit_only") is not True:
        return _fail("WITNESS_SCOPE_INVALID")
    for field in required_false:
        if scope.get(field) is not False:
            return _fail("WITNESS_SCOPE_OVERCLAIM:"+field)

    run_context=step_auth.run_context_digest(
        goal=doc.get("goal"),
        decision_payload=doc.get("decision_payload"),
        artifact_paths=doc.get("artifact_paths"),
        hard_defect_profile_id=doc.get("hard_defect_profile_id"),
        detected_triggers=doc.get("detected_triggers"),
    )
    if doc.get("run_context_sha256")!=run_context:
        return _fail("RUN_CONTEXT_DIGEST_MISMATCH")

    evidence_sha=doc.get("evidence_sha256")
    if not isinstance(evidence_sha,str) or len(evidence_sha)!=64:
        return _fail("EVIDENCE_SHA256_INVALID")
    core=dict(doc)
    core.pop("evidence_sha256",None)
    if _hash(_canon(core))!=evidence_sha:
        return _fail("EVIDENCE_DIGEST_MISMATCH")

    return _base(
        "PASS__R3_V7_REALIZATION_WITNESS_CONTENT_AND_SCOPE_VALID",
        passed=True,
        subject_id=SUBJECT_ID,
        subject_sha256=SUBJECT_SHA256,
        run_context_sha256=run_context,
        evidence_sha256=evidence_sha,
        source_artifact_sha256=doc.get("source_artifact_sha256"),
        output_artifact_sha256=doc.get("output_artifact_sha256"),
        output_audience_view_png_sha256=doc.get("output_audience_view_png_sha256"),
        public_replay_still_required=True,
    )
