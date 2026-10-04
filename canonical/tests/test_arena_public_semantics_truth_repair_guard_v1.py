from canonical.runtime.arena_public_semantics_truth_repair_guard_v1 import verify

def test_arena_truth_repair():
    out=verify()
    assert out["status"]=="PASS"
    assert out["unauthenticated_public_overclaim_repaired"] is True
    assert out["terminal_counts_preserved"] is True
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"]==0
