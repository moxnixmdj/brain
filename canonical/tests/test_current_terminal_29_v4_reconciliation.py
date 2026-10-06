from canonical.runtime.current_terminal_29_v4_reconciliation_verifier import verify


def test_current_terminal_29_v4_reconciliation():
    out = verify()
    assert out["status"] == "PASS__CURRENT_TERMINAL_CONTROL_REBOUND_TO_VERIFIED_29_V4_BASIS"
    assert out["load_bearing_atomic_open"] == 21
    assert out["meta_open"] == 8
    assert out["open_truth_obligations"] == 29
    assert out["route_counts"] == {"J": 0, "G": 0, "T": 0, "D": 15, "U": 14}
    assert out["root2_touching"] == 17
    assert out["root3_touching"] == 7
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
