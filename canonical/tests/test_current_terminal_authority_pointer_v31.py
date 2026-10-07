from canonical.runtime.current_terminal_authority_pointer_v31_verifier import verify


def test_v31_binds_lower_bound_without_deleting_frontier():
    out = verify()
    assert out["pass"], out["errors"]
    assert out["pointer_schema"] == "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V31"
    assert out["open_refinement_family_count"] == 13
    assert out["information_wake_class_count"] == 15
    assert out["presentation_lower_bound_verified"] is True


def test_v31_remains_fail_closed():
    out = verify()
    assert out["U_empty_proved"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
