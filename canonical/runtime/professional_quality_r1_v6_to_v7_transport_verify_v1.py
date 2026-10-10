"""Verify transport of R1 final-subject binding from V6 to additive V7."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_V6_TO_V7_TRANSPORT_VERIFY_V1"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V4.json"
BINDING_BLOB="b0b05ecd50a094c20fc7a6584a6840f6869561c9"
V6_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V6_DECLARED_SYSTEM_SUBJECT_20261010_V5.json"
V6_BLOB="994a6a6aef44b6bb33161f7179d1983a1b50b633"
V7_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
V7_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
OLD_BIND_PATH="canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V3.json"
OLD_BIND_BLOB="25f02a605da31c8f9d2c6208b82597e85f00be87"
OLD_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R1_FINAL_V6_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json"
OLD_VERIFY_BLOB="7887c58604d822b42a020ebada137f16bbf13b98"
V7_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json"
V7_VERIFY_BLOB="b7a9df36780513ad73fd14c6a2756c8474d8434d"
ADDED={
 ("canonical/runtime/professional_quality_p1_router_v7.py","765b5994c2fcb5eb669b5fd0d989cc79c1609908"),
 ("canonical/runtime/professional_step_binding_authority_v1.py","27f3c137dae7f00925083a0824d008c2b4d10f0a"),
}
INHERITED_R1={
 "router_v6":"88644e0517d472d9fbef8d5bc6cf3495f2b50005",
 "goal_binding_kernel":"5b4573475437e9fc83338b900556b5c4f31c8d65",
 "target_semantics":"583612b0e2226053ac758683087b5c5d0f510996",
 "hard_defect_preflight":"1921ef67ec36ac1847243e99c49f638bf7cc170a",
}

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def _read(root:Path,path:str,sha:str):
 p=(root/path).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None,"PATH_OUTSIDE_ROOT:"+path
 if not p.is_file() or p.is_symlink():return None,"FILE_INVALID:"+path
 if _blob(p)!=sha:return None,"BLOB_STALE:"+path
 try:o=json.loads(p.read_text())
 except Exception:return None,"JSON_INVALID:"+path
 return (o,None) if isinstance(o,dict) else (None,"DOC_INVALID:"+path)
def _fail(reason:str):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,"root_subject_binding_authority":False,"quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
def _components(doc):
 return {(x.get("path"),x.get("git_blob_sha")) for x in (doc.get("system_material") or {}).get("components",[]) if isinstance(x,dict)}

def verify(*,repo_root:str|Path|None=None):
 root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
 b,e=_read(root,BINDING_PATH,BINDING_BLOB)
 if e:return _fail(e)
 v6,e=_read(root,V6_PATH,V6_BLOB)
 if e:return _fail(e)
 v7,e=_read(root,V7_PATH,V7_BLOB)
 if e:return _fail(e)
 old,e=_read(root,OLD_VERIFY_PATH,OLD_VERIFY_BLOB)
 if e:return _fail(e)
 v7v,e=_read(root,V7_VERIFY_PATH,V7_VERIFY_BLOB)
 if e:return _fail(e)
 c6=_components(v6);c7=_components(v7)
 if not c6 or c7-c6!=ADDED or c6-c7:return _fail("SUBJECT_COMPONENT_DELTA_NOT_EXACT")
 sup=v7.get("supersedes") or {}
 if sup.get("path")!=V6_PATH or sup.get("git_blob_sha")!=V6_BLOB:return _fail("V7_SUPERSESSION_BINDING_INVALID")
 if old.get("root_subject_binding_authority") is not True or not str(old.get("status") or "").startswith("PASS__"):return _fail("V6_R1_BINDING_NOT_VERIFIED")
 if not str(v7v.get("status") or "").startswith("PASS__") or (v7v.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_ROUTER_VERIFY_INSUFFICIENT")
 inherited=v7v.get("inherited_exact_blobs") or {}
 for k,sha in INHERITED_R1.items():
  if inherited.get(k)!=sha:return _fail("R1_INHERITED_BLOB_CHANGED:"+k)
 if v7v.get("semantic_truth_authority") is not False or v7v.get("quality_authority") is not False or v7v.get("terminal_authority") is not False:return _fail("V7_ADDITION_AUTHORITY_OVERCLAIM")
 proved=set(v7v.get("proves") or [])
 for x in ("CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY","ONLY_AFTER_ALL_SEVEN_AUTHENTICATE_ARE_INTERNAL_PASS_VALUES_DERIVED_FOR_THE_EXISTING_V6_V4_V3_CHAIN"):
  if x not in proved:return _fail("V7_RESTRICTION_PROOF_MISSING")
 if b.get("subject_id")!=v7.get("subject_id") or b.get("subject_sha256")!=v7.get("subject_sha256"):return _fail("V7_BINDING_SUBJECT_MISMATCH")
 for f in ("root_subject_binding_authority","semantic_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if b.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+f)
 return {"schema":SCHEMA,"pass":True,"status":"PASS__R1_V6_BINDING_TRANSPORTED_TO_EXACT_ADDITIVE_V7_SUBJECT","root_id":"R1_TARGET_SPECIFICATION","subject_id":v7["subject_id"],"subject_sha256":v7["subject_sha256"],"root_subject_binding_authority":True,"semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0}

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
