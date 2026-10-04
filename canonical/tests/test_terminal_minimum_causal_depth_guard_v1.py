from canonical.runtime.terminal_minimum_causal_depth_guard_v1 import verify

def test_guard_passes():
    out = verify()
    assert out["status"] == "PASS"
    assert out["terminal_counts_preserved"] is True
    assert out["relative_elo_transport_fail_closed"] is True
    assert out["arena_account_inference_fail_closed"] is True
    assert out["isolation_authority_fail_closed"] is True
    assert out["acceptance_credit_delta"] == 0
