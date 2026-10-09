from canonical.runtime.r2_current_pointer_bounded_concept_registry_verify_v1 import evaluate

def test_current_r2_pointer_binds_bounded_concept_registry_without_false_closure():
    out=evaluate()
    assert out["pass"] is True,out
    assert out["bounded_registry_coverage_live"] is True
    assert out["finance_residual_still_open"] is True
    assert out["global_open_world_closure_claimed"] is False
    assert out["terminal_credit_delta"]==0
