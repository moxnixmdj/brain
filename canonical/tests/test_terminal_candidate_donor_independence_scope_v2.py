from canonical.runtime import terminal_candidate_donor_independence_audit_v1 as audit

def test_static_audit_never_grants_donor_independence_authority(tmp_path):
    out=audit.evaluate(tmp_path)
    assert out["donor_independence_authority"] is False
    assert out["runtime_cognition_provenance_authority"] is False
    assert out["full_runtime_dependency_inventory_complete"] is False
    assert out["external_contribution_census_complete"] is False
    assert out["model_dependency_count"] is None
    assert out["external_model_runtime_dependency_count"] is None
    assert out["terminal_credit_delta"] == 0
