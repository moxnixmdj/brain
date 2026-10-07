from canonical.runtime.unknown_domain_two_behavior_shared_semantic_frontier_v1 import project

EXPECTED = {
    "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
    "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
}


def test_exact_two_behavior_residual_projects_to_one_shared_frontier():
    out = project()
    assert out["pass"] is True, out
    assert set(out["residual_behaviors"]) == EXPECTED
    assert out["residual_behavior_count"] == 2
    assert out["shared_generic_semantic_frontier_count"] == 1
    assert out["duplicate_generic_mechanism_hunts_deleted"] == 1
    assert out["whole_behavior_acceptance_obligations_remaining"] == 2
    assert out["terminal_closed"] is False
    assert out["terminal_credit_delta"] == 0


def test_fail_closed_boundaries_remain_explicit():
    out = project()
    assert out["specification_acceptance_explicitly_not_owned"] is True
    assert out["research_control_current_terminal_result_absent"] is True
