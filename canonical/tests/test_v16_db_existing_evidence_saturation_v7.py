from canonical.runtime.v16_db_existing_evidence_saturation_verifier_v7 import verify

def test_live_fifteen_region_union_is_exact_and_fail_closed():
    out=verify()
    assert out["pass"] is True, out
    assert out["live_base_count"]==13
    assert out["delta_count"]==2
    assert out["known_sound_region_certificate_count"]==15
    assert set(out["added_ids"])=={
        "SYNTHESIS_TARGET_SCOPE_REQUIRED_CLAIM_COVERAGE_TOP_LAW",
        "P3_T1_T3_FROZEN_60_WHOLE_DIRECT_SYNTHESIS_CONJUNCTION",
    }

def test_no_global_overclaim_from_cache_cardinality():
    out=verify()
    assert out["regions_may_overlap"] is True
    assert out["coverage_measure_claimed"] is False
    assert out["abc_closed"] is False
    assert out["d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0
