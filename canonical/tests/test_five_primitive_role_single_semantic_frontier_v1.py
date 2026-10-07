from canonical.runtime.five_primitive_role_single_semantic_frontier_v1 import project

EXPECTED={
    "B0_INPUT_PERCEPTION_AND_GROUNDING",
    "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
    "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
    "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
    "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION",
}

def test_exact_five_role_projection():
    out=project()
    assert out["pass"] is True,out
    assert out["coarse_escape_role_count"]==6
    assert out["b9_is_conditionally_derivative"] is True
    assert out["conditional_on_C"] is True
    assert out["primitive_escape_role_count"]==5
    assert set(out["primitive_escape_roles"])==EXPECTED
    assert out["independent_new_implementation_searches_required"]==0
    assert out["context_specific_semantic_certificate_work_remains"] is True
    assert out["distributional_dominance_remains"] is True
    assert out["resource_and_ownership_remain"] is True
    assert out["terminal_credit_delta"]==0

def test_all_five_have_explicit_semantic_responsibility():
    out=project()
    assert set(out["role_to_semantic_responsibility"])==EXPECTED
    assert all(out["role_to_semantic_responsibility"].values())
