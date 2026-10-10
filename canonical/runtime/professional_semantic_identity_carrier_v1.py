"""Claim-scoped lossless identity semantic carrier for professional leaves.

The coverage-completeness theorem requires a mission-sufficient carrier before
claim-scoped root closure.  Compression is optional.  The identity projection
is the correctness baseline:

    Omega_C = W_C
    pi_C(w) = w

Therefore pi_C(w1) == pi_C(w2) implies w1 == w2, and because M_C is a
function on W_C, M_C(w1) == M_C(w2).  No finite witness set is used and no
mission-relevant distinction can be erased.

This proves carrier factorization only.  It grants no leaf property truth,
quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime.coverage_claim_scope_guard_v1 import validate_claim

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_V1"
CERT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_CERTIFICATE_V1"
BATCH_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_BATCH_V1"
EPOCH="2026-10-10T18:05:00+02:00"
MISSION_BLOB=domain.MISSION_BLOB
CARRIER_KIND="OTHER_TYPED_OBJECT_WITH_PROVED_MISSION_FACTORIZATION"
PROJECTION="IDENTITY_ON_COMPLETE_FROZEN_CLAIM_WORLD_STATE"
PROOF_MODE="FORMAL_REDUCTION__IDENTITY_FUNCTION_CONGRUENCE"
SEMANTIC_SUFFIX="::SEMANTIC"
EXPECTED_R12_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "domain_runtime":("canonical/runtime/professional_quality_whole_leaf_domain_equivalence_v1.py","76bf7e1a6f26ff3664ed8c355dff8a688b074159"),
 "domain_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "carrier_governance":("canonical/governance/MISSION_SUFFICIENT_SEMANTIC_CARRIER_V1.json","3c8da3adfcea2134dadae18634fc4dd7b14b19e7"),
 "claim_guard":("canonical/runtime/coverage_claim_scope_guard_v1.py","d1de61aa9bc00a184772a50f7ec9d5ee2853d747"),
 "mission_authority":("canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json","13c470645b037bbb46245c687dd35197b420d51a"),
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

def build_certificate(claim_scope:Mapping[str,Any])->dict[str,Any]:
 claim=claim_scope.get("claim") or {}
 cid=str(claim.get("claim_id") or "")
 world="W_CLAIM_WORLD_STATE:"+cid
 return {
  "schema":CERT_SCHEMA,
  "claim_id":cid,
  "scope_sha256":claim.get("scope_sha256"),
  "semantics_sha256":claim.get("semantics_sha256"),
  "leaf_id":claim_scope.get("leaf_id"),
  "root_id":claim_scope.get("root_id"),
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
  "hard_nonclaims":[
    "NO_LEAF_PROPERTY_TRUTH",
    "NO_ROOT_CLOSURE",
    "NO_GLOBAL_MISSION_COMPLETION",
    "NO_CARRIER_COMPRESSION_OR_EFFICIENCY_CLAIM",
    "NO_QUALITY_ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY",
  ],
  "terminal_credit_delta":0,
  "incremental_spend_usd":0,
 }

def evaluate(manifest:Mapping[str,Any],claim_scope:Mapping[str,Any],certificate:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(manifest,Mapping) or not isinstance(claim_scope,Mapping) or not isinstance(certificate,Mapping):
  return _fail("INPUT_NOT_MAPPING")
 dv=domain.evaluate(manifest,claim_scope)
 if dv.get("pass") is not True or dv.get("whole_leaf_domain_equivalence_proved") is not True:
  return _fail("WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED",domain_verdict=dv)
 claim=claim_scope.get("claim")
 if not isinstance(claim,Mapping):
  return _fail("CLAIM_MISSING")
 guard=validate_claim(claim,current_mission_blob_sha=MISSION_BLOB)
 if guard.get("pass") is not True:
  return _fail("CLAIM_GUARD_REJECTED",claim_guard=guard)
 expected=build_certificate(claim_scope)
 fixed=(
  "schema","claim_id","scope_sha256","semantics_sha256","leaf_id","root_id",
  "carrier_kind","world_space_id","carrier_space_id","projection",
  "projection_total","projection_injective","semantic_information_loss",
  "carrier_abstraction_applied","mission_function_domain",
 )
 for field in fixed:
  if certificate.get(field)!=expected.get(field):
   return _fail("IDENTITY_CARRIER_BINDING_DRIFT:"+field)
 if certificate.get("world_space_id")!=certificate.get("carrier_space_id"):
  return _fail("CARRIER_SPACE_NOT_IDENTICAL_TO_WORLD_SPACE")
 if certificate.get("projection")!=PROJECTION:
  return _fail("PROJECTION_NOT_IDENTITY")
 if certificate.get("projection_total") is not True:
  return _fail("IDENTITY_PROJECTION_TOTALITY_REQUIRED")
 if certificate.get("projection_injective") is not True:
  return _fail("IDENTITY_PROJECTION_INJECTIVITY_REQUIRED")
 if certificate.get("semantic_information_loss") is not False:
  return _fail("SEMANTIC_INFORMATION_LOSS_FORBIDDEN")
 if certificate.get("carrier_abstraction_applied") is not False:
  return _fail("IDENTITY_CARRIER_ABSTRACTION_FORBIDDEN")
 f=certificate.get("factorization")
 ef=expected["factorization"]
 if not isinstance(f,Mapping):
  return _fail("FACTORIZATION_PROOF_MISSING")
 for field in ("formula","proof_mode","premises","derivation","universal_not_sampled","universal_factorization_proved"):
  if f.get(field)!=ef.get(field):
   return _fail("FACTORIZATION_PROOF_DRIFT:"+field)
 if f.get("universal_not_sampled") is not True or f.get("universal_factorization_proved") is not True:
  return _fail("UNIVERSAL_FORMAL_PROOF_REQUIRED")
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__CLAIM_SCOPED_IDENTITY_CARRIER_UNIVERSAL_FACTORIZATION",
  "leaf_id":claim_scope["leaf_id"],"root_id":claim_scope["root_id"],
  "claim_id":claim["claim_id"],"scope_sha256":claim["scope_sha256"],
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

def batch(manifest:Mapping[str,Any],*,epoch:str=EPOCH)->dict[str,Any]:
 semantic=[]
 for row in manifest.get("roots") or []:
  if not isinstance(row,Mapping): continue
  leaf=row.get("semantic_leaf")
  if isinstance(leaf,Mapping) and isinstance(leaf.get("id"),str):
   semantic.append(leaf["id"])
 if len(semantic)!=12 or len(set(semantic))!=12:
  return _fail("SEMANTIC_LEAF_SET_NOT_12",observed_count=len(semantic))
 rows=[]
 for leaf_id in sorted(semantic):
  cs=domain.build_claim_scope(manifest,leaf_id,epoch=epoch)
  cert=build_certificate(cs)
  verdict=evaluate(manifest,cs,cert)
  if verdict.get("pass") is not True:
   return _fail("IDENTITY_CARRIER_BATCH_MEMBER_FAILED",leaf_id=leaf_id,verdict=verdict)
  rows.append({
   "leaf_id":leaf_id,"claim_id":verdict["claim_id"],
   "scope_sha256":verdict["scope_sha256"],"semantics_sha256":verdict["semantics_sha256"],
   "universal_factorization_proved":True,
   "leaf_property_truth_authority":False,
  })
 r12=next((x for x in rows if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"),None)
 if not r12 or r12["claim_id"]!=EXPECTED_R12_CLAIM_ID:
  return _fail("R12_BATCH_CLAIM_ID_DRIFT",observed_r12_claim_id=(r12 or {}).get("claim_id"))
 return {
  "schema":BATCH_SCHEMA,"pass":True,
  "status":"PASS__12_OF_12_SEMANTIC_CLAIMS_IDENTITY_CARRIER_FACTORIZATION",
  "semantic_leaf_count":12,"factorization_pass_count":12,
  "unique_claim_id_count":len({x["claim_id"] for x in rows}),
  "r12_claim_id":r12["claim_id"],
  "all_projection_total":True,"all_projection_injective":True,
  "all_semantic_information_loss_false":True,
  "current_property_truth_count_delta":0,
  "rows":rows,
  "next":"INSTANTIATE_CLAIM_SCOPED_COVERAGE_ROOT_CERTIFICATES__IDENTITY_CARRIER_PRECONDITION_NO_LONGER_OPEN",
  "leaf_property_truth_authority":False,"semantic_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  if key=="manifest":
   try:docs[key]=json.loads(p.read_text(encoding="utf-8"))
   except Exception:return _fail("MANIFEST_JSON_INVALID")
 carrier=json.loads((root/PINS["carrier_governance"][0]).read_text(encoding="utf-8"))
 allowed=set(((carrier.get("carrier_semantics") or {}).get("allowed_element_kinds") or []))
 if CARRIER_KIND not in allowed:return _fail("CARRIER_KIND_NOT_ALLOWED_BY_GOVERNANCE")
 if (carrier.get("claim_scope") or {}).get("factorization")!="FOR_ALL_w1_w2_IN_W_C__pi_C(w1)=pi_C(w2)_IMPLIES_M_C(w1)=M_C(w2)":
  return _fail("CARRIER_GOVERNANCE_FACTORIZATION_DRIFT")
 return batch(docs["manifest"])

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
