from canonical.runtime.finance_direct_source_coverage_audit_v1 import evaluate

def test_finance_source_coverage_gap_is_localized_on_bound_bytes():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["general_substrate_source_gate_already_passed"] is True
    assert out["semantic_ir_declares_no_raw_semantic_inference"] is True
    assert out["two_world_countermodel"]["route_distinguishes_worlds"] is False
    assert out["two_world_countermodel"]["protocol_truth_differs"] is True
    assert "ALL_MATERIAL_EXCEPTIONS_AND_ESCALATION_CONDITIONS_PRESERVED" in out["protocol_load_bearing_completeness_obligations"]
    assert "NO_DECISION_RELEVANT_FACT_DROPPED" in out["protocol_load_bearing_completeness_obligations"]
    assert out["terminal_credit_delta"] == 0
