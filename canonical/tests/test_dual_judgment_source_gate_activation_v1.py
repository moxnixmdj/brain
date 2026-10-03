from canonical.runtime.dual_judgment_source_gate_activation_v1 import evaluate

def test_exact_two_requirement_discharge_only():
    out=evaluate()
    assert out["pass"] is True, out
    assert len(out["discharged_requirements"])==2
    assert out["remaining_acceptance_predicate_delta"]==0
    assert out["new_reality_units_consumed"]==0
    assert out["global_fresh_reality_authority"] is False
