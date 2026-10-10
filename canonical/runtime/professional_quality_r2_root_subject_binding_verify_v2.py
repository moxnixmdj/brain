"""Independent verifier for R2 candidate-search binding on the V7 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_ROOT_SUBJECT_BINDING_VERIFY_V2"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R2_CANDIDATE_SEARCH"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R2_ROOT_SUBJECT_BINDING_20261010_V2.json"
BINDING_BLOB="d16ec4ce481880e7b3ca85dab64ba2ead744f088"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REFS={
 "generator_basis":("canonical/governance/PROFESSIONAL_QUALITY_R2_V7_CANDIDATE_GENERATOR_BASIS_20261010_V1.json","b472f2c181ebad16c03747e2089b8205360ff612"),
 "generator_verification":("canonical/verification/PROFESSIONAL_QUALITY_R2_V7_CANDIDATE_BRANCH_BASIS_VERIFY_20261010_V1.json","e2f0143891f10961a15d6fc1e7faf97a0b81d9e8"),
 "proof_bound_profile_execution":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "search_semantics":("canonical/governance/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_SCOPE_20261010_V1.json","c12893656c0546aafa79135dec221f2e5f7e9774"),
 "search_execution":("canonical/governance/PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_SCOPE_20261010_V1.json","b074b6e260cf2d5b534a822c3684171b1cc95b2e"),
 "search_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_VERIFY_20261010_V1.json","06da6b94712ec844a56c0f663cce67f059b7ba8d"),
 "search_execution_verification":("canonical/verification/PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_VERIFY_20261010_V1.json","b66115513d1dde4527a65e5eda1ddea300138aca"),
}
REQUIRED_LIMITS={
 "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS","NO_OPEN_WORLD_HYPOTHESIS_COMPLETENESS",
 "NO_POLICY_GENERATION_COMPLETENESS","NO_CANDIDATE_ARTIFACT_REALIZATION_COMPLETENESS",
 "NO_POLICY_ADEQUACY_FROM_GENERATION","NO_REAL_TASK_STEP_RECEIPT_FROM_THIS_BINDING",
 "NO_GLOBAL_R2_ROOT_CLOSURE","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
}
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND","EXACT_V3_EXECUTION_PROFILE_BOUND",
 "FINITE_PROFILE_DERIVED_CANDIDATE_BASIS_DETERMINISTIC",
 "REAL_PROFILE_BASIS_HAS_22_BRANCHES_WITH_INCUMBENT_PRESERVED_EXACTLY_ONCE",
 "GENERATED_UNIVERSE_IDENTITY_DEPENDS_ON_EXACT_TARGET_AND_INCUMBENT",
 "EXISTING_FINITE_SEARCH_SEMANTICS_REUSED_WITHOUT_GLOBALIZING_SCOPE",
 "CALLER_SUPPLIED_CANDIDATE_GENERATION_STEP_RESULTS_HAVE_ZERO_V7_AUTHORITY",
 "ACTUAL_V7_CANDIDATE_GENERATION_STEP_RESULT_REQUIRES_INDEPENDENT_CONTENT_ADDRESSED_STEP_BINDING",
 "POLICY_ADEQUACY_AND_TRUTHFUL_OBSERVATION_PREMISES_REMAIN_INDEPENDENT",
}
STEP="GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION"

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

def verify(*,repo_root:str|Path|None=None):
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 b,e=_read(root,BINDING_PATH,BINDING_BLOB)
 if e:return _fail(e)
 if b.get("schema")!=BINDING_SCHEMA or b.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
 if (b.get("subject_kind"),b.get("subject_id"),b.get("subject_sha256"))!=("DECLARED_SYSTEM",SUBJECT_ID,SUBJECT_SHA256):
  return _fail("SUBJECT_TUPLE_MISMATCH")
 for f in ("global_subject_identity_authority","root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if b.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+f)
 if b.get("generator_is_external_root_support") is not True or b.get("candidate_generator_inside_subject_required") is not False:
  return _fail("GENERATOR_BOUNDARY_INVALID")
 if b.get("actual_v7_step_receipt_required_for_execution") is not True:return _fail("STEP_RECEIPT_REQUIREMENT_MISSING")
 sref=b.get("subject") or {}
 if sref.get("path")!=SUBJECT_PATH or sref.get("git_blob_sha")!=SUBJECT_BLOB:return _fail("SUBJECT_REFERENCE_MISMATCH")
 s,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
 if e:return _fail(e)
 if s.get("subject_id")!=SUBJECT_ID or s.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
 refs=b.get("bridge_evidence")
 if not isinstance(refs,Mapping):return _fail("BRIDGE_EVIDENCE_INVALID")
 docs={}
 for k,(path,sha) in REFS.items():
  ref=refs.get(k)
  if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:return _fail("BRIDGE_REFERENCE_MISMATCH:"+k)
  d,e=_read(root,path,sha)
  if e:return _fail(e)
  docs[k]=d
 gv=docs["generator_verification"]
 ir=gv.get("independent_replay") or {}
 if not str(gv.get("status") or "").startswith("PASS__") or ir.get("tests_passed")!=7 or ir.get("real_profile_candidate_count")!=22 or ir.get("incumbent_branch_count")!=1:
  return _fail("GENERATOR_VERIFICATION_INSUFFICIENT")
 if "NO_R2_ROOT_SUBJECT_BINDING_AUTHORITY_YET" not in set(gv.get("hard_nonclaims") or []):return _fail("GENERATOR_RECEIPT_SCOPE_TOO_BROAD")
 gb=docs["generator_basis"]
 if (gb.get("subject") or {}).get("subject_id")!=SUBJECT_ID:return _fail("GENERATOR_BASIS_SUBJECT_MISMATCH")
 gs=gb.get("scope") or {}
 if gs.get("global_candidate_completeness") is not False or gs.get("policy_adequacy_inferred") is not False:return _fail("GENERATOR_BASIS_SCOPE_OVERCLAIM")
 pv=docs["proof_bound_profile_execution"]
 if (pv.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_PROOF_BOUND_REPLAY_INSUFFICIENT")
 proves=set(pv.get("proves") or [])
 if "CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY" not in proves:return _fail("CALLER_STEP_NONAUTHORITY_UNPROVED")
 if "ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS" not in proves:return _fail("SEVEN_STEP_BINDING_REQUIREMENT_UNPROVED")
 if pv.get("quality_authority") is not False or pv.get("terminal_authority") is not False:return _fail("V7_PROOF_BOUND_OVERCLAIM")
 sem=docs["search_semantics"]; exe=docs["search_execution"]
 if "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS" not in set(sem.get("limitations") or []):return _fail("SEARCH_SEMANTIC_SCOPE_TOO_BROAD")
 if "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS" not in set(exe.get("limitations") or []):return _fail("SEARCH_EXECUTION_SCOPE_TOO_BROAD")
 if not str(docs["search_semantic_verification"].get("status") or "").startswith("PASS__"):return _fail("SEARCH_SEMANTIC_VERIFY_NOT_PASS")
 if not str(docs["search_execution_verification"].get("status") or "").startswith("PASS__"):return _fail("SEARCH_EXECUTION_VERIFY_NOT_PASS")
 bs=b.get("binding_scope") or {}
 if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
 if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
 return {"schema":SCHEMA,"pass":True,"status":"PASS__R2_BOUND_TO_V7_SUBJECT_WITH_VERIFIED_FINITE_GENERATOR_AND_PROOF_BOUND_STEP_BOUNDARY",
 "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,"subject_binding_git_blob_sha":BINDING_BLOB,
 "root_subject_binding_authority":True,"semantic_truth_authority":False,"execution_authority":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
 "real_task_step_receipt_proved":False,"global_candidate_search_complete":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
