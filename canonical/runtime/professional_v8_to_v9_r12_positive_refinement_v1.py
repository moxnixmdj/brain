"""Exact V8->V9 R12 refinement check. Zero property/terminal credit."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v8 as v8
from canonical.runtime import professional_quality_p1_router_v9 as v9
from canonical.runtime import professional_v8_r12_reuse_closure_v1 as reuse

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V8_TO_V9_R12_REFINEMENT_V1"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V9_DECLARED_SYSTEM_SUBJECT_20261010_V8.json"
SUBJECT_BLOB="2ff32e4bb78e63635244c86d47fa369d7ba53900"
VERIFY_PATH="canonical/verification/PROFESSIONAL_R12_V9_EXECUTABLE_TOTALITY_SEMANTIC_INDEPENDENT_VERIFY_20261010_V2.json"
VERIFY_BLOB="450b28d112be708bb65698581f64410e4991e86d"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V9_EXECUTABLE_TOTALITY_SEMANTICS_SYSTEM_20261010_V8"
SUBJECT_SHA256="adf7f09e1913526e460b7350c02cd148c2cd14de90eed33fa7fae84d395d9912"
PRESERVED=(
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION","R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C3_ABSTRACTION_SOUNDNESS","R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING","R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
)

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _fail(reason:str)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "positive_route_refinement_proved":False,"preserved_clause_reverification_admissible":False,
  "c8_nonvacuity_transport_proved":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 prior=reuse.verify_preserved_c1_c7(repo_root=root)
 if prior.get("pass") is not True or prior.get("preserved_c1_c7_v8_reverified") is not True:
  return _fail("V8_REUSE_PREMISE_NOT_PROVED")
 if tuple(prior.get("preserved_clause_ids") or ())!=PRESERVED:return _fail("PRESERVED_SET_DRIFT")
 if v9.base is not v8:return _fail("V9_NOT_EXACT_V8_WRAPPER")
 for rel,blob in ((SUBJECT_PATH,SUBJECT_BLOB),(VERIFY_PATH,VERIFY_BLOB)):
  p=root/rel
  if not p.is_file() or p.is_symlink() or _blob(p)!=blob:return _fail("PIN_INVALID:"+rel)
 subject=json.loads((root/SUBJECT_PATH).read_text())
 if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:
  return _fail("V9_SUBJECT_IDENTITY_DRIFT")
 paths={x.get("path") for x in (subject.get("system_material") or {}).get("components",[]) if isinstance(x,Mapping)}
 for rel in ("canonical/runtime/professional_quality_p1_router_v8.py",
             "canonical/runtime/professional_quality_p1_router_v9.py",
             "canonical/runtime/professional_r12_totality_semantic_receipt_v1.py"):
  if rel not in paths:return _fail("V9_COMPONENT_MISSING:"+rel)
 receipt=json.loads((root/VERIFY_PATH).read_text())
 proved=set(receipt.get("proves") or [])
 need={"V9_POSITIVE_PATH_REQUIRES_EXECUTABLE_R12_TOTALITY_SEMANTIC_VERIFICATION",
       "INDEPENDENT_RECEIPT_MUST_BIND_EXACT_RERUN_RESULT_SHA256",
       "V9_27_COMPONENT_DECLARED_SYSTEM_IS_CURRENT_ON_SECOND_CARRIER_AT_REBASED_MAIN"}
 if not need.issubset(proved):return _fail("V9_INDEPENDENT_PROOF_INCOMPLETE")
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__V9_STRICTLY_HARDENS_V8_POSITIVE_ROUTE__C1_TO_C7_REUSE_ADMISSIBLE__C8_OPEN",
  "positive_route_refinement_proved":True,"preserved_clause_reverification_admissible":True,
  "preserved_clause_ids":list(PRESERVED),"v9_subject_id":SUBJECT_ID,"v9_subject_sha256":SUBJECT_SHA256,
  "c8_nonvacuity_transport_proved":False,"cross_subject_property_authority_transport":False,
  "semantic_property_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
