from canonical.runtime.verify_matched_brain_first_current_reconciliation_v1 import verify

def test_current_brain_first_reconciliation():
    out=verify()
    assert out["pass"] is True,out
    assert out["target_count"]==3
    assert out["remaining_prebrain_cut_count"]==4
    assert out["comparator_before_brain_required"] is False
    assert out["scheduling_authority"] is True
    assert out["execution_authority"] is False
    assert out["terminal_credit_delta"]==0
