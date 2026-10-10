"""Verify current R12 CC_R3 truth: all eight root-contract clauses verified,
while the stronger material-defeater totality obligation remains open.

This is a reconciliation theorem only. It does not grant CC_R3 terminal closure,
semantic property truth, R4 proof realization, quality, acceptance, promotion,
or terminal authority.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_R12_CC_R3_TRUTH_RECONCILIATION_V3_VERIFY_V1"
PROPERTY_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
V3_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
PINS={
 "v2":("canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V2.json","ba25f3b35093c7e8372fd6f14fe63441880774a8"),
 "v2_verify":("canonical/verification/PROFESSIONAL_R12_CC_R3_TRUTH_RECONCILIATION_V2_VERIFY_20261010_V1.json","3159755d347502597b50721d6b624f176bf45fb8"),
 "c1":("canonical/verification/PROFESSIONAL_R12_STABLE_C1_INDEPENDENT_VERIFY_20261010_V1.json","42b16818beca1d5f624b817fa68761a4ba795e37"),
 "c8":("canonical/verification/PROFESSIONAL_R12_C8_NONVACUITY_INDEPENDENT_VERIFY_20261010_V1.json","077de7c62f3ab2df1a7ddbb3836f38450345d8f6"),
}
ALL_CLAUSES={
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C3_ABSTRACTION_SOUNDNESS",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
 "R12C8_NONVACUITY",
}
PREVIOUS_VERIFIED=ALL_CLAUSES-{
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
 "R12C8_NONVACUITY",
}

def _blob(p:Path)->str:
 raw=p.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(p:Path)->dict[str,Any]:
 x=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(x,dict): raise ValueError("JSON_OBJECT_REQUIRED")
 return x

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "property_claim_id":PROPERTY_CLAIM_ID,"scope_claim_id":SCOPE_CLAIM_ID,
  "leaf_id":LEAF_ID,"verified_clause_count":0,"partial_clause_count":0,
  "open_clause_count":8,"all_eight_root_contract_clauses_verified":False,
  "stronger_material_defeater_totality_proved":False,
  "claim_scoped_totality_proved":False,"cc_r3_terminal_closure_proved":False,
  "semantic_property_truth_authority":False,"r4_proof_realization_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def validate(
 v3:Mapping[str,Any],
 v2:Mapping[str,Any],
 v2_verify:Mapping[str,Any],
 c1:Mapping[str,Any],
 c8:Mapping[str,Any],
)->dict[str,Any]:
 if not all(isinstance(x,Mapping) for x in (v3,v2,v2_verify,c1,c8)):
  return _fail("INPUT_NOT_MAPPING")
 if v3.get("property_claim_id")!=PROPERTY_CLAIM_ID or v3.get("scope_claim_id")!=SCOPE_CLAIM_ID:
  return _fail("V3_CLAIM_IDENTITY_DRIFT")
 if v3.get("leaf_id")!=LEAF_ID:return _fail("V3_LEAF_DRIFT")

 if not str(v2_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE__5_OF_5"):
  return _fail("V2_RECONCILIATION_VERIFY_NOT_PASS")
 truth=v2_verify.get("truth") or {}
 if truth.get("verified_clause_count")!=6 or truth.get("partial_clause_count")!=2:
  return _fail("V2_RECONCILIATION_COUNTS_DRIFT")
 if set(truth.get("verified_clause_ids") or [])!=PREVIOUS_VERIFIED:
  return _fail("V2_VERIFIED_CLAUSE_SET_DRIFT")
 if set(truth.get("partial_clause_ids") or [])!={ALL_CLAUSES.pop() if False else "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION","R12C8_NONVACUITY"}:
  return _fail("V2_PARTIAL_CLAUSE_SET_DRIFT")
 if truth.get("stronger_material_defeater_totality_open") is not True:
  return _fail("V2_STRONGER_TOTALITY_BOUNDARY_LOST")
 if truth.get("cc_r3_terminal_closure_proved") is not False:
  return _fail("V2_CC_R3_OVERCLAIM")

 if c1.get("stable_claim",{}).get("claim_id")!=PROPERTY_CLAIM_ID:
  return _fail("C1_PROPERTY_CLAIM_DRIFT")
 if c1.get("c1_assumption_guarantee_composition_proved") is not True:
  return _fail("C1_NOT_PROVED")
 if c1.get("cc_r3_terminal_closure_proved") is not False:
  return _fail("C1_CC_R3_OVERCLAIM")
 if c1.get("semantic_property_truth_authority") is not False:
  return _fail("C1_PROPERTY_OVERCLAIM")

 c8truth=c8.get("truth") or {}
 if c8truth.get("c8_nonvacuity_proved") is not True:
  return _fail("C8_NOT_PROVED")
 if c8truth.get("independently_observed_positive_route_count",0)<1:
  return _fail("C8_POSITIVE_ROUTE_MISSING")
 if c8truth.get("stronger_material_defeater_totality_proved") is not False:
  return _fail("C8_TOTALITY_OVERCLAIM")
 if c8truth.get("semantic_property_truth_authority") is not False:
  return _fail("C8_PROPERTY_OVERCLAIM")

 rows=v3.get("clause_state")
 if not isinstance(rows,list) or len(rows)!=8:return _fail("V3_CLAUSE_ROWS_INVALID")
 states={r.get("id"):r.get("state") for r in rows if isinstance(r,Mapping)}
 if set(states)!=ALL_CLAUSES:return _fail("V3_CLAUSE_SET_INVALID",states=states)
 if any(v!="VERIFIED_CURRENT" for v in states.values()):
  return _fail("V3_NOT_ALL_CLAUSES_VERIFIED",states=states)
 d=v3.get("derived") or {}
 if d.get("verified_clause_count")!=8 or d.get("partial_clause_count")!=0 or d.get("open_clause_count")!=0:
  return _fail("V3_DERIVED_COUNTS_INVALID")
 if d.get("all_eight_root_contract_clauses_verified") is not True:
  return _fail("V3_EIGHT_CLAUSE_FLAG_MISSING")
 if d.get("stronger_target_residual_open") is not True:
  return _fail("V3_STRONGER_TARGET_RESIDUAL_MUST_REMAIN_OPEN")
 if d.get("cc_r3_terminal_closure_proved") is not False:
  return _fail("V3_CC_R3_OVERCLAIM")

 stronger=v3.get("stronger_target_residual") or {}
 if stronger.get("state")!="OPEN":
  return _fail("V3_STRONGER_TARGET_STATE_NOT_OPEN")
 if stronger.get("obligation")!="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION":
  return _fail("V3_STRONGER_TARGET_OBLIGATION_DRIFT")
 if stronger.get("known_defeater_search_is_not_unknown_defeater_completeness") is not True:
  return _fail("V3_UNKNOWN_DEFEATER_BOUNDARY_LOST")

 for field in (
  "claim_scoped_totality_proved","cc_r3_terminal_closure_proved",
  "semantic_property_truth_authority","r4_proof_realization_authority",
  "quality_authority","acceptance_authority","promotion_authority","terminal_authority"
 ):
  if v3.get(field) is not False:return _fail("V3_AUTHORITY_OVERCLAIM:"+field)

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_CC_R3_V3__8_OF_8_ROOT_CONTRACT_CLAUSES_VERIFIED__STRONGER_MATERIAL_DEFEATER_TOTALITY_OPEN__ZERO_PROPERTY_OR_TERMINAL_CREDIT",
  "property_claim_id":PROPERTY_CLAIM_ID,"scope_claim_id":SCOPE_CLAIM_ID,
  "leaf_id":LEAF_ID,"verified_clause_count":8,"partial_clause_count":0,
  "open_clause_count":0,"verified_clause_ids":sorted(ALL_CLAUSES),
  "all_eight_root_contract_clauses_verified":True,
  "stronger_material_defeater_totality_proved":False,
  "claim_scoped_totality_proved":False,"cc_r3_terminal_closure_proved":False,
  "semantic_property_truth_authority":False,"r4_proof_realization_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  docs={}
  for key,(rel,sha) in PINS.items():
   p=root/rel
   if not p.is_file() or p.is_symlink():return _fail("PIN_MISSING:"+key)
   actual=_blob(p)
   if actual!=sha:return _fail("PIN_BLOB_DRIFT:"+key,expected=sha,observed=actual)
   docs[key]=_load(p)
  v3p=root/V3_PATH
  if not v3p.is_file() or v3p.is_symlink():return _fail("V3_RECONCILIATION_MISSING")
  return validate(_load(v3p),docs["v2"],docs["v2_verify"],docs["c1"],docs["c8"])
 except Exception as exc:
  return _fail("VERIFY_EXCEPTION",detail=type(exc).__name__+":"+str(exc))

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
