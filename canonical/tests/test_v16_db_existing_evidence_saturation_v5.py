from canonical.runtime.v16_db_existing_evidence_saturation_verifier_v5 import verify

def test_unified_v16_db_saturation_is_exact_and_zero_credit():
    out = verify()
    assert out["pass"] is True, out
    assert out["base_certificate_count"] == 10
    assert out["added_certificate_count"] == 3
    assert out["known_sound_D_B_region_certificate_count"] == 13
    assert out["fresh_target_reality_consumed"] == 0
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
