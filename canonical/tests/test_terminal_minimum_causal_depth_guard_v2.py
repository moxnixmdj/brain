from canonical.runtime.terminal_minimum_causal_depth_guard_v2 import verify

def test_guard_passes():
    out = verify()
    assert out["status"] == "PASS"
    assert out["v1_verified_subject_immutability_preserved"] is True
    assert out["terminal_counts_preserved"] is True
    assert out["relative_elo_transport_fail_closed"] is True
    assert out["blind_threshold_minimum_information_bound"] is True
    assert out["arena_account_inference_fail_closed"] is True
    assert out["isolation_authority_fail_closed"] is True
    assert out["acceptance_credit_delta"] == 0
