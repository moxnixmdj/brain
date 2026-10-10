"""Current-claim identity carrier factorization for professional semantic leaves.

The current semantic property claims are frozen in the V2 claim pack.  For each
claim C, use the complete frozen claim world state itself as the carrier:

    Omega_C = W_C
    pi_C = identity

Then pi_C(w1) == pi_C(w2) implies w1 == w2, so any claim-bound mission function
M_C has equal outputs.  This is a universal formal reduction, not finite
sampling.  It proves only mission-sufficient carrier factorization.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import validate_claim

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_V2"
CERT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_CERTIFICATE_V2"
BATCH_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_BATCH_V2"
PACK_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_TOTALITY_FROZEN_CLAIM_PACK_20261010_V2.json"
MISSION_PATH="canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
EXPECTED_R12_CLAIM_ID="97ff74650749db87f378d5926ed820e004f3f792583c2c8455e51c3ccacbe7f7"
CARRIER_KIND="OTHER_TYPED_OBJECT_WITH_PROVED_MISSION_FACTORIZATION"
PROJECTION="IDENTITY_ON_COMPLETE_FROZEN_CLAIM_WORLD_STATE"
PROOF_MODE="FORMAL_REDUCTION__IDENTITY_FUNCTION_CONGRUENCE"
PINS={
 "claim_pack":(PACK_PATH,"f16aab3760d4f5958da986782632f3cb2bbd2646"),
 "claim_pack_verify":("canonical/verification/PROFESSIONAL_SEMANTIC_TOTALITY_CLAIM_PACK_VERIFY_20261010_V2.json","3d1f32e6e0e24d49c394daa365a7e3797c7d9984"),
 "carrier_governance":("canonical/governance/MISSION_SUFFICIENT_SEMANTIC_CARRIER_V1.json","3c8da3adfcea2134dadae18634fc4dd7b14b19e7"),
 "claim_guard":("canonical/runtime/coverage_claim_scope_guard_v1.py","d1de61aa9bc00a184772a50f7ec9d5ee2853d747"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _canon_sha(x:Any)->str:
 return sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "universal_factorization_proved":False,"semantic_information_loss":None,
  "leaf_property_truth_authority":False,"semantic_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
  **extra,
 }

def build_certificate(row:Mapping[str,Any])->dict[str,Any]:
 claim=row.get("frozen_claim") or {}
 cid=str(claim.get("claim_id") or "")
 world="W_CLAIM_WORLD_STATE:"+cid
 return {
  "schema":CERT_SCHEMA,
  "claim_id":cid,
  "mission_blob_sha":claim.get("mission_blob_sha"),
  "scope_sha256":claim.get("scope_sha256"),
  "target_predicate_sha256":claim.get("target_predicate_sha256"),
  "semantics_sha256":claim.get("semantics_sha256"),
  "leaf_id":row.get("leaf_id"),
  "root_id":row.get("root_id"),
  "carrier_kind":CARRIER_KIND,
  "world_space_id":world,
  "carrier_space_id":world,
  "projection":PROJECTION,
  "projection_total":True,
  "projection_injective":True,
  "semantic_information_loss":False,
  "carrier_abstraction_applied":False,
  "mission_function_domain":"EXACT_COMPLETE_FROZEN_CLAIM_WORLD_STATE",
  "factorization":{
   "formula":"FOR_ALL_w1_w2_IN_W_C__pi_C(w1)=pi_C(w2)_IMPLIES_M_C(w1)=M_C(w2)",
   "proof_mode":PROOF_MODE,
   "premises":[
    "OMEGA_C_EQUALS_W_C",
    "PI_C_IS_IDENTITY_ON_W_C",
    "IDENTITY_EQUAL_OUTPUT_IMPLIES_EQUAL_INPUT",
    "M_C_IS_A_FUNCTION_ON_W_C",
   ],
   "derivation":[
    "ASSUME_PI_C_W1_EQUALS_PI_C_W2",
    "SUBSTITUTE_IDENTITY_TO_DERIVE_W1_EQUALS_W2",
    "APPLY_FUNCTION_CONGRUENCE_TO_M_C",
    "DERIVE_M_C_W1_EQUALS_M_C_W2",
   ],
   "universal_not_sampled":True,
   "universal_factorization_proved":True,
  },
  "terminal_credit_delta":0,
  "incremental_spend_usd":0,
 }

def evaluate_claim(row:Mapping[str,Any],certificate:Mapping[str,Any],*,current_mission_blob_sha:str)->dict[str,Any]:
 if not isinstance(row,Mapping) or not isinstance(certificate,Mapping):
  return _fail("INPUT_NOT_MAPPING")
 claim=row.get("frozen_claim")
 if not isinstance(claim,Mapping):
  return _fail("FROZEN_CLAIM_MISSING")
 leaf_id=row.get("leaf_id")
 root_id=row.get("root_id")
 target=row.get("target_predicate")
 semantics=row.get("semantics")
 if not isinstance(leaf_id,str) or not leaf_id.endswith("::SEMANTIC"):
  return _fail("SEMANTIC_LEAF_ID_INVALID")
 if not isinstance(root_id,str) or not root_id:
  return _fail("ROOT_ID_INVALID")
 if not isinstance(target,Mapping) or target.get("leaf_id")!=leaf_id:
  return _fail("TARGET_PREDICATE_LEAF_BINDING_INVALID")
 if not isinstance(semantics,Mapping) or (semantics.get("bounded_witnesses_are_totality_authority") is not False):
  return _fail("SEMANTICS_OBJECT_INVALID")
 if row.get("scope_definition_sha256")!=claim.get("scope_sha256"):
  return _fail("ROW_SCOPE_CLAIM_SCOPE_MISMATCH")
 if _canon_sha(target)!=claim.get("target_predicate_sha256"):
  return _fail("TARGET_PREDICATE_HASH_MISMATCH")
 if _canon_sha(semantics)!=claim.get("semantics_sha256"):
  return _fail("SEMANTICS_HASH_MISMATCH")
 if claim.get("mission_blob_sha")!=current_mission_blob_sha:
  return _fail("CURRENT_MISSION_BINDING_STALE")
 guard=validate_claim(claim,current_mission_blob_sha=current_mission_blob_sha)
 if guard.get("pass") is not True:
  return _fail("CLAIM_GUARD_REJECTED",claim_guard=guard)
 expected=build_certificate(row)
 for field in (
  "schema","claim_id","mission_blob_sha","scope_sha256","target_predicate_sha256",
  "semantics_sha256","leaf_id","root_id","carrier_kind","world_space_id",
  "carrier_space_id","projection","projection_total","projection_injective",
  "semantic_information_loss","carrier_abstraction_applied","mission_function_domain",
 ):
  if certificate.get(field)!=expected.get(field):
   return _fail("IDENTITY_CARRIER_BINDING_DRIFT:"+field)
 if certificate.get("world_space_id")!=certificate.get("carrier_space_id"):
  return _fail("CARRIER_SPACE_NOT_IDENTICAL_TO_WORLD_SPACE")
 f=certificate.get("factorization")
 if not isinstance(f,Mapping):
  return _fail("FACTORIZATION_PROOF_MISSING")
 for field in ("formula","proof_mode","premises","derivation","universal_not_sampled","universal_factorization_proved"):
  if f.get(field)!=expected["factorization"].get(field):
   return _fail("FACTORIZATION_PROOF_DRIFT:"+field)
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__CURRENT_CLAIM_SCOPED_IDENTITY_CARRIER_UNIVERSAL_FACTORIZATION",
  "leaf_id":leaf_id,"root_id":root_id,"claim_id":claim["claim_id"],
  "mission_blob_sha":claim["mission_blob_sha"],"scope_sha256":claim["scope_sha256"],
  "target_predicate_sha256":claim["target_predicate_sha256"],
  "semantics_sha256":claim["semantics_sha256"],
  "carrier_kind":CARRIER_KIND,"projection":PROJECTION,
  "projection_total":True,"projection_injective":True,
  "semantic_information_loss":False,"carrier_abstraction_applied":False,
  "universal_factorization_proved":True,
  "proof_basis":"IDENTITY_PROJECTION_PLUS_FUNCTION_CONGRUENCE__NO_FINITE_WITNESS_SET",
  "leaf_property_truth_authority":False,"semantic_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def evaluate_pack(pack:Mapping[str,Any],*,current_mission_blob_sha:str)->dict[str,Any]:
 if not isinstance(pack,Mapping):
  return _fail("PACK_NOT_MAPPING")
 if pack.get("pass") is not True or pack.get("semantic_claim_count")!=12 or pack.get("unique_claim_id_count")!=12:
  return _fail("CURRENT_SEMANTIC_PACK_NOT_VERIFIED_SHAPE")
 if pack.get("mission_blob_sha")!=current_mission_blob_sha:
  return _fail("PACK_MISSION_BINDING_STALE")
 if pack.get("single_active_claim_policy_preserved") is not True or pack.get("cross_claim_root_transport_authorized") is not False:
  return _fail("PACK_CLAIM_AUTHORITY_BOUNDARY_INVALID")
 claims=pack.get("claims")
 if not isinstance(claims,list) or len(claims)!=12:
  return _fail("SEMANTIC_CLAIM_SET_NOT_12")
 leaf_ids=[x.get("leaf_id") for x in claims if isinstance(x,Mapping)]
 claim_ids=[(x.get("frozen_claim") or {}).get("claim_id") for x in claims if isinstance(x,Mapping)]
 if len(leaf_ids)!=12 or len(set(leaf_ids))!=12 or len(claim_ids)!=12 or len(set(claim_ids))!=12:
  return _fail("SEMANTIC_CLAIM_IDENTITIES_NOT_UNIQUE")
 rows=[]
 for row in sorted(claims,key=lambda x:str(x.get("leaf_id") or "")):
  cert=build_certificate(row)
  verdict=evaluate_claim(row,cert,current_mission_blob_sha=current_mission_blob_sha)
  if verdict.get("pass") is not True:
   return _fail("IDENTITY_CARRIER_BATCH_MEMBER_FAILED",leaf_id=row.get("leaf_id"),verdict=verdict)
  rows.append({
   "leaf_id":verdict["leaf_id"],"claim_id":verdict["claim_id"],
   "scope_sha256":verdict["scope_sha256"],"target_predicate_sha256":verdict["target_predicate_sha256"],
   "semantics_sha256":verdict["semantics_sha256"],"universal_factorization_proved":True,
  })
 r12=next((x for x in rows if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"),None)
 if not r12 or r12["claim_id"]!=EXPECTED_R12_CLAIM_ID:
  return _fail("R12_CURRENT_CLAIM_ID_DRIFT",observed_r12_claim_id=(r12 or {}).get("claim_id"))
 return {
  "schema":BATCH_SCHEMA,"pass":True,
  "status":"PASS__CURRENT_V2_12_OF_12_SEMANTIC_CLAIMS_IDENTITY_CARRIER_FACTORIZATION",
  "semantic_leaf_count":12,"factorization_pass_count":12,"unique_claim_id_count":12,
  "mission_blob_sha":current_mission_blob_sha,"r12_claim_id":r12["claim_id"],
  "all_projection_total":True,"all_projection_injective":True,
  "all_semantic_information_loss_false":True,"rows":rows,
  "mission_sufficient_carrier_factorization_proved_count":12,
  "property_truth_count_delta":0,
  "next":"REMOVE_CURRENT_CARRIER_FACTORIZATION_FROM_ALL_12_SEMANTIC_CLAIM_CUTS__INSTANTIATE_CLAIM_SPECIFIC_CC_R1_CC_R2_CC_R3_R4",
  "leaf_property_truth_authority":False,"semantic_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():
   return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:
   return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual,expected_blob=expected)
 try:
  pack=json.loads((root/PACK_PATH).read_text(encoding="utf-8"))
  pack_verify=json.loads((root/PINS["claim_pack_verify"][0]).read_text(encoding="utf-8"))
  carrier=json.loads((root/PINS["carrier_governance"][0]).read_text(encoding="utf-8"))
 except Exception as exc:
  return _fail("BOUND_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))
 mission=root/MISSION_PATH
 if not mission.is_file() or mission.is_symlink():
  return _fail("CURRENT_MISSION_POINTER_MISSING")
 mission_blob=_blob(mission)
 subj=pack_verify.get("subject") or {}
 frozen=(subj.get("frozen_claim_pack") or {})
 if frozen.get("git_blob_sha")!=PINS["claim_pack"][1]:
  return _fail("PACK_VERIFY_SUBJECT_MISMATCH")
 if (pack_verify.get("frozen_claims") or {}).get("semantic_claim_count")!=12:
  return _fail("PACK_VERIFY_COUNT_MISMATCH")
 allowed=set(((carrier.get("carrier_semantics") or {}).get("allowed_element_kinds") or []))
 if CARRIER_KIND not in allowed:
  return _fail("CARRIER_KIND_NOT_ALLOWED_BY_GOVERNANCE")
 return evaluate_pack(pack,current_mission_blob_sha=mission_blob)

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
