from canonical.runtime.p2_strong_quality_visible_certifier_v1 import certify, P2

def base():
    return {
      "public":{
        "contract":P2,
        "task":{
          "audience":"executive",
          "required_topics":["T1"],
          "evidence":[{"fact_id":"F1","topic":"T1","text":"fact","provenance":["S1"]}],
          "edit_candidates":[
            {"id":"E1","analysis_kind":"quantify","topic":"T1","claims":["F1"],"intended_audience":"executive","cost":1,"text":"x"}
          ],
          "edit_budget":1,
        }
      },
      "quality_binding":{
        "lossless_p2_membership_proved":True,
        "lossless_p2_membership_receipt":"m1",
        "explicit_rubric_equivalent_to_p2_objective":True,
        "rubric_equivalence_receipt":"r1",
        "baseline_layout_nonobscuring":True,
        "baseline_layout_receipt":"l1",
        "mechanics_only_baseline_equals_empty_p2_plan":True,
        "mechanics_only_baseline_equivalence_receipt":"b1",
        "ablation_rescue_semantics_bound_to_certifier_policy":True,
        "ablation_rescue_semantics_receipt":"a1",
        "native_mechanical_gate_required":False,
      }
    }

def test_strong_visible_quality_passes():
    x=certify(base()); assert x["pass"] is True,x
    assert all(x["gates"].values())
    assert x["selected_objective"]>x["mechanics_only_baseline_objective"]
    assert x["ablation"]["marginal_loss"]>0
    assert x["ablation"]["rescue_objective"]==x["selected_objective"]

def test_missing_rubric_equivalence_fails_closed():
    x=base(); x["quality_binding"]["explicit_rubric_equivalent_to_p2_objective"]=False
    y=certify(x); assert y["pass"] is False
    assert "RUBRIC_EQUIVALENCE_NOT_PROVED" in y["errors"]

def test_baseline_layout_certificate_required():
    x=base(); x["quality_binding"]["baseline_layout_nonobscuring"]=False
    y=certify(x); assert y["pass"] is False
    assert "BASELINE_LAYOUT_NOT_CERTIFIED" in y["errors"]

def test_layout_selected_plan_is_rejected():
    x=base(); x["public"]["task"]["required_topics"]=[]
    x["public"]["task"]["edit_candidates"][0]["analysis_kind"]="layout"
    y=certify(x); assert y["pass"] is False
    assert "QUALITY_GATE_FAILED:LAYOUT_OR_STRUCTURE_CHOICE_DOES_NOT_OBSCURE_REQUIRED_INFORMATION" in y["errors"]

def test_missing_required_analytic_coverage_is_rejected():
    x=base(); x["public"]["task"]["edit_candidates"][0]["analysis_kind"]="layout"
    y=certify(x); assert y["pass"] is False
    assert "QUALITY_GATE_FAILED:REQUIRED_ANALYSIS_COVERED" in y["errors"]

def test_native_gate_must_be_bound_when_required():
    x=base(); q=x["quality_binding"]; q["native_mechanical_gate_required"]=True; q["native_mechanical_gate_pass"]=False
    y=certify(x); assert y["pass"] is False
    assert "NATIVE_MECHANICAL_GATE_NOT_PASS" in y["errors"]

def test_lossless_membership_must_be_proved():
    x=base(); x["quality_binding"]["lossless_p2_membership_proved"]=False
    y=certify(x); assert y["pass"] is False
    assert "LOSSLESS_P2_MEMBERSHIP_NOT_PROVED" in y["errors"]

def test_audience_mismatch_selected_plan_is_rejected():
    x=base(); x["public"]["task"]["edit_candidates"][0]["intended_audience"]="auditor"
    y=certify(x); assert y["pass"] is False
    assert "QUALITY_GATE_FAILED:AUDIENCE_EMPHASIS_MATCHES_VISIBLE_OBJECTIVE" in y["errors"]

def test_rubric_equivalence_receipt_is_required():
    x=base(); x["quality_binding"]["rubric_equivalence_receipt"]=""
    y=certify(x); assert y["pass"] is False
    assert "RUBRIC_EQUIVALENCE_RECEIPT_MISSING" in y["errors"]

def test_native_gate_receipt_is_required_when_native_gate_is_required():
    x=base(); q=x["quality_binding"]
    q["native_mechanical_gate_required"]=True
    q["native_mechanical_gate_pass"]=True
    q["native_mechanical_gate_receipt"]=""
    y=certify(x); assert y["pass"] is False
    assert "NATIVE_MECHANICAL_GATE_RECEIPT_MISSING" in y["errors"]

def test_mechanics_baseline_equivalence_is_required():
    x=base(); x["quality_binding"]["mechanics_only_baseline_equals_empty_p2_plan"]=False
    y=certify(x); assert y["pass"] is False
    assert "MECHANICS_BASELINE_EQUIVALENCE_NOT_PROVED" in y["errors"]

def test_ablation_rescue_semantics_binding_is_required():
    x=base(); x["quality_binding"]["ablation_rescue_semantics_bound_to_certifier_policy"]=False
    y=certify(x); assert y["pass"] is False
    assert "ABLATION_RESCUE_SEMANTICS_NOT_BOUND" in y["errors"]
