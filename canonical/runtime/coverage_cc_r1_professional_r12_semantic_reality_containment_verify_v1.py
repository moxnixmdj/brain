"""CC_R1 reality-containment verifier for the frozen professional R12 semantic claim.

Proves only B_real[C] subseteq B_plus[C] for the exact claim. The proof reuses
the independently verified exact whole-leaf domain plus the lossless identity
semantic carrier. It grants no semantic property truth or promotion authority.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime import professional_semantic_identity_carrier_v1 as identity

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_REALITY_CONTAINMENT_VERIFY_V1"
ROOT_ID="CC_R1_REALITY_CONTAINMENT_V1"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
SCOPE_SHA="3958f259dba6bc6d4dfe1dad0b3ec26ecb1b8d92ea4763985f52ce96cfc55a1d"
SEMANTICS_SHA="bdb1e40284acf8f93f0552143ccfb2a3246428a1862c3f37907a00b20d18fc3e"
TARGET_SHA="4967b35be044567ae9fbcd01f2443996dc675f3154fd386790f79301ae9cff09"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
EPOCH="2026-10-10T18:05:00+02:00"

CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json"
CLAIM_BLOB="5e7c198da31b901bb4f53c4fc15cee7d6298c114"
CERT_PATH="canonical/governance/COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_REALITY_CONTAINMENT_CERTIFICATE_20261010_V1.json"
CERT_BLOB="121ba155ee82ac148c7b140e8c434397de925ee8"
MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
MANIFEST_BLOB="a7cad32c9fd969ff2c3857bb924c7bd746237ec2"
DOMAIN_RUNTIME_PATH="canonical/runtime/professional_quality_whole_leaf_domain_equivalence_v1.py"
DOMAIN_RUNTIME_BLOB="76bf7e1a6f26ff3664ed8c355dff8a688b074159"
DOMAIN_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json"
DOMAIN_VERIFY_BLOB="b6b826d1658d8a2c88ea80260ee667e86ae99394"
SCOPE_BATCH_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json"
SCOPE_BATCH_VERIFY_BLOB="4c2d40a262f18f34bb35f94b59660d60972d45ef"
IDENTITY_RUNTIME_PATH="canonical/runtime/professional_semantic_identity_carrier_v1.py"
IDENTITY_RUNTIME_BLOB="3a8a27b6fdd0a397b83b94f2daaf185996e9ad62"
IDENTITY_ACTIVATION_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_ACTIVATION_20261010_V1.json"
IDENTITY_ACTIVATION_BLOB="3e99ddbf25cd8e392c5a22a5c14ae5fea5dc3138"
IDENTITY_VERIFY_PATH="canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json"
IDENTITY_VERIFY_BLOB="35a3ccf9ad454aa0318a4ed10edc065830c3874d"

EXPECTED_TERMS={
 "B_real":"ALL_REAL_IN_SCOPE_R12_SEMANTIC_CLAIM_WORLD_STATES_ADMISSIBLE_UNDER_THE_EXACT_FROZEN_WHOLE_LEAF_DOMAIN",
 "W_C":"EXACT_COMPLETE_FROZEN_R12_SEMANTIC_CLAIM_WORLD_STATE",
 "B_plus":"OMEGA_C_EQUALS_W_C_UNDER_THE_VERIFIED_IDENTITY_CARRIER",
 "scope_relation":"EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN__NO_FILTERS__NO_EXCLUSIONS",
}
EXPECTED_STATEMENT="FOR_THE_EXACT_FROZEN_R12_SEMANTIC_CLAIM__EVERY_REAL_IN_SCOPE_STATE_IS_BY_THE_VERIFIED_WHOLE_DOMAIN_DEFINITION_AN_ELEMENT_OF_W_C__THE_VERIFIED_IDENTITY_CARRIER_SETS_OMEGA_C_EQUAL_TO_W_C_WITH_TOTAL_INJECTIVE_IDENTITY_PROJECTION_AND_ZERO_SEMANTIC_INFORMATION_LOSS__THEREFORE_B_REAL_C_IS_A_SUBSET_OF_B_PLUS_C"

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
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "cc_r1_reality_containment_proved":False,"b_real_subseteq_b_plus":False,
  "r12_semantic_property_truth_authority":False,"leaf_property_truth_authority":False,
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
  "incremental_spend_usd":0,**extra,
 }

def evaluate_documents(*,manifest:Mapping[str,Any],frozen:Mapping[str,Any],certificate:Mapping[str,Any],
                       identity_activation:Mapping[str,Any],identity_verification:Mapping[str,Any],
                       domain_verification:Mapping[str,Any],scope_batch_verification:Mapping[str,Any])->dict[str,Any]:
 errors:list[str]=[]
 expected_scope=domain.build_claim_scope(manifest,LEAF_ID,epoch=EPOCH)
 dv=domain.evaluate(manifest,expected_scope)
 if dv.get("pass") is not True or dv.get("whole_leaf_domain_equivalence_proved") is not True:
  return _fail("CANONICAL_DOMAIN_EQUIVALENCE_RECOMPUTE_FAILED",domain_verdict=dv)
 claim=expected_scope.get("claim") or {}
 for field,value in (
  ("claim_id",CLAIM_ID),("scope_sha256",SCOPE_SHA),("semantics_sha256",SEMANTICS_SHA),
  ("target_predicate_sha256",TARGET_SHA),("mission_blob_sha",MISSION_BLOB),
 ):
  if claim.get(field)!=value: errors.append("CANONICAL_CLAIM_DRIFT:"+field)
 if frozen.get("claim_scope")!=expected_scope: errors.append("FROZEN_CLAIM_SCOPE_DRIFT")
 if frozen.get("claim_id")!=CLAIM_ID: errors.append("FROZEN_CLAIM_ID_DRIFT")

 scope=(expected_scope.get("scope_definition") or {}).get("domain_definition") or {}
 if scope.get("quantifier")!="FOR_ALL_ADMISSIBLE_LEAF_INPUTS": errors.append("WHOLE_DOMAIN_QUANTIFIER_DRIFT")
 if scope.get("filters")!=[] or scope.get("exclusions")!=[]: errors.append("WHOLE_DOMAIN_NARROWED")
 if scope.get("scope_relation")!="EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN": errors.append("WHOLE_DOMAIN_RELATION_DRIFT")
 if domain_verification.get("status","").startswith("PASS__") is not True: errors.append("DOMAIN_INDEPENDENT_VERIFY_NOT_PASS")
 dr=domain_verification.get("independent_replay") or {}
 if dr.get("real_manifest_leaf_count")!=24 or dr.get("real_manifest_passed")!=24: errors.append("DOMAIN_REPLAY_NOT_24_OF_24")
 if scope_batch_verification.get("scope_complete_count")!=24 or scope_batch_verification.get("domain_equivalence_pass_count")!=24:
  errors.append("SCOPE_BATCH_NOT_24_OF_24")

 if identity_activation.get("status")!="ACTIVE_CANDIDATE__INDEPENDENTLY_VERIFIED_12_OF_12_CLAIM_SCOPED_IDENTITY_CARRIER_FACTORIZATION__ZERO_PROPERTY_TRUTH_CREDIT":
  errors.append("IDENTITY_ACTIVATION_STATUS_DRIFT")
 istate=identity_activation.get("current_state") or {}
 if istate.get("r12_claim_id")!=CLAIM_ID or istate.get("claim_scoped_identity_factorization_proved_count")!=12:
  errors.append("IDENTITY_ACTIVATION_R12_DRIFT")
 ir=identity_verification.get("independent_replay") or {}
 if ir.get("r12_claim_id")!=CLAIM_ID or ir.get("tests_passed")!=8 or ir.get("factorization_pass_count")!=12:
  errors.append("IDENTITY_INDEPENDENT_VERIFY_INVALID")
 if identity_verification.get("property_truth_count_delta")!=0: errors.append("IDENTITY_PROPERTY_OVERCLAIM")

 if certificate.get("root_id")!=ROOT_ID: errors.append("CERTIFICATE_ROOT_MISMATCH")
 if certificate.get("claim_id")!=CLAIM_ID: errors.append("CERTIFICATE_CLAIM_MISMATCH")
 cref=certificate.get("active_claim") or {}
 if (cref.get("path"),cref.get("git_blob_sha"))!=(CLAIM_PATH,CLAIM_BLOB): errors.append("CERTIFICATE_CLAIM_REF_DRIFT")
 terms=certificate.get("claim_scoped_terms")
 if not isinstance(terms,Mapping) or any(terms.get(k)!=v for k,v in EXPECTED_TERMS.items()):
  errors.append("CERTIFICATE_TERMS_DRIFT")
 theorem=certificate.get("theorem") or {}
 if theorem.get("statement")!=EXPECTED_STATEMENT: errors.append("THEOREM_STATEMENT_DRIFT")
 if theorem.get("proof_mode")!="FORMAL_REDUCTION__EXACT_DOMAIN_IDENTITY_PLUS_IDENTITY_CARRIER":
  errors.append("THEOREM_MODE_DRIFT")
 for field,value in (
  ("finite_sampling_used",False),("catalog_completeness_required",False),
  ("carrier_abstraction_applied",False),("semantic_information_loss",False),
  ("future_claim_or_scope_drift_covered",False),("r12_semantic_property_truth_implied",False),
  ("global_professional_quality_closure_implied",False),
 ):
  if theorem.get(field) is not value: errors.append("THEOREM_BOUNDARY_DRIFT:"+field)
 for field in ("r12_semantic_property_truth_authority","promotion_authority","terminal_authority"):
  if certificate.get(field) is not False: errors.append("CERTIFICATE_SELF_AUTHORITY_FORBIDDEN:"+field)
 acct=certificate.get("accounting") or {}
 if acct.get("property_truth_credit_delta")!=0 or acct.get("terminal_credit_delta")!=0:
  errors.append("CERTIFICATE_NONZERO_CREDIT")

 if errors:return _fail("CC_R1_REALITY_CONTAINMENT_PREMISE_FAILED",errors=sorted(set(errors)))
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__CC_R1_R12_SEMANTIC_REALITY_CONTAINMENT_FORMAL_REDUCTION",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "cc_r1_reality_containment_proved":True,"b_real_subseteq_b_plus":True,
  "whole_domain_exact":True,"whole_domain_filters":0,"whole_domain_exclusions":0,
  "identity_projection_total":True,"identity_projection_injective":True,
  "semantic_information_loss":False,"finite_sampling_used":False,
  "catalog_completeness_required":False,"claim_scoped_property_only":True,
  "r12_semantic_property_truth_authority":False,"leaf_property_truth_authority":False,
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
  "incremental_spend_usd":0,"errors":[],
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 fixed={
  "manifest":(MANIFEST_PATH,MANIFEST_BLOB),"claim":(CLAIM_PATH,CLAIM_BLOB),
  "certificate":(CERT_PATH,CERT_BLOB),"domain_runtime":(DOMAIN_RUNTIME_PATH,DOMAIN_RUNTIME_BLOB),
  "domain_verification":(DOMAIN_VERIFY_PATH,DOMAIN_VERIFY_BLOB),
  "scope_batch_verification":(SCOPE_BATCH_VERIFY_PATH,SCOPE_BATCH_VERIFY_BLOB),
  "identity_runtime":(IDENTITY_RUNTIME_PATH,IDENTITY_RUNTIME_BLOB),
  "identity_activation":(IDENTITY_ACTIVATION_PATH,IDENTITY_ACTIVATION_BLOB),
  "identity_verification":(IDENTITY_VERIFY_PATH,IDENTITY_VERIFY_BLOB),
 }
 docs={}
 for key,(rel,expected) in fixed.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  if key in {"manifest","claim","certificate","domain_verification","scope_batch_verification","identity_activation","identity_verification"}:
   try:docs[key]=_load(p)
   except Exception:return _fail(key.upper()+"_JSON_INVALID")
 ident=identity.verify(repo_root=root)
 if ident.get("pass") is not True or ident.get("r12_claim_id")!=CLAIM_ID:
  return _fail("IDENTITY_CARRIER_RECOMPUTE_FAILED",identity_verdict=ident)
 return evaluate_documents(
  manifest=docs["manifest"],frozen=docs["claim"],certificate=docs["certificate"],
  identity_activation=docs["identity_activation"],identity_verification=docs["identity_verification"],
  domain_verification=docs["domain_verification"],scope_batch_verification=docs["scope_batch_verification"],
 )

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
