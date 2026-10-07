from canonical.runtime.terminal_scheduling_current_authority_v2 import verify

def test_v14_execution_authority():
    x=verify()
    assert x["pass"],x
    assert x["authorized_action_count"]==4
    assert x["top_level_predicates"]==2
    assert x["cached_D_B_regions"]==9
    assert x["fresh_reality_authority"] is False
    assert x["promotion_authority"] is False

def test_finality_guards():
    x=verify()
    assert x["abc_closed"] is False
    assert x["d_finality_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0
