from canonical.runtime.target_role_escape_frontier_v1 import project

def test_exact_current_role_escape_frontier():
    out=project()
    assert out["pass"] is True,out
    assert out["accepted_family_count"]==5
    assert out["fully_accepted_role_count"]==4
    assert out["structural_escape_role_count"]==6
    assert set(out["fully_accepted_roles"])=={
        "B3_TEMPORAL_STATE_MEMORY_AND_CONTINUITY",
        "B5_TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        "B6_DELEGATION_AND_COORDINATION",
        "B8_SELF_VERIFICATION_FAILURE_LOCALIZATION_AND_RECOVERY",
    }
    assert "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING" in out["structural_escape_roles"]
    assert out["terminal_credit_delta"]==0
