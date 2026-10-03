"""Fail-closed audit of the Tool Discovery frozen-scope completeness receipt.

The independently verified receipt proves a narrower fact: inside each generated
terminal case, every case-local tool identity is visible to the candidate and the
oracle ranges over the same identity list.

It does not prove that the generated 180-case population is the exact complete
case universe of the unchanged frozen protocol.  The protocol/behavior text still
requires unknown-tool discovery on fresh unseen tool sets and "Discover candidate
tools if needed", while the bound candidate has no DISCOVER action and the frozen
source binding explicitly disclaims exhaustive open-domain scope.

This audit prevents per-case identity completeness from being relabeled as
protocol-wide case-universe completeness.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_SCOPE_TRUTH_REPAIR_V1"
PROTOCOL="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
BINDING="canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
CANDIDATE="canonical/runtime/tool_discovery_information_safe_candidate.py"
SCOPE_RECEIPT="canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
SCOPE_DISCHARGE="canonical/runtime/tool_discovery_frozen_scope_completeness_discharge_v1.py"
EXPECTED={
 PROTOCOL:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 REGISTRY:"ee187f611a0e82b2de495ee377682f39bc31dd31",
 BINDING:"6bcabc0a7d0525532ce7b80e132278f7c99caa43",
 CANDIDATE:"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
 SCOPE_RECEIPT:"c9adf25c2e63f9e8b111f1d022acda264d6571f5",
 SCOPE_DISCHARGE:"dc2d88528ae9f6569d24d8611d780579480602f4",
}

def _blob(rel:str)->str:
 data=(ROOT/rel).read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _json(rel:str)->dict[str,Any]:
 v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError(rel+":NOT_OBJECT")
 return v

def _find_behavior(obj:Any)->dict[str,Any]|None:
 if isinstance(obj,dict):
  if obj.get("behavior_id")=="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001": return obj
  for v in obj.values():
   got=_find_behavior(v)
   if got is not None: return got
 elif isinstance(obj,list):
  for v in obj:
   got=_find_behavior(v)
   if got is not None: return got
 return None

def evaluate()->dict[str,Any]:
 drift={p:{"expected":want,"actual":_blob(p)} for p,want in EXPECTED.items() if _blob(p)!=want}
 if drift:
  return _fail("SOURCE_BLOB_DRIFT",source_blob_drift=drift)

 protocols=_json(PROTOCOL)
 row=next((x for x in protocols.get("protocols",[]) if x.get("family")=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"),None)
 behavior=_find_behavior(_json(REGISTRY))
 binding=_json(BINDING)
 receipt=_json(SCOPE_RECEIPT)
 candidate=(ROOT/CANDIDATE).read_text(encoding="utf-8")

 if row is None or behavior is None:
  return _fail("FROZEN_TARGET_NOT_FOUND")

 target_requires_identity_discovery=all([
  "unknown tool discovery" in list(row.get("task_dimensions") or []),
  "fresh unseen tool sets" in str(behavior.get("success_condition") or ""),
  "Discover candidate tools if needed" in str(behavior.get("required_output_or_action") or ""),
  "Unknown/changing tool ecosystem" in str(behavior.get("scope") or ""),
 ])
 bound_route_preenumerates_all_ids=all([
  "TOOL_IDS_AND_DECLARED_COSTS" in binding.get("information_boundary",{}).get("candidate_visible",[]),
  "DISCOVER" not in candidate,
  'public.get("tools", [])' in candidate,
 ])
 source_binding_not_protocol_exhaustive=(
  binding.get("source_pool",{}).get("terminal_scope_claim")
  =="DIRECT_OBJECTIVE_INSTRUMENTATION_INSIDE_T2_T3__NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS"
 )
 receipt_only_proves_per_case_identity_completeness=all([
  "V1_PUBLIC_EXPOSES_COMPLETE_CASE_TOOL_IDENTITY_LIST" in receipt.get("verified",[]),
  "V1_ORACLE_RANGES_OVER_EXACT_SAME_CASE_TOOL_LIST" in receipt.get("verified",[]),
  "V2_INHERITS_V1_GENERATED_IDENTITY_UNIVERSE" in receipt.get("verified",[]),
  "complete_target_case_set" not in receipt.get("verified",[]),
  "ALL_ADMISSIBLE_TARGET_CASES_ENUMERATED" not in receipt.get("verified",[]),
 ])
 receipt_overclaims_complete_case_universe=all([
  receipt.get("basis_kind")=="EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
  receipt.get("complete_target_case_set") is True,
  receipt_only_proves_per_case_identity_completeness,
 ])
 defect=all([
  target_requires_identity_discovery,
  bound_route_preenumerates_all_ids,
  source_binding_not_protocol_exhaustive,
  receipt_overclaims_complete_case_universe,
 ])

 if not defect:
  return _fail(
   "COUNTERPROOF_NOT_ESTABLISHED",
   target_requires_identity_discovery=target_requires_identity_discovery,
   bound_route_preenumerates_all_ids=bound_route_preenumerates_all_ids,
   source_binding_not_protocol_exhaustive=source_binding_not_protocol_exhaustive,
   receipt_only_proves_per_case_identity_completeness=receipt_only_proves_per_case_identity_completeness,
   receipt_overclaims_complete_case_universe=receipt_overclaims_complete_case_universe,
  )

 return {
  "schema":SCHEMA,
  "status":"PASS__SCOPE_RECEIPT_OVERCLAIM_FALSIFIED__PER_CASE_IDENTITY_COMPLETENESS_DOES_NOT_PROVE_PROTOCOL_CASE_UNIVERSE__ZERO_CREDIT",
  "frozen_target_preserved":True,
  "target_family":"TOOL_DISCOVERY_SELECTION_AND_LEARNING",
  "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
  "target_requires_identity_discovery":True,
  "bound_terminal_route_preenumerates_all_case_tool_ids":True,
  "source_binding_explicitly_nonexhaustive_beyond_direct_objective_instrumentation":True,
  "scope_receipt_valid_narrow_fact":"PREENUMERATED_TOOL_IDS_COMPLETE_WITHIN_EACH_GENERATED_TERMINAL_CASE",
  "scope_receipt_invalid_stronger_fact":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
  "complete_target_case_set_supported":False,
  "acceptance_reduction_using_exact_complete_target_case_universe_is_admissible":False,
  "required_repair":(
   "USE_A_UNIVERSAL_OR_EXHAUSTIVE_SCOPE_PROOF_THAT_COVERS_THE_UNCHANGED_UNKNOWN_TOOL_DISCOVERY_PROTOCOL__"
   "OR_A_MATCHED_COMPARATOR_ROUTE__DO_NOT_PROMOTE_180_OF_180_FROM_PER_CASE_IDENTITY_COMPLETENESS"
  ),
  "preserve":[
   "RAW_180_OF_180_EXECUTED_SAMPLE",
   "PER_CASE_IDENTITY_COMPLETENESS_FACT",
   "DYNAMIC_V4_AND_LATER_PROGRAM_SIDE_TRUTH_REPAIRS",
   "CURRENT_3_OF_19_FAMILY_ACCEPTANCE_UNTIL_A_SOUND_SCOPE_PROOF_PASSES"
  ],
  "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
 }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 out={
  "schema":SCHEMA,"status":"FAIL_CLOSED__"+reason,
  "complete_target_case_set_supported":False,
  "acceptance_reduction_using_exact_complete_target_case_universe_is_admissible":False,
  "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
 }
 out.update(extra); return out

if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
