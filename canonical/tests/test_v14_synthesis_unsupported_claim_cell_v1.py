from canonical.runtime.v14_synthesis_unsupported_claim_cell_verifier_v1 import verify

def test_current_cell_verifies():
    x=verify()
    assert x["pass"] is True,x
    assert x["cell_closed"] is True
    assert x["synthesis_family_closed"] is False
    assert x["abc_closed"] is False
    assert x["terminal_credit_delta"]==0
