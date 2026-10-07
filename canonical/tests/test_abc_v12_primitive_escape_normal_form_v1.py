from canonical.runtime.abc_v12_primitive_escape_normal_form_v1 import verify

def test_v12_scope_and_frontier():
    out = verify()
    assert out["pass"], out
    assert out["target_scope_closed"] is True
    assert out["primitive_escape_role_count"] == 5
    assert out["shared_semantic_frontier_count"] == 1

def test_b9_and_terminal_guards():
    out = verify()
    assert out["b9_independent_semantic_primitive"] is False
    assert out["complete_selected_context_abc_closed"] is False
    assert out["global_d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
