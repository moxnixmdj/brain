from canonical.runtime.native_artifact_v12_selected_context_abc_verifier_v1 import verify

def test_native_artifact_exact_cell_is_top_without_target_info():
    out=verify()
    assert out["pass"], out
    assert out["K_c_minus_empty"] is True
    assert out["target_information_required"] is False

def test_scope_and_finality_guards_remain():
    out=verify()
    assert out["B7_role_closed"] is False
    assert out["global_D_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
