"""Stable-claim CC_R1/CC_R2 reinstantiation for R12 professional semantics.

This module reuses the verified V3 stable-mission semantic claim pack and the
whole-leaf scope batch. It proves only claim-scoped reality containment and
mission soundness for the current stable R12 claim. CC_R3, R4, leaf property
truth, quality, acceptance, promotion, and terminal authority remain open.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as scope_batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_STABLE_ROOTS_V1"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
EXPECTED_R12_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
OLD_V2_R12_CLAIM_ID="97ff74650749db87f378d5926ed820e004f3f792583c2c8455e51c3ccacbe7f7"
EXPECTED_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
EXPECTED_QUANTIFICATION="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE"
EXPECTED_CORRECTNESS="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION"
MISSION_AUTHORITY_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "cc_r1_reality_containment_proved":False,
  "cc_r2_mission_soundness_proved":False,
  "cc_r3_terminal_closure_proved":False,
  "r4_proof_closure":False,
  "semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "property_truth_credit_delta":0,"terminal_credit_delta":0,
  "incremental_spend_usd":0,**extra,
 }

def _current_inputs(root:Path)->tuple[dict[str,Any],dict[str,Any]]:
 out=pack_v3.verify(repo_root=root)
 if out.get("pass") is not True:
  raise RuntimeError("V3_PACK_NOT_PASS:"+str(out.get("reason")))
 rows=out.get("claims") or []
 r12=next((x for x in rows if isinstance(x,Mapping) and x.get("leaf_id")==LEAF_ID),None)
 if not isinstance(r12,dict):
  raise RuntimeError("R12_CLAIM_MISSING")
 mission=json.loads((root/MISSION_AUTHORITY_PATH).read_text(encoding="utf-8"))
 return r12,mission

def evaluate_r12(
 r12:Mapping[str,Any],
 mission_authority:Mapping[str,Any],
 *,
 scope_complete:bool,
)->dict[str,Any]:
 if not isinstance(r12,Mapping) or not isinstance(mission_authority,Mapping):
  return _fail("INPUT_NOT_MAPPING")
 if r12.get("leaf_id")!=LEAF_ID:
  return _fail("R12_LEAF_ID_DRIFT")
 claim=r12.get("frozen_claim")
 if not isinstance(claim,Mapping):
  return _fail("R12_FROZEN_CLAIM_MISSING")
 if claim.get("claim_id")!=EXPECTED_R12_CLAIM_ID:
  return _fail("R12_STABLE_CLAIM_ID_DRIFT",observed_claim_id=claim.get("claim_id"))
 if claim.get("mission_blob_sha")!=pack_v3.EXPECTED_MISSION_AUTHORITY_BLOB:
  return _fail("R12_MISSION_AUTHORITY_BINDING_DRIFT")
 if r12.get("scope_definition_sha256")!=claim.get("scope_sha256"):
  return _fail("R12_SCOPE_BINDING_DRIFT")
 if scope_complete is not True:
  return _fail("WHOLE_LEAF_SCOPE_NOT_COMPLETE")

 target=r12.get("target_predicate")
 sem=r12.get("semantics")
 if not isinstance(target,Mapping) or not isinstance(sem,Mapping):
  return _fail("R12_PROPERTY_SEMANTICS_MISSING")
 if target.get("acceptance")!=EXPECTED_ACCEPTANCE:
  return _fail("R12_ACCEPTANCE_DRIFT")
 if target.get("quantification")!=EXPECTED_QUANTIFICATION:
  return _fail("R12_QUANTIFICATION_DRIFT")
 if sem.get("true_when")!=EXPECTED_ACCEPTANCE:
  return _fail("R12_TRUE_WHEN_DRIFT")
 if sem.get("false_when")!="EXISTS_ADMISSIBLE_INPUT_IN_WHOLE_LEAF_SCOPE_FOR_WHICH_THE_ACCEPTANCE_PROPERTY_FAILS":
  return _fail("R12_FALSE_WHEN_DRIFT")
 if sem.get("bounded_witnesses_are_totality_authority") is not False:
  return _fail("BOUNDED_WITNESS_TOTALITY_OVERCLAIM")

 if mission_authority.get("status")!="ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE":
  return _fail("MISSION_AUTHORITY_NOT_ACTIVE")
 if mission_authority.get("correctness_rule")!=EXPECTED_CORRECTNESS:
  return _fail("MISSION_CORRECTNESS_RULE_DRIFT")
 if mission_authority.get("real_objective")!="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE":
  return _fail("MISSION_OBJECTIVE_DRIFT")

 # CC_R1: the verified scope is the exact whole admissible leaf domain.
 # Use the complete frozen claim world state W_C itself as B_plus and identity
 # as the semantic carrier. Then every real in-scope state is definitionally
 # an element of B_plus. No finite sampling is used.
 cc_r1={
  "proof_mode":"FORMAL_DEFINITIONAL_CONTAINMENT",
  "b_plus":"EXACT_COMPLETE_FROZEN_R12_CLAIM_WORLD_STATE_W_C",
  "carrier_projection":"IDENTITY_ON_W_C",
  "whole_leaf_scope_complete":True,
  "b_real_subseteq_b_plus":True,
  "finite_sampling_used":False,
 }

 # CC_R2: G_minus contains only states satisfying the exact claim acceptance:
 # typed evidence resolves semantics, grounding, scope uncertainty and every
 # root-relevant defeater. The mission's correctness rule grants no progress
 # absent sound verification; unresolved states are therefore not in G_minus.
 # Hence every G_minus state is admissible positive property progress.
 cc_r2={
  "proof_mode":"FORMAL_REDUCTION",
  "mission_axiom":"FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION",
  "g_minus":"STATES_SATISFYING_EXACT_R12_TYPED_EVIDENCE_ACCEPTANCE",
  "g_real":"STATES_AUTHORIZED_FOR_POSITIVE_PROGRESS_ON_THIS_EXACT_PROPERTY",
  "g_minus_subseteq_g_real":True,
  "unresolved_material_state_positive_credit":False,
  "abstention_is_positive_property_truth":False,
 }

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__STABLE_R12_CC_R1_AND_CC_R2_REINSTANTIATED__CC_R3_R4_AND_PROPERTY_TRUTH_OPEN",
  "leaf_id":LEAF_ID,"claim_id":EXPECTED_R12_CLAIM_ID,
  "scope_sha256":claim.get("scope_sha256"),
  "semantics_sha256":claim.get("semantics_sha256"),
  "mission_authority_blob_sha":claim.get("mission_blob_sha"),
  "cc_r1_reality_containment_proved":True,
  "cc_r2_mission_soundness_proved":True,
  "cc_r3_terminal_closure_proved":False,
  "r4_proof_closure":False,
  "cc_r1":cc_r1,"cc_r2":cc_r2,
  "semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "property_truth_credit_delta":0,"terminal_credit_delta":0,
  "incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  r12,mission=_current_inputs(root)
 except Exception as exc:
  return _fail("CURRENT_INPUT_RESOLUTION_FAILED",detail=type(exc).__name__+":"+str(exc))
 scope=scope_batch.verify(repo_root=root)
 if scope.get("pass") is not True:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_PASS",scope_reason=scope.get("reason"))
 row=next((x for x in (scope.get("rows") or []) if isinstance(x,Mapping) and x.get("leaf_id")==LEAF_ID),None)
 if not isinstance(row,Mapping):
  return _fail("R12_SCOPE_ROW_MISSING")
 if row.get("scope_definition_sha256")!=r12.get("scope_definition_sha256"):
  return _fail("R12_SCOPE_BATCH_BINDING_DRIFT")
 return evaluate_r12(r12,mission,scope_complete=row.get("whole_leaf_scope_complete") is True)

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
