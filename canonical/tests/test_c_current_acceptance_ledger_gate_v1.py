from canonical.runtime.c_current_acceptance_ledger_gate_v1 import verify_current

def test_current_acceptance_ledger_has_no_transport_inheritance():
    out=verify_current()
    assert out["pass"] is True,out
    assert out["proved_count"]==14
    assert out["direct_count"]==14
    assert out["transported_count"]==0
    assert out["future_unknown_or_transport_proof_kind_fails_closed"] is True
    assert out["terminal_credit_delta"]==0
