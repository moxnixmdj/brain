"""Independent-style verifier for the stable R12 coverage-root candidate registry.

This composes:
- stable mission-authority registry guard V2,
- exact active R12 frozen claim identity,
- executable semantic rerun of every PROVED_CURRENT root slot.

It certifies that CC_R1, CC_R2 and CC_R3 are current and derives R4 proof closure only after executable semantic rerun of all three.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime import coverage_root_certificate_registry_guard_v2 as guard
from canonical.runtime.coverage_root_semantic_receipt_v1 import validate_semantic_root_slot

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_ROOT_REGISTRY_VERIFY_V3"
REGISTRY_PATH="canonical/governance/COVERAGE_ROOT_REGISTRY_PROFESSIONAL_R12_SEMANTIC_20261011_V3.json"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
MISSION_AUTHORITY_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_AUTHORITY_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
MISSION_POINTER_PATH="canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
EXPECTED_PROVED=["CC_R1_REALITY_CONTAINMENT_V1","CC_R2_MISSION_SOUNDNESS_V1","CC_R3_TERMINAL_CLOSURE_V1"]
EXPECTED_OPEN=[]

def _blob(p:Path)->str:
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _fail(*errors:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
  "proved_root_count":0,"open_root_count":3,"r4_proof_closure":False,
  "semantic_property_truth_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,**extra}

def evaluate(registry:Mapping[str,Any],*,repo_root:Path)->dict[str,Any]:
 root=repo_root.resolve();errors=[]
 try:
  pointer=json.loads((root/MISSION_POINTER_PATH).read_text(encoding="utf-8"))
  authority_path=root/MISSION_AUTHORITY_PATH
  authority=json.loads(authority_path.read_text(encoding="utf-8"))
 except Exception:return _fail("MISSION_BINDING_LOAD_FAILED")
 if _blob(authority_path)!=MISSION_AUTHORITY_BLOB:return _fail("MISSION_AUTHORITY_BLOB_DRIFT")
 base=guard.validate(registry,current_mission_pointer=pointer,current_mission_authority=authority,current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB)
 if base.get("pass") is not True:errors.extend("REGISTRY:"+str(x) for x in base.get("errors") or ["INVALID"])
 active=registry.get("active_claim")
 if not isinstance(active,Mapping):errors.append("ACTIVE_CLAIM_MISSING");active={}
 if active.get("claim_id")!=CLAIM_ID:errors.append("ACTIVE_R12_CLAIM_ID_DRIFT")
 ref=active.get("claim_reference") or {}
 if not isinstance(ref,Mapping):errors.append("ACTIVE_CLAIM_REFERENCE_MISSING")
 else:
  p=root/str(ref.get("path") or "")
  if not p.is_file() or p.is_symlink():errors.append("ACTIVE_CLAIM_FILE_MISSING")
  elif _blob(p)!=ref.get("git_blob_sha"):errors.append("ACTIVE_CLAIM_BLOB_MISMATCH")
  else:
   try:frozen=json.loads(p.read_text(encoding="utf-8"))
   except Exception:frozen={};errors.append("ACTIVE_CLAIM_JSON_INVALID")
   for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id"):
    if frozen.get(k)!=active.get(k):errors.append("ACTIVE_CLAIM_REFERENCE_MISMATCH:"+k)

 semantic_results={}
 for slot in registry.get("certificate_slots") or []:
  if not isinstance(slot,Mapping):continue
  if slot.get("status")=="PROVED_CURRENT":
   out=validate_semantic_root_slot(root,slot,active)
   semantic_results[str(slot.get("root_id"))]=out
   if out.get("pass") is not True:errors.append("SEMANTIC_ROOT_REPLAY_FAILED:"+str(slot.get("root_id")))
 proved=list(base.get("proved_root_ids") or [])
 opened=list(base.get("open_root_ids") or [])
 if proved!=EXPECTED_PROVED:errors.append("PROVED_ROOT_SET_DRIFT")
 if opened!=EXPECTED_OPEN:errors.append("OPEN_ROOT_SET_DRIFT")
 if base.get("r4_proof_closure") is not True:errors.append("R4_NOT_CLOSED_AFTER_ALL_THREE_ROOTS")
 if registry.get("exact_remaining_root")!="CC_R3_TERMINAL_CLOSURE_V1":errors.append("REMAINING_ROOT_DRIFT")
 if registry.get("exact_remaining_obligation")!="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION":errors.append("REMAINING_OBLIGATION_DRIFT")
 if errors:return _fail(*errors,semantic_root_results=semantic_results)
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__STABLE_R12_ROOT_REGISTRY__CC_R1_CC_R2_CC_R3_PROVED_CURRENT__R4_PROOF_CLOSURE_TRUE__ZERO_TERMINAL_CREDIT",
  "claim_id":CLAIM_ID,"proved_root_ids":proved,"open_root_ids":opened,
  "proved_root_count":3,"open_root_count":0,"r4_proof_closure":True,
  "semantic_root_results":semantic_results,
  "exact_remaining_root":"CC_R3_TERMINAL_CLOSURE_V1",
  "exact_remaining_obligation":"ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION",
  "new_primitive_required":False,
  "semantic_property_truth_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"errors":[]}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 p=root/REGISTRY_PATH
 if not p.is_file() or p.is_symlink():return _fail("REGISTRY_FILE_MISSING")
 try:o=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return _fail("REGISTRY_JSON_INVALID")
 if not isinstance(o,dict):return _fail("REGISTRY_NOT_OBJECT")
 return evaluate(o,repo_root=root)
