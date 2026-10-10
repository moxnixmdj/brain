"""Verify R3 V2: current V1 structural binding plus one exact real V7 render-step receipt."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

from canonical.runtime import professional_quality_r3_root_subject_binding_verify_v1 as base_v1
from canonical.runtime import professional_step_binding_authority_v1 as step_auth

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_VERIFY_V2"
ROOT_ID="R3_REALIZATION_OBSERVATION"
STEP_ID="RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json"
BINDING_BLOB="2fe91ecba3830641ed800d04b70279a3f84283bf"
EVIDENCE_PATH="canonical/evidence/PROFESSIONAL_QUALITY_R3_V7_EXACT_REALIZATION_INSTANCE_20261010_V1.json"
EVIDENCE_BLOB="13e7e58b3621b3cabb7abdebe23689f3a72678d2"
RECEIPT_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_20261010_V3.json"
RECEIPT_BLOB="8a524bd90cee783d9d342b80a95b990d23a413e0"
VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_VERIFY_20261010_V3.json"
VERIFY_BLOB="734f88f5d201e778f59133c9e22f29ae4d451121"
BASE_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json"
BASE_VERIFY_BLOB="92cacbd5f7b37cb515db9ebbc3685c961fc9e34e"
BUNDLE_SHA="d617dc6a3dc28ebaa89c16ee1928eebc525143bf8e6f820d3fa13a24424b8978"
RUN_CONTEXT="sha256:4e74da6a85ebf4662d88e770fed0b1c8ad3e9308c9830afe9605dbe458d8a1f0"

def _blob(p:Path)->str:
    d=p.read_bytes()
    return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _read(root:Path,path:str,sha:str):
    p=(root/path).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None,"OUTSIDE_ROOT:"+path
    if not p.is_file() or p.is_symlink():return None,"FILE_INVALID:"+path
    if _blob(p)!=sha:return None,"BLOB_STALE:"+path
    try:d=json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None,"JSON_INVALID:"+path
    return (d,None) if isinstance(d,dict) else (None,"DOCUMENT_INVALID:"+path)

def _fail(reason:str,**extra:Any):
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "root_id":ROOT_ID,"root_subject_binding_authority":False,
      "real_task_render_step_receipt_bound":False,"global_r3_root_closed":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def verify(*,repo_root:str|Path|None=None):
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]

    base=base_v1.verify(repo_root=root)
    if base.get("pass") is not True or base.get("root_subject_binding_authority") is not True:
        return _fail("BASE_V1_BINDING_NOT_VERIFIED",base=base)
    if base.get("real_task_step_receipt_proved") is not False or base.get("global_r3_root_closed") is not False:
        return _fail("BASE_V1_TRUTH_BOUNDARY_DRIFT")

    base_receipt,e=_read(root,BASE_VERIFY_PATH,BASE_VERIFY_BLOB)
    if e:return _fail(e)
    if "NO_REAL_TASK_RENDER_STEP_RECEIPT" not in set(base_receipt.get("hard_nonclaims") or []):
        return _fail("BASE_V1_REAL_TASK_NONCLAIM_MISSING")

    binding,e=_read(root,BINDING_PATH,BINDING_BLOB)
    if e:return _fail(e)
    if binding.get("root_id")!=ROOT_ID or binding.get("subject_id")!=SUBJECT_ID or binding.get("subject_sha256")!=SUBJECT_SHA:
        return _fail("V2_BINDING_IDENTITY_INVALID")
    sup=binding.get("supersedes") or {}
    if sup.get("git_blob_sha")!=base.get("subject_binding_git_blob_sha"):
        return _fail("V2_DOES_NOT_EXACTLY_SUPERSEDE_VERIFIED_V1")
    for f in ("root_subject_binding_authority","real_task_render_step_receipt_bound","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if binding.get(f) is not False:return _fail("V2_SELF_AUTHORITY_FORBIDDEN:"+f)

    evidence,e=_read(root,EVIDENCE_PATH,EVIDENCE_BLOB)
    if e:return _fail(e)
    receipt,e=_read(root,RECEIPT_PATH,RECEIPT_BLOB)
    if e:return _fail(e)
    step_verify,e=_read(root,VERIFY_PATH,VERIFY_BLOB)
    if e:return _fail(e)

    exact=binding.get("exact_instance") or {}
    for key,path,sha in (
      ("evidence",EVIDENCE_PATH,EVIDENCE_BLOB),
      ("step_receipt",RECEIPT_PATH,RECEIPT_BLOB),
      ("step_verification",VERIFY_PATH,VERIFY_BLOB),
    ):
        row=exact.get(key) or {}
        if row.get("path")!=path or row.get("git_blob_sha")!=sha:return _fail("V2_EXACT_REF_MISMATCH:"+key)
    if exact.get("run_context_sha256")!=RUN_CONTEXT or exact.get("raw_bundle_sha256")!=BUNDLE_SHA:
        return _fail("V2_EXACT_IDENTITY_MISMATCH")

    context=step_auth.run_context_digest(
      goal=evidence.get("goal"),
      decision_payload=evidence.get("decision_payload"),
      artifact_paths=evidence.get("artifact_paths"),
      hard_defect_profile_id=evidence.get("hard_defect_profile_id"),
      detected_triggers=evidence.get("detected_triggers"),
    )
    if context!=RUN_CONTEXT:return _fail("RUN_CONTEXT_RECOMPUTE_MISMATCH",actual=context)

    auth=step_auth.authenticate_step_binding(
      {"receipt":{"path":RECEIPT_PATH,"git_blob_sha":RECEIPT_BLOB},
       "verification":{"path":VERIFY_PATH,"git_blob_sha":VERIFY_BLOB}},
      behavior_id=BEHAVIOR_ID,subject_id=SUBJECT_ID,subject_sha256=SUBJECT_SHA,
      step_id=STEP_ID,run_context_sha256=RUN_CONTEXT,repo_root=root,
    )
    if auth.get("pass") is not True:return _fail("STEP_AUTHENTICATION_FAILED",step_authentication=auth)

    if evidence.get("behavior_id")!=BEHAVIOR_ID or evidence.get("subject_id")!=SUBJECT_ID or evidence.get("subject_sha256")!=SUBJECT_SHA:
        return _fail("EVIDENCE_SUBJECT_OR_BEHAVIOR_DRIFT")
    if evidence.get("step_id")!=STEP_ID or evidence.get("run_context_sha256")!=RUN_CONTEXT:
        return _fail("EVIDENCE_STEP_OR_CONTEXT_DRIFT")
    if (evidence.get("durable_raw_bundle") or {}).get("sha256")!=BUNDLE_SHA:
        return _fail("RAW_BUNDLE_SHA_DRIFT")

    producer=evidence.get("producer") or {}
    visual=producer.get("visual_verdict") or {}
    structural=producer.get("structural_verdict") or {}
    if structural.get("pass") is not True or structural.get("changed_members")!=["word/document.xml"]:
        return _fail("STRUCTURAL_INSTANCE_INVALID")
    if visual.get("pass") is not True or visual.get("page_count")!=1 or visual.get("changed_page_count")!=1:
        return _fail("VISUAL_INSTANCE_INVALID")
    if not (0.0 < float(visual.get("max_pixel_fraction",1.0)) <= 0.025):
        return _fail("PIXEL_LOCALIZATION_INVALID")
    if not (0.0 < float(visual.get("max_bbox_fraction",1.0)) <= 0.1):
        return _fail("BBOX_LOCALIZATION_INVALID")

    replay=step_verify.get("exact_instance") or {}
    if replay.get("visible_localized_change_pass") is not True or replay.get("producer_metric_match") is not True:
        return _fail("INDEPENDENT_INSTANCE_REPLAY_INVALID")
    if step_verify.get("producer_verifier_distinct") is not True:
        return _fail("PRODUCER_VERIFIER_DISTINCTNESS_UNPROVED")

    limits=set((binding.get("binding_scope") or {}).get("limitations") or [])
    for req in ("EXACT_SINGLE_INSTANCE_ONLY","NO_GENERIC_RENDERER_VERSION_TRANSPORT","NO_GLOBAL_R3_ROOT_CLOSURE","NO_SAME_SUBJECT_COMPOSITION_PASS"):
        if req not in limits:return _fail("V2_LIMITATION_MISSING:"+req)

    return {"schema":SCHEMA,"pass":True,
      "status":"PASS__R3_V2_V7_STRUCTURAL_BINDING_PLUS_ONE_EXACT_REAL_TASK_RENDER_RECEIPT",
      "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA,
      "subject_binding_git_blob_sha":BINDING_BLOB,
      "root_subject_binding_authority":True,"real_task_render_step_receipt_bound":True,
      "exact_real_task_receipt_count":1,"global_r3_root_closed":False,
      "generic_renderer_version_transport":False,
      "semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
