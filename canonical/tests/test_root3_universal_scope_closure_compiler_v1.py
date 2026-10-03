from copy import deepcopy
from canonical.runtime.root3_universal_scope_closure_compiler_v1 import FORMAL, compile_root3

def docs():
 root_state={"current_residual_root_partition":{
  "root3_only":[
   "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","VISION_DENSE_NONCHART_SCOPE",
   "FINANCE_UNCOVERED_SCOPE_AUDIT","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
   "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT","COMPOSITION_COMPONENT_SCOPED_PROOFS",
   "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"],
  "root2_and_root3":[
   "AGENCY_MATCHED_SUCCESS_NONINFERIOR","IF_SCOPE_BOUNDARY_NONINFERIOR",
   "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"],
  "root3_only_count":7,"root2_and_root3_count":4}}
 residual={"compressed_residuals":[
  {"predicate_id":"FINANCE_UNCOVERED_SCOPE_AUDIT","current_residual":"TWO_FROZEN_DIRECT_ORACLE_LEAVES","source_admission_work_remaining":False},
  {"predicate_id":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT","current_residual":"TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES__OPERATIVE_V4_LEARNING_OVERLAY_VERIFIED","source_admission_work_remaining":False},
  {"predicate_id":"COMPOSITION_COMPONENT_SCOPED_PROOFS"},
  {"predicate_id":"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"}],
  "remaining_root3_targets_without_a_current_positive_pair_overlay_bound_here":sorted(FORMAL)}
 saturation={"current_matched_surface_result":{"pair_count":96,"direct_reuse_closures":0},
  "other_live_root3_target_result":{"targets":sorted(FORMAL)}}
 composition={"truth":{"frozen_interface_count":12,"current_admissible_scoped_proved":4,"current_open":8},
  "open_components":["research","tool use","artifact creation","browser/computer action","coding","debugging","evidence synthesis","artifact production"]}
 synthesis={"expected_residual":{"missing_scope_relation":True,"missing_atoms":["metric:matched_quality"],
  "missing_metric_bounds":["matched_quality_noninferiority","required_claim_coverage_noninferiority"]}}
 return root_state,residual,saturation,composition,synthesis

def test_exact_compression():
 out=compile_root3(*docs())
 assert out["status"].startswith("PASS"),out
 assert out["live_root3_predicate_count"]==11
 assert out["work_class_count"]==4
 assert out["formal_shared_target_count"]==7
 assert out["composition_open_component_count"]==8
 assert out["frozen_direct_oracle_leaf_count"]==4
 assert out["primary_zero_reality_action_id"]=="ROOT3_FORMAL_SCOPE_SHARED_V1"
 assert out["fresh_reality_authority"] is False
 assert out["acceptance_credit_delta"]==0

def test_unknown_target_fails_closed():
 d=list(docs()); d[0]=deepcopy(d[0])
 d[0]["current_residual_root_partition"]["root3_only"].append("SURPRISE_SCOPE_TARGET")
 d[0]["current_residual_root_partition"]["root3_only_count"]=8
 out=compile_root3(*d)
 assert out["status"]=="FAIL_CLOSED"
 assert "LIVE_ROOT3_SET_DRIFT" in out["errors"]

def test_changed_saturation_fails_closed():
 d=list(docs()); d[2]=deepcopy(d[2])
 d[2]["current_matched_surface_result"]["direct_reuse_closures"]=1
 out=compile_root3(*d)
 assert out["status"]=="FAIL_CLOSED"
 assert "CURRENT_8X12_SATURATION_DRIFT" in out["errors"]

def test_oracle_reinternalization_is_rejected():
 d=list(docs()); d[1]=deepcopy(d[1])
 d[1]["compressed_residuals"][0]["source_admission_work_remaining"]=True
 out=compile_root3(*d)
 assert out["status"]=="FAIL_CLOSED"
 assert "FINANCE_SOURCE_ADMISSION_REOPENED" in out["errors"]

def test_composition_is_event_driven():
 out=compile_root3(*docs())
 row=next(x for x in out["work_classes"] if x["id"]=="ROOT3_COMPOSITION_DEPENDENCY_RECOMPUTE_V1")
 assert row["available_now"] is False
 assert row["new_reality_units"]==0
 assert len(row["open_components"])==8

def test_four_oracle_leaves_not_authorized():
 out=compile_root3(*docs())
 row=next(x for x in out["work_classes"] if x["id"]=="ROOT3_FROZEN_DIRECT_ORACLE_MINCUT_V1")
 assert row["available_now"] is False
 assert row["new_reality_units"]==4
 assert out["fresh_reality_authority"] is False
