from canonical.runtime.current_terminal_authority_v5_verifier import verify

def test_counts_preserved():
    x=verify(); assert x["pass"],x
    assert x["open_truth_obligations"]==29
    assert x["accepted_families"]==5
    assert x["open_families"]==14

def test_a_blackbox_not_global_finality():
    assert verify()["A_blackbox_global_finality"] is False

def test_c_sequence_explosion_removed_not_c_closed():
    x=verify()
    assert x["C_arbitrary_sequence_enumeration_required"] is False
    assert x["terminal"] is False

def test_d_compiler_integrated_not_d_closed():
    x=verify()
    assert x["D_effect_footprint_compiler_integrated"] is True
    assert x["terminal"] is False

def test_zero_credit():
    assert verify()["terminal_credit_delta"]==0
