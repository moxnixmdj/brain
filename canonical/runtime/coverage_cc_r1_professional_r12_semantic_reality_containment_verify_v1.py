"""Executable CC_R1 reality-containment verifier for the frozen R12 semantic claim.

This proves only B_real[C] subseteq B_plus[C] for one exact claim C.
B_plus is the complete admissible whole-leaf world-state domain with the
independently verified identity carrier and unresolved values retained as TOP.
No semantic property, quality, acceptance, promotion, or terminal authority is
created by this proof.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_CC_R1_PROFESSIONAL_R12_SEMANTIC_REALITY_CONTAINMENT_VERIFY_V1"
ROOT_ID="CC_R1_REALITY_CONTAINMENT_V1"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json"
CLAIM_BLOB="5e7c198da31b901bb4f53c4fc15cee7d6298c114"
CERT_PATH="canonical/governance/COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_REALITY_CONTAINMENT_CERTIFICATE_20261010_V1.json"
DOMAIN_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json"
DOMAIN_BLOB="b6b826d1658d8a2c88ea80260ee667e86ae99394"
SCOPE_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json"
SCOPE_BLOB="4c2d40a262f18f34bb35f94b59660d60972d45ef"
IDENTITY_PATH="canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json"
IDENTITY_BLOB="35a3ccf9ad454aa0318a4ed10edc065830c3874d"
IDENTITY_ACTIVATION_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_ACTIVATION_20261010_V1.json"
IDENTITY_ACTIVATION_BLOB="3e99ddbf25cd8e392c5a22a5c14ae5fea5dc3138"
MISSION_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
EXPECTED_CORE={
 "claim_id":CLAIM_ID,
 "claim_kind":"PROPERTY_CERTIFICATE",
 "mission_blob_sha":MISSION_BLOB,
 "scope_sha256":"3958f259dba6bc6d4dfe1dad0b3ec26ecb1b8d92ea4763985f52ce96cfc55a1d",
 "target_predicate_sha256":"4967b35be044567ae9fbcd01f2443996dc675f3154fd386790f79301ae9cff09",
 "semantics_sha256":"bdb1e40284acf8f93f0552143ccfb2a3246428a1862c3f37907a00b20d18fc3e",
 "epoch":"2026-10-10T18:05:00+02:00",
 "authority_id":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF",
}
EXPECTED_BPLUS_SEMANTICS={
 "EVERY_REAL_IN_SCOPE_R12_SEMANTIC_WORLD_STATE_IS_AN_ADMISSIBLE_STATE_OF_THE_EXACT_FROZEN_WHOLE_LEAF_DOMAIN",
 "ALL_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_DEFEATER_AND_NONVACUITY_FIELDS_REMAIN_EXPLICIT_IN_THE_COMPLETE_WORLD_STATE",
 "UNRESOLVED_OR_UNKNOWN_VALUES_REMAIN_TOP_OR_UNKNOWN_AND_ARE_NOT_DROPPED_NARROWED_OR_ASSUMED_FAVORABLE",
 "THE_CLAIM_SCOPED_CARRIER_IS_IDENTITY_AND_THEREFORE_LOSSES_NO_SEMANTIC_INFORMATION",
 "NO_FILTER_EXCLUSION_FINITE_WITNESS_SET_OR_BOUNDED_EVIDENCE_SUBSET_DEFINES_THE_REALITY_ENVELOPE",
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load_bound(root:Path,path:str,blob:str)->dict[str,Any]|None:
 p=(root/path).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 if not p.is_file() or p.is_symlink() or _blob(p)!=blob:return None
 try:d=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None
 return d if isinstance(d,dict) else None

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
  "reason":reason,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "semantic_claim_verified":False,"cc_r1_reality_containment_authority":False,
  "r12_semantic_property_truth_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,**extra,
 }

def evaluate_documents(*,frozen:Mapping[str,Any],certificate:Mapping[str,Any],
 domain:Mapping[str,Any],scope:Mapping[str,Any],identity:Mapping[str,Any],
 identity_activation:Mapping[str,Any],mission:Mapping[str,Any],
 active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 errors:list[str]=[]
 if root_id!=ROOT_ID:errors.append("ROOT_ID_MISMATCH")
 for k,v in EXPECTED_CORE.items():
  if active_claim.get(k)!=v:errors.append("ACTIVE_CLAIM_CORE_DRIFT:"+k)
  if frozen.get(k)!=v:errors.append("FROZEN_CLAIM_CORE_DRIFT:"+k)
  if (certificate.get("claim_binding") or {}).get(k)!=v:errors.append("CERTIFICATE_CLAIM_CORE_DRIFT:"+k)
 if certificate.get("root_id")!=ROOT_ID:errors.append("CERTIFICATE_ROOT_DRIFT")
 if certificate.get("claim_id")!=CLAIM_ID:errors.append("CERTIFICATE_CLAIM_ID_DRIFT")
 if certificate.get("mission_authority_blob_sha")!=MISSION_BLOB:errors.append("CERTIFICATE_MISSION_BLOB_DRIFT")
 for field in ("semantic_claim_verified","cc_r1_reality_containment_authority","r12_semantic_property_truth_authority","promotion_authority","terminal_authority"):
  if certificate.get(field) is not False:errors.append("CERTIFICATE_SELF_AUTHORITY_FORBIDDEN:"+field)
 acct=certificate.get("accounting") or {}
 if acct.get("property_truth_credit_delta")!=0 or acct.get("terminal_credit_delta")!=0:
  errors.append("CERTIFICATE_NONZERO_CREDIT_FORBIDDEN")

 ref=certificate.get("active_claim") or {}
 if (ref.get("path"),ref.get("git_blob_sha"))!=(CLAIM_PATH,CLAIM_BLOB):
  errors.append("CERTIFICATE_ACTIVE_CLAIM_REF_DRIFT")
 evidence=certificate.get("evidence") or {}
 expected_refs={
  "whole_domain_equivalence":(DOMAIN_PATH,DOMAIN_BLOB),
  "scope_batch":(SCOPE_PATH,SCOPE_BLOB),
  "identity_carrier":(IDENTITY_PATH,IDENTITY_BLOB),
  "identity_activation":(IDENTITY_ACTIVATION_PATH,IDENTITY_ACTIVATION_BLOB),
  "mission_authority":(MISSION_PATH,MISSION_BLOB),
 }
 for key,(path,blob) in expected_refs.items():
  row=evidence.get(key) or {}
  if (row.get("path"),row.get("git_blob_sha"))!=(path,blob):
   errors.append("CERTIFICATE_EVIDENCE_REF_DRIFT:"+key)

 cs=frozen.get("claim_scope") or {}
 sd=cs.get("scope_definition") or {}
 dd=sd.get("domain_definition") or {}
 if sd.get("entire_admissible_leaf_domain") is not True:errors.append("WHOLE_DOMAIN_FLAG_NOT_TRUE")
 if dd.get("quantifier")!="FOR_ALL_ADMISSIBLE_LEAF_INPUTS":errors.append("WHOLE_DOMAIN_QUANTIFIER_DRIFT")
 if dd.get("scope_relation")!="EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN":errors.append("WHOLE_DOMAIN_RELATION_DRIFT")
 if dd.get("filters")!=[]:errors.append("WHOLE_DOMAIN_FILTER_NARROWING")
 if dd.get("exclusions")!=[]:errors.append("WHOLE_DOMAIN_EXCLUSION_NARROWING")
 if cs.get("leaf_id")!="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC":errors.append("LEAF_ID_DRIFT")

 if not str(domain.get("status") or "").startswith("PASS__PYCOMPILE__8_OF_8_ADVERSARIAL_TESTS__24_OF_24_REAL_MANIFEST_LEAVES"):
  errors.append("DOMAIN_EQUIVALENCE_NOT_VERIFIED")
 dr=domain.get("independent_replay") or {}
 if dr.get("real_manifest_leaf_count")!=24 or dr.get("real_manifest_passed")!=24 or dr.get("unique_claim_id_count")!=24:
  errors.append("DOMAIN_EQUIVALENCE_COUNTS_DRIFT")

 if not str(scope.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  errors.append("SCOPE_BATCH_NOT_VERIFIED")
 sr=scope.get("independent_replay") or {}
 if sr.get("leaf_count")!=24 or sr.get("domain_equivalence_pass_count")!=24 or sr.get("scope_complete_count")!=24:
  errors.append("SCOPE_BATCH_COUNTS_DRIFT")
 if sr.get("property_truth_count")!=0:errors.append("SCOPE_BATCH_SELF_PROMOTION")

 if not str(identity.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE__PYCOMPILE__8_OF_8__12_OF_12_SEMANTIC_CLAIMS_UNIVERSAL_IDENTITY_FACTORIZATION"):
  errors.append("IDENTITY_CARRIER_NOT_VERIFIED")
 if identity.get("semantic_leaf_count")!=12 or identity.get("universal_factorization_proved_count")!=12:
  errors.append("IDENTITY_CARRIER_COUNTS_DRIFT")
 it=identity.get("theorem") or {}
 if it.get("finite_witness_set_used") is not False:errors.append("FINITE_WITNESS_REALITY_NARROWING")
 if it.get("semantic_information_loss") is not False:errors.append("IDENTITY_CARRIER_INFORMATION_LOSS")
 ir=identity.get("independent_replay") or {}
 if ir.get("r12_claim_id")!=CLAIM_ID:errors.append("IDENTITY_R12_CLAIM_DRIFT")
 ist=identity_activation.get("current_state") or {}
 if ist.get("r12_claim_id")!=CLAIM_ID or ist.get("claim_scoped_identity_factorization_proved_count")!=12:
  errors.append("IDENTITY_ACTIVATION_DRIFT")

 if mission.get("real_objective")!="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE":
  errors.append("MISSION_OBJECTIVE_DRIFT")
 if mission.get("correctness_rule")!="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION":
  errors.append("MISSION_CORRECTNESS_RULE_DRIFT")

 bp=certificate.get("b_plus_model") or {}
 if bp.get("domain_quantifier")!="FOR_ALL_ADMISSIBLE_LEAF_INPUTS":errors.append("BPLUS_QUANTIFIER_DRIFT")
 if bp.get("entire_admissible_leaf_domain") is not True:errors.append("BPLUS_WHOLE_DOMAIN_NOT_TRUE")
 if bp.get("filters")!=[]:errors.append("BPLUS_FILTER_NARROWING")
 if bp.get("exclusions")!=[]:errors.append("BPLUS_EXCLUSION_NARROWING")
 if bp.get("carrier")!="OMEGA_C_EQUALS_W_C__IDENTITY_ON_COMPLETE_FROZEN_CLAIM_WORLD_STATE":errors.append("BPLUS_CARRIER_DRIFT")
 sem=set(bp.get("semantics") or [])
 if not EXPECTED_BPLUS_SEMANTICS<=sem:errors.append("BPLUS_TOP_SEMANTICS_INCOMPLETE")

 th=certificate.get("theorem") or {}
 if th.get("proof_mode")!="KERNEL_CHECKED":errors.append("THEOREM_PROOF_MODE_DRIFT")
 if th.get("conservative_overapproximation") is not True:errors.append("THEOREM_NOT_CONSERVATIVE")
 if th.get("b_real_subseteq_b_plus") is not True:errors.append("THEOREM_CONTAINMENT_NOT_ASSERTED")
 if th.get("semantic_information_loss") is not False:errors.append("THEOREM_INFORMATION_LOSS")
 if th.get("finite_witness_set_used") is not False:errors.append("THEOREM_FINITE_WITNESS_FORBIDDEN")
 if th.get("r12_semantic_property_truth_implied") is not False:errors.append("THEOREM_PROPERTY_OVERCLAIM")
 if th.get("global_mission_completion_implied") is not False:errors.append("THEOREM_GLOBAL_OVERCLAIM")

 if errors:return _fail("CC_R1_PREMISE_FAILED",errors=sorted(set(errors)))
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__CC_R1_R12_SEMANTIC_WHOLE_DOMAIN_REALITY_CONTAINMENT",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "semantic_claim_verified":True,"cc_r1_reality_containment_authority":True,
  "b_real_subseteq_b_plus":True,"whole_admissible_domain":True,
  "identity_carrier_lossless":True,"unresolved_values_retained_as_top":True,
  "finite_witness_set_used":False,"claim_scoped_property_only":True,
  "r12_semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,"errors":[],
 }

def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=root.resolve()
 fixed={
  "frozen":(CLAIM_PATH,CLAIM_BLOB),"domain":(DOMAIN_PATH,DOMAIN_BLOB),
  "scope":(SCOPE_PATH,SCOPE_BLOB),"identity":(IDENTITY_PATH,IDENTITY_BLOB),
  "identity_activation":(IDENTITY_ACTIVATION_PATH,IDENTITY_ACTIVATION_BLOB),
  "mission":(MISSION_PATH,MISSION_BLOB),
 }
 docs:dict[str,dict[str,Any]]={}
 for key,(path,blob) in fixed.items():
  d=_load_bound(root,path,blob)
  if d is None:return _fail(key.upper()+"_BYTES_INVALID")
  docs[key]=d
 try:
  cert=json.loads(certificate_path.read_text(encoding="utf-8"))
 except Exception:return _fail("CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,dict):return _fail("CERTIFICATE_NOT_OBJECT")
 return evaluate_documents(
  frozen=docs["frozen"],certificate=cert,domain=docs["domain"],scope=docs["scope"],
  identity=docs["identity"],identity_activation=docs["identity_activation"],
  mission=docs["mission"],active_claim=active_claim,root_id=root_id,
 )

if __name__=="__main__":
 frozen=_load_bound(ROOT,CLAIM_PATH,CLAIM_BLOB) or {}
 print(json.dumps(verify_certificate(root=ROOT,certificate_path=ROOT/CERT_PATH,active_claim=frozen,root_id=ROOT_ID),indent=2,sort_keys=True))
