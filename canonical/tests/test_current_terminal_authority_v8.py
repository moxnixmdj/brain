from canonical.runtime.current_terminal_authority_v8_verifier import verify

def test_v8_current_authority_binds_exact_sources():
    out=verify()
    assert out["pass"] is True,out
    assert out["status"].startswith("PASS__")
    assert out["terminal_credit_delta"]==0
