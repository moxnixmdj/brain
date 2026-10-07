from canonical.runtime.v17_professional_quality_information_cut_verifier_v1 import verify

def test_professional_quality_information_cut():
    out = verify()
    assert out["pass"] is True, out
    assert out["professional_quality_global_scope_equivalent_now"] is False
    assert out["bounded_p2_cell_remains_valid"] is True
    assert out["universal_visible_policy_exists_for_opposed_hidden_worlds"] is False
    assert out["minimax_visible_only_success"] == "1/2"
    assert out["new_information_or_new_structural_restriction_required"] is True
    assert out["fresh_target_case_executed"] is False
    assert out["abc_closed"] is False
    assert out["d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
