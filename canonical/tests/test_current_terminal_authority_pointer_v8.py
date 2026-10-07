from canonical.runtime.current_terminal_authority_pointer_v8_verifier import verify


def test_pointer_v8_preserves_fail_closed_terminal_state():
    out = verify()
    assert out["pass"], out["errors"]
    assert out["authority_schema"] == "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V8"
    assert out["sound_record_count"] == 16
    assert out["newly_closed_refinement"] == "IF_SCOPE_BOUNDARY_NONINFERIOR"
    assert out["U_empty_proved"] is False
    assert out["ABC_closed"] is False
    assert out["D_finality_closed"] is False
    assert out["terminal"] is False


def test_pointer_v8_grants_no_terminal_credit():
    out = verify()
    assert out["terminal_credit_delta"] == 0
