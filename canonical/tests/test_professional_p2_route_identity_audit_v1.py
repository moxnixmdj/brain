from canonical.runtime.professional_p2_route_identity_audit_v1 import evaluate

def test_professional_top_cell_route_identity_mismatch_is_localized():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["selected_route_identity_matches_execution_snapshot"] is False
    assert out["p2_binding_candidate_matches_execution_snapshot"] is False
    assert out["execution_snapshot"]["p2_mode"] == "CONTRACT_NATIVE"
    assert out["terminal_credit_delta"] == 0

def test_contract_native_public_task_exposes_fields_frozen_p2_binding_hides():
    out = evaluate()
    info = out["information_boundary_conflicts"]
    assert info["gold_quality_effect_visible_as_scores"] is True
    assert info["grounding_truth_visible_as_supported"] is True
    assert info["binding_hides_per_edit_quality_effect"] is True
    assert info["binding_hides_grounding_truth"] is True
    assert info["binding_requires_edit_options_without_gold_effects"] is True
