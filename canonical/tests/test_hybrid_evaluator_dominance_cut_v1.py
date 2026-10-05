from fractions import Fraction

from canonical.runtime.hybrid_evaluator_dominance_cut_v1 import (
    expected_value,
    explicit_evaluator_global_argmax_dominates,
    hidden_evaluator_policy_kernel_equivalence,
    hidden_utility_value,
    rollout_distribution,
)


def test_explicit_global_argmax_dominates_arbitrary_target_distribution():
    reward = {"a": 0, "b": 3, "c": 2}
    target = {"a": "1/5", "b": "1/5", "c": "3/5"}
    assert explicit_evaluator_global_argmax_dominates(target, reward, "b")
    assert expected_value(target, reward) == Fraction(9, 5)


def test_non_argmax_is_rejected():
    reward = {"a": 0, "b": 3, "c": 2}
    target = {"b": 1}
    assert not explicit_evaluator_global_argmax_dominates(target, reward, "c")


def test_equal_policy_kernel_gives_equal_hidden_utility_for_stochastic_environment():
    initial = {"s0": 1}
    policy = {
        "s0": {"left": "1/3", "right": "2/3"},
        "s1": {"stay": 1},
        "s2": {"stay": 1},
    }
    transition = {
        ("s0", "left"): {"s1": 1},
        ("s0", "right"): {"s1": "1/4", "s2": "3/4"},
        ("s1", "stay"): {"s1": 1},
        ("s2", "stay"): {"s2": 1},
    }
    assert hidden_evaluator_policy_kernel_equivalence(
        initial, policy, policy, transition, horizon=2
    )
    target_rollout = rollout_distribution(initial, policy, transition, 2)
    brain_rollout = rollout_distribution(initial, policy, transition, 2)
    utility = {trajectory: i for i, trajectory in enumerate(sorted(target_rollout, key=repr))}
    assert hidden_utility_value(target_rollout, utility) == hidden_utility_value(
        brain_rollout, utility
    )


def test_changed_policy_is_detected_even_when_environment_is_same():
    initial = {"s0": 1}
    target_policy = {"s0": {"left": 1}, "s1": {"stay": 1}, "s2": {"stay": 1}}
    brain_policy = {"s0": {"right": 1}, "s1": {"stay": 1}, "s2": {"stay": 1}}
    transition = {
        ("s0", "left"): {"s1": 1},
        ("s0", "right"): {"s2": 1},
        ("s1", "stay"): {"s1": 1},
        ("s2", "stay"): {"s2": 1},
    }
    assert not hidden_evaluator_policy_kernel_equivalence(
        initial, target_policy, brain_policy, transition, horizon=1
    )


def test_zero_horizon_needs_no_policy_and_preserves_initial_distribution():
    initial = {"x": "2/3", "y": "1/3"}
    out = rollout_distribution(initial, {}, {}, 0)
    assert out == {(("x",), ()): Fraction(2, 3), (("y",), ()): Fraction(1, 3)}
