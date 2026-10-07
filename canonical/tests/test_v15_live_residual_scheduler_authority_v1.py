from canonical.runtime.v15_live_residual_scheduler_authority_verifier_v1 import verify

def test_v15_scheduler_state():
    x=verify()
    assert x["pass"],x
    assert x["top_level_predicates"]==2
    assert x["cached_D_B_regions"]==9
    assert x["active_program_count"]==4
    assert x["authorized_action_count"]==4
    assert x["global_M0_required"] is False

def test_authority_boundaries():
    x=verify()
    assert x["fresh_reality_authority"] is False
    assert x["promotion_authority"] is False
    assert x["abc_closed"] is False
    assert x["d_finality_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0
