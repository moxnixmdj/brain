from canonical.runtime.current_terminal_authority_pointer_v15_candidate_verifier import verify

def test_pointer_v15_candidate():
    x=verify()
    assert x["pass"] is True,x
    assert x["db_records"]==17
    assert x["open_abc"]==13
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0
