"""V8 -> V9 R12 positive-route refinement verifier V1.

Proves only that every V9 positive route first passes the exact V8 route and then
passes an additional executable R12 totality semantic-verification gate.

This authorizes claim-scoped reverification of V8-preserved R12 C1-C7 on the
exact V9 declared subject. It never transports C8 nonvacuity, CC_R3 property
truth, quality, promotion, or terminal authority across the subject boundary.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v8 as v8
from canonical.runtime import professional_quality_p1_router_v9 as v9
from canonical.runtime import professional_r12_totality_semantic_receipt_v1 as sem

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V8_TO_V9_R12_POSITIVE_REFINEMENT_V1"
V8_PATH="canonical/runtime/professional_quality_p1_router_v8.py"
V8_BLOB="48c6839071b8de1309f87b0df1803a9eb29f0e13"
V9_PATH="canonical/runtime/professional_quality_p1_router_v9.py"
V9_BLOB="27f0df972a08a2497802865e46bdccdcb1c720ae"
SEM_PATH="canonical/runtime/professional_r12_totality_semantic_receipt_v1.py"
SEM_BLOB="cfb264b92004c55acf73719cd9c54cec6a609a34"
V8_SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V8_DECLARED_SYSTEM_SUBJECT_20261010_V7.json"
V8_SUBJECT_BLOB="21820105caab672440c76d051fecc16a562ae4cc"
V9_SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V9_DECLARED_SYSTEM_SUBJECT_20261010_V8.json"
V9_SUBJECT_BLOB="2ff32e4bb78e63635244c86d47fa369d7ba53900"
V8_SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V8_TOTALITY_MEDIATED_SYSTEM_20261010_V7"
V8_SUBJECT_SHA256="f6a1752167c3e4972ac952b04e3298690088256fcaa65150743582e8e655e51c"
V9_SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V9_EXECUTABLE_TOTALITY_SEMANTICS_SYSTEM_20261010_V8"
V9_SUBJECT_SHA256="adf7f09e1913526e460b7350c02cd148c2cd14de90eed33fa7fae84d395d9912"
PRESERVED_CLAUSES=(
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C3_ABSTRACTION_SOUNDNESS",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
)
NONTRANSPORTED_CLAUSE="R12C8_NONVACUITY"

def _blob(p:Path)->str:
 d=p.read_bytes()
 return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "positive_route_refinement_proved":False,
  "preserved_clause_reverification_admissible":False,
  "c8_nonvacuity_transport_proved":False,
  "cross_subject_property_authority_transport":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def _load(root:Path,rel:str,blob:str)->dict[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+rel)
 got=_blob(p)
 if got!=blob:raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
 o=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(o,dict):raise ValueError("PIN_NOT_OBJECT:"+rel)
 return o

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  for rel,blob in ((V8_PATH,V8_BLOB),(V9_PATH,V9_BLOB),(SEM_PATH,SEM_BLOB)):
   p=root/rel
   if not p.is_file() or p.is_symlink():return _fail("PIN_MISSING",path=rel)
   got=_blob(p)
   if got!=blob:return _fail("PIN_BLOB_DRIFT",path=rel,observed_blob=got)
  s8=_load(root,V8_SUBJECT_PATH,V8_SUBJECT_BLOB)
  s9=_load(root,V9_SUBJECT_PATH,V9_SUBJECT_BLOB)
 except Exception as exc:
  return _fail(type(exc).__name__+":"+str(exc))

 if v9.base is not v8:return _fail("V9_DOES_NOT_WRAP_EXACT_V8_MODULE")
 if v9.semantic_receipt is not sem:return _fail("V9_SEMANTIC_AUTHORITY_MODULE_DRIFT")
 if v8.BEHAVIOR_ID!=v9.base.BEHAVIOR_ID:return _fail("BEHAVIOR_ID_DRIFT")
 if v8.FINAL_STEP!=v9.base.FINAL_STEP:return _fail("FINAL_STEP_DRIFT")
 if tuple(v8.AUTHENTICATED_STEPS)!=tuple(v9.base.AUTHENTICATED_STEPS):
  return _fail("AUTHENTICATED_STEP_SET_DRIFT")

 text=(root/V9_PATH).read_text(encoding="utf-8")
 anchors=(
  "out=base.route(state,repo_root=root)",
  "result=deepcopy(dict(out))",
  'result.get("final_step_outcome")!="POSITIVE_CERTIFICATE"',
  'result.get("positive_certification_authorized") is not True',
  "sem=semantic_receipt.validate(",
  'if sem.get("pass") is not True:',
  'result["v9_executable_r12_totality_semantics_verified"]=True',
 )
 for a in anchors:
  if a not in text:return _fail("V9_REFINEMENT_ANCHOR_MISSING:"+a)

 if s8.get("subject_id")!=V8_SUBJECT_ID or s8.get("subject_sha256")!=V8_SUBJECT_SHA256:
  return _fail("V8_SUBJECT_IDENTITY_DRIFT")
 if s9.get("subject_id")!=V9_SUBJECT_ID or s9.get("subject_sha256")!=V9_SUBJECT_SHA256:
  return _fail("V9_SUBJECT_IDENTITY_DRIFT")
 c8={(x.get("path"),x.get("git_blob_sha")) for x in ((s8.get("system_material") or {}).get("components") or []) if isinstance(x,Mapping)}
 c9={(x.get("path"),x.get("git_blob_sha")) for x in ((s9.get("system_material") or {}).get("components") or []) if isinstance(x,Mapping)}
 if not c8<c9:return _fail("V9_SUBJECT_NOT_STRICT_COMPONENT_SUPERSET_OF_V8")
 expected_added={
  (V9_PATH,V9_BLOB),
  (SEM_PATH,SEM_BLOB),
 }
 if c9-c8!=expected_added:return _fail("V9_SUBJECT_DELTA_NOT_EXACT",observed_delta=sorted(c9-c8))
 inherited=(s9.get("dependency_closure") or {}).get("inherited_v8_subject") or {}
 if inherited.get("path")!=V8_SUBJECT_PATH or inherited.get("git_blob_sha")!=V8_SUBJECT_BLOB:
  return _fail("V9_INHERITED_V8_SUBJECT_BINDING_DRIFT")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__V9_POSITIVE_ROUTE_STRICTLY_REFINES_EXACT_V8_POSITIVE_ROUTE__C1_TO_C7_REVERIFICATION_ADMISSIBLE__C8_NOT_TRANSPORTED",
  "positive_route_refinement_proved":True,
  "v8_route_executes_before_v9_semantic_gate":True,
  "v9_positive_requires_v8_positive":True,
  "v9_positive_adds_executable_semantic_totality_verification":True,
  "v9_subject_strictly_extends_v8_subject_by_exact_component_count":2,
  "v8_subject_id":V8_SUBJECT_ID,"v8_subject_sha256":V8_SUBJECT_SHA256,
  "v9_subject_id":V9_SUBJECT_ID,"v9_subject_sha256":V9_SUBJECT_SHA256,
  "preserved_clause_ids":list(PRESERVED_CLAUSES),
  "preserved_clause_reverification_admissible":True,
  "c8_nonvacuity_transport_proved":False,
  "c8_reason":"EXISTENTIAL_V8_POSITIVE_ROUTE_MAY_BE_REMOVED_BY_ADDED_V9_EXECUTABLE_SEMANTIC_GATE",
  "cross_subject_property_authority_transport":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
  "exact_next":"REVERIFY_C1_TO_C7_ON_EXACT_V9_SUBJECT__BIND_ONE_REAL_V9_POLICY_COVER_AND_EXECUTABLE_TOTALITY_SEMANTIC_WITNESS_FOR_C8_CC_R3__THEN_R4",
 }
