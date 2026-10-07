from canonical.runtime.current_terminal_authority_v7_verifier import verify

def test_v7_reconciles_v6_with_verified_28_truth_basis():
    out=verify()
    assert out["pass"] is True,out
    assert out["open_truth_obligations"]==28
    assert out["accepted_families"]==5
    assert out["open_families"]==14
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0

def test_no_hidden_credit_from_reconciliation():
    out=verify()
    assert out["status"].endswith("ZERO_CREDIT")
