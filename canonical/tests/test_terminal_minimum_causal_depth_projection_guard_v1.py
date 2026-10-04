from canonical.runtime.terminal_minimum_causal_depth_projection_guard_v1 import verify

def test_projection_guard():
    out=verify()
    assert out["status"]=="PASS"
    assert out["root_pointer_bound"] is True
    assert out["current_authority_pointer_bound"] is True
    assert out["terminal_counts_preserved"] is True
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"]==0
