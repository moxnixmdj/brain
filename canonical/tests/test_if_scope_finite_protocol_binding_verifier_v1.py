from canonical.runtime.if_scope_finite_protocol_binding_verifier_v1 import verify

def test_if_finite_scope_protocol_binding_truth_repair():
    out = verify()
    assert out["pass"] is True, out["errors"]
    assert out["declared_scope_mode"] == "FINITE_DECLARED_SCOPE"
    assert out["case_count"] == 160
    assert out["brain_success_count"] == 160
    assert out["required_atom_count"] == 5
    assert out["covered_atom_count"] == 5
    assert out["opus_query_required"] is False
    assert out["if_scope_boundary_refinement_closed"] is True
    assert out["terminal_credit_delta"] == 0
