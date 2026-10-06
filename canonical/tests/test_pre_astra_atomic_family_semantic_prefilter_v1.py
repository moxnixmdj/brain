from canonical.runtime.pre_astra_atomic_family_semantic_prefilter_v1 import evaluate


def test_prefilter_current_exact_authorities_pass():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["unresolved_atomic_count"] == 24
    assert out["family_count"] == 14
    assert out["fixed_bar_target_tuple_count"] == 14
    assert out["family_E_or_M_credit"] == 0
    assert out["astra_access_consumed"] == 0
    assert out["terminal_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
