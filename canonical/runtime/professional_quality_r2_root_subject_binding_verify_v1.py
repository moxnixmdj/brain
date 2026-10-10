"""Independent verifier for R2 binding on the final V6 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R2_CANDIDATE_SEARCH"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R2_ROOT_SUBJECT_BINDING_20261010_V1.json"
EXPECTED_BINDING_BLOB="c39b31c25aaa49febb63e5fb1d2c038425b406a1"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V6_DECLARED_SYSTEM_SUBJECT_20261010_V5.json"
SUBJECT_BLOB="994a6a6aef44b6bb33161f7179d1983a1b50b633"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V6_DEPENDENCY_CLOSED_AUTHENTICATED_TARGET_SYSTEM_20261010_V5"
SUBJECT_SHA256="353978ba4866d1e35794390968a14500ee1d8a4f0bddfb8f081e9a1a71ba468d"

REFS={
 "generator_basis":("canonical/governance/PROFESSIONAL_QUALITY_R2_FINAL_V6_CANDIDATE_GENERATOR_BASIS_20261010_V1.json","e50e82e8b46e833f70a8c5c5f24e243ccfbdca38"),
 "generator_verification":("canonical/verification/PROFESSIONAL_QUALITY_R2_CANDIDATE_BRANCH_BASIS_VERIFY_20261010_V1.json","37e29ba250944fa455fe4bee3d3e7c667b1d0fe5"),
 "search_semantics":("canonical/governance/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_SCOPE_20261010_V1.json","c12893656c0546aafa79135dec221f2e5f7e9774"),
 "search_execution":("canonical/governance/PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_SCOPE_20261010_V1.json","b074b6e260cf2d5b534a822c3684171b1cc95b2e"),
 "search_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_VERIFY_20261010_V1.json","06da6b94712ec844a56c0f663cce67f059b7ba8d"),
 "search_execution_verification":("canonical/verification/PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_VERIFY_20261010_V1.json","b66115513d1dde4527a65e5eda1ddea300138aca"),
}
REQUIRED_LIMITS={
 "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS","NO_OPEN_WORLD_HYPOTHESIS_COMPLETENESS",
 "NO_POLICY_GENERATION_COMPLETENESS","NO_CANDIDATE_ARTIFACT_REALIZATION_COMPLETENESS",
 "NO_POLICY_ADEQUACY_FROM_GENERATION","NO_GLOBAL_R2_ROOT_CLOSURE",
 "NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
}
REQUIRED_GUARANTEES={
 "EXACT_FINAL_V6_SUBJECT_TUPLE_BOUND","EXACT_V3_EXECUTION_PROFILE_BOUND",
 "FINITE_PROFILE_DERIVED_CANDIDATE_BASIS_DETERMINISTIC","INCUMBENT_PRESERVED_EXACTLY_ONCE",
 "ONE_FOCUS_BRANCH_PER_DECLARED_EXECUTION_STEP","ONE_FOCUS_BRANCH_PER_DECLARED_ESCALATION_TRIGGER",
 "GENERATED_UNIVERSE_IDENTITY_DEPENDS_ON_EXACT_TARGET_AND_INCUMBENT",
 "EXISTING_FINITE_SEARCH_SEMANTICS_REUSED_WITHOUT_GLOBALIZING_SCOPE",
 "POLICY_ADEQUACY_AND_TRUTHFUL_OBSERVATION_PREMISES_REMAIN_INDEPENDENT",
}

def _blob(path:Path)->str:
 data=path.read_bytes();return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _read(root:Path,path:str,sha:str):
 p=(root/path).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None,"PATH_OUTSIDE_ROOT:"+path
 if not p.is_file() or p.is_symlink():return None,"FILE_INVALID:"+path
 if _blob(p)!=sha:return None,"BLOB_STALE:"+path
 try:d=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None,"JSON_INVALID:"+path
 return (d,None) if isinstance(d,dict) else (None,"DOCUMENT_INVALID:"+path)

def _fail(reason:str,**extra:Any):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "root_id":ROOT_ID,"root_subject_binding_authority":False,
 "global_subject_identity_authority":False,"semantic_truth_authority":False,
 "execution_authority":False,"quality_authority":False,"acceptance_authority":False,
 "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**extra}

def verify(*,repo_root:str|Path|None=None):
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 b,e=_read(root,BINDING_PATH,EXPECTED_BINDING_BLOB)
 if e:return _fail(e)
 if b.get("schema")!=BINDING_SCHEMA or b.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
 if b.get("subject_kind")!="DECLARED_SYSTEM" or b.get("subject_id")!=SUBJECT_ID or b.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_TUPLE_MISMATCH")
 for field in ("root_subject_binding_authority","global_subject_identity_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if b.get(field) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+field)
 if b.get("subject_refresh_required") is not False or b.get("generator_is_external_root_support") is not True or b.get("candidate_generator_inside_subject_required") is not False:return _fail("EXTERNAL_GENERATOR_BOUNDARY_INVALID")
 sr=b.get("subject") or {}
 if sr.get("path")!=SUBJECT_PATH or sr.get("git_blob_sha")!=SUBJECT_BLOB:return _fail("SUBJECT_REFERENCE_MISMATCH")
 s,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
 if e:return _fail(e)
 if s.get("subject_id")!=SUBJECT_ID or s.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
 refs=b.get("bridge_evidence") or {}
 docs={}
 for key,(path,sha) in REFS.items():
  ref=refs.get(key)
  if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:return _fail("BRIDGE_REFERENCE_MISMATCH:"+key)
  d,e=_read(root,path,sha)
  if e:return _fail(e)
  docs[key]=d
 gv=docs["generator_verification"]
 ir=gv.get("independent_reimplementation") or {}
 if not str(gv.get("status") or "").startswith("PASS__") or ir.get("structural_checks_run")!=14 or ir.get("structural_checks_passed")!=14 or ir.get("generated_branch_count")!=22 or ir.get("unique_candidate_ids")!=22 or ir.get("incumbent_branch_count")!=1:return _fail("GENERATOR_VERIFICATION_INSUFFICIENT")
 if ir.get("deterministic_ids") is not True or ir.get("target_sensitive_universe") is not True or ir.get("incumbent_sensitive_universe") is not True:return _fail("GENERATOR_IDENTITY_PROPERTIES_UNPROVED")
 gg=docs["generator_basis"]; scope=gg.get("scope") or {}
 if scope.get("global_candidate_completeness") is not False or scope.get("artifact_realization_completeness") is not False or scope.get("policy_adequacy_inferred") is not False:return _fail("GENERATOR_SCOPE_OVERCLAIM")
 sem=docs["search_semantics"]
 if "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS" not in set(sem.get("limitations") or []):return _fail("SEARCH_SEMANTIC_SCOPE_TOO_BROAD")
 exe=docs["search_execution"]
 if "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS" not in set(exe.get("limitations") or []):return _fail("SEARCH_EXECUTION_SCOPE_TOO_BROAD")
 sv=docs["search_semantic_verification"]
 if not str(sv.get("status") or "").startswith("PASS__"):return _fail("SEARCH_SEMANTIC_VERIFY_NOT_PASS")
 ev=docs["search_execution_verification"]
 if not str(ev.get("status") or "").startswith("PASS__"):return _fail("SEARCH_EXECUTION_VERIFY_NOT_PASS")
 bs=b.get("binding_scope") or {}
 if bs.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":return _fail("BEHAVIOR_ID_INVALID")
 if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
 if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
 return {"schema":SCHEMA,"pass":True,"status":"PASS__R2_BOUND_TO_FINAL_V6_SUBJECT_WITH_FINITE_EXTERNAL_GENERATOR_BASIS",
 "root_id":ROOT_ID,"subject_kind":"DECLARED_SYSTEM","subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
 "subject_binding_git_blob_sha":EXPECTED_BINDING_BLOB,"root_subject_binding_authority":True,
 "global_subject_identity_authority":False,"semantic_truth_authority":False,"execution_authority":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
