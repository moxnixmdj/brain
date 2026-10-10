"""Independent verifier for exact-instance R3 binding on the V7 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_VERIFY_V1"
ROOT_ID="R3_REALIZATION_OBSERVATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="fe360ed0f4f958f303ab4ba968c6782d5860f8e5"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
EVIDENCE_PATH="canonical/evidence/PROFESSIONAL_QUALITY_R3_V7_EXACT_REALIZATION_INSTANCE_20261010_V1.json"
EVIDENCE_BLOB="13e7e58b3621b3cabb7abdebe23689f3a72678d2"
RECEIPT_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_20261010_V2.json"
RECEIPT_BLOB="7149011b50c97e14906d4bba3c537cad846ec0fb"
VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_VERIFY_20261010_V2.json"
VERIFY_BLOB="4ba735698a530a1a7c42a528efd0e92ea8a30c9f"
SEM_SCOPE_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_SCOPE_20261010_V1.json"
SEM_SCOPE_BLOB="1edbd92b4e7b01591162d692f1d4c9b785b4c102"
SEM_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_VERIFY_20261010_V1.json"
SEM_VERIFY_BLOB="3c9a6f03c9dfb7597cdb7c5ca01e9eaf66a596e0"
RUN_CONTEXT="sha256:4e74da6a85ebf4662d88e770fed0b1c8ad3e9308c9830afe9605dbe458d8a1f0"
PRODUCER_EVIDENCE_SHA="9d9dc65dfb3d12f7f2e5737cfd6a4ddaafa7f7f423d88effaa4217382b5bccac"
RAW_BUNDLE_SHA="d617dc6a3dc28ebaa89c16ee1928eebc525143bf8e6f820d3fa13a24424b8978"
STEP_ID="RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"

def _blob(path:Path)->str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _read(root:Path,path:str,sha:str):
    p=(root/path).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None,"PATH_OUTSIDE_ROOT:"+path
    if not p.is_file() or p.is_symlink():return None,"FILE_INVALID:"+path
    if _blob(p)!=sha:return None,"BLOB_STALE:"+path
    try:doc=json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None,"JSON_INVALID:"+path
    return (doc,None) if isinstance(doc,dict) else (None,"DOCUMENT_INVALID:"+path)

def _fail(reason:str,**extra:Any):
    return {
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "root_id":ROOT_ID,"root_subject_binding_authority":False,
      "semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def verify(*,repo_root:str|Path|None=None):
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    b,e=_read(root,BINDING_PATH,BINDING_BLOB)
    if e:return _fail(e)
    if b.get("root_id")!=ROOT_ID:return _fail("BINDING_ROOT_INVALID")
    if (b.get("subject_kind"),b.get("subject_id"),b.get("subject_sha256"))!=("DECLARED_SYSTEM",SUBJECT_ID,SUBJECT_SHA):
        return _fail("BINDING_SUBJECT_TUPLE_INVALID")
    for field in ("root_subject_binding_authority","global_subject_identity_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if b.get(field) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+field)

    s,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
    if e:return _fail(e)
    if s.get("subject_id")!=SUBJECT_ID or s.get("subject_sha256")!=SUBJECT_SHA:
        return _fail("SUBJECT_IDENTITY_INVALID")

    refs=b.get("bridge_evidence") or {}
    expected={
      "exact_realization_instance":(EVIDENCE_PATH,EVIDENCE_BLOB),
      "render_step_binding":(RECEIPT_PATH,RECEIPT_BLOB),
      "render_step_verification":(VERIFY_PATH,VERIFY_BLOB),
    }
    for key,(p,sha) in expected.items():
        ref=refs.get(key)
        if not isinstance(ref,Mapping) or ref.get("path")!=p or ref.get("git_blob_sha")!=sha:
            return _fail("BRIDGE_REFERENCE_MISMATCH:"+key)

    evidence,e=_read(root,EVIDENCE_PATH,EVIDENCE_BLOB)
    if e:return _fail(e)
    receipt,e=_read(root,RECEIPT_PATH,RECEIPT_BLOB)
    if e:return _fail(e)
    stepv,e=_read(root,VERIFY_PATH,VERIFY_BLOB)
    if e:return _fail(e)
    sem,e=_read(root,SEM_SCOPE_PATH,SEM_SCOPE_BLOB)
    if e:return _fail(e)
    semv,e=_read(root,SEM_VERIFY_PATH,SEM_VERIFY_BLOB)
    if e:return _fail(e)

    for doc,name in ((evidence,"evidence"),(receipt,"receipt"),(stepv,"step_verify")):
        if doc.get("subject_id")!=SUBJECT_ID or doc.get("subject_sha256")!=SUBJECT_SHA:
            return _fail("SUBJECT_DRIFT:"+name)
        if doc.get("run_context_sha256")!=RUN_CONTEXT:
            return _fail("RUN_CONTEXT_DRIFT:"+name)
        if doc.get("step_id")!=STEP_ID:
            return _fail("STEP_ID_DRIFT:"+name)
        if doc.get("behavior_id")!=BEHAVIOR_ID:
            return _fail("BEHAVIOR_DRIFT:"+name)

    if receipt.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_STEP_RESULT_BINDING_V1":
        return _fail("STEP_RECEIPT_SCHEMA_INVALID")
    if receipt.get("result")!="PASS" or receipt.get("binding_proved") is not True:
        return _fail("STEP_RECEIPT_NOT_PASS")
    if receipt.get("evidence_sha256")!=PRODUCER_EVIDENCE_SHA:
        return _fail("STEP_RECEIPT_EVIDENCE_SHA_DRIFT")
    if receipt.get("raw_bundle_sha256")!=RAW_BUNDLE_SHA:
        return _fail("STEP_RECEIPT_BUNDLE_SHA_DRIFT")
    if receipt.get("renderer_version_transport_claim") is not False:
        return _fail("RENDERER_TRANSPORT_OVERCLAIM")

    if stepv.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_STEP_RESULT_BINDING_INDEPENDENT_VERIFICATION_V1":
        return _fail("STEP_VERIFY_SCHEMA_INVALID")
    if stepv.get("subject_git_blob_sha")!=RECEIPT_BLOB:
        return _fail("STEP_VERIFY_RECEIPT_BLOB_MISMATCH")
    for field in ("pass","independent_verified","semantic_preservation_verified","evidence_scope_verified","producer_verifier_distinct"):
        if stepv.get(field) is not True:return _fail("STEP_VERIFY_PREMISE_MISSING:"+field)
    if stepv.get("evidence_sha256")!=PRODUCER_EVIDENCE_SHA or stepv.get("raw_bundle_sha256")!=RAW_BUNDLE_SHA:
        return _fail("STEP_VERIFY_EVIDENCE_IDENTITY_DRIFT")
    if stepv.get("producer_id_observed")==stepv.get("independent_verifier_id"):
        return _fail("PRODUCER_VERIFIER_NOT_DISTINCT")

    artifacts=evidence.get("artifacts") or {}
    for field in ("source_docx_sha256","output_docx_sha256","source_pdf_sha256","output_pdf_sha256"):
        value=artifacts.get(field)
        if not isinstance(value,str) or len(value)!=64:return _fail("ARTIFACT_SHA_INVALID:"+field)
    if artifacts["source_docx_sha256"]==artifacts["output_docx_sha256"]:
        return _fail("SOURCE_OUTPUT_DOCX_IDENTICAL")
    if evidence.get("durable_raw_bundle",{}).get("sha256")!=RAW_BUNDLE_SHA:
        return _fail("DURABLE_BUNDLE_SHA_DRIFT")

    prod=evidence.get("producer") or {}
    sv=prod.get("structural_verdict") or {}
    vv=prod.get("visual_verdict") or {}
    if sv.get("pass") is not True or sv.get("changed_members")!=["word/document.xml"]:
        return _fail("PRODUCER_STRUCTURAL_VERDICT_INVALID")
    if vv.get("pass") is not True or vv.get("page_count")!=1 or vv.get("changed_page_count")!=1:
        return _fail("PRODUCER_VISUAL_VERDICT_INVALID")
    if not (0 < float(vv.get("max_pixel_fraction",1)) <= 0.025):
        return _fail("PIXEL_FRACTION_OUT_OF_BOUNDS")
    if not (0 < float(vv.get("max_bbox_fraction",1)) <= 0.1):
        return _fail("BBOX_FRACTION_OUT_OF_BOUNDS")

    replay=stepv.get("independent_render_replay") or {}
    if replay.get("localized_visible_change_pass") is not True or replay.get("producer_metric_match") is not True:
        return _fail("INDEPENDENT_RENDER_REPLAY_INVALID")
    if replay.get("page_count")!=1 or replay.get("page_size")!=[816,1056]:
        return _fail("INDEPENDENT_RENDER_GEOMETRY_INVALID")
    if float(replay.get("pixel_fraction",1))>0.025 or float(replay.get("bbox_fraction",1))>0.1:
        return _fail("INDEPENDENT_RENDER_THRESHOLD_VIOLATION")

    if not str(sem.get("status") or "").startswith("ACTIVE_SCOPED_PINNED_NATIVE_ARTIFACT_RENDER_REALIZATION_SEMANTICS"):
        return _fail("BACKGROUND_SEMANTIC_SCOPE_NOT_ACTIVE")
    if not str(semv.get("status") or "").startswith("PASS__"):
        return _fail("BACKGROUND_SEMANTIC_VERIFY_NOT_PASS")
    if "NO_GENERIC_RENDERER_VERSION_TRANSPORT" not in set((b.get("binding_scope") or {}).get("limitations") or []):
        return _fail("CURRENT_STACK_SCOPE_BOUNDARY_MISSING")
    if "NO_PINNED_2026_10_02_RENDER_STACK_IDENTITY_CLAIM" not in set((b.get("binding_scope") or {}).get("limitations") or []):
        return _fail("PINNED_STACK_NONCLAIM_MISSING")

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__R3_EXACT_REALIZATION_INSTANCE_BOUND_TO_V7_DECLARED_SYSTEM_SUBJECT",
      "root_id":ROOT_ID,"subject_kind":"DECLARED_SYSTEM","subject_id":SUBJECT_ID,
      "subject_sha256":SUBJECT_SHA,"subject_binding_git_blob_sha":BINDING_BLOB,
      "root_subject_binding_authority":True,
      "binding_scope_kind":"EXACT_SINGLE_V7_BOUND_DOCX_BOUNDED_TEXT_EDIT_REALIZATION_INSTANCE",
      "global_r3_root_closed":False,"generic_renderer_version_transport":False,
      "semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
