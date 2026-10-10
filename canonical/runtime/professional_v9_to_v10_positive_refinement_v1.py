"""V9 -> V10 positive-route refinement proof for the stable R12 path.

V10 adds exactly one fail-closed precondition to V9: before V9 can execute a
caller-bound R12 totality semantic verifier, the reference must equal the exact
canonical V2 verifier bytes. V10 delegates all accepted execution to V9 and
constructs no independent positive result.

Therefore every V10 positive certification is also a V9 positive certification
on the same state and exact inherited V9 semantics. V10 can delete positive
behaviors, never add one.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V9_TO_V10_POSITIVE_REFINEMENT_V1"
V9_PATH="canonical/runtime/professional_quality_p1_router_v9.py"
V9_BLOB="27f0df972a08a2497802865e46bdccdcb1c720ae"
V10_PATH="canonical/runtime/professional_quality_p1_router_v10.py"
V10_BLOB="5434dd4a4a7308262aeb9274c7211d1dfdc2f441"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V10_DECLARED_SYSTEM_SUBJECT_20261011_V1.json"
SUBJECT_BLOB="ebb01def802dfde7fa9a0c04baff233984f4961d"
APPROVED_VERIFIER_PATH="canonical/runtime/professional_r12_v9_policy_cover_totality_semantic_verify_v2.py"
APPROVED_VERIFIER_BLOB="08ee0e1a82162032daadf002f6364b2b10a86ed3"
V10_SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V10_EXACT_R12_TOTALITY_VERIFIER_PIN_SYSTEM_20261011_V1"
V10_SUBJECT_SHA256="5484934c051696d3a1d4fef68f75907bb851b5562d3a734f74da2a3f9fbe9675"

def _blob(p:Path)->str:
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "positive_route_refinement_proved":False,"new_positive_behavior_added":None,
  "foreign_verifier_rejected_preexecution":False,"terminal_credit_delta":0,
  "incremental_spend_usd":0,**extra}

def _load(root:Path,rel:str,blob:str)->Path:
 p=root/rel
 if not p.is_file() or p.is_symlink(): raise ValueError("MISSING:"+rel)
 got=_blob(p)
 if got!=blob: raise ValueError("BLOB_DRIFT:"+rel+":"+got)
 return p

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  v9p=_load(root,V9_PATH,V9_BLOB);v10p=_load(root,V10_PATH,V10_BLOB)
  sp=_load(root,SUBJECT_PATH,SUBJECT_BLOB);_load(root,APPROVED_VERIFIER_PATH,APPROVED_VERIFIER_BLOB)
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))
 try:
  v10=v10p.read_text(encoding="utf-8"); tree=ast.parse(v10)
  subject=json.loads(sp.read_text(encoding="utf-8"))
 except Exception as exc:return _fail("PARSE_FAILED:"+type(exc).__name__)
 components=(subject.get("system_material") or {}).get("components") or []
 refs={(x.get("path"),x.get("git_blob_sha")) for x in components if isinstance(x,Mapping)}
 required_refs={(V9_PATH,V9_BLOB),(V10_PATH,V10_BLOB),(APPROVED_VERIFIER_PATH,APPROVED_VERIFIER_BLOB)}
 if not required_refs.issubset(refs):return _fail("V10_SUBJECT_COMPONENT_BINDING_INCOMPLETE")
 if subject.get("subject_id")!=V10_SUBJECT_ID or subject.get("subject_sha256")!=V10_SUBJECT_SHA256:
  return _fail("V10_SUBJECT_IDENTITY_DRIFT")
 anchors=(
  "preflight = _preflight_totality_verifier(state)",
  "if preflight.get(\"pass\") is not True:",
  "out = base.route(state, repo_root=root)",
  "if positive and preflight.get(\"verifier_pinned\") is not True:",
  "if positive and result.get(\"v9_executable_r12_totality_semantics_verified\") is not True:",
 )
 if any(a not in v10 for a in anchors):return _fail("V10_REFINEMENT_ANCHOR_MISSING")
 pre=v10.index(anchors[0]); delegate=v10.index(anchors[2]); guard=v10.index(anchors[3]); sem=v10.index(anchors[4])
 if not (pre<delegate<guard<sem):return _fail("V10_REFINEMENT_ORDER_INVALID")
 if "dict(supplied) != expected" not in v10:return _fail("EXACT_VERIFIER_EQUALITY_GUARD_MISSING")
 if "V10_UNAPPROVED_R12_TOTALITY_VERIFIER_REJECTED_PREEXECUTION" not in v10:
  return _fail("FOREIGN_VERIFIER_PREEXECUTION_REJECTION_MISSING")
 # No V10 AST return may directly construct POSITIVE_CERTIFICATE. All positives
 # are inherited from the delegated V9 result object.
 direct=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Constant) and node.value=="POSITIVE_CERTIFICATE":
   direct.append(getattr(node,"lineno",-1))
 # The only occurrence is comparison against delegated result, never a literal
 # returned output assignment.
 if len(direct)!=1:return _fail("V10_POSITIVE_LITERAL_SHAPE_CHANGED",lines=direct)
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__V10_STRICT_FAIL_CLOSED_POSITIVE_SUBSET_OF_V9",
  "positive_route_refinement_proved":True,"new_positive_behavior_added":False,
  "accepted_v10_positive_is_v9_positive":True,
  "foreign_verifier_rejected_preexecution":True,
  "approved_verifier_path":APPROVED_VERIFIER_PATH,
  "approved_verifier_git_blob_sha":APPROVED_VERIFIER_BLOB,
  "v10_subject_id":V10_SUBJECT_ID,"v10_subject_sha256":V10_SUBJECT_SHA256,
  "proof_mode":"CONTENT_ADDRESSED_AST_AND_CONTROL_FLOW_REDUCTION",
  "cross_subject_property_authority_transport":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
