from canonical.runtime.research_control_v2_universal_selected_cell_verifier_v1 import verify


def test_research_control_v2_universal_selected_cell_verifier():
    out = verify()
    assert out["pass"] is True, out
    assert out["v1_counterexample_reproduced"] is True
    assert out["v2_counterexample_repaired"] is True
    assert out["selected_cell_scope_complete"] is True
    assert out["open_world_research_scope_complete"] is False
    assert out["unknown_domain_family_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
