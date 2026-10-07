from canonical.runtime.v16_db_existing_evidence_saturation_verifier_v4 import verify

def test_v16_twelve_region_saturation():
    out = verify()
    assert out["pass"] is True, out
    assert out["base_region_count"] == 10
    assert out["new_region_count"] == 12
    assert out["delta_region_count"] == 2
    assert out["delta_region_ids"] == [
        "PROFESSIONAL_ARTIFACT_P2_INFO_SAFE_V2_ALL_GENERATED_CASES",
        "PROFESSIONAL_ARTIFACT_T1_FROZEN_30_ZERO_UNSUPPORTED_MATERIAL_CONTENT",
    ]
    assert out["abc_closed"] is False
    assert out["d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
