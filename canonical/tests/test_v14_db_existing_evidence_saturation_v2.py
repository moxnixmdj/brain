from canonical.runtime.v14_db_existing_evidence_saturation_verifier_v2 import verify

def test_nine_region_saturation():
    x=verify()
    assert x["pass"] is True,x
    assert x["base_region_count"]==7
    assert x["new_region_count"]==9
    assert x["delta_region_count"]==2
    assert x["abc_closed"] is False
    assert x["d_finality_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0
