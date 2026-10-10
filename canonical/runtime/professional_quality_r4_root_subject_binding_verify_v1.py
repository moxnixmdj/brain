"""Independent verifier for R4 measurement/construct binding on the V7 professional subject."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R4_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R4_MEASUREMENT_CONSTRUCT"
STEP_ID="RUN_DETERMINISTIC_FACT_STRUCTURE_FORMAT_AND_GROUNDING_CHECKS"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R4_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="5a99d72d8a6c8fe01241e8a611cceb528fb8c512"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REFS={
 "execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "proof_bound_step_verification":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "r4_semantic_scope":("canonical/governance/PROFESSIONAL_QUALITY_R4_MEASUREMENT_SEMANTIC_SCOPE_20261010_V1.json","a5b3e1984da25b09a5cb503b615806acdbf88e81"),
 "r4_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R4_MEASUREMENT_SEMANTIC_VERIFY_20261010_V1.json","c91074f2f187834936c0b7297579a6b8ba125fae"),
 "measurement_binding":("canonical/governance/ARTIFACT_MEASUREMENT_BINDING_20261007_V1.json","a174825b4c10fefa06c3a7ba09eb68c0d40af14a"),
 "measurement_verification":("canonical/verification/ARTIFACT_MEASUREMENT_VERIFY_20261007_V1.json","34c64ed759d2e70df48a76d7a254047ac5fe9e2b"),
}
EXPECTED_KINDS={
 "DOCX_PARAGRAPH_COUNT","DOCX_TABLE_COUNT","DOCX_TEXT_CONTAINS",
 "FILE_BASENAME","FILE_SIZE_BYTES","FILE_SUFFIX","OOXML_MEMBER_EXISTS",
 "PPTX_SLIDE_COUNT","PPTX_TEXT_CONTAINS","XLSX_SHEET_COUNT","XLSX_SHEET_EXISTS",
}
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND",
 "V7_DETERMINISTIC_FACT_STRUCTURE_FORMAT_AND_GROUNDING_STEP_IS_CONTENT_ADDRESSED_AND_INDEPENDENTLY_VERIFIED_BEFORE_INTERNAL_PASS_DERIVATION",
 "R4_SUPPORT_IS_LIMITED_TO_EXISTING_CONTENT_ADDRESSED_TYPED_MECHANICAL_MEASUREMENT_SEMANTICS",
 "CANDIDATE_MEASUREMENT_VALUES_MUST_BE_DERIVED_FROM_EXACT_ARTIFACT_BYTES",
 "MEASURED_FIELD_SET_AND_TYPES_MUST_MATCH_THE_TYPED_ACCEPTANCE_PROGRAM_EXACTLY",
 "EXACT_CRITERION_MEASUREMENT_PROGRAM_SCALE_AND_ACCEPTANCE_RELATIONS_MUST_BE_BOUND_IN_STEP_EVIDENCE",
 "ACTUAL_V7_R4_EXECUTION_REQUIRES_A_FRESH_RUN_CONTEXT_BOUND_PROFESSIONAL_STEP_RECEIPT",
 "CALLER_SUPPLIED_CANDIDATE_MEASUREMENT_VALUES_HAVE_ZERO_AUTHORITY",
}
REQUIRED_LIMITS={
 "NO_REAL_TASK_DETERMINISTIC_CHECK_STEP_RECEIPT_FROM_THIS_BINDING",
 "NO_AUTOMATIC_FIELD_TO_RUBRIC_OR_CONSTRUCT_SEMANTIC_ALIGNMENT",
 "NO_HOLISTIC_OR_VISUAL_QUALITY_MEASUREMENT",
 "NO_UNSUPPORTED_MEASUREMENT_KIND_SEMANTICS",
 "NO_OPEN_WORLD_MEASUREMENT_COMPLETENESS",
 "NO_GLOBAL_R4_ROOT_CLOSURE","NO_GLOBAL_R4_SEMANTIC_LEAF_CLOSURE",
 "NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
}
ROUTER_V7_BLOB="765b5994c2fcb5eb669b5fd0d989cc79c1609908"
STEP_AUTH_BLOB="27f3c137dae7f00925083a0824d008c2b4d10f0a"
MEASURED_ACCEPTANCE_BLOB="7cb47bbefa807e93007e13e84607b41e27245f62"
MEASUREMENT_BLOB="4da88dc71e85874b6445988b792951fb3c36d62f"
TYPED_INTERPRETER_BLOB="7fd2e575bd2d5c36f48c713f15177d5b0d7e68c5"

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
 if STEP_ID not in set(profile.get("steps") or []):return _fail("V7_PROFILE_MEASUREMENT_STEP_MISSING")
 pv=docs["proof_bound_step_verification"]
 if (pv.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_STEP_BINDING_REPLAY_INSUFFICIENT")
 if STEP_ID not in set(pv.get("formerly_self_attested_steps") or []):return _fail("MEASUREMENT_STEP_NOT_PROOF_BOUND")
 proves=set(pv.get("proves") or [])
 for premise in (
  "CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY",
  "ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS",
  "STEP_BINDINGS_ARE_BOUND_TO_EXACT_BEHAVIOR_SUBJECT_RUN_CONTEXT_STEP_RESULT_AND_EVIDENCE_DIGEST",
 ):
  if premise not in proves:return _fail("V7_STEP_BINDING_PREMISE_MISSING",premise=premise)

 scope=docs["r4_semantic_scope"]
 if scope.get("root_id")!=ROOT_ID:return _fail("R4_SCOPE_ROOT_MISMATCH")
 if set(scope.get("measurement_kinds") or [])!=EXPECTED_KINDS:return _fail("R4_MEASUREMENT_KIND_SCOPE_DRIFT")
 sl=set(scope.get("limitations") or [])
 for req in ("NO_AUTOMATIC_FIELD_TO_RUBRIC_OR_CONSTRUCT_SEMANTIC_ALIGNMENT","NO_HOLISTIC_OR_VISUAL_QUALITY_MEASUREMENT","NO_GLOBAL_R4_ROOT_CLOSURE"):
  if req not in sl:return _fail("R4_SCOPE_LIMITATION_MISSING",limitation=req)

 sem=docs["r4_semantic_verification"]
 if not str(sem.get("status") or "").startswith("PASS__"):return _fail("R4_SEMANTIC_VERIFY_NOT_PASS")
 if set((sem.get("claim_scope") or {}).get("measurement_kinds") or [])!=EXPECTED_KINDS:return _fail("R4_SEMANTIC_VERIFY_KIND_DRIFT")
 for req in ("NO_AUTOMATIC_FIELD_TO_RUBRIC_SEMANTIC_ALIGNMENT","NO_HOLISTIC_OR_VISUAL_QUALITY_MEASUREMENT","NO_OPEN_WORLD_MEASUREMENT_COMPLETENESS"):
  if req not in set(sem.get("hard_nonclaims") or []):return _fail("R4_SEMANTIC_VERIFY_NONCLAIM_MISSING",nonclaim=req)

 mb=docs["measurement_binding"]
 rep=mb.get("repair") or {}
 if rep.get("measured_acceptance_runtime")!="canonical/runtime/measured_typed_acceptance_program_v1.py":return _fail("MEASURED_ACCEPTANCE_RUNTIME_MISMATCH")
 if set(rep.get("supported_v1") or [])!=EXPECTED_KINDS:return _fail("MEASUREMENT_BINDING_KIND_DRIFT")
 for req in ("NO_CLAIM_FIELD_TO_RUBRIC_SEMANTIC_ALIGNMENT_IS_AUTOMATIC","NO_CLAIM_HOLISTIC_OR_VISUAL_QUALITY_IS_MEASURED"):
  if req not in set(mb.get("hard_nonclaims") or []):return _fail("MEASUREMENT_BINDING_NONCLAIM_MISSING",nonclaim=req)

 mv=docs["measurement_verification"]
 if (mv.get("result") or {}).get("passed")!=8 or (mv.get("result") or {}).get("total")!=8:return _fail("MEASUREMENT_VERIFY_REPLAY_INSUFFICIENT")
 blobs=mv.get("blobs") or {}
 if blobs.get("measured_acceptance")!=MEASURED_ACCEPTANCE_BLOB or blobs.get("measurement")!=MEASUREMENT_BLOB or blobs.get("typed_interpreter")!=TYPED_INTERPRETER_BLOB:
  return _fail("MEASUREMENT_VERIFY_BLOB_DRIFT")
 vv=set(mv.get("verified") or [])
 for req in ("ARTIFACT_SHA_AND_MEASUREMENTS_DERIVED_FROM_REAL_BYTES","PATH_ESCAPE_FAILS_CLOSED","FIELD_TYPE_MISMATCH_FAILS_CLOSED"):
  if req not in vv:return _fail("MEASUREMENT_VERIFY_PREMISE_MISSING",premise=req)

 bs=binding.get("binding_scope") or {}
 if bs.get("step_id")!=STEP_ID:return _fail("BINDING_STEP_ID_MISMATCH")
 if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
 if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__R4_BOUND_TO_V7_SUBJECT_THROUGH_PROOF_BOUND_DETERMINISTIC_CHECK_STEP_AND_TYPED_MECHANICAL_MEASUREMENT_SCOPE",
  "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
  "subject_binding_git_blob_sha":BINDING_BLOB,"step_id":STEP_ID,
  "root_subject_binding_authority":True,"semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"real_task_step_receipt_proved":False,"global_r4_root_closed":False,
  "holistic_quality_measured":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

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

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
