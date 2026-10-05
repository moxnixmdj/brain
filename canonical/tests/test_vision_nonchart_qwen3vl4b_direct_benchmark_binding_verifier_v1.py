from canonical.runtime.vision_nonchart_qwen3vl4b_direct_benchmark_binding_verifier_v1 import evaluate


def test_current_binding_passes_without_credit():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["direct_leaf_witness_count"] == 4
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
    assert out["incremental_spend_usd"] == 0
    assert out["new_reality_units_consumed"] == 0
    assert out["fresh_reality_authority"] is False
