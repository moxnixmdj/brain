from canonical.runtime.finance_semantic_zero_reality_fixed_point_v1 import evaluate

def test_finance_semantic_zero_reality_fixed_point_replays_current_bound_sources():
    out=evaluate()
    assert out["pass"] is True,out
    assert out["two_world_countermodel_preserved_by_policy_quotient"] is True
    assert out["zero_reality_internal_recomputation_exhausted"] is True
    assert out["finance_semantic_adequacy_tail_state"]=="EXTERNAL_REQUIRED_SLEEP"
    assert out["root2_globally_closed"] is False
    assert out["terminal_credit_delta"]==0
