from canonical.runtime.current_terminal_pointer_v3_truth_repair_verifier_v1 import verify

def test_current_terminal_pointer_excludes_revoked_p3_whole_cell():
    out=verify()
    assert out["pass"] is True,out
    assert out["sound_D_B_record_count"]==14
    assert out["revoked_p3_whole_cell_excluded"] is True
    assert out["U_empty_proved"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"]==0
