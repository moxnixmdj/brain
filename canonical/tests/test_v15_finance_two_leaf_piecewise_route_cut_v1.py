from canonical.runtime.v15_finance_two_leaf_piecewise_route_cut_verifier_v1 import verify

def test_finance_two_leaf_piecewise_cut():
    out=verify()
    assert out["pass"] is True,out
    assert out["residual_semantic_binding_count"]==2
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0
