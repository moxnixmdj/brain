from canonical.runtime.dual_judgment_general_substrate_role_v1 import evaluate

def test_role_qualification_passes_current_bound_bytes():
    out=evaluate()
    assert out["pass"] is True, out
    assert out["general_substrate_test_pass"] is True
    assert out["source_gate_v2_pass"] is True
    assert out["direct_oracle_execution_authority"] is True
    assert len(out["requirements_eligible_to_close"])==2
    assert out["new_reality_units_consumed"]==0
    assert out["acceptance_predicate_delta"]==0
    assert out["family_acceptance_delta"]==0
    assert out["ownership_delta"]==0
