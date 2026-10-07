from canonical.runtime.current_zero_reality_minimum_cut_active_pointer_v3 import verify

def test_v14_native_scheduler_pointer():
    x=verify()
    assert x["pass"],x
    assert x["top_level_predicates"]==2
    assert x["cached_D_B_regions"]==9
    assert x["active_program_count"]==4
    assert x["target_scope_closed"] is True

def test_finality_guards():
    x=verify()
    assert x["abc_closed"] is False
    assert x["d_finality_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0
