from canonical.runtime.trajectory_residual_leaf_transport_v1 import evaluate

def test_exact_trajectory_leaf_transport():
    out = evaluate()
    assert out["pass"], out
    assert out["discharged_leaf_incidence_count"] == 3
    assert set(out["target_families"]) == {
        "COMPLEX_MULTI_TOOL_AGENCY",
        "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
        "MULTI_CAPABILITY_COMPOSITION",
    }
    assert all(v == 1 for v in out["target_leaf_incidences"].values())
    assert out["new_reality_units_consumed"] == 0
    assert out["acceptance_credit_delta"] == 0
    assert out["atomic_predicate_credit_delta"] == 0
    assert out["fresh_reality_authority"] is False
