from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R2_CANDIDATE_SEARCH"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R2_ROOT_SUBJECT_BINDING_20261010_V1.json"
EXPECTED_BINDING_BLOB="723925734eb353e783cca1ccb6bdb05d20518596"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
PROFILE_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
PROFILE_BLOB="f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"
REFS={
"subject_verification":("canonical/verification/PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V7_VERIFY_20261010_V1.json","9bca985bfcef8f5cc6d62b42a51ccc72a6abfd2c"),
"candidate_generator_verification":("canonical/verification/PROFESSIONAL_QUALITY_R2_V7_CANDIDATE_BRANCH_BASIS_VERIFY_20261010_V1.json","e2f0143891f10961a15d6fc1e7faf97a0b81d9e8"),
"r2_search_semantics":("canonical/verification/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_VERIFY_20261010_V1.json","06da6b94712ec844a56c0f663cce67f059b7ba8d"),
"r2_scope_complete_execution":("canonical/verification/PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_VERIFY_20261010_V1.json","b66115513d1dde4527a65e5eda1ddea300138aca")}

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def _path(root:Path,s:Any):
 if not isinstance(s,str) or not s.startswith("canonical/"):return None
 p=(root/s).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 return p
def _read(root:Path,path:str,sha:str):
 p=_path(root,path)
 if p is None or not p.is_file() or p.is_symlink():return None,"FILE_INVALID:"+path
 if _blob(p)!=sha:return None,"BLOB_STALE:"+path
 try:d=json.loads(p.read_text())
 except Exception:return None,"JSON_INVALID:"+path
 return (d,None) if isinstance(d,dict) else (None,"DOCUMENT_INVALID:"+path)
def _fail(reason:str):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,"root_id":ROOT_ID,
 "root_subject_binding_authority":False,"semantic_truth_authority":False,"execution_authority":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None):
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 b,e=_read(root,BINDING_PATH,EXPECTED_BINDING_BLOB)
 if e:return _fail(e)
 if b.get("schema")!=BINDING_SCHEMA or b.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
 if (b.get("subject_id"),b.get("subject_sha256"))!=(SUBJECT_ID,SUBJECT_SHA256):return _fail("SUBJECT_TUPLE_MISMATCH")
 for f in ("root_subject_binding_authority","global_subject_identity_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if b.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+f)
 sr=b.get("subject") or {}
 if sr.get("path")!=SUBJECT_PATH or sr.get("git_blob_sha")!=SUBJECT_BLOB:return _fail("SUBJECT_REFERENCE_MISMATCH")
 s,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
 if e:return _fail(e)
 if (s.get("subject_id"),s.get("subject_sha256"))!=(SUBJECT_ID,SUBJECT_SHA256):return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
 material={(x.get("path"),x.get("git_blob_sha")) for x in (s.get("system_material") or {}).get("components",[]) if isinstance(x,Mapping)}
 if (PROFILE_PATH,PROFILE_BLOB) not in material:return _fail("PINNED_PROFILE_NOT_IN_V7_SUBJECT")
 docs={}
 bre=b.get("bridge_evidence")
 if not isinstance(bre,Mapping):return _fail("BRIDGE_EVIDENCE_INVALID")
 for k,(p,h) in REFS.items():
  ref=bre.get(k)
  if not isinstance(ref,Mapping) or ref.get("path")!=p or ref.get("git_blob_sha")!=h:return _fail("BRIDGE_REFERENCE_MISMATCH:"+k)
  docs[k],e=_read(root,p,h)
  if e:return _fail(e)
 sv=(docs["subject_verification"].get("real_subject_replay") or {})
 if not(sv.get("pass") is True and sv.get("component_count")==22 and sv.get("component_currentness_verified") is True and sv.get("subject_identity_verified") is True):return _fail("SUBJECT_VERIFICATION_INSUFFICIENT")
 g=docs["candidate_generator_verification"];c=g.get("exact_candidate") or {};r=g.get("independent_replay") or {}
 if (c.get("subject_id"),c.get("subject_sha256"))!=(SUBJECT_ID,SUBJECT_SHA256):return _fail("GENERATOR_SUBJECT_TUPLE_MISMATCH")
 if (c.get("execution_profile_path"),c.get("execution_profile_git_blob_sha"))!=(PROFILE_PATH,PROFILE_BLOB):return _fail("GENERATOR_PROFILE_MISMATCH")
 if r.get("tests_passed")!=7 or r.get("tests_failed")!=0 or r.get("real_profile_candidate_count")!=22:return _fail("GENERATOR_VERIFICATION_INSUFFICIENT")
 gp=set(g.get("proves") or [])
 if not {"FINITE_PROFILE_DERIVED_CANDIDATE_BASIS_IS_DETERMINISTIC_ON_V7_SUBJECT_IDENTITY","GENERATOR_OUTPUT_DOES_NOT_SELF_AUTHORIZE_THE_V7_PROFESSIONAL_STEP"}<=gp:return _fail("GENERATOR_PROOF_INSUFFICIENT")
 if "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS" not in set(g.get("hard_nonclaims") or []):return _fail("GENERATOR_SCOPE_BOUNDARY_INSUFFICIENT")
 sem=docs["r2_search_semantics"];ss=sem.get("claim_scope") or {}
 if (sem.get("replay") or {}).get("tests_passed")!=8 or ss.get("kind")!="FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS":return _fail("R2_SEMANTIC_EVIDENCE_INSUFFICIENT")
 if not {"NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS","NO_GLOBAL_R2_ROOT_CLOSURE","NO_POLICY_GENERATION_COMPLETENESS"}<=set(ss.get("limitations") or []):return _fail("R2_SEMANTIC_SCOPE_TOO_BROAD")
 ex=docs["r2_scope_complete_execution"]
 if (ex.get("replay") or {}).get("tests_passed")!=9:return _fail("R2_EXECUTION_REPLAY_INSUFFICIENT")
 if "INDEPENDENT_POLICY_ADEQUACY_IS_REQUIRED" not in set(ex.get("proved") or []):return _fail("POLICY_ADEQUACY_INDEPENDENCE_UNPROVED")
 limits=set((b.get("binding_scope") or {}).get("limitations") or [])
 need={"NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS","NO_POLICY_GENERATION_COMPLETENESS","NO_POLICY_ADEQUACY_FROM_GENERATION","NO_GLOBAL_R2_ROOT_CLOSURE","NO_R3_THROUGH_R12_ROOT_SUBJECT_BINDING","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION"}
 if not need<=limits:return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
 return {"schema":SCHEMA,"pass":True,"status":"PASS__R2_ROOT_BOUND_TO_V7_PROOF_BOUND_EXECUTION_SUBJECT","root_id":ROOT_ID,
 "subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,"subject_binding_git_blob_sha":EXPECTED_BINDING_BLOB,
 "root_subject_binding_authority":True,"semantic_truth_authority":False,"execution_authority":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
