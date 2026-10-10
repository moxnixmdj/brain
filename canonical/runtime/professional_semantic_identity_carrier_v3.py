"""Stable-authority identity-carrier factorization for V3 professional semantic claims.

Reuses the independently verified V2 identity-projection theorem. V3 changes only
claim admission: claims bind the immutable real mission authority and are checked
through coverage_claim_scope_guard_v2. No semantic property truth is granted.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import coverage_claim_scope_guard_v2 as guard_v2
from canonical.runtime import professional_semantic_identity_carrier_v2 as carrier_v2
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_V3"
BATCH_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_BATCH_V3"
EXPECTED_R12_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
PINS={
 "claim_pack_runtime":("canonical/runtime/professional_semantic_totality_claim_pack_v3.py","803bda772beaa11318ebaafb7f47e45512150e0b"),
 "base_identity_theorem":("canonical/runtime/professional_semantic_identity_carrier_v2.py","66d0cc279c581f82e703af8b878fcbe15af7fd01"),
 "stable_claim_guard":("canonical/runtime/coverage_claim_scope_guard_v2.py","f28a25ad29cec75fd76f50754ce9a36618583c8d"),
 "carrier_governance":("canonical/governance/MISSION_SUFFICIENT_SEMANTIC_CARRIER_V1.json","3c8da3adfcea2134dadae18634fc4dd7b14b19e7"),
}
MISSION_POINTER=pack_v3.MISSION_POINTER_PATH
MISSION_AUTHORITY=pack_v3.MISSION_AUTHORITY_PATH
MISSION_AUTHORITY_BLOB=pack_v3.EXPECTED_MISSION_AUTHORITY_BLOB

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError("NOT_OBJECT")
 return value

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "semantic_leaf_count":0,"factorization_pass_count":0,
  "mission_sufficient_carrier_factorization_proved_count":0,
  "semantic_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
  **extra,
 }

def evaluate_pack(
 pack:Mapping[str,Any],
 *,
 current_pointer:Mapping[str,Any],
 mission_authority:Mapping[str,Any],
 mission_authority_blob_sha:str,
)->dict[str,Any]:
 if not isinstance(pack,Mapping) or pack.get("pass") is not True:
  return _fail("V3_PACK_NOT_PASS")
 if pack.get("semantic_claim_count")!=12 or pack.get("unique_claim_id_count")!=12:
  return _fail("V3_PACK_SHAPE_INVALID")
 if pack.get("mission_blob_sha")!=mission_authority_blob_sha:
  return _fail("V3_PACK_MISSION_AUTHORITY_DRIFT")
 if pack.get("single_active_claim_policy_preserved") is not True:
  return _fail("V3_SINGLE_ACTIVE_CLAIM_POLICY_DRIFT")
 if pack.get("cross_claim_root_transport_authorized") is not False:
  return _fail("V3_CROSS_CLAIM_TRANSPORT_BOUNDARY_DRIFT")
 rows0=pack.get("claims")
 if not isinstance(rows0,list) or len(rows0)!=12:
  return _fail("V3_CLAIMS_NOT_12")
 rows=[]
 for row in sorted(rows0,key=lambda x:str((x or {}).get("leaf_id") or "")):
  if not isinstance(row,Mapping):
   return _fail("V3_CLAIM_ROW_INVALID")
  claim=row.get("frozen_claim")
  if not isinstance(claim,Mapping):
   return _fail("V3_FROZEN_CLAIM_MISSING",leaf_id=row.get("leaf_id"))
  admission=guard_v2.validate_claim(
   claim,
   current_pointer=current_pointer,
   mission_authority=mission_authority,
   mission_authority_blob_sha=mission_authority_blob_sha,
  )
  if admission.get("pass") is not True:
   return _fail("V3_STABLE_CLAIM_GUARD_REJECTED",leaf_id=row.get("leaf_id"),claim_guard=admission)
  cert=carrier_v2.build_certificate(row)
  verdict=carrier_v2.evaluate_claim(
   row,cert,current_mission_blob_sha=mission_authority_blob_sha
  )
  if verdict.get("pass") is not True:
   return _fail("V3_IDENTITY_FACTORIZATION_MEMBER_FAILED",leaf_id=row.get("leaf_id"),verdict=verdict)
  rows.append({
   "leaf_id":verdict["leaf_id"],
   "root_id":verdict["root_id"],
   "claim_id":verdict["claim_id"],
   "scope_sha256":verdict["scope_sha256"],
   "target_predicate_sha256":verdict["target_predicate_sha256"],
   "semantics_sha256":verdict["semantics_sha256"],
   "universal_factorization_proved":True,
  })
 ids=[r["claim_id"] for r in rows]
 if len(set(ids))!=12:
  return _fail("V3_CLAIM_IDENTITIES_NOT_UNIQUE")
 r12=next((r for r in rows if r["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"),None)
 if not r12 or r12["claim_id"]!=EXPECTED_R12_CLAIM_ID:
  return _fail("V3_R12_CLAIM_ID_DRIFT",observed_r12_claim_id=(r12 or {}).get("claim_id"))
 return {
  "schema":BATCH_SCHEMA,"pass":True,
  "status":"PASS__STABLE_V3_12_OF_12_SEMANTIC_CLAIMS_IDENTITY_CARRIER_FACTORIZATION",
  "semantic_leaf_count":12,"factorization_pass_count":12,"unique_claim_id_count":12,
  "mission_blob_sha":mission_authority_blob_sha,
  "r12_claim_id":r12["claim_id"],
  "rows":rows,
  "all_projection_total":True,"all_projection_injective":True,
  "all_semantic_information_loss_false":True,
  "mission_sufficient_carrier_factorization_proved_count":12,
  "property_truth_count_delta":0,
  "cross_claim_root_transport_authorized":False,
  "next":"INSTANTIATE_V3_CLAIM_SPECIFIC_CC_R1_CC_R2_CC_R3_R4__R12_FIRST_BY_EXISTING_PROOF_DENSITY",
  "semantic_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected: return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual,expected_blob=expected)
 try:
  pointer=_load(root/MISSION_POINTER)
  authority=_load(root/MISSION_AUTHORITY)
  governance=_load(root/PINS["carrier_governance"][0])
 except Exception as exc:
  return _fail("BOUND_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))
 if _blob(root/MISSION_AUTHORITY)!=MISSION_AUTHORITY_BLOB:
  return _fail("MISSION_AUTHORITY_BLOB_STALE")
 allowed=set(((governance.get("carrier_semantics") or {}).get("allowed_element_kinds") or []))
 if carrier_v2.CARRIER_KIND not in allowed:
  return _fail("CARRIER_KIND_NOT_ALLOWED")
 pack=pack_v3.verify(repo_root=root)
 return evaluate_pack(
  pack,current_pointer=pointer,mission_authority=authority,
  mission_authority_blob_sha=MISSION_AUTHORITY_BLOB,
 )

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
