"""Verify R12 semantic CC_R3 reuse cut V2 as exact V1 + C5 delta."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_CC_R3_REUSE_CUT_V2_VERIFY_V1"
CUT="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_REUSE_CUT_20261010_V2.json"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
EXPECTED_IDS=[
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C3_ABSTRACTION_SOUNDNESS",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
 "R12C8_NONVACUITY",
]
PROVED={"R12C2_SAME_SUBJECT_ROOT_CONJUNCTION","R12C3_ABSTRACTION_SOUNDNESS","R12C5_COVERAGE_ACCOUNTING"}
PINS={
 "v1_cut":("canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_REUSE_CUT_20261010_V1.json","4f71b36b76c3bab197fd42b6374f0825fcae6e15"),
 "v1_verify":("canonical/verification/PROFESSIONAL_R12_SEMANTIC_CC_R3_REUSE_CUT_VERIFY_20261010_V1.json","63e29cd1b85a0f61830aa0c315c2f9360d7ecec3"),
 "c5_verify":("canonical/verification/PROFESSIONAL_R12_SEMANTIC_C5_CLAIM_BOUND_VERIFY_20261010_V1.json","c3f390a230ba6e9dc6bd3f14c3e878fae9315c77"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 x=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(x,dict):raise ValueError("NOT_OBJECT")
 return x

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "proved_by_reuse_count":0,"open_root_contract_clause_count":8,
  "cc_r3_terminal_closure_proved":False,"semantic_property_truth_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,**extra,
 }

def validate(cut:Mapping[str,Any],v1:Mapping[str,Any],c5:Mapping[str,Any])->dict[str,Any]:
 if not all(isinstance(x,Mapping) for x in (cut,v1,c5)):return _fail("INPUT_NOT_MAPPING")
 if cut.get("claim_id")!=CLAIM_ID:return _fail("CUT_CLAIM_ID_DRIFT")
 if not str(v1.get("status") or "").startswith("PASS__"):return _fail("V1_VERIFY_NOT_PASS")
 v1proved=(v1.get("proved") or {})
 if v1proved.get("proved_by_reuse_count")!=2 or set(v1proved.get("proved_clause_ids") or [])!={"R12C2_SAME_SUBJECT_ROOT_CONJUNCTION","R12C3_ABSTRACTION_SOUNDNESS"}:
  return _fail("V1_PROVED_SET_DRIFT")
 if not str(c5.get("status") or "").startswith("PASS__"):return _fail("C5_VERIFY_NOT_PASS")
 if c5.get("subject",{}).get("claim_id")!=CLAIM_ID:return _fail("C5_CLAIM_ID_DRIFT")
 if "R12C5_COVERAGE_ACCOUNTING_IS_PROVED_FOR_THE_EXACT_FROZEN_CLAIM" not in set(c5.get("proves") or []):
  return _fail("C5_EXACT_PROOF_MISSING")
 if "NO_MATERIAL_DEFEATER_TOTALITY" not in set(c5.get("hard_nonclaims") or []):
  return _fail("C5_TOTALITY_BOUNDARY_LOST")

 rows=cut.get("clause_reuse")
 if not isinstance(rows,list) or len(rows)!=8:return _fail("CUT_ROWS_INVALID")
 ids=[r.get("id") for r in rows if isinstance(r,Mapping)]
 if ids!=EXPECTED_IDS:return _fail("CUT_ID_ORDER_DRIFT")
 by={r["id"]:r for r in rows}
 observed={cid for cid,row in by.items() if row.get("state")=="PROVED_BY_REUSE"}
 if observed!=PROVED:return _fail("CUT_PROVED_SET_OVER_OR_UNDERCLAIM",observed=sorted(observed))
 for cid in set(EXPECTED_IDS)-PROVED:
  if by[cid].get("state")!="OPEN":return _fail("CUT_OPEN_SET_OVERCLAIM",clause_id=cid)
 c5row=by["R12C5_COVERAGE_ACCOUNTING"]
 if c5row.get("proof_source")!="r12_c5_claim_bound":return _fail("C5_PROOF_SOURCE_DRIFT")

 derived=cut.get("derived") or {}
 if derived.get("proved_by_reuse_count")!=3 or derived.get("open_root_contract_clause_count")!=5:
  return _fail("DERIVED_COUNTS_INVALID")
 if set(derived.get("proved_by_reuse_clause_ids") or [])!=PROVED:
  return _fail("DERIVED_PROVED_SET_INVALID")
 if set(derived.get("open_root_contract_clause_ids") or [])!=set(EXPECTED_IDS)-PROVED:
  return _fail("DERIVED_OPEN_SET_INVALID")
 if derived.get("cc_r3_terminal_closure_proved") is not False:
  return _fail("CC_R3_PREMATURE_CLOSURE")

 stronger=cut.get("stronger_target_predicate_residual") or {}
 if (
  stronger.get("state")!="OPEN"
  or stronger.get("unknown_defeater_completeness_proved") is not False
  or stronger.get("not_counted_as_one_of_the_eight_root_contract_clauses") is not True
 ):
  return _fail("STRONGER_TARGET_RESIDUAL_OVERCLAIM")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_CC_R3_REUSE_CUT_V2__C2_C3_C5_PROVED__FIVE_ROOT_CLAUSES_PLUS_STRONGER_TOTALITY_OPEN",
  "claim_id":CLAIM_ID,
  "proved_by_reuse_clause_ids":sorted(PROVED),
  "open_root_contract_clause_ids":sorted(set(EXPECTED_IDS)-PROVED),
  "proved_by_reuse_count":3,"open_root_contract_clause_count":5,
  "stronger_material_defeater_obligation_open":True,
  "unknown_defeater_completeness_proved":False,
  "cc_r3_terminal_closure_proved":False,
  "semantic_property_truth_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  cut=_load(root/CUT)
  docs={}
  for key,(rel,expected) in PINS.items():
   p=root/rel
   if not p.is_file() or p.is_symlink():return _fail(key.upper()+"_MISSING")
   actual=_blob(p)
   if actual!=expected:return _fail(key.upper()+"_BLOB_DRIFT",observed=actual)
   docs[key]=_load(p)
  return validate(cut,docs["v1_verify"],docs["c5_verify"])
 except Exception as exc:
  return _fail(type(exc).__name__+":"+str(exc))

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
