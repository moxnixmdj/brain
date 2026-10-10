"""Independent verifier for R3 realization/observation binding on the V7 professional subject."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R3_REALIZATION_OBSERVATION"
STEP_ID="RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="c49c120a61620d400e372884266b63ec34a054d2"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REFS={
 "execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "proof_bound_step_verification":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "r3_semantic_scope":("canonical/governance/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_SCOPE_20261010_V1.json","1edbd92b4e7b01591162d692f1d4c9b785b4c102"),
 "r3_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_VERIFY_20261010_V1.json","3c9a6f03c9dfb7597cdb7c5ca01e9eaf66a596e0"),
 "native_render_preflight":("canonical/governance/NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1.json","b5ddc896811875b59840959e27dbb515265fc9f8"),
 "native_render_public_verification":("canonical/verification/NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json","1a0b4ca6627aaf28eb25f6990682e87319d14d6d"),
}
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND",
 "V7_RENDER_AND_OBSERVATION_STEP_IS_CONTENT_ADDRESSED_AND_INDEPENDENTLY_VERIFIED_BEFORE_INTERNAL_PASS_DERIVATION",
 "R3_SUPPORT_IS_LIMITED_TO_THE_EXISTING_PINNED_NATIVE_RENDER_REALIZATION_SCOPE",
 "EXACT_ARTIFACT_BYTES_AND_AUDIENCE_VIEW_EVIDENCE_MUST_BE_BOUND_BY_THE_STEP_EVIDENCE_AND_INDEPENDENT_SCOPE_VERIFICATION",
 "PINNED_NATIVE_RENDER_SCOPE_REUSES_LIBREOFFICE_POPPLER_AND_HIDDEN_STRUCTURAL_ORACLE_BOUNDARIES",
 "ACTUAL_V7_R3_EXECUTION_REQUIRES_A_FRESH_RUN_CONTEXT_BOUND_PROFESSIONAL_STEP_RECEIPT",
 "CALLER_SUPPLIED_RENDER_STEP_PASS_HAS_ZERO_AUTHORITY",
}
REQUIRED_LIMITS={
 "NO_REAL_TASK_RENDER_STEP_RECEIPT_FROM_THIS_BINDING",
 "NO_ARBITRARY_SEMANTIC_TARGET_CORRECTNESS",
 "NO_WHOLE_OPEN_ENDED_NATIVE_ARTIFACT_CONTRACT_SCOPE_EQUIVALENCE",
 "NO_ALL_RENDERER_OR_ENVIRONMENT_INVARIANCE",
 "NO_GLOBAL_R3_ROOT_CLOSURE",
 "NO_GLOBAL_R3_SEMANTIC_LEAF_CLOSURE",
 "NO_SAME_SUBJECT_COMPOSITION_PASS",
 "NO_LIVE_DEFAULT_PROMOTION",
}
NATIVE_RUNTIME_BLOB="39374e775d54cdc58315d7a1f877d834282a64f7"
ROUTER_V7_BLOB="765b5994c2fcb5eb669b5fd0d989cc79c1609908"
STEP_AUTH_BLOB="27f3c137dae7f00925083a0824d008c2b4d10f0a"

def _blob(p:Path)->str:
    d=p.read_bytes(); return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

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
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,"root_id":ROOT_ID,
      "root_subject_binding_authority":False,"semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def evaluate_documents(binding:Mapping[str,Any],subject:Mapping[str,Any],docs:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
    if binding.get("schema")!=BINDING_SCHEMA or binding.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
    if (binding.get("subject_kind"),binding.get("subject_id"),binding.get("subject_sha256"))!=("DECLARED_SYSTEM",SUBJECT_ID,SUBJECT_SHA256):
        return _fail("SUBJECT_TUPLE_MISMATCH")
    if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
    comps={(r.get("path"),r.get("git_blob_sha")) for r in ((subject.get("system_material") or {}).get("components") or []) if isinstance(r,Mapping)}
    if ("canonical/runtime/professional_quality_p1_router_v7.py",ROUTER_V7_BLOB) not in comps:return _fail("V7_ROUTER_NOT_IN_SUBJECT")
    if ("canonical/runtime/professional_step_binding_authority_v1.py",STEP_AUTH_BLOB) not in comps:return _fail("STEP_AUTHORITY_NOT_IN_SUBJECT")
    for f in ("global_subject_identity_authority","root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if binding.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN",field=f)
    if binding.get("actual_v7_step_receipt_required_for_execution") is not True:return _fail("FRESH_STEP_RECEIPT_REQUIREMENT_MISSING")
    refs=binding.get("bridge_evidence") or {}
    for key,(path,sha) in REFS.items():
        row=refs.get(key)
        if not isinstance(row,Mapping) or row.get("path")!=path or row.get("git_blob_sha")!=sha:return _fail("BRIDGE_REF_MISMATCH",ref=key)

    profile=docs["execution_profile"]
    if STEP_ID not in set(profile.get("steps") or []):return _fail("V7_PROFILE_RENDER_STEP_MISSING")
    pv=docs["proof_bound_step_verification"]
    if (pv.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_STEP_BINDING_REPLAY_INSUFFICIENT")
    former=set(pv.get("formerly_self_attested_steps") or [])
    if STEP_ID not in former:return _fail("RENDER_STEP_NOT_PROOF_BOUND")
    proves=set(pv.get("proves") or [])
    for premise in (
      "CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY",
      "ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS",
      "STEP_BINDINGS_ARE_BOUND_TO_EXACT_BEHAVIOR_SUBJECT_RUN_CONTEXT_STEP_RESULT_AND_EVIDENCE_DIGEST",
    ):
        if premise not in proves:return _fail("V7_STEP_BINDING_PREMISE_MISSING",premise=premise)
    if pv.get("quality_authority") is not False or pv.get("terminal_authority") is not False:return _fail("V7_PROOF_BOUND_OVERCLAIM")

    scope=docs["r3_semantic_scope"]
    if scope.get("root_id")!=ROOT_ID:return _fail("R3_SCOPE_ROOT_MISMATCH")
    if set(scope.get("formats") or [])!={"docx","xlsx","pptx","pdf"}:return _fail("R3_FORMAT_SCOPE_DRIFT")
    limits=set(scope.get("limitations") or [])
    for req in ("BOUNDED_GENERATED_EXPLICIT_LOW_LEVEL_TEXT_EDITS_ONLY","NO_ARBITRARY_SEMANTIC_TARGET_SELECTION","NO_GLOBAL_R3_ROOT_CLOSURE","NO_ALL_RENDERER_OR_ENVIRONMENT_INVARIANCE"):
        if req not in limits:return _fail("R3_SCOPE_LIMITATION_MISSING",limitation=req)
    sem=docs["r3_semantic_verification"]
    if not str(sem.get("status") or "").startswith("PASS__"):return _fail("R3_SEMANTIC_VERIFY_NOT_PASS")
    if (sem.get("exact_blobs") or {}).get("runtime")!="eb3c5e6537d48640078b52a525a8f1791d88386b":return _fail("R3_SEMANTIC_RUNTIME_DRIFT")
    if (sem.get("exact_blobs") or {}).get("source_verification")!=REFS["native_render_public_verification"][1]:return _fail("R3_SOURCE_VERIFY_DRIFT")
    if "ARBITRARY_SEMANTIC_TARGET_CORRECTNESS" not in set(sem.get("not_proved") or []):return _fail("R3_SEMANTIC_NONCLAIM_MISSING")

    pre=docs["native_render_preflight"]
    if pre.get("behavior_id")!="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":return _fail("NATIVE_PREFLIGHT_BEHAVIOR_MISMATCH")
    if "BOUNDED_EXPLICIT_LOW_LEVEL_TEXT_EDITS" not in str(pre.get("scope_limitation") or ""):return _fail("NATIVE_PREFLIGHT_SCOPE_TOO_BROAD")
    pub=docs["native_render_public_verification"]
    if (pub.get("independent_public_runner") or {}).get("conclusion")!="success":return _fail("NATIVE_PUBLIC_VERIFY_NOT_SUCCESS")
    if (pub.get("exact_brain_blobs") or {}).get("canonical/runtime/native_artifact_render_preservation_proof_v1.py")!=NATIVE_RUNTIME_BLOB:
        return _fail("NATIVE_RENDER_RUNTIME_DRIFT")
    if "EXACT_BRAIN_BLOBS_VERIFIED_BY_PUBLIC_CAPSULE" not in set(pub.get("verified") or []):return _fail("NATIVE_EXACT_BYTES_UNPROVED")

    bs=binding.get("binding_scope") or {}
    if bs.get("step_id")!=STEP_ID:return _fail("BINDING_STEP_ID_MISMATCH")
    if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
    if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
    return {"schema":SCHEMA,"pass":True,
      "status":"PASS__R3_BOUND_TO_V7_SUBJECT_THROUGH_PROOF_BOUND_RENDER_STEP_AND_PINNED_NATIVE_REALIZATION_SCOPE",
      "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
      "subject_binding_git_blob_sha":BINDING_BLOB,"step_id":STEP_ID,
      "root_subject_binding_authority":True,"semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"real_task_step_receipt_proved":False,"global_r3_root_closed":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None):
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    b,e=_read(root,BINDING_PATH,BINDING_BLOB)
    if e:return _fail(e)
    s,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
    if e:return _fail(e)
    docs={}
    for key,(path,sha) in REFS.items():
        d,e=_read(root,path,sha)
        if e:return _fail(e,ref=key)
        docs[key]=d
    return evaluate_documents(b,s,docs)

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
