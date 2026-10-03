from canonical.runtime import tool_discovery_frozen_scope_universal_theorem_v1 as th

def test_theorem():
    out = th.evaluate()
    assert out["source_blob_drift"] == []
    assert all(out["semantic_preconditions"].values())
    assert all(out["policy_shape_preconditions"].values())
    assert out["minimum_missing_scope_semantics_fact_discharged_for_frozen_protocol"] is True
    assert out["finite_180_case_transport_used"] is False
    assert out["open_domain_identity_exhaustion_claimed"] is False
    assert out["dynamic_v3_promoted"] is False
