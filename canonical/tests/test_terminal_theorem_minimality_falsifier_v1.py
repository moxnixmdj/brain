from canonical.runtime.terminal_theorem_minimality_falsifier_v1 import (
    compile_falsification,
    overreach_countermodel,
    underbinding_countermodel,
    utility_semantics_countermodel,
)


def test_full_trace_superset_dominance_is_not_necessary_for_target_relative_goal():
    out = overreach_countermodel()
    assert out["terminal_goal_true"] is True
    assert out["literal_full_superset_dominance"] is False
    assert out["falsifies_necessity_of_full_superset_dominance"] is True


def test_declared_target_without_completeness_binding_is_not_sufficient():
    out = underbinding_countermodel()
    assert out["declared_certificate_w1"] is True
    assert out["declared_certificate_w2"] is True
    assert out["terminal_w1"] is True
    assert out["terminal_w2"] is False
    assert out["proves_target_completeness_binding_is_necessary"] is True


def test_compiler_classifies_result_as_truth_repair_not_terminal_credit():
    out = compile_falsification()
    assert out["status"].startswith("PASS__")
    assert out["literal_full_superset_reading_falsified"] is True
    assert out["target_completeness_binding_required"] is True
    assert out["utility_relevance_and_outcome_ordering_required"] is True
    assert out["terminal_credit"] is False
    assert out["classification"] == "TRUTH_REPAIR"


def test_observable_difference_alone_is_not_a_useful_capability():
    out = utility_semantics_countermodel()
    assert out["observable_difference"] is True
    assert out["terminal_utility_equal"] is True
    assert out["observable_difference_not_sufficient_for_useful_capability"] is True
