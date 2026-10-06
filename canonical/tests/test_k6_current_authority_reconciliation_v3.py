from canonical.runtime.k6_current_authority_reconciliation_v3 import verify

def test_current_k6_authority_v3():
    out=verify()
    assert out["pass"] is True, out
    assert out["truth_count"]==29
    assert out["unbound_preproof_implementation_generators"]==0
    assert out["open_semantic_information_interfaces"]==1
    assert out["terminal_credit_delta"]==0
