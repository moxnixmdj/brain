from canonical.runtime.v17_db_existing_evidence_saturation_verifier_v1 import verify


def test_v17_db_existing_evidence_saturation():
    out = verify()
    assert out["pass"] is True, out
    assert out["base_region_count"] == 10
    assert out["new_named_context_region_count"] == 1
    assert out["resulting_named_context_region_count"] == 11
    assert out["redundant_same_context_certificate_count"] == 1
    assert out["coverage_measure_claimed"] is False
    assert out["abc_closed"] is False
    assert out["d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
