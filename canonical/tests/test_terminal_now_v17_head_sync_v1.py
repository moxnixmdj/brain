from canonical.runtime.terminal_now_v17_head_sync_verifier_v1 import verify

def test_terminal_now_v17_head_sync():
    out=verify()
    assert out["pass"] is True,out
    assert out["db_region_delta"]==1
    assert out["known_sound_D_B_region_count"]==11
    assert out["finance_route_exists"] is True
    assert out["abc_closed"] is False
    assert out["d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0
