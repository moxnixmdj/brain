from canonical.runtime.root2_v13_decision_only_control_plane_guard_v1 import verify

def test_control_plane():
    out=verify()
    assert out["status"]=="PASS"
    assert out["counts_preserved_5_12_26"] is True
    assert out["root2_v13_projection_exact"] is True
    assert out["decision_only_projection_exact"] is True
    assert out["stale_v10_instruction_deleted"] is True
    assert out["v14_through_v18_not_promoted"] is True
    assert out["arena_truth_repair_preserved"] is True
    assert out["execution_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"]==0
