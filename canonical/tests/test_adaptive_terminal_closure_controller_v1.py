from canonical.runtime.adaptive_terminal_closure_controller_v1 import (
    Action,
    Policy,
    beta_posterior_mean,
    capture_recapture_unseen,
    frontier,
    ownership_ready,
    rank,
    should_stop_finite_bar,
)


def test_fresh_reality_is_fail_closed_by_default():
    a = Action(
        action_id="REALITY",
        action_class="MEASURE",
        expected_seconds=1,
        p_discharge=1,
        predicate_delta=1,
        fresh_reality_units=1,
    )
    row = rank([a])[0]
    assert row["admissible"] is False
    assert row["inadmissible_reason"] == "FRESH_REALITY_AUTHORITY_FALSE"
    assert row["acceptance_credit"] == 0


def test_tb4_execution_is_blocked_while_180_lt_220():
    a = Action(
        action_id="TB4_EXECUTE",
        action_class="BENCHMARK_EXECUTE",
        expected_seconds=1,
        p_discharge=1,
        predicate_delta=1,
        tb4_execution=True,
    )
    row = rank([a], Policy(tb4_attainable_upper_bound=180, tb4_required_successes=220))[0]
    assert row["admissible"] is False
    assert "UNATTAINABLE" in row["inadmissible_reason"]


def test_consumed_tool_discovery_epoch_cannot_replay():
    a = Action(
        action_id="REPLAY",
        action_class="RETRIEVE",
        expected_seconds=1,
        p_discharge=0.9,
        information_gain=1,
        tool_discovery_retrieval=True,
        source_epoch_consumed=True,
    )
    row = rank([a])[0]
    assert row["admissible"] is False
    assert row["inadmissible_reason"] == "CONSUMED_TOOL_DISCOVERY_SOURCE_EPOCH_REPLAY_FORBIDDEN"


def test_family_and_ownership_terminal_value_can_outrank_many_predicates():
    shallow = Action(
        action_id="MANY_PREDICATES",
        action_class="PROOF",
        expected_seconds=10,
        p_discharge=0.8,
        predicate_delta=5,
    )
    terminal = Action(
        action_id="FAMILY_OWNERSHIP",
        action_class="PROOF",
        expected_seconds=10,
        p_discharge=0.8,
        predicate_delta=1,
        family_delta=1,
        ownership_delta=1,
    )
    rows = rank([shallow, terminal])
    assert rows[0]["action_id"] == "FAMILY_OWNERSHIP"


def test_parallel_frontier_does_not_serialize_independent_work():
    actions = [
        Action("A", "PROOF", 1, 0.5, predicate_delta=1),
        Action("B", "PROOF", 2, 0.5, predicate_delta=1),
    ]
    f = frontier(actions)
    assert set(f["parallel_launch"]) == {"A", "B"}
    assert f["fixed_point_after_every_verified_delta"] is True
    assert f["promotion_authority"] is False


def test_beta_posterior_is_scheduling_only_numeric_helper():
    assert beta_posterior_mean(9, 1) == 10 / 12


def test_capture_recapture_never_claims_completeness():
    x = capture_recapture_unseen(10, 5)
    assert x["estimated_unseen"] == 10.0
    assert x["completeness_proof"] is False
    y = capture_recapture_unseen(10, 0)
    assert y["estimated_unseen"] is None
    assert y["completeness_proof"] is False


def test_exact_finite_early_stop_both_directions():
    assert should_stop_finite_bar(8, 8, 10, 8) == "STOP_PASS"
    assert should_stop_finite_bar(3, 8, 10, 6) == "STOP_FAIL"
    assert should_stop_finite_bar(4, 6, 10, 6) == "CONTINUE"


def test_ownership_requires_all_four_conditions():
    assert ownership_ready(
        acceptance_pass=True,
        internalized=True,
        donor_independent=True,
        scope_complete=True,
    )
    assert not ownership_ready(
        acceptance_pass=True,
        internalized=True,
        donor_independent=False,
        scope_complete=True,
    )
