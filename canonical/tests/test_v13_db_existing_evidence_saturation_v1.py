from canonical.runtime.v13_db_existing_evidence_saturation_verifier_v1 import verify

def test_current_saturation_manifest():
    x=verify()
    assert x["pass"] is True,x
    assert x["known_region_count"]==7
    assert x["abc_closed"] is False
    assert x["terminal_credit_delta"]==0
