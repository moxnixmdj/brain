from canonical.runtime.owned_target_outcome_frontier_simulation_v1 import (
    better_case,
    compile_kernel,
    hidden_capability_case,
    owned_frontier_simulates,
    pareto_frontier,
    punctuation_case,
    tradeoff_case,
)


def test_utility_irrelevant_trace_difference_is_ignored():
    out = punctuation_case()
    assert out["raw_trace_differs"] is True
    assert out["outcome_equivalent"] is True
    assert out["simulation_passes"] is True


def test_incomparable_tradeoffs_must_both_be_covered():
    assert tradeoff_case()["simulation_passes"] is False


def test_unnamed_capability_frontier_expansion_is_detected():
    assert hidden_capability_case()["simulation_passes"] is False


def test_strictly_better_owned_outcome_passes():
    assert better_case()["simulation_passes"] is True


def test_dominated_opus_points_need_not_be_matched_separately():
    opus = ((1.0, 1.0), (2.0, 2.0))
    brain = ((2.0, 2.0),)
    assert pareto_frontier(opus) == ((2.0, 2.0),)
    assert owned_frontier_simulates(opus, brain) is True


def test_kernel_has_zero_terminal_credit():
    out = compile_kernel()
    assert out["status"] == "PASS__FINITE_FRONTIER_SIMULATION_KERNEL"
    assert out["terminal_credit"] is False
