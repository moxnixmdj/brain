from canonical.runtime.terminal_now_v17_live_cut_verifier_v1 import verify

def test_terminal_now_v17_live_cut():
    out = verify()
    assert out["pass"] is True, out
    assert out["known_sound_D_B_region_count"] == 10
    assert out["finance_residual_count"] == 2
    assert out["abc_closed"] is False
    assert out["d_finality_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
