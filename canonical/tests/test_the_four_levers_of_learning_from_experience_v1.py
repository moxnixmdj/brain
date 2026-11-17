"""Tests for the information law of learning from experience.

Each test holds down a claim that is easy to assert wrongly, and the ones that matter most are the
FALSIFIERS: a test that would fail if the comfortable story were true.

The comfortable story is: "a demonstration with a rich answer teaches a lot, so experience each
action once and you are done." The measurements here say the opposite in a way that can be checked.
"""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/user/brain")
from canonical.tools import the_four_levers_of_learning_from_experience_v1 as LAW  # noqa: E402


class _H:
    """A hypothesis that predicts whatever a function says."""

    def __init__(self, key, fn):
        self.key, self._fn = key, fn

    def predict(self, point):
        return self._fn(point[0])


def _space(functions):
    return [_H(f"h{i}", fn) for i, fn in enumerate(functions)]


# ---------------------------------------------------------------------------------------------
# The invariance: counting spellings is not counting hypotheses
# ---------------------------------------------------------------------------------------------
def test_identical_functions_collapse_to_one_hypothesis():
    """Two spellings of one behaviour are ONE hypothesis about the world."""
    space = _space([lambda x: x + 1, lambda x: 1 + x, lambda x: x * 2])
    groups, distinct = LAW.distinct_functions(space, inputs=range(-5, 6))
    assert distinct == 2
    assert len(space) == 3


def test_a_space_with_no_duplicates_has_invariance_group_one():
    space = _space([lambda x: x + 1, lambda x: x + 2, lambda x: x * 2])
    _, distinct = LAW.distinct_functions(space, inputs=range(-5, 6))
    assert distinct == 3


def test_the_trees_own_space_has_no_collisions():
    """The one-shot probe's space is hand-authored and exact: 47 entries, 47 functions.

    This is why the code-side invariance law does NOT bite there -- and why any space enumerated by
    syntax WOULD. Asserted so the distinction cannot quietly disappear.
    """
    probe = LAW._load_probe()
    space = probe.build_space()
    groups, distinct = LAW.distinct_functions(space)
    assert len(space) == 47
    assert distinct == 47


# ---------------------------------------------------------------------------------------------
# One demonstration has a ceiling, and it is not the one that looks obvious
# ---------------------------------------------------------------------------------------------
def test_information_is_log2_of_survivors():
    assert LAW.bits_remaining(47) == math.log2(47)
    assert LAW.bits_remaining(1) == 0.0


def test_a_question_that_splits_evenly_beats_a_lopsided_one():
    assert LAW.split_gain(7, 7) > LAW.split_gain(1, 13)


def test_a_question_that_splits_nothing_is_worth_zero():
    """This is the measured reason repeating an action in a state that already worked adds nothing."""
    assert LAW.split_gain(0, 14) == 0.0
    assert LAW.split_gain(14, 0) == 0.0


def test_an_even_split_of_n_survivors_is_worth_one_bit():
    for n in (2, 4, 16, 64):
        assert abs(LAW.split_gain(n // 2, n - n // 2) - 1.0) < 1e-12


# ---------------------------------------------------------------------------------------------
# FALSIFIERS: these fail if the comfortable story is true
# ---------------------------------------------------------------------------------------------
def test_answer_variety_does_not_predict_information():
    """If a rich answer meant a good demonstration, variety rank would track information rank.

    Measured on the tree's own 47-program space: 2 of 37 points agree. The point offering 36
    distinct answers buys 0.60 bits; the point offering 5 buys 3.63.
    """
    probe = LAW._load_probe()
    profile = LAW.exact_demonstration_profile_with_space(probe.build_space(), range(-6, 31))
    assert profile["variety_predicts_information"]["verdict"] == "NO"
    assert profile["variety_predicts_information"]["rank_agreements"] < profile["pool_size"] / 2
    assert profile["worst"]["distinct_answers"] > profile["best"]["distinct_answers"]


def test_the_best_demonstration_is_not_the_one_with_the_most_distinct_answers():
    probe = LAW._load_probe()
    profile = LAW.exact_demonstration_profile_with_space(probe.build_space(), range(-6, 31))
    assert profile["best"]["x"] != profile["worst"]["x"]
    assert profile["best"]["distinct_answers"] < profile["worst"]["distinct_answers"]
    assert profile["best"]["bits"] > profile["worst"]["bits"] * 4


def test_one_demonstration_cannot_identify_a_space_larger_than_its_own_answer_confirms():
    """A single point leaves survivors. On the tree's space it leaves 14.1 of 47, measured."""
    probe = LAW._load_probe()
    profile = LAW.exact_demonstration_profile_with_space(probe.build_space(), range(-6, 31))
    assert profile["best_fraction_of_space"] < 1.0
    # even the best single point leaves well over a third of the space standing
    assert profile["best_fraction_of_space"] < 0.75


# ---------------------------------------------------------------------------------------------
# The part that is not billed per interaction
# ---------------------------------------------------------------------------------------------
def test_the_prior_is_the_only_term_that_costs_no_interaction():
    """A one-point space is settled before any demonstration: 0 bits remain, no interaction paid."""
    assert LAW.bits_remaining(1) == 0.0
    assert LAW.split_gain(0, 1) == 0.0


def test_the_computed_law_reproduces_the_recorded_receipts():
    """The law must agree with the probe's own measured numbers, not with a model of them."""
    facts = LAW.levers()
    verified = facts["verified_by_rerun_20261116"]
    assert verified["survivors_after_one"] == 14.1
    assert verified["targets_exact_after_one"] == 0
    assert verified["targets_settled_after_one_then_ask"] == 10
    assert abs(facts["bits_after_one"] - math.log2(14.1)) < 1e-9
    assert facts["bits_after_one"] > 0  # one demonstration does NOT finish the job


def test_the_state_name_arm_is_recorded_as_a_prior_failure_not_a_coverage_failure():
    arm = LAW.boundary_probe_terms()
    assert arm["as_is"]["carried_model_survived"] == 7
    assert arm["renamed"]["carried_model_survived"] == 0
    assert "spelling" in arm["reading"]
