"""Independent verifier for R6 evidence-grounding binding on the V7 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_scoped_evidence_v1 as scoped

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R6_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R6_EVIDENCE_GROUNDING_DEPENDENCE"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R6_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="8d0d35c979a101110307a633e21b40f57fbcfc1f"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REFS={
 "proof_bound_step_verification":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "leaf_binder_verification":("canonical/verification/PROFESSIONAL_QUALITY_LEAF_BINDER_V2_VERIFY_20261010_V1.json","b65a67e8edaee925338fe3f2d61dad6b0f52d129"),
 "scoped_registry":("canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json","b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"),
 "leaf_registry":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json","d25cb6fe746eef992f71b138446dc999c0f2a307"),
 "leaf_manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "assurance_graph":("canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json","03530e29d70206b46b690b33a04c66765ff86ad7"),
}
SUBJECT_COMPONENTS={
 "canonical/runtime/professional_quality_p1_router_v7.py":"765b5994c2fcb5eb669b5fd0d989cc79c1609908",
 "canonical/runtime/professional_step_binding_authority_v1.py":"27f3c137dae7f00925083a0824d008c2b4d10f0a",
 "canonical/runtime/professional_quality_scoped_evidence_v1.py":"940fc381fa10559bf7ec8f59048562809f1031c0",
 "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json":"b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba",
 "canonical/runtime/professional_quality_leaf_binder_v2.py":"1a181b453271a2ce4fc112c3f6586afaf5effbd7",
 "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json":"d25cb6fe746eef992f71b138446dc999c0f2a307",
 "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json":"a7cad32c9fd969ff2c3857bb924c7bd746237ec2",
 "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json":"03530e29d70206b46b690b33a04c66765ff86ad7",
}
EXPECTED_ROOTS={
 "R1_TARGET_SPECIFICATION","R2_CANDIDATE_SEARCH","R3_REALIZATION_OBSERVATION",
 "R4_MEASUREMENT_CONSTRUCT","R5_EVALUATOR_REFERENCE","R6_EVIDENCE_GROUNDING_DEPENDENCE",
 "R7_CAUSAL_PRESCRIPTIVE","R8_POPULATION_CONTEXT_OPERATOR","R9_TEMPORAL_DEPLOYMENT",
 "R10_ANALYSIS_DECISION","R11_ADAPTIVE_INTEGRITY_SECURITY","R12_META_COMPOSITION_CLOSURE",
}
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND",
 "CURRENT_SCOPED_EVIDENCE_REGISTRY_IS_EXACTLY_CONTENT_ADDRESSED",
 "ALL_CURRENT_21_SCOPED_CAPABILITY_ENTRIES_MUST_BE_ADMITTED_BY_THE_EXISTING_HANDLER_SPECIFIC_SCOPED_EVIDENCE_VALIDATOR",
 "ALL_CURRENT_12_ROOTS_MUST_REMAIN_REPRESENTED_IN_THE_ADMITTED_SCOPED_CAPABILITY_SET",
 "SCOPED_ADMISSION_REQUIRES_BOUND_SOURCE_RECEIPT_COMPILER_VERIFICATION_AND_REUSABLE_COMPILER_BYTES",
 "V7_LOAD_BEARING_STEP_RESULTS_REQUIRE_CONTENT_ADDRESSED_RECEIPT_AND_INDEPENDENT_VERIFICATION",
 "V7_STEP_VERIFICATION_REQUIRES_SEMANTIC_PRESERVATION_AND_EVIDENCE_SCOPE_VERIFIED",
 "CALLER_SUPPLIED_STEP_PASS_AND_MANIFEST_STATUS_STRINGS_HAVE_ZERO_AUTHORITY",
 "GLOBAL_LEAF_REGISTRY_REMAINS_EMPTY_AND_GRANTS_ZERO_GLOBAL_LEAF_ROOT_OR_DOMAIN_CLOSURE",
}
REQUIRED_LIMITS={
 "NO_GENERAL_EVIDENCE_TRUTH_CLOSURE","NO_GENERAL_EVIDENCE_INDEPENDENCE_CLOSURE",
 "NO_GENERAL_UNCERTAINTY_SEMANTICS_CLOSURE","NO_CLAIM_ANY_REAL_TASK_ALREADY_HAS_ALL_REQUIRED_V7_STEP_RECEIPTS",
 "NO_GLOBAL_R6_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE","NO_GLOBAL_R6_ROOT_CLOSURE",
 "NO_GLOBAL_PROFESSIONAL_LEAF_OR_ROOT_CLOSURE","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
}

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
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "global_leaf_closure":False,"global_root_closure":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def evaluate_documents(binding:Mapping[str,Any],subject:Mapping[str,Any],docs:Mapping[str,Mapping[str,Any]],scoped_result:Mapping[str,Any])->dict[str,Any]:
 if binding.get("schema")!=BINDING_SCHEMA or binding.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
 if (binding.get("subject_kind"),binding.get("subject_id"),binding.get("subject_sha256"))!=("DECLARED_SYSTEM",SUBJECT_ID,SUBJECT_SHA256):
  return _fail("SUBJECT_TUPLE_MISMATCH")
 if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
 comps={(r.get("path"),r.get("git_blob_sha")) for r in ((subject.get("system_material") or {}).get("components") or []) if isinstance(r,Mapping)}
 for path,sha in SUBJECT_COMPONENTS.items():
  if (path,sha) not in comps:return _fail("REQUIRED_R6_COMPONENT_NOT_IN_SUBJECT",path=path)
 for f in ("global_subject_identity_authority","root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if binding.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN",field=f)
 if binding.get("all_real_task_step_receipts_proved") is not False:return _fail("ALL_REAL_TASK_STEP_RECEIPTS_OVERCLAIM")
 if binding.get("global_leaf_registry_must_remain_empty") is not True:return _fail("EMPTY_GLOBAL_LEAF_REGISTRY_REQUIREMENT_MISSING")
 refs=binding.get("bridge_evidence") or {}
 for key,(path,sha) in REFS.items():
  row=refs.get(key)
  if not isinstance(row,Mapping) or row.get("path")!=path or row.get("git_blob_sha")!=sha:return _fail("BRIDGE_REF_MISMATCH",ref=key)

 pv=docs["proof_bound_step_verification"]
 if (pv.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_STEP_BINDING_REPLAY_INSUFFICIENT")
 proves=set(pv.get("proves") or [])
 for premise in (
  "CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY",
  "ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS",
  "STEP_BINDINGS_ARE_BOUND_TO_EXACT_BEHAVIOR_SUBJECT_RUN_CONTEXT_STEP_RESULT_AND_EVIDENCE_DIGEST",
 ):
  if premise not in proves:return _fail("V7_STEP_BINDING_PREMISE_MISSING",premise=premise)

 leafv=docs["leaf_binder_verification"]
 if (leafv.get("replay") or {}).get("tests_passed")!=5:return _fail("LEAF_BINDER_REPLAY_INSUFFICIENT")
 lp=set(leafv.get("proved") or [])
 for premise in (
  "MANIFEST_VERIFIED_STATUS_HAS_ZERO_PROMOTION_AUTHORITY",
  "LEAF_CLOSURE_REQUIRES_SCOPE_MATCHED_CONTENT_ADDRESSED_RECEIPT",
  "RECEIPT_MUST_BIND_EXACT_ROOT_CONTRACT_AND_EXACT_LEAF_ACCEPTANCE",
  "RECEIPT_VERIFICATION_BASIS_MUST_BE_CONTENT_ADDRESSED_AND_CURRENT",
  "UNKNOWN_REGISTRY_LEAF_IDS_FAIL_STRUCTURE",
 ):
  if premise not in lp:return _fail("LEAF_BINDER_PREMISE_MISSING",premise=premise)
 state=leafv.get("current_state") or {}
 if state.get("verified_leaf_count")!=0 or state.get("open_leaf_count")!=24 or state.get("promotion_ready") is not False:
  return _fail("GLOBAL_LEAF_STATE_NOT_FAIL_CLOSED_OPEN")

 leafreg=docs["leaf_registry"]
 if leafreg.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_V1":return _fail("LEAF_REGISTRY_SCHEMA_INVALID")
 if leafreg.get("leaf_receipts")!={}:return _fail("GLOBAL_LEAF_REGISTRY_NOT_EMPTY")
 if leafreg.get("terminal_authority") is not False:return _fail("LEAF_REGISTRY_TERMINAL_AUTHORITY_INVALID")
 if "MANIFEST_STATUS_STRINGS_HAVE_ZERO_PROMOTION_AUTHORITY" not in str(leafreg.get("admission_law") or ""):
  return _fail("LEAF_REGISTRY_STATUS_NONAUTHORITY_MISSING")

 if scoped_result.get("pass") is not True:return _fail("SCOPED_EVIDENCE_VALIDATION_NOT_PASS",scoped_status=scoped_result.get("status"))
 if scoped_result.get("admitted_scope_count")!=21 or scoped_result.get("rejected_scope_count")!=0:return _fail("SCOPED_EVIDENCE_COUNT_MISMATCH")
 admitted=scoped_result.get("admitted_scopes") or []
 roots={x.get("root_id") for x in admitted if isinstance(x,Mapping)}
 if roots!=EXPECTED_ROOTS:return _fail("SCOPED_EVIDENCE_ROOT_SET_MISMATCH",roots=sorted(str(x) for x in roots))
 r6=[x for x in admitted if isinstance(x,Mapping) and x.get("root_id")==ROOT_ID]
 if len(r6)!=1:return _fail("R6_SCOPED_ADMISSION_COUNT_INVALID")
 claim_scope=r6[0].get("claim_scope") or {}
 if claim_scope.get("kind")!="CONTENT_ADDRESSED_SCOPE_MATCHED_LEAF_EVIDENCE_ADMISSION_WITH_STATUS_NONAUTHORITY":return _fail("R6_CLAIM_SCOPE_KIND_INVALID")
 for lim in ("NO_GENERAL_EVIDENCE_TRUTH_CLOSURE","NO_GENERAL_EVIDENCE_INDEPENDENCE_CLOSURE","NO_GENERAL_UNCERTAINTY_SEMANTICS_CLOSURE","NO_GLOBAL_R6_LEAF_OR_ROOT_CLOSURE"):
  if lim not in set(claim_scope.get("limitations") or []):return _fail("R6_SCOPED_LIMITATION_MISSING",limitation=lim)
 for field in ("global_leaf_closure","global_root_closure","domain_semantic_closure","domain_execution_closure"):
  if scoped_result.get(field) is not False:return _fail("SCOPED_EVIDENCE_GLOBAL_OVERCLAIM",field=field)

 bs=binding.get("binding_scope") or {}
 if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
 if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__R6_BOUND_TO_V7_SUBJECT_THROUGH_FULL_CURRENT_SCOPED_EVIDENCE_ADMISSION_AND_PROOF_BOUND_STEP_EVIDENCE_AUTHENTICATION",
  "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
  "subject_binding_git_blob_sha":BINDING_BLOB,"root_subject_binding_authority":True,
  "admitted_scoped_capability_count":21,"admitted_root_count":12,
  "all_real_task_step_receipts_proved":False,"global_leaf_registry_empty":True,
  "global_leaf_closure":False,"global_root_closure":False,
  "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
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
 try:
  sr=scoped.evaluate(registry_path=root/REFS["scoped_registry"][0],repo_root=root)
 except Exception as exc:
  return _fail("SCOPED_EVIDENCE_EVALUATION_EXCEPTION",exception_type=type(exc).__name__,detail=str(exc)[:200])
 return evaluate_documents(b,s,docs,sr)

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
