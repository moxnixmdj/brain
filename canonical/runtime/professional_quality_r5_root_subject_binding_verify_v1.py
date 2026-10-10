"""Independent verifier for R5 evaluator/reference binding on the V7 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R5_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R5_EVALUATOR_REFERENCE"
STEP_ID="RUN_CRITERION_SPECIFIC_PLUS_HOLISTIC_COMPARATIVE_EVALUATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R5_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="4b07f5ed007fd71ccec1d47410984bb1fb70f42b"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REFS={
 "execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "proof_bound_step_verification":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "r5_semantic_scope":("canonical/governance/PROFESSIONAL_QUALITY_R5_EVALUATOR_SEMANTIC_SCOPE_20261010_V1.json","dc10374849f5c26e354e9c396aa1f581b5f56d63"),
 "r5_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R5_EVALUATOR_SEMANTIC_VERIFY_20261010_V1.json","33d5e8c11e07e4a153edf3970503c6753c5343d2"),
 "evaluator_uncertainty_governance":("canonical/governance/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_20261008_V1.json","1b61fa4eb98e0039a46f349d31da725bb02c16e0"),
 "evaluator_uncertainty_verification":("canonical/verification/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_20261008_V1.json","e852c4fbc14147c17469f1a4ede4e274d768bbf7"),
}
ROUTER_V7_BLOB="765b5994c2fcb5eb669b5fd0d989cc79c1609908"
STEP_AUTH_BLOB="27f3c137dae7f00925083a0824d008c2b4d10f0a"
RUNTIME_BLOB="7adf19997ec90913fb70e618eb4e3adda055deac"
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND",
 "V7_COMPARATIVE_EVALUATION_STEP_IS_CONTENT_ADDRESSED_AND_INDEPENDENTLY_VERIFIED_BEFORE_INTERNAL_PASS_DERIVATION",
 "R5_SUPPORT_IS_CONDITIONAL_ON_AN_INDEPENDENTLY_AUTHENTICATED_EVALUATOR_OUTER_CLASS_OR_EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
 "ROBUST_MARGIN_IS_CHECKED_WITH_EXACT_RATIONAL_ARITHMETIC_INSIDE_THE_EXISTING_BOUNDED_EVALUATOR_UNCERTAINTY_MECHANISM",
 "UNPROVED_OR_NONINDEPENDENT_EVALUATOR_CLASS_MEMBERSHIP_FAILS_CLOSED",
 "PUBLIC_RUBRIC_ONLY_OR_UNVERIFIED_RECONSTRUCTED_GRADER_HAS_ZERO_OWNER_SEMANTIC_AUTHORITY",
 "ACTUAL_V7_R5_EXECUTION_REQUIRES_A_FRESH_RUN_CONTEXT_BOUND_PROFESSIONAL_STEP_RECEIPT",
 "CALLER_SUPPLIED_EVALUATION_STEP_PASS_HAS_ZERO_AUTHORITY",
}
REQUIRED_LIMITS={
 "NO_REAL_TASK_COMPARATIVE_EVALUATION_STEP_RECEIPT_FROM_THIS_BINDING",
 "NO_PROOF_THE_TRUE_CURRENT_OWNER_EVALUATOR_IS_IN_ANY_PROPOSED_DECOMPOSITION",
 "NO_PROOF_PUBLIC_RUBRIC_DIRECTIONS_ARE_OWNER_MONOTONE",
 "NO_CURRENT_BRAIN_VS_OPUS55_DIFFERENCE_VECTOR_BINDING",
 "NO_GLOBAL_R5_ROOT_CLOSURE","NO_GLOBAL_R5_SEMANTIC_LEAF_CLOSURE",
 "NO_QUALITY_ACCEPTANCE_FROM_THIS_BINDING","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
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
 "true_current_owner_evaluator_containment_proved":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

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
 if binding.get("true_current_owner_evaluator_containment_proved") is not False:return _fail("OWNER_EVALUATOR_CONTAINMENT_OVERCLAIM")
 refs=binding.get("bridge_evidence") or {}
 for key,(path,sha) in REFS.items():
  row=refs.get(key)
  if not isinstance(row,Mapping) or row.get("path")!=path or row.get("git_blob_sha")!=sha:return _fail("BRIDGE_REF_MISMATCH",ref=key)

 profile=docs["execution_profile"]
 if STEP_ID not in set(profile.get("steps") or []):return _fail("V7_PROFILE_EVALUATION_STEP_MISSING")
 pv=docs["proof_bound_step_verification"]
 if (pv.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_STEP_BINDING_REPLAY_INSUFFICIENT")
 if STEP_ID not in set(pv.get("formerly_self_attested_steps") or []):return _fail("EVALUATION_STEP_NOT_PROOF_BOUND")
 for premise in ("CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY","ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS","STEP_BINDINGS_ARE_BOUND_TO_EXACT_BEHAVIOR_SUBJECT_RUN_CONTEXT_STEP_RESULT_AND_EVIDENCE_DIGEST"):
  if premise not in set(pv.get("proves") or []):return _fail("V7_STEP_BINDING_PREMISE_MISSING",premise=premise)

 scope=docs["r5_semantic_scope"]
 if scope.get("root_id")!=ROOT_ID:return _fail("R5_SCOPE_ROOT_MISMATCH")
 sg=set(scope.get("guarantees") or []); sl=set(scope.get("limitations") or [])
 for req in ("ROBUST_MARGIN_MEANING_IS_CONDITIONAL_ON_AN_INDEPENDENTLY_AUTHENTICATED_EVALUATOR_OUTER_CLASS","UNPROVED_OR_NONINDEPENDENT_EVALUATOR_CLASS_MEMBERSHIP_FAILS_CLOSED","PUBLIC_RUBRIC_ONLY_CANNOT_BIND_OWNER_PREFERENCE_SEMANTICS"):
  if req not in sg:return _fail("R5_SCOPE_GUARANTEE_MISSING",guarantee=req)
 for req in ("NO_PROOF_THE_TRUE_CURRENT_OWNER_EVALUATOR_IS_IN_ANY_PROPOSED_DECOMPOSITION","NO_PROOF_PUBLIC_RUBRIC_DIRECTIONS_ARE_OWNER_MONOTONE","NO_GLOBAL_R5_SEMANTIC_LEAF_OR_ROOT_CLOSURE"):
  if req not in sl:return _fail("R5_SCOPE_LIMITATION_MISSING",limitation=req)

 sem=docs["r5_semantic_verification"]
 if (sem.get("replay") or {}).get("tests_passed")!=6:return _fail("R5_SEMANTIC_REPLAY_INSUFFICIENT")
 if "REAL_OWNER_EVALUATOR_CLASS_MEMBERSHIP_REMAINS_AN_EXTERNAL_INDEPENDENT_PREMISE" not in set(sem.get("proved") or []):return _fail("OWNER_PREMISE_EXTERNALITY_UNPROVED")
 if "TRUE_CURRENT_GDPVAL_OWNER_EVALUATOR_CONTAINMENT" not in set(sem.get("not_proved") or []):return _fail("OWNER_CONTAINMENT_NONCLAIM_MISSING")

 gov=docs["evaluator_uncertainty_governance"]
 reality=gov.get("current_reality") or {}
 for field in ("sound_complete_gdpval_owner_decomposition_bound","current_owner_pairwise_relation_bound","gdpval_closed"):
  if reality.get(field) is not False:return _fail("EVALUATOR_GOVERNANCE_OVERCLAIM",field=field)
 firewall=gov.get("soundness_firewall") or {}
 forbidden=set(firewall.get("forbidden_as_semantic_containment_proof") or [])
 if not {"PUBLIC_METHODOLOGY_ONLY","PUBLIC_RUBRIC_ONLY","UNVERIFIED_RECONSTRUCTED_GRADER"}<=forbidden:return _fail("EVALUATOR_FIREWALL_INSUFFICIENT")
 if (gov.get("runtime") or {}).get("path")!="canonical/runtime/gdpval_hybrid_evaluator_uncertainty_v1.py":return _fail("EVALUATOR_RUNTIME_PATH_DRIFT")

 ev=docs["evaluator_uncertainty_verification"]
 if (ev.get("replay") or {}).get("tests_passed")!=11:return _fail("EVALUATOR_RUNTIME_REPLAY_INSUFFICIENT")
 if (ev.get("subject") or {}).get("runtime",{}).get("git_blob_sha")!=RUNTIME_BLOB:return _fail("EVALUATOR_RUNTIME_BLOB_DRIFT")
 boundary=" ".join(ev.get("verification_boundary") or [])
 if "DOES NOT PROVE THE TRUE CURRENT GDPVAL OWNER EVALUATOR" not in boundary:return _fail("EVALUATOR_VERIFICATION_BOUNDARY_MISSING")

 bs=binding.get("binding_scope") or {}
 if bs.get("step_id")!=STEP_ID:return _fail("BINDING_STEP_ID_MISMATCH")
 if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
 if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
 return {"schema":SCHEMA,"pass":True,
 "status":"PASS__R5_BOUND_TO_V7_SUBJECT_THROUGH_PROOF_BOUND_COMPARATIVE_EVALUATION_AND_CONDITIONAL_AUTHENTICATED_EVALUATOR_ROBUSTNESS",
 "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,"subject_binding_git_blob_sha":BINDING_BLOB,
 "step_id":STEP_ID,"root_subject_binding_authority":True,"true_current_owner_evaluator_containment_proved":False,
 "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,"acceptance_authority":False,
 "promotion_authority":False,"terminal_authority":False,"real_task_step_receipt_proved":False,"global_r5_root_closed":False,
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
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
