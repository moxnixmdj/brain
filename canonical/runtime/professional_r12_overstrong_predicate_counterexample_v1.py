"""Constructive falsifier for the overstrong whole-leaf R12 semantic predicate.

The current frozen stronger predicate requires semantic sufficiency on EVERY
admissible professional-quality input. This module constructs one ordinary
professional deliverable input whose required source fact is information-
theoretically unavailable under the input's authorized information boundary.

Two complete admissible worlds have identical visible information but opposite
required source truth. No grounded positive policy is valid in both worlds.
Fail-closed abstention is mission-correct and receives zero progress credit.

Therefore the stronger universal-success predicate is not a valid mandatory
correctness gate for the real mission. This does not grant R12 property truth;
it is a counterexample/truth-repair witness only.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import finite_minimax_decision_region_v1 as minimax

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_OVERSTRONG_PREDICATE_COUNTEREXAMPLE_V1"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
STRONGER_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SAFE_CLAIM_ID="4d94bc346ec20e2778c1fe8655274dd0e9ff4cd67e94681164f77be9fb4e1962"
PINS={
 "mission":("canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json","13c470645b037bbb46245c687dd35197b420d51a"),
 "behavior_registry":("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53"),
 "stronger_claim":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json","7b26ddba501358d42d6fa342efd27d389bb30654"),
 "whole_domain_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
 "safe_property_verify":("canonical/verification/PROFESSIONAL_R12_SAFE_CERTIFICATION_DISPOSITION_PROPERTY_INDEPENDENT_VERIFY_20261011_V1.json","50f7a819fd43cca277cbf882e3a05934908729d8"),
 "spec_split_verify":("canonical/verification/PROFESSIONAL_R12_SEMANTIC_SPEC_SPLIT_GUARD_INDEPENDENT_VERIFY_20261011_V1.json","60602fb3b0ffdab3626c041ec43c83d008bb5c24"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "counterexample_admissible":False,
  "stronger_universal_predicate_falsified":False,
  "safe_fail_closed_policy_exists":False,
  "stronger_r12_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _load(root:Path,key:str)->dict[str,Any]:
 rel,expected=PINS[key]
 p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+key)
 got=_blob(p)
 if got!=expected:raise ValueError("PIN_BLOB_DRIFT:"+key+":"+got)
 obj=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(obj,dict):raise ValueError("PIN_NOT_OBJECT:"+key)
 return obj

def _professional_contract(registry:Mapping[str,Any])->Mapping[str,Any]|None:
 rows=registry.get("active_contracted_residuals")
 if not isinstance(rows,list):return None
 found=[x for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR_ID]
 return found[0] if len(found)==1 else None

def build_counterexample()->dict[str,Any]:
 visible={
  "user_objective":"Produce a professional memo that states the exact externally-owned binary source fact H and certifies that the statement is source-grounded.",
  "audience":"professional decision maker",
  "source_evidence":{
   "source_id":"EXTERNAL_SOURCE_S",
   "visible_statement":"H exists and is either 0 or 1.",
   "value_disclosed":False,
   "authorized_value_observation_interface":None,
  },
  "artifact_type":"professional memo",
  "constraints":[
   "The memo must state exactly one value for H.",
   "The stated value must equal the source truth.",
   "Unsupported guessing is forbidden.",
   "No information outside the declared allowed-information boundary may be used."
  ],
  "current_draft_or_render":"H = [REQUIRED_SOURCE_VALUE]",
 }
 worlds=[
  {"world_id":"W_H0","visible_input":visible,"source_truth":{"H":0}},
  {"world_id":"W_H1","visible_input":visible,"source_truth":{"H":1}},
 ]
 problem={
  "hypothesis_set_complete":True,
  "worlds":[{"world_id":"W_H0"},{"world_id":"W_H1"}],
  "policy_regions":[
   {"policy_id":"STATE_H0","world_ids":["W_H0"],"region_complete":True},
   {"policy_id":"STATE_H1","world_ids":["W_H1"],"region_complete":True},
  ],
  # Empty observation library is complete by construction for this input:
  # the sole truth-bearing source exposes no authorized observation interface.
  "observations":[],
 }
 return {
  "schema":"PROJECT_BRAIN_PROFESSIONAL_R12_ADMISSIBLE_TWO_WORLD_COUNTEREXAMPLE_V1",
  "behavior_id":BEHAVIOR_ID,
  "leaf_id":LEAF_ID,
  "stronger_claim_id":STRONGER_CLAIM_ID,
  "visible_input":visible,
  "worlds":worlds,
  "world_hypothesis_set_complete":True,
  "authorized_observation_library_complete":True,
  "authorized_observation_count":0,
  "positive_semantic_resolution_problem":problem,
  "safe_common_policy":{
   "policy_id":"ABSTAIN_WITH_MINIMUM_BLOCKING_CUT",
   "valid_in_world_ids":["W_H0","W_H1"],
   "positive_property_credit":False,
   "blocking_cut":["MISSING_AUTHORIZED_SOURCE_VALUE:H"],
  },
  "material_defeater":{
   "id":"UNGROUNDED_REQUIRED_SOURCE_FACT_H",
   "root_relevant":True,
   "reason":"A positive memo must choose H=0 or H=1; identical visible evidence cannot ground which value is true.",
   "decision_null":False,
  },
 }

def evaluate(counterexample:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 if not isinstance(counterexample,Mapping):return _fail("COUNTEREXAMPLE_NOT_OBJECT")
 try:
  mission=_load(root,"mission")
  registry=_load(root,"behavior_registry")
  claim=_load(root,"stronger_claim")
  domainv=_load(root,"whole_domain_verify")
  safev=_load(root,"safe_property_verify")
  splitv=_load(root,"spec_split_verify")
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))

 if mission.get("correctness_rule")!="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION":
  return _fail("MISSION_FAIL_CLOSED_RULE_DRIFT")
 contract=_professional_contract(registry)
 if not isinstance(contract,Mapping):return _fail("PROFESSIONAL_BEHAVIOR_CONTRACT_MISSING")
 if counterexample.get("behavior_id")!=BEHAVIOR_ID or counterexample.get("leaf_id")!=LEAF_ID:
  return _fail("COUNTEREXAMPLE_DOMAIN_BINDING_DRIFT")
 if claim.get("claim_id")!=STRONGER_CLAIM_ID:return _fail("STRONGER_CLAIM_ID_DRIFT")
 target=claim.get("target_predicate") or {}
 sem=claim.get("semantics") or {}
 if target.get("quantification")!="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE":
  return _fail("STRONGER_CLAIM_NOT_UNIVERSAL")
 if sem.get("false_when")!="EXISTS_ADMISSIBLE_INPUT_IN_WHOLE_LEAF_SCOPE_FOR_WHICH_THE_ACCEPTANCE_PROPERTY_FAILS":
  return _fail("STRONGER_FALSE_CONDITION_DRIFT")
 if not str(domainv.get("status") or "").startswith("PASS__"):
  return _fail("WHOLE_DOMAIN_EQUIVALENCE_NOT_VERIFIED")
 replay=domainv.get("independent_replay") or {}
 if replay.get("real_manifest_passed")!=24:return _fail("WHOLE_DOMAIN_REPLAY_INCOMPLETE")
 if (safev.get("truth") or {}).get("safe_wrapper_claim_property_truth_proved") is not True:
  return _fail("SAFE_PROPERTY_NOT_PROVED")
 if (safev.get("truth") or {}).get("stronger_r12_semantic_sufficiency_proved") is not False:
  return _fail("SAFE_PROPERTY_STRONGER_OVERCLAIM")
 if not str(splitv.get("status") or "").startswith("PASS__SECOND_INDEPENDENT_SPRITE"):
  return _fail("SPEC_SPLIT_NOT_INDEPENDENT_PASS")

 # Admissibility: exact professional behavior contract takes objective, audience,
 # source evidence, artifact type, constraints and current draft/render. The
 # whole-leaf scope has no filters/exclusions, so an input of that declared form
 # is not excluded merely because its evidence is insufficient for success.
 visible=counterexample.get("visible_input")
 if not isinstance(visible,Mapping):return _fail("VISIBLE_INPUT_MISSING")
 for k in ("user_objective","audience","source_evidence","artifact_type","constraints","current_draft_or_render"):
  if k not in visible:return _fail("VISIBLE_INPUT_FIELD_MISSING:"+k)
 if "source evidence" not in str(contract.get("inputs") or "").lower():
  return _fail("BEHAVIOR_CONTRACT_INPUT_SHAPE_DRIFT")
 if "unsupported content" not in str(contract.get("failure_condition") or "").lower():
  return _fail("BEHAVIOR_CONTRACT_GROUNDING_FAILURE_BOUNDARY_DRIFT")

 worlds=counterexample.get("worlds")
 if not isinstance(worlds,list) or len(worlds)!=2:return _fail("TWO_WORLD_WITNESS_REQUIRED")
 if worlds[0].get("visible_input")!=worlds[1].get("visible_input"):
  return _fail("WORLDS_NOT_VISIBLY_INDISTINGUISHABLE")
 truths={json.dumps((w.get("source_truth") or {}).get("H")) for w in worlds}
 if truths!={"0","1"}:return _fail("WORLDS_DO_NOT_OPPOSE_REQUIRED_SOURCE_TRUTH")
 if counterexample.get("world_hypothesis_set_complete") is not True:
  return _fail("HYPOTHESIS_SET_COMPLETENESS_UNPROVED")
 if counterexample.get("authorized_observation_library_complete") is not True or counterexample.get("authorized_observation_count")!=0:
  return _fail("AUTHORIZED_OBSERVATION_BOUNDARY_NOT_CLOSED")
 source=visible.get("source_evidence")
 if not isinstance(source,Mapping) or source.get("value_disclosed") is not False or source.get("authorized_value_observation_interface") is not None:
  return _fail("SOURCE_VALUE_NOT_PROVED_WITHHELD")

 problem=counterexample.get("positive_semantic_resolution_problem")
 verdict=minimax.solve(problem) if isinstance(problem,Mapping) else {"pass":False,"reason":"PROBLEM_MISSING"}
 if verdict.get("pass") is not False or verdict.get("status")!="FAIL_CLOSED__NO_DECLARED_OBSERVATION_POLICY_CAN_REACH_A_COMMON_DECISION_REGION":
  return _fail("POSITIVE_COMMON_POLICY_NONIDENTIFIABILITY_NOT_PROVED",minimax_verdict=verdict)
 pair=sorted(verdict.get("unresolved_pair_witnesses") or [])
 if pair!=[["W_H0","W_H1"]]:return _fail("EXPECTED_UNRESOLVED_PAIR_NOT_PROVED")

 defeater=counterexample.get("material_defeater") or {}
 if defeater.get("root_relevant") is not True or defeater.get("decision_null") is not False:
  return _fail("MATERIAL_DEFEATER_BINDING_INVALID")
 safe=counterexample.get("safe_common_policy") or {}
 if safe.get("policy_id")!="ABSTAIN_WITH_MINIMUM_BLOCKING_CUT" or safe.get("positive_property_credit") is not False:
  return _fail("SAFE_ABSTENTION_POLICY_INVALID")
 if set(safe.get("valid_in_world_ids") or [])!={"W_H0","W_H1"}:
  return _fail("SAFE_ABSTENTION_NOT_COMMON")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__CONSTRUCTIVE_ADMISSIBLE_COUNTEREXAMPLE_FALSIFIES_OVERSTRONG_UNIVERSAL_R12_SEMANTIC_SUCCESS_PREDICATE",
  "counterexample_admissible":True,
  "behavior_id":BEHAVIOR_ID,"leaf_id":LEAF_ID,
  "stronger_claim_id":STRONGER_CLAIM_ID,"safe_claim_id":SAFE_CLAIM_ID,
  "world_count":2,"visible_information_identical":True,
  "hypothesis_set_complete":True,"authorized_observation_library_complete":True,
  "common_positive_semantic_resolution_policy_exists":False,
  "unresolved_pair_witnesses":[["W_H0","W_H1"]],
  "material_root_relevant_defeater_unresolved":True,
  "material_defeater_decision_null":False,
  "safe_fail_closed_policy_exists":True,
  "safe_policy":"ABSTAIN_WITH_MINIMUM_BLOCKING_CUT",
  "safe_policy_positive_property_credit":False,
  "mission_correct_abstention":True,
  "stronger_universal_predicate_falsified":True,
  "proof_rule":"ONE_ADMISSIBLE_COUNTEREXAMPLE_SUFFICES_TO_FALSIFY_FOR_ALL_ADMISSIBLE_INPUTS",
  "required_repair":"SPLIT_UNIVERSAL_CERTIFICATION_SAFETY_FROM_POSITIVE_ADEQUACY_COVERAGE__DO_NOT_REQUIRE_POSITIVE_SEMANTIC_RESOLUTION_WHEN_AUTHORIZED_INFORMATION_IS_INSUFFICIENT",
  "stronger_r12_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 return evaluate(build_counterexample(),repo_root=repo_root)

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
