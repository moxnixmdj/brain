from canonical.runtime.v14_db_existing_evidence_saturation_verifier_v2 import verify

def test_current_v14_saturation():
    x=verify()
    assert x["pass"] is True,x
    assert x["known_region_count"]==9
    assert x["abc_closed"] is False
    assert x["terminal_credit_delta"]==0
