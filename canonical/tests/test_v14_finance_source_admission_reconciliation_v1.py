from canonical.runtime.v14_finance_source_admission_reconciliation_verifier_v1 import verify

def test_finance_source_reconciliation():
    x=verify()
    assert x["pass"] is True,x
    assert x["finance_source_admitted"] is True
    assert x["remaining_direct_leaf_count"]==2
    assert x["terminal_credit_delta"]==0
