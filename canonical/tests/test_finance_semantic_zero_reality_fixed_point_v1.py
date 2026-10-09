from canonical.runtime.finance_semantic_zero_reality_fixed_point_v1 import evaluate

def test_finance_semantic_zero_reality_fixed_point_replays_current_bound_sources():
    out=evaluate()
    assert out["pass"] is True,out
    assert out["two_world_countermodel_preserved_by_policy_quotient"] is True
    assert out["zero_reality_internal_recomputation_exhausted"] is True
    assert out["finance_semantic_adequacy_tail_state"]=="INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT"
    assert out["pending_acquisition_or_experiment_required"] is True
    assert out["information_theoretic_externality_proved"] is False
    assert out["irreducible_external_information_proved"] is False
    assert out["legacy_scheduler_state"]=="EXTERNAL_REQUIRED_SLEEP"
    assert out["legacy_scheduler_state_authoritative"] is False
    assert out["root2_globally_closed"] is False
    assert out["terminal_credit_delta"]==0
