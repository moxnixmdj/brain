"""Fail-closed compiler for the live Root-3 scope-completeness frontier."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_ROOT3_UNIVERSAL_SCOPE_CLOSURE_COMPILER_V1"

FORMAL={
 "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
 "VISION_DENSE_NONCHART_SCOPE",
 "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
 "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
 "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
 "IF_SCOPE_BOUNDARY_NONINFERIOR",
 "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}
SYNTHESIS={"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"}
COMPOSITION={"COMPOSITION_COMPONENT_SCOPED_PROOFS"}
ORACLE={"FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"}
EXPECTED=FORMAL|SYNTHESIS|COMPOSITION|ORACLE

METHOD_ORDER=[
 "EXACT_OR_SUPERSET_CONTENT_ADDRESSED_SCOPE_CERTIFICATE",
 "VERIFIED_LOGICAL_IMPLICATION",
 "INDUCTIVE_INVARIANT_OR_UNIVERSAL_THEOREM",
 "RESIDUAL_ACTION_INVARIANCE",
 "GENUINELY_EXHAUSTIVE_FINITE_PARTITION",
 "ASSUME_GUARANTEE_COMPOSITION",
 "COUNTEREXAMPLE_GUIDED_ABSTRACTION_REFINEMENT",
 "IRREDUCIBLE_ADMISSIBLE_REALITY_ONLY_AFTER_FIXED_POINT",
]

def fail(*errors:str)->dict[str,Any]:
 return {
  "schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
  "execution_authority":False,"fresh_reality_authority":False,
  "promotion_authority":False,"new_reality_units_consumed":0,
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
 }

def compile_root3(
 root_state:Mapping[str,Any],
 residual:Mapping[str,Any],
 saturation:Mapping[str,Any],
 composition:Mapping[str,Any],
 synthesis:Mapping[str,Any],
)->dict[str,Any]:
 e=[]
 part=root_state.get("current_residual_root_partition")
 if not isinstance(part,Mapping): return fail("ROOT_PARTITION_MISSING")
 r3=part.get("root3_only"); mixed=part.get("root2_and_root3")
 if not isinstance(r3,list) or not isinstance(mixed,list): return fail("ROOT3_LISTS_INVALID")
 if any(not isinstance(x,str) or not x for x in r3+mixed): return fail("ROOT3_ID_INVALID")
 live=set(r3)|set(mixed)
 if len(live)!=len(r3)+len(mixed): e.append("ROOT3_PARTITION_OVERLAP")
 if part.get("root3_only_count")!=len(r3): e.append("ROOT3_ONLY_COUNT_DRIFT")
 if part.get("root2_and_root3_count")!=len(mixed): e.append("ROOT3_MIXED_COUNT_DRIFT")
 if live!=EXPECTED: e.append("LIVE_ROOT3_SET_DRIFT")

 rows=residual.get("compressed_residuals")
 if not isinstance(rows,list): e.append("COMPRESSED_RESIDUALS_INVALID"); by={}
 else:
  by={x.get("predicate_id"):x for x in rows if isinstance(x,Mapping) and isinstance(x.get("predicate_id"),str)}
 other=residual.get("remaining_root3_targets_without_a_current_positive_pair_overlay_bound_here")
 if not isinstance(other,list) or set(other)!=FORMAL: e.append("FORMAL_TARGET_SET_DRIFT")

 sat=saturation.get("current_matched_surface_result")
 if not isinstance(sat,Mapping) or sat.get("pair_count")!=96 or sat.get("direct_reuse_closures")!=0:
  e.append("CURRENT_8X12_SATURATION_DRIFT")
 so=saturation.get("other_live_root3_target_result")
 if not isinstance(so,Mapping) or set(so.get("targets") or [])!=FORMAL:
  e.append("FORMAL_SATURATION_TARGET_DRIFT")

 fin=by.get("FINANCE_UNCOVERED_SCOPE_AUDIT",{})
 unk=by.get("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",{})
 if fin.get("current_residual")!="TWO_FROZEN_DIRECT_ORACLE_LEAVES":
  e.append("FINANCE_ORACLE_RESIDUAL_DRIFT")
 if not str(unk.get("current_residual","")).startswith("TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES"):
  e.append("UNKNOWN_ORACLE_RESIDUAL_DRIFT")
 if fin.get("source_admission_work_remaining") is not False: e.append("FINANCE_SOURCE_ADMISSION_REOPENED")
 if unk.get("source_admission_work_remaining") is not False: e.append("UNKNOWN_SOURCE_ADMISSION_REOPENED")

 ct=composition.get("truth")
 opens=composition.get("open_components")
 if not isinstance(ct,Mapping): e.append("COMPOSITION_TRUTH_MISSING")
 else:
  if ct.get("frozen_interface_count")!=12: e.append("COMPOSITION_INTERFACE_COUNT_DRIFT")
  if ct.get("current_admissible_scoped_proved")!=4: e.append("COMPOSITION_PROVED_COUNT_DRIFT")
  if ct.get("current_open")!=8: e.append("COMPOSITION_OPEN_COUNT_DRIFT")
 if not isinstance(opens,list) or len(opens)!=8: e.append("COMPOSITION_OPEN_COMPONENTS_INVALID")

 exp=synthesis.get("expected_residual")
 if not isinstance(exp,Mapping): e.append("SYNTHESIS_INPUT_INVALID")
 else:
  if exp.get("missing_scope_relation") is not True: e.append("SYNTHESIS_SCOPE_RELATION_DRIFT")
  if exp.get("missing_atoms")!=["metric:matched_quality"]: e.append("SYNTHESIS_MISSING_ATOM_DRIFT")
  if set(exp.get("missing_metric_bounds") or [])!={"matched_quality_noninferiority","required_claim_coverage_noninferiority"}:
   e.append("SYNTHESIS_METRIC_RESIDUAL_DRIFT")

 if e: return fail(*e)

 work=[
  {
   "id":"ROOT3_FORMAL_SCOPE_SHARED_V1","kind":"ZERO_REALITY_FORMAL_SCOPE",
   "target_predicates":sorted(FORMAL),"target_count":7,"available_now":True,
   "new_reality_units":0,"method_order":METHOD_ORDER,
   "stop_rule":"STOP_GENERIC_SEARCH_UNLESS_A_SATURATION_RESUME_CONDITION_CHANGES",
  },
  {
   "id":"ROOT3_SYNTHESIS_SCOPE_RELATION_V1","kind":"ZERO_REALITY_SEMANTIC_SCOPE_BINDING",
   "target_predicates":sorted(SYNTHESIS),"target_count":1,"available_now":True,
   "new_reality_units":0,"already_verified_operational_atoms":7,
   "root3_residual_only":["missing_scope_relation"],
   "root2_residuals_preserved":["metric:matched_quality","matched_quality_noninferiority","required_claim_coverage_noninferiority"],
  },
  {
   "id":"ROOT3_COMPOSITION_DEPENDENCY_RECOMPUTE_V1","kind":"EVENT_DRIVEN_ASSUME_GUARANTEE_DEPENDENCY",
   "target_predicates":sorted(COMPOSITION),"target_count":1,"available_now":False,
   "new_reality_units":0,"proved_components":4,"open_components":list(opens),
   "wake_condition":"ANY_NEW_INDEPENDENT_CURRENT_SCOPE_COMPLETE_UPSTREAM_COMPONENT_RECEIPT",
  },
  {
   "id":"ROOT3_FROZEN_DIRECT_ORACLE_MINCUT_V1","kind":"IRREDUCIBLE_REALITY_CANDIDATE",
   "target_predicates":sorted(ORACLE),"target_count":2,"available_now":False,
   "new_reality_units":4,"frozen_leaf_count":4,
   "wake_condition":"GLOBAL_ZERO_REALITY_FIXED_POINT_REACHED_AND_FRESH_REALITY_EXPLICITLY_AUTHORIZED",
  },
 ]
 for w in work:
  w["deterministic_leverage"]=float(w["target_count"])/float(1+int(w["new_reality_units"]))
 runnable=sorted((w for w in work if w["available_now"]),key=lambda x:(-x["deterministic_leverage"],x["id"]))
 return {
  "schema":SCHEMA,
  "status":"PASS__EXACT_11_ROOT3_TARGETS_COMPRESSED_TO_4_NONOVERLAPPING_WORK_CLASSES__ZERO_CREDIT",
  "live_root3_predicate_count":11,"root3_only_count":7,"root2_and_root3_count":4,
  "work_class_count":4,"work_classes":work,
  "primary_zero_reality_action_id":runnable[0]["id"],
  "runnable_zero_reality_actions":[w["id"] for w in runnable],
  "formal_shared_target_count":7,"synthesis_scope_relation_count":1,
  "composition_open_component_count":8,"frozen_direct_oracle_leaf_count":4,
  "generic_current_witness_search_saturated":True,
  "generic_current_witness_pairs_checked":96,
  "generic_current_witness_direct_closures":0,
  "rule":"SHARED_FORMAL_SCOPE_PROOF_PLUS_ONE_SYNTHESIS_SCOPE_RELATION_PLUS_EVENT_DRIVEN_COMPOSITION_PLUS_ONLY_AFTER_FIXED_POINT_FOUR_FROZEN_DIRECT_ORACLE_LEAVES",
  "execution_authority":False,"fresh_reality_authority":False,
  "promotion_authority":False,"new_reality_units_consumed":0,
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
 }

def main()->int:
 root=Path(__file__).resolve().parents[2]
 def load(p:str): return json.loads((root/p).read_text(encoding="utf-8"))
 out=compile_root3(
  load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"),
  load("canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json"),
  load("canonical/governance/CURRENT_ROOT3_ZERO_REALITY_STRONGER_PROOF_SATURATION_V1.json"),
  load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json"),
  load("canonical/governance/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_INPUT_V2.json"),
 )
 print(json.dumps(out,indent=2,sort_keys=True))
 return 0 if out["status"].startswith("PASS") else 1

if __name__=="__main__": raise SystemExit(main())
