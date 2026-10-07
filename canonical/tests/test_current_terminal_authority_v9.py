from canonical.runtime.current_terminal_authority_v9_verifier import verify

def test_v9_selected_context_authority_is_fail_closed():
    out=verify()
    assert out["pass"] is True,out
    assert out["status"].startswith("PASS__")
    assert out["terminal_credit_delta"]==0
