from canonical.runtime.p2_strong_quality_visible_certifier_v4 import certify,P2
def task(two=False):
 edits=[{"id":"E1","analysis_kind":"quantify","topic":"T1","claims":["F1"],"intended_audience":"executive","cost":1,"text":"x"}]
 evidence=[{"fact_id":"F1","topic":"T1","text":"fact","provenance":["S1"]}]
 required=["T1"]; budget=1
 if two:
  edits.append({"id":"E2","analysis_kind":"quantify","topic":"T2","claims":["F2"],"intended_audience":"executive","cost":1,"text":"y"})
  evidence.append({"fact_id":"F2","topic":"T2","text":"fact2","provenance":["S2"]}); required=["T1","T2"]; budget=2
 return {"public":{"contract":P2,"task":{"audience":"executive","required_topics":required,"evidence":evidence,"edit_candidates":edits,"edit_budget":budget}},"quality_binding":{"lossless_p2_membership_proved":True,"lossless_p2_membership_receipt":"m1","baseline_layout_nonobscuring":True,"baseline_layout_receipt":"l1","native_mechanical_gate_required":False}}
def legacy():
 x=task(); q=x["quality_binding"]; q.update({"mechanics_only_baseline_equals_empty_p2_plan":True,"mechanics_only_baseline_equivalence_receipt":"b","ablation_rescue_semantics_bound_to_certifier_policy":True,"ablation_rescue_semantics_receipt":"a","explicit_rubric_equivalent_to_p2_objective":True,"rubric_equivalence_receipt":"r"}); return x
def target_bound():
 x=task(True); q=x["quality_binding"]; q.update({"mechanics_baseline_bound":True,"mechanics_baseline_id":"MB-1","mechanics_baseline_binding_receipt":"mb","target_ablation_bound":True,"target_ablation_edit_id":"E2","target_ablation_binding_receipt":"ta","target_comparison_order_bound":True,"target_comparison_order_receipt":"ord","comparison_order":{"selected_edit_ids":["E1","E2"],"baseline_id":"MB-1","ablated_edit_id":"E2","selected_gt_baseline":True,"selected_gt_ablated":True,"rescue_eq_selected":True}}); return x
def test_legacy_exact_still_passes(): assert certify(legacy())["pass"] is True
def test_target_bound_ablation_can_differ_from_p2_surrogate():
 y=certify(target_bound()); assert y["pass"] is True,y
 assert y["quality_order_binding"]["ablation_binding_mode"]=="BOUND_TARGET_ABLATION"
 assert y["ablation"]["edit_id"]=="E2"
 assert y["ablation"]["p2_surrogate_chosen_edit_id"]=="E1"
def test_target_ablation_receipt_required():
 x=target_bound(); x["quality_binding"]["target_ablation_binding_receipt"]=""; assert "ABLATION_BINDING_MISSING" in certify(x)["errors"]
def test_target_ablation_id_required():
 x=target_bound(); x["quality_binding"]["target_ablation_edit_id"]=""; assert "ABLATION_BINDING_MISSING" in certify(x)["errors"]
def test_target_ablation_must_be_selected():
 x=target_bound(); x["quality_binding"]["target_ablation_edit_id"]="NOPE"; x["quality_binding"]["comparison_order"]["ablated_edit_id"]="NOPE"; assert "TARGET_ABLATION_EDIT_NOT_IN_SELECTED_PLAN" in certify(x)["errors"]
def test_comparison_ablation_id_must_match():
 x=target_bound(); x["quality_binding"]["comparison_order"]["ablated_edit_id"]="E1"; assert "COMPARISON_ABLATED_EDIT_MISMATCH" in certify(x)["errors"]
def test_exact_mode_requires_p2_ablation_binding():
 x=legacy(); q=x["quality_binding"]; q["ablation_rescue_semantics_bound_to_certifier_policy"]=False; q["ablation_rescue_semantics_receipt"]=""; q["target_ablation_bound"]=True; q["target_ablation_edit_id"]="E1"; q["target_ablation_binding_receipt"]="ta"; assert "FULL_RUBRIC_MODE_REQUIRES_P2_ABLATION_BINDING" in certify(x)["errors"]
def test_target_selected_gt_ablation_required():
 x=target_bound(); x["quality_binding"]["comparison_order"]["selected_gt_ablated"]=False; assert "COMPARISON_SELECTED_GT_ABLATED_NOT_PROVED" in certify(x)["errors"]
def test_target_rescue_required():
 x=target_bound(); x["quality_binding"]["comparison_order"]["rescue_eq_selected"]=False; assert "COMPARISON_RESCUE_EQ_SELECTED_NOT_PROVED" in certify(x)["errors"]
def test_audience_still_fail_closed():
 x=target_bound(); x["public"]["task"]["edit_candidates"][0]["intended_audience"]="auditor"; assert "QUALITY_GATE_FAILED:AUDIENCE_EMPHASIS_MATCHES_VISIBLE_OBJECTIVE" in certify(x)["errors"]
def test_membership_still_required():
 x=target_bound(); x["quality_binding"]["lossless_p2_membership_proved"]=False; assert "LOSSLESS_P2_MEMBERSHIP_NOT_PROVED" in certify(x)["errors"]
