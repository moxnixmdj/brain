from canonical.runtime.outcome_frontier_stochastic_countermodel_v1 import (
    compile_countermodel,
    pareto_frontier_1d,
    stochastic_reliability_countermodel,
    support_frontier_simulates,
)


def test_same_support_has_same_point_frontier():
    assert pareto_frontier_1d((0.0, 1.0)) == (1.0,)
    assert support_frontier_simulates((0.0, 1.0), (0.0, 1.0)) is True


def test_same_support_can_hide_large_reliability_gap():
    out = stochastic_reliability_countermodel()
    assert out["same_outcome_support"] is True
    assert out["point_frontier_simulation_passes"] is True
    assert out["opus_success_probability"] == 0.99
    assert out["brain_success_probability"] == 0.51
    assert out["terminal_reliability_noninferiority_passes"] is False
    assert out["countermodel_valid"] is True


def test_compiler_classifies_truth_repair_only():
    out = compile_countermodel()
    assert out["status"] == "PASS__POINT_SUPPORT_FRONTIER_INSUFFICIENT_FOR_STOCHASTIC_RELIABILITY"
    assert out["classification"] == "TRUTH_REPAIR"
    assert out["terminal_credit"] is False
