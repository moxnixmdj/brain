from canonical.runtime.finance_shared_semantic_residual_reconciliation_verifier_v1 import verify

def test_current_finance_reconciliation_passes():
    x=verify()
    assert x["pass"] is True,x
    assert x["finance_route_exists"] is True
    assert x["finance_uncovered_scope_closed"] is False
    assert x["terminal_credit_delta"]==0
