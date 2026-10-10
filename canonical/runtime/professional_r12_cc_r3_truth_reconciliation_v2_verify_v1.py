"""Verify R12 CC_R3 truth reconciliation V2 = verified V1 + exact C3 proof."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping
ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_R12_CC_R3_TRUTH_RECONCILIATION_V2_VERIFY_V1"
V2="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V2.json"
PINS={
 "v1":("canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V1.json","b469e2f13c318d57aaca71d8b29ad1930636507d"),
 "c3":("canonical/verification/PROFESSIONAL_R12_C3_LOSSLESS_COMPOSITION_PROJECTION_VERIFY_20261010_V1.json","5965b692dc6bfcffda90cfcdf41fa760f67488d0"),
}
VERIFIED={
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION","R12C3_ABSTRACTION_SOUNDNESS",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH","R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY","R12C7_META_CONTROLLER_FALSIFICATION",
}
PARTIAL={"R12C1_ASSUMPTION_GUARANTEE_COMPOSITION","R12C8_NONVACUITY"}
def _blob(p:Path)->str:
 raw=p.read_bytes();return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def _load(p:Path):
 x=json.loads(p.read_text());assert isinstance(x,dict);return x
def _fail(reason:str,**x:Any):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "verified_clause_count":0,"partial_clause_count":0,"cc_r3_terminal_closure_proved":False,
 "semantic_property_truth_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**x}
def validate(v2:Mapping[str,Any],c3:Mapping[str,Any]):
 rows=v2.get("clause_state")
 if not isinstance(rows,list) or len(rows)!=8:return _fail("CLAUSE_ROWS_INVALID")
 states={r.get("id"):r.get("state") for r in rows if isinstance(r,Mapping)}
 if {k for k,v in states.items() if v=="VERIFIED_EXISTING"}!=VERIFIED:return _fail("VERIFIED_SET_DRIFT",states=states)
 if {k for k,v in states.items() if v=="PARTIAL_EXISTING_EVIDENCE"}!=PARTIAL:return _fail("PARTIAL_SET_DRIFT",states=states)
 d=v2.get("derived") or {}
 if d.get("verified_clause_count")!=6 or d.get("partial_clause_count")!=2 or d.get("open_clause_count")!=0:return _fail("DERIVED_COUNTS_INVALID")
 if set(d.get("partial_clause_ids") or [])!=PARTIAL:return _fail("DERIVED_PARTIAL_SET_INVALID")
 if d.get("stronger_target_residual_open") is not True or d.get("cc_r3_terminal_closure_proved") is not False:return _fail("TERMINAL_OR_STRONGER_RESIDUAL_OVERCLAIM")
 s=v2.get("stronger_target_residual") or {}
 if s.get("state")!="OPEN" or s.get("known_defeater_search_is_not_unknown_defeater_completeness") is not True:return _fail("STRONGER_TARGET_BOUNDARY_LOST")
 if not str(c3.get("status") or "").startswith("PASS__"):return _fail("C3_RECEIPT_NOT_PASS")
 if "R12C3_ABSTRACTION_SOUNDNESS_IS_PROVED_AT_THE_ROOT_BINDING_TO_SAME_SUBJECT_COMPOSITION_BOUNDARY" not in set(c3.get("proves") or []):return _fail("C3_PROOF_MISSING")
 if "NO_GLOBAL_SEMANTIC_COMPLETENESS_INSIDE_ANY_ROOT" not in set(c3.get("hard_nonclaims") or []):return _fail("C3_BOUNDARY_MISSING")
 return {"schema":SCHEMA,"pass":True,"status":"PASS__R12_CC_R3_V2__6_VERIFIED_2_PARTIAL__STRONGER_TOTALITY_OPEN",
 "verified_clause_count":6,"partial_clause_count":2,"verified_clause_ids":sorted(VERIFIED),"partial_clause_ids":sorted(PARTIAL),
 "stronger_material_defeater_totality_open":True,"cc_r3_terminal_closure_proved":False,
 "semantic_property_truth_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
def verify(repo_root=None):
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  for k,(rel,sha) in PINS.items():
   p=root/rel
   if not p.is_file() or _blob(p)!=sha:return _fail(k.upper()+"_BLOB_DRIFT")
  v2=_load(root/V2);c3=_load(root/PINS["c3"][0])
  return validate(v2,c3)
 except Exception as e:return _fail(type(e).__name__+":"+str(e))
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
