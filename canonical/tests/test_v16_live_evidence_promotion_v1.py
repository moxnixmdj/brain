from canonical.runtime.v16_live_evidence_promotion_verifier_v1 import verify

def test_v16_source_bound_live_authority():
    out = verify()
    assert out["pass"], out
    assert out["known_sound_D_B_regions_lower_bound"] == 11
    assert out["top_level_terminal_predicates"] == 2
    assert out["finance_residual_count"] == 2
    assert out["general_router_intelligence_global_blocker"] is False
    assert out["fresh_reality_authority"] is False
    assert out["promotion_authority"] is False
    assert out["abc_closed"] is False
    assert out["d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
