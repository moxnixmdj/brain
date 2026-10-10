"""Repaired professional semantic safety/adequacy normal form V1.

This is the reuse bridge after the shared 12-leaf universal-success
specification was constructively falsified.

It binds two already-existing mechanisms without granting repaired leaf credit:

1. UNIVERSAL CREDIT SAFETY
   professional_quality_leaf_binder_v2 admits semantic credit only when an exact
   frozen claim, scope, target, semantics, claim-scoped totality, CC_R1, CC_R2,
   CC_R3 and R4 all match. Any missing premise fails closed.

2. POSITIVE ADEQUACY PROGRESS
   one_shot_reality_closure_v2 keeps constructive capability gaps and acquirable
   evidence as active work, permits externality only after proof, preserves the
   exact gap losslessly, and asks for minimum policy-changing information.

Abstention is correct when sound verification is unavailable, but it is never
counted as capability success. The optimization target remains maximum verified
positive capability/coverage per resource.
"""
from __future__ import annotations

from hashlib import sha1
import importlib.util
import json
from pathlib import Path
import sys
import types
from typing import Any, Mapping

from canonical.runtime import professional_quality_leaf_binder_v2 as binder
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3
from canonical.runtime import professional_semantic_shared_overstrong_predicate_falsifier_v1 as falsifier

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_SAFETY_ADEQUACY_NORMAL_FORM_V1"
PINS={
 "mission":("canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json","13c470645b037bbb46245c687dd35197b420d51a"),
 "binder":("canonical/runtime/professional_quality_leaf_binder_v2.py","96dedf3641009b08a2e21a8be376459f7ae06a58"),
 "reality":("canonical/runtime/one_shot_reality_closure_v2.py","b8347a3993f96aa5e6fa2f1fe68d7c8afccb8bec"),
 "shared_falsifier_verify":("canonical/verification/PROFESSIONAL_SEMANTIC_SHARED_OVERSTRONG_PREDICATE_FALSIFIER_INDEPENDENT_VERIFY_20261011_V1.json","60000cda3277777766bb9ffdd3454bf38bf2bfe1"),
}

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _load(root:Path,key:str)->dict[str,Any]:
 rel,expected=PINS[key];p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+key)
 got=_blob(p)
 if got!=expected:raise ValueError("PIN_BLOB_DRIFT:"+key+":"+got)
 if p.suffix==".json":
  o=json.loads(p.read_text(encoding="utf-8"))
  if not isinstance(o,dict):raise ValueError("PIN_NOT_OBJECT:"+key)
  return o
 return {}

def _load_reality_helpers(root:Path):
 path=root/PINS["reality"][0]
 if _blob(path)!=PINS["reality"][1]:
  raise ValueError("PIN_BLOB_DRIFT:reality")
 spec=importlib.util.spec_from_file_location("_brain_reality_closure_v2_isolated",path)
 if spec is None or spec.loader is None:raise RuntimeError("REALITY_SPEC_LOAD_FAILED")
 saved={}
 names=[
  "canonical.runtime.one_shot_verified_closure_v1",
  "canonical.runtime.promote_r2_direct_route_v1",
 ]
 try:
  for name in names:
   saved[name]=sys.modules.get(name)
   stub=types.ModuleType(name)
   if name.endswith("one_shot_verified_closure_v1"):
    stub.learning=types.SimpleNamespace(DEFAULT_STATE_PATH=None)
   else:
    stub.promote=lambda **kwargs: {"pass":False,"status":"STUB_NOT_EXECUTED"}
   sys.modules[name]=stub
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module
 finally:
  for name in names:
   old=saved[name]
   if old is None:sys.modules.pop(name,None)
   else:sys.modules[name]=old

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "old_overstrong_semantic_spec_falsified_count":0,
  "semantic_credit_safety_mechanism_ready_count":0,
  "adequacy_gap_classifier_verified":False,
  "minimum_information_policy_verified":False,
  "repaired_semantic_property_truth_proved_count":0,
  "positive_adequacy_coverage_increase":0,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _good_semantic_receipt(claim:Mapping[str,Any])->dict[str,Any]:
 frozen=claim["frozen_claim"]
 return {
  "semantic_claim_id":frozen["claim_id"],
  "semantic_scope_sha256":frozen["scope_sha256"],
  "semantic_target_predicate_sha256":frozen["target_predicate_sha256"],
  "semantic_semantics_sha256":frozen["semantics_sha256"],
  "claim_scoped_totality_proved":True,
  "cc_r1_reality_containment_proved":True,
  "cc_r2_mission_soundness_proved":True,
  "cc_r3_terminal_closure_proved":True,
  "r4_proof_realization_authority":True,
 }

def _verify_credit_safety(claim:Mapping[str,Any])->tuple[bool,str|None]:
 good=_good_semantic_receipt(claim)
 if binder._semantic_receipt_errors(good,claim):
  return False,"VALID_PROOF_SHAPE_REJECTED"
 mutations={
  "semantic_claim_id":"0"*64,
  "semantic_scope_sha256":"0"*64,
  "semantic_target_predicate_sha256":"0"*64,
  "semantic_semantics_sha256":"0"*64,
  "claim_scoped_totality_proved":False,
  "cc_r1_reality_containment_proved":False,
  "cc_r2_mission_soundness_proved":False,
  "cc_r3_terminal_closure_proved":False,
  "r4_proof_realization_authority":False,
 }
 for field,bad in mutations.items():
  candidate=dict(good);candidate[field]=bad
  if not binder._semantic_receipt_errors(candidate,claim):
   return False,"MUTATION_NOT_REJECTED:"+field
 return True,None

def _closure(*,internal=(),evidence=(),pending=False,external=False,passed=False)->dict[str,Any]:
 return {
  "schema":"TEST_SOURCE","status":"TEST","pass":passed,
  "irreducible_external_information_proved":external,
  "initial_frontier_digest":"a","final_frontier_digest":"b","final_state_sha256":"c",
  "closure_class":"TEST",
  "residual":{
   "internal_blockers":list(internal),
   "evidence_blockers":list(evidence),
   "pending_acquisition_or_experiment_required":pending,
   "irreducible_external_information_proved":external,
   "information_theoretic_externality_proved":external,
  },
 }

def _verify_adequacy_mechanism(root:Path)->tuple[bool,dict[str,Any]]:
 reality=_load_reality_helpers(root)
 cases={
  "constructive":(reality.compile_gap_contract(_closure(internal=["MISSING_CAPABILITY"])),"CONSTRUCTIVE_CAPABILITY_GAP"),
  "acquisition":(reality.compile_gap_contract(_closure(evidence=["MISSING_EVIDENCE"],pending=True)),"PENDING_ACQUISITION_OR_EXPERIMENT"),
  "external":(reality.compile_gap_contract(_closure(external=True,passed=True)),"PROVEN_INFORMATION_THEORETICALLY_EXTERNAL"),
  "unclassified":(reality.compile_gap_contract(_closure()),"UNCLASSIFIED_OPEN_GAP"),
 }
 observed={}
 for name,(row,expected) in cases.items():
  observed[name]=row.get("gap_class")
  if row.get("gap_class")!=expected:return False,{"case":name,"expected":expected,"observed":row}
  if row.get("verification_authority_mutation_allowed") is not False:return False,{"case":name,"reason":"AUTHORITY_MUTATION_ALLOWED"}
  if row.get("terminal_credit") is not False:return False,{"case":name,"reason":"TERMINAL_CREDIT_OVERCLAIM"}
  if row.get("search_before_new_code_required") is not True:return False,{"case":name,"reason":"SEARCH_BEFORE_CODE_MISSING"}
  if row.get("minimum_missing_transform_only") is not True:return False,{"case":name,"reason":"MINIMUM_TRANSFORM_BOUNDARY_MISSING"}

 gap=reality.compile_gap_contract(_closure(evidence=["E1","E2"],pending=True))
 decision=reality.compile_decision_sufficient_contract(gap)
 minimum=reality.compile_minimum_information_contract(gap,decision)
 if decision.get("pass") is not True or decision.get("reduction_mode")!="LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION":
  return False,{"reason":"DECISION_REPRESENTATION_NOT_LOSSLESS","decision":decision}
 if decision.get("omitted_evidence")!=[]:return False,{"reason":"DECISION_EVIDENCE_OMITTED"}
 if minimum.get("request_count")!=2:return False,{"reason":"MINIMUM_REQUEST_COUNT_DRIFT","minimum":minimum}
 for request in minimum.get("requests") or []:
  if request.get("broad_acquisition_forbidden_without_minimality_proof") is not True:
   return False,{"reason":"BROAD_ACQUISITION_NOT_FORBIDDEN"}
 if minimum.get("proof_precedence")!=[
  "FORMAL_IMPLICATION","EXISTING_CONTENT_ADDRESSED_RECEIPT",
  "DETERMINISTIC_SCOPE_OR_DOMINANCE_CERTIFICATE",
  "MINIMUM_POLICY_CHANGING_OBSERVATION","FULL_EMPIRICAL_EVALUATION_LAST"]:
  return False,{"reason":"PROOF_PRECEDENCE_DRIFT","minimum":minimum}
 return True,{"gap_classes":observed,"decision":decision,"minimum":minimum}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  mission=_load(root,"mission");_load(root,"binder");_load(root,"reality")
  fv=_load(root,"shared_falsifier_verify")
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))
 if mission.get("correctness_rule")!="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION":
  return _fail("MISSION_CORRECTNESS_RULE_DRIFT")
 if mission.get("optimization_objective")!="MAXIMIZE_REUSABLE_VERIFIED_CAPABILITY_GENERALIZATION_RELIABILITY_AND_EFFICIENCY_PER_AVAILABLE_RESOURCE_WHILE_PRESERVING_SEMANTIC_CAPABILITY_AND_FUTURE_OPTION_VALUE":
  return _fail("MISSION_OPTIMIZATION_OBJECTIVE_DRIFT")
 if (fv.get("truth") or {}).get("all_12_existing_universal_success_predicates_falsified") is not True:
  return _fail("SHARED_OVERSTRONG_SPEC_FALSIFICATION_NOT_PROVED")
 if (fv.get("truth") or {}).get("repaired_semantic_property_truth_proved_count")!=0:
  return _fail("FALSIFIER_RECEIPT_OVERCLAIMS_REPAIRED_TRUTH")

 live_falsifier=falsifier.evaluate(repo_root=root)
 if live_falsifier.get("pass") is not True or live_falsifier.get("overstrong_predicate_falsified_count")!=12:
  return _fail("LIVE_SHARED_FALSIFIER_NOT_CURRENT",verdict=live_falsifier)

 pack=pack_v3.verify(repo_root=root)
 claims=pack.get("claims") if isinstance(pack,Mapping) else None
 if pack.get("pass") is not True or not isinstance(claims,list) or len(claims)!=12:
  return _fail("CURRENT_SEMANTIC_CLAIM_PACK_NOT_PASS")
 rows=[]
 for claim in claims:
  if not isinstance(claim,Mapping):return _fail("CLAIM_ROW_INVALID")
  ok,reason=_verify_credit_safety(claim)
  if not ok:return _fail("SEMANTIC_CREDIT_SAFETY_FAILED:"+str(reason),leaf_id=claim.get("leaf_id"))
  rows.append({"leaf_id":claim.get("leaf_id"),"credit_safety_gate_ready":True})
 if len({r["leaf_id"] for r in rows})!=12:return _fail("SEMANTIC_LEAF_SET_NOT_UNIQUE")

 adequate,detail=_verify_adequacy_mechanism(root)
 if not adequate:return _fail("ADEQUACY_MECHANISM_REUSE_FAILED",detail=detail)

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__REPAIRED_SEMANTIC_NORMAL_FORM_MECHANISMS_READY__12_OF_12_OLD_SUCCESS_SPECS_FALSIFIED__12_OF_12_CREDIT_SAFETY_GATES_REUSABLE__PROOF_CARRYING_ADEQUACY_PROGRESS_REUSABLE__ZERO_REPAIRED_PROPERTY_CREDIT",
  "old_overstrong_semantic_spec_falsified_count":12,
  "semantic_credit_safety_mechanism_ready_count":12,
  "semantic_credit_safety_mutations_rejected_per_leaf":9,
  "semantic_credit_safety_leaf_count":12,
  "semantic_credit_safety":"EXACT_CLAIM_SCOPE_TARGET_SEMANTICS_PLUS_TOTALITY_CC_R1_CC_R2_CC_R3_R4_REQUIRED_BEFORE_SEMANTIC_CREDIT",
  "adequacy_gap_classifier_verified":True,
  "adequacy_gap_classes":[
   "CONSTRUCTIVE_CAPABILITY_GAP",
   "PENDING_ACQUISITION_OR_EXPERIMENT",
   "PROVEN_INFORMATION_THEORETICALLY_EXTERNAL",
   "UNCLASSIFIED_OPEN_GAP",
  ],
  "externality_rule":"CURRENT_ABSENCE_IS_NOT_EXTERNALITY__INFORMATION_THEORETIC_EXTERNALITY_REQUIRES_PROOF_AND_INTERNAL_BYPASS_EXHAUSTION",
  "decision_sufficient_representation":"LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
  "minimum_information_policy_verified":True,
  "proof_precedence":[
   "FORMAL_IMPLICATION","EXISTING_CONTENT_ADDRESSED_RECEIPT",
   "DETERMINISTIC_SCOPE_OR_DOMINANCE_CERTIFICATE",
   "MINIMUM_POLICY_CHANGING_OBSERVATION","FULL_EMPIRICAL_EVALUATION_LAST",
  ],
  "search_before_new_code_required":True,
  "minimum_missing_transform_only":True,
  "abstention_is_capability_success":False,
  "positive_adequacy_coverage_must_continue_to_improve":True,
  "repaired_semantic_property_truth_proved_count":0,
  "positive_adequacy_coverage_increase":0,
  "new_primitive_required":False,
  "semantic_leaf_rows":sorted(rows,key=lambda x:str(x["leaf_id"])),
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
  "exact_next":"FREEZE_REPAIRED_SEMANTIC_CLAIMS_UNDER_SAFETY_PLUS_ADEQUACY_SPLIT__REUSE_GENERIC_CREDIT_SAFETY_GATE__ROUTE_ONLY_CONSTRUCTIVE_OR_ACQUIRABLE_ADEQUACY_RESIDUALS_TO_REALITY_CLOSURE__NEVER_COUNT_EXTERNAL_ABSTENTION_AS_CAPABILITY_SUCCESS",
 }

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
