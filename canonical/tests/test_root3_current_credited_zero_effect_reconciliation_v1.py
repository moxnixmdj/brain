from canonical.runtime.root3_current_credited_zero_effect_reconciliation_verifier_v1 import verify


def test_current_credited_root3_zero_effect_cut_is_exact_and_fail_closed():
    out = verify()
    assert out["pass"] is True, out
    assert out["credited_route_count"] == 4
    assert out["material_effect_count"] == 0
    assert out["current_effect_driver_gap"] is False
    assert out["D_finality_closed"] is False
    assert out["complete_selected_context_ABC_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
