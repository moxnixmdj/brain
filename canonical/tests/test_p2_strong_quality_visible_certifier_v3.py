from canonical.runtime.p2_strong_quality_visible_certifier_v3 import certify,P2
def base():
 return {"public":{"contract":P2,"task":{"audience":"executive","required_topics":["T1"],"evidence":[{"fact_id":"F1","topic":"T1","text":"fact","provenance":["S1"]}],"edit_candidates":[{"id":"E1","analysis_kind":"quantify","topic":"T1","claims":["F1"],"intended_audience":"executive","cost":1,"text":"x"}],"edit_budget":1}},"quality_binding":{"lossless_p2_membership_proved":True,"lossless_p2_membership_receipt":"m1","baseline_layout_nonobscuring":True,"baseline_layout_receipt":"l1","ablation_rescue_semantics_bound_to_certifier_policy":True,"ablation_rescue_semantics_receipt":"a1","native_mechanical_gate_required":False}}
def empty_base():
 x=base(); q=x["quality_binding"]; q["mechanics_only_baseline_equals_empty_p2_plan"]=True; q["mechanics_only_baseline_equivalence_receipt"]="b-empty"; return x
def bound_base():
 x=base(); q=x["quality_binding"]; q["mechanics_baseline_bound"]=True; q["mechanics_baseline_id"]="MECH-BASE-17"; q["mechanics_baseline_binding_receipt"]="b-real"; return x
def exact():
 x=empty_base(); q=x["quality_binding"]; q["explicit_rubric_equivalent_to_p2_objective"]=True; q["rubric_equivalence_receipt"]="r1"; return x
def comp_empty():
 x=empty_base(); q=x["quality_binding"]; q["target_comparison_order_bound"]=True; q["target_comparison_order_receipt"]="ord1"; q["comparison_order"]={"selected_edit_ids":["E1"],"baseline_id":"EMPTY_P2_PLAN","ablated_edit_id":"E1","selected_gt_baseline":True,"selected_gt_ablated":True,"rescue_eq_selected":True}; return x
def comp_bound():
 x=bound_base(); q=x["quality_binding"]; q["target_comparison_order_bound"]=True; q["target_comparison_order_receipt"]="ord2"; q["comparison_order"]={"selected_edit_ids":["E1"],"baseline_id":"MECH-BASE-17","ablated_edit_id":"E1","selected_gt_baseline":True,"selected_gt_ablated":True,"rescue_eq_selected":True}; return x
def test_legacy_exact(): assert certify(exact())["pass"] is True
def test_comparison_empty(): assert certify(comp_empty())["pass"] is True
def test_comparison_bound_actual_baseline():
 y=certify(comp_bound()); assert y["pass"] is True,y
 assert y["baseline_binding"]["mode"]=="BOUND_ACTUAL_MECHANICS_BASELINE"
 assert y["mechanics_only_baseline_objective"] is None
def test_bound_baseline_receipt_required():
 x=comp_bound(); x["quality_binding"]["mechanics_baseline_binding_receipt"]=""; y=certify(x); assert "MECHANICS_BASELINE_BINDING_MISSING" in y["errors"]
def test_bound_baseline_identity_required():
 x=comp_bound(); x["quality_binding"]["mechanics_baseline_id"]=""; y=certify(x); assert "MECHANICS_BASELINE_BINDING_MISSING" in y["errors"]
def test_comparison_baseline_identity_must_match():
 x=comp_bound(); x["quality_binding"]["comparison_order"]["baseline_id"]="OTHER"; y=certify(x); assert "COMPARISON_BASELINE_ID_MISMATCH" in y["errors"]
def test_exact_mode_cannot_use_opaque_bound_baseline():
 x=bound_base(); q=x["quality_binding"]; q["explicit_rubric_equivalent_to_p2_objective"]=True; q["rubric_equivalence_receipt"]="r1"; y=certify(x); assert "FULL_RUBRIC_MODE_REQUIRES_EMPTY_P2_BASELINE_EQUIVALENCE" in y["errors"]
def test_no_baseline_binding_fails():
 x=base(); q=x["quality_binding"]; q["target_comparison_order_bound"]=True; q["target_comparison_order_receipt"]="o"; q["comparison_order"]={}; y=certify(x); assert "MECHANICS_BASELINE_BINDING_MISSING" in y["errors"]
def test_selected_gt_baseline_still_required():
 x=comp_bound(); x["quality_binding"]["comparison_order"]["selected_gt_baseline"]=False; assert "COMPARISON_SELECTED_GT_BASELINE_NOT_PROVED" in certify(x)["errors"]
def test_audience_still_fail_closed():
 x=comp_bound(); x["public"]["task"]["edit_candidates"][0]["intended_audience"]="auditor"; assert "QUALITY_GATE_FAILED:AUDIENCE_EMPHASIS_MATCHES_VISIBLE_OBJECTIVE" in certify(x)["errors"]
def test_membership_still_required():
 x=comp_bound(); x["quality_binding"]["lossless_p2_membership_proved"]=False; assert "LOSSLESS_P2_MEMBERSHIP_NOT_PROVED" in certify(x)["errors"]
