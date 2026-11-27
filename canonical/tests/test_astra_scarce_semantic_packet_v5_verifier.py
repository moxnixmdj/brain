from canonical.runtime.astra_scarce_semantic_packet_v5_verifier import evaluate


def test_packet_v5_behavior_context_semantic_unit_passes():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["active_behavior_contract_count"] == 12
    assert out["family_label_semantic_authority"] is False
    assert out["astra_access_consumed"] == 0
    assert out["terminal_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
