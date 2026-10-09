from canonical.runtime.cursorbench_public_score_nonidentifiability_v1 import (
    construct_world_pair,
    verify_current,
)

def observation():
    return {
        "threshold": 57.8,
        "private_tasks": True,
        "public_brain_score": None,
    }

def test_current_exact_sources_produce_narrow_nonidentifiability_only():
    out = verify_current()
    assert out["pass"] is True, out
    assert out["public_data_exact_score_route"] == "PROVED_NONIDENTIFIABLE"
    assert out["stronger_scope_complete_policy_adequacy_route"] == "INTERNAL_UNSOLVED"
    assert out["whole_acceptance_predicate_external"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["terminal_credit_delta"] == 0

def test_two_worlds_have_same_accessible_observation_and_different_actions():
    out = construct_world_pair(
        threshold_percent=57.8,
        accessible_observation=observation(),
    )
    assert out["nonidentifiable"] is True
    assert out["observations_equal"] is True
    assert out["actions_differ"] is True
    assert out["world_pass"]["required_action"] == "ACCEPT"
    assert out["world_fail"]["required_action"] == "REJECT"

def test_public_brain_score_collapses_nonidentifiability():
    out = construct_world_pair(
        threshold_percent=57.8,
        accessible_observation=observation(),
        public_brain_score_percent=60.0,
    )
    assert out["nonidentifiable"] is False
    assert out["reason"] == "BRAIN_SCORE_IS_ALREADY_ACCESSIBLE"
    assert out["required_action"] == "ACCEPT"

def test_public_failing_brain_score_also_collapses_nonidentifiability():
    out = construct_world_pair(
        threshold_percent=57.8,
        accessible_observation=observation(),
        public_brain_score_percent=40.0,
    )
    assert out["nonidentifiable"] is False
    assert out["required_action"] == "REJECT"

def test_zero_threshold_cannot_generate_pass_fail_counterworlds():
    out = construct_world_pair(
        threshold_percent=0.0,
        accessible_observation=observation(),
    )
    assert out["nonidentifiable"] is False
    assert out["reason"] == "THRESHOLD_ZERO_HAS_NO_PASS_FAIL_SEPARATION"

def test_invalid_threshold_rejected():
    try:
        construct_world_pair(
            threshold_percent=101.0,
            accessible_observation=observation(),
        )
    except ValueError as exc:
        assert str(exc) == "THRESHOLD_OUT_OF_RANGE"
    else:
        raise AssertionError("expected ValueError")

def test_empty_accessible_observation_rejected():
    try:
        construct_world_pair(
            threshold_percent=57.8,
            accessible_observation={},
        )
    except ValueError as exc:
        assert str(exc) == "ACCESSIBLE_OBSERVATION_REQUIRED"
    else:
        raise AssertionError("expected ValueError")
