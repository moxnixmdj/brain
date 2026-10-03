"""Derive the current minimum-action cut for canonical Root-3 scope closure."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_ROOT3_MINIMUM_ACTION_CUT_V1"

P={
 "activation":"canonical/governance/ROOT3_UNIVERSAL_SCOPE_CLOSURE_ACTIVATION_V1.json",
 "coalescence":"canonical/governance/ROOT3_TARGET_POPULATION_COALESCENCE_V1.json",
 "superportfolio":"canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json",
 "saturation":"canonical/governance/CURRENT_ROOT3_ZERO_REALITY_STRONGER_PROOF_SATURATION_V1.json",
 "residual":"canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json",
 "composition":"canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json",
}

def load(p:str)->dict[str,Any]:
 x=json.loads((ROOT/p).read_text(encoding="utf-8"))
 assert isinstance(x,dict)
 return x

def evaluate()->dict[str,Any]:
 a,c,sat,b,resid,comp=(load(P[k]) for k in ("activation","coalescence","saturation","superportfolio","residual","composition"))
 e=[]
 if a.get("current_truth",{}).get("live_root3_predicates")!=11: e.append("ROOT3_COUNT_DRIFT")
 if a.get("status","").find("11_ROOT3_TARGETS_TO_4_WORK_CLASSES")<0: e.append("ACTIVATION_NOT_CURRENT")
 if c.get("accounting",{}).get("formal_root3_target_count")!=7 or c.get("accounting",{}).get("population_group_count")!=4: e.append("FORMAL_POPULATION_COMPRESSION_DRIFT")
 if sat.get("current_matched_surface_result",{}).get("pair_count")!=96 or sat.get("current_matched_surface_result",{}).get("direct_reuse_closures")!=0: e.append("SATURATION_DRIFT")
 if b.get("execution_compression",{}).get("matched_scope_target_count")!=8 or b.get("execution_compression",{}).get("shared_future_superportfolio_wave_count")!=1: e.append("SUPERPORTFOLIO_DRIFT")
 by={x.get("predicate_id"):x for x in resid.get("compressed_residuals",[]) if isinstance(x,Mapping)}
 if by.get("FINANCE_UNCOVERED_SCOPE_AUDIT",{}).get("current_residual")!="TWO_FROZEN_DIRECT_ORACLE_LEAVES": e.append("FINANCE_LEAF_DRIFT")
 if not str(by.get("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",{}).get("current_residual","")).startswith("TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES"): e.append("UNKNOWN_LEAF_DRIFT")
 syn=by.get("SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",{}).get("current_residual",{})
 if syn.get("missing_scope_relation") is not True: e.append("SYNTHESIS_SCOPE_RELATION_DRIFT")
 truth=comp.get("truth",{})
 if truth.get("current_admissible_scoped_proved")!=4 or truth.get("current_open")!=8: e.append("COMPOSITION_DEPENDENCY_DRIFT")
 if e:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(e)),"execution_authority":False,"fresh_reality_authority":False}

 events=[
  {
   "id":"NEW_SCOPE_CERTIFICATE_EVENT",
   "covers":["4_FORMAL_POPULATION_IDENTITIES","1_SYNTHESIS_SCOPE_RELATION"],
   "action":"ADMIT_ONLY_NEW_INDEPENDENT_CONTENT_ADDRESSED_EXACT_OR_SUPERSET_SCOPE_CERTIFICATES_OR_FULL_PROTOCOL_UNIVERSAL_WITNESSES",
   "currently_runnable":False,
   "reason":"CURRENT_BOUND_ZERO_REALITY_SCOPE_SEARCH_SATURATED__96_PAIRS__0_DIRECT_CLOSURES",
   "cost_new_reality_units":0,
  },
  {
   "id":"UPSTREAM_SCOPE_RECEIPT_EVENT",
   "covers":["COMPOSITION_COMPONENT_SCOPED_PROOFS"],
   "action":"RECOMPUTE_8_OPEN_COMPOSITION_INTERFACES_ONLY_WHEN_NEW_SCOPE_COMPLETE_UPSTREAM_RECEIPTS_LAND",
   "currently_runnable":False,
   "reason":"EVENT_DRIVEN_DEPENDENCY__NO_DIRECT_REALITY",
   "cost_new_reality_units":0,
  },
  {
   "id":"ROOT3_FRESH_REALITY_EVENT",
   "covers":["8_MATCHED_SCOPE_TARGETS_IN_ONE_SUPERPORTFOLIO_WAVE","4_FROZEN_DIRECT_ORACLE_LEAVES"],
   "action":"AFTER_GLOBAL_ZERO_REALITY_FIXED_POINT_AND_REQUIRED_COMPARATOR_ADMISSIBILITY__RUN_ONE_SHARED_MATCHED_WAVE_PLUS_ONE_FOUR_LEAF_DIRECT_ORACLE_BATCH",
   "currently_runnable":False,
   "reason":"FRESH_REALITY_NOT_AUTHORIZED",
   "cost_new_reality_units":"MINIMUM_CUT_TO_BE_FINALIZED_AT_FIXED_POINT",
  },
 ]
 return {
  "schema":SCHEMA,
  "status":"PASS__ROOT3_COMPRESSED_TO_3_EVENT_CLASSES__NO_CURRENT_NONDOMINATED_ROOT3_EXECUTION",
  "live_root3_predicates":11,
  "formal_population_identities":4,
  "synthesis_scope_relations":1,
  "composition_open_interfaces":8,
  "matched_scope_targets_shared_wave":8,
  "direct_oracle_leaves":4,
  "event_class_count":3,
  "event_classes":events,
  "currently_runnable_event_count":0,
  "current_root3_state":"ZERO_REALITY_SATURATED__WAITING_ON_NEW_CERTIFICATE_OR_UPSTREAM_SCOPE_RECEIPT_OR_GLOBAL_FRESH_REALITY_AUTHORIZATION",
  "forbidden_now":[
    "REPEAT_GENERIC_ROOT3_SEARCH",
    "RUN_DIRECT_COMPOSITION_REALITY",
    "REPROVE_SEVEN_SYNTHESIS_OPERATIONAL_ATOMS",
    "REINTERNALIZE_FINANCE_OR_UNKNOWN_DOMAIN_SOURCES",
    "GENERATE_MATCHED_CASES_BEFORE_COMPARATOR_ADMISSIBILITY_AND_FIXED_POINT",
    "EXECUTE_FOUR_DIRECT_ORACLE_LEAVES_BEFORE_AUTHORIZATION",
  ],
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False,
  "fresh_reality_authority":False,
 }

if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
