from canonical.runtime.finance_uncovered_scope_source_admission_reconciliation_v1 import verify

def test_reconciliation():
    out=verify()
    assert out["pass"] is True
    assert out["finance_source_admitted"] is True
    assert out["direct_leaves_executed"] is False

def test_no_overclaim():
    out=verify()
    assert out["acceptance_closed"] is False
    assert out["fresh_reality_authorized"] is False
    assert out["terminal_credit_delta"] == 0
