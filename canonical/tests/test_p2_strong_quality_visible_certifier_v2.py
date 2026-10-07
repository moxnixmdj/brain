from canonical.runtime.p2_strong_quality_visible_certifier_v2 import certify,P2
def base():
 return {"public":{"contract":P2,"task":{"audience":"executive","required_topics":["T1"],"evidence":[{"fact_id":"F1","topic":"T1","text":"fact","provenance":["S1"]}],"edit_candidates":[{"id":"E1","analysis_kind":"quantify","topic":"T1","claims":["F1"],"intended_audience":"executive","cost":1,"text":"x"}],"edit_budget":1}},"quality_binding":{"lossless_p2_membership_proved":True,"lossless_p2_membership_receipt":"m1","baseline_layout_nonobscuring":True,"baseline_layout_receipt":"l1","mechanics_only_baseline_equals_empty_p2_plan":True,"mechanics_only_baseline_equivalence_receipt":"b1","ablation_rescue_semantics_bound_to_certifier_policy":True,"ablation_rescue_semantics_receipt":"a1","native_mechanical_gate_required":False}}
def exact():
 x=base(); q=x["quality_binding"]; q["explicit_rubric_equivalent_to_p2_objective"]=True; q["rubric_equivalence_receipt"]="r1"; return x
def comparison():
 x=base(); q=x["quality_binding"]; q["target_comparison_order_bound"]=True; q["target_comparison_order_receipt"]="ord1"; q["comparison_order"]={"selected_edit_ids":["E1"],"ablated_edit_id":"E1","selected_gt_baseline":True,"selected_gt_ablated":True,"rescue_eq_selected":True}; return x
def test_exact(): assert certify(exact())["pass"] is True
def test_comparison(): 
 y=certify(comparison()); assert y["pass"] is True and y["quality_order_binding"]["mode"]=="BOUND_COMPARISON_ORDER"
def test_missing(): assert "QUALITY_ORDER_CERTIFICATE_MISSING" in certify(base())["errors"]
def test_receipt():
 x=comparison(); x["quality_binding"]["target_comparison_order_receipt"]=""; assert "QUALITY_ORDER_CERTIFICATE_MISSING" in certify(x)["errors"]
def test_selected_mismatch():
 x=comparison(); x["quality_binding"]["comparison_order"]["selected_edit_ids"]=["WRONG"]; assert "COMPARISON_SELECTED_PLAN_MISMATCH" in certify(x)["errors"]
def test_ablation_mismatch():
 x=comparison(); x["quality_binding"]["comparison_order"]["ablated_edit_id"]="WRONG"; assert "COMPARISON_ABLATED_EDIT_MISMATCH" in certify(x)["errors"]
def test_base_order():
 x=comparison(); x["quality_binding"]["comparison_order"]["selected_gt_baseline"]=False; assert "COMPARISON_SELECTED_GT_BASELINE_NOT_PROVED" in certify(x)["errors"]
def test_ablation_order():
 x=comparison(); x["quality_binding"]["comparison_order"]["selected_gt_ablated"]=False; assert "COMPARISON_SELECTED_GT_ABLATED_NOT_PROVED" in certify(x)["errors"]
def test_rescue():
 x=comparison(); x["quality_binding"]["comparison_order"]["rescue_eq_selected"]=False; assert "COMPARISON_RESCUE_EQ_SELECTED_NOT_PROVED" in certify(x)["errors"]
def test_audience():
 x=comparison(); x["public"]["task"]["edit_candidates"][0]["intended_audience"]="auditor"; assert "QUALITY_GATE_FAILED:AUDIENCE_EMPHASIS_MATCHES_VISIBLE_OBJECTIVE" in certify(x)["errors"]
def test_membership():
 x=comparison(); x["quality_binding"]["lossless_p2_membership_proved"]=False; assert "LOSSLESS_P2_MEMBERSHIP_NOT_PROVED" in certify(x)["errors"]
