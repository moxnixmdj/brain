from canonical.runtime.astra_scarce_semantic_packet_v4_verifier import evaluate


def test_packet_v4_exact_compression_bindings_pass():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["family_count"] == 14
    assert out["atomic_contract_count_removed_from_query_budget"] == 24
    assert out["fixed_target_tuple_count_removed_from_query_budget"] == 14
    assert out["public_evaluator_family_count_removed_from_query_budget"] == 10
    assert out["astra_access_consumed"] == 0
    assert out["terminal_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
