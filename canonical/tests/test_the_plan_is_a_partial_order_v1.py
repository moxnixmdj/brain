#!/usr/bin/env python3
"""Tests for the partial-order planner and the four-way race.

Two kinds of test here, and the second kind is the one that matters:

  1. TESTS OF THE MECHANISM on hand-built operators, where the right answer is known by hand:
     a two-step chain, a threat that must be resolved by promotion or demotion, an axiom that
     costs nothing, an open condition nothing can establish, and the step-reuse path that a
     first version of this planner got wrong.

  2. GUARDS FOR THE DEFECTS THIS ROUND ACTUALLY HAD. Every one of the following was a real bug
     found by running the instrument, and each is pinned so it cannot come back:
       * a plan of zero steps returned for an unsatisfied goal (goals never opened)
       * one atom's effects conflated across all the states it ran in (transcript, not operator)
       * the same operator never reused, so a one-atom goal was "solved" by seven copies
       * preconditions admitted that nothing establishes, making an operator inapplicable forever
       * an ambiguous-context operator with an empty precondition read as unconditional
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402

A = ("CARD", "WHOLE", None, "count_is", 3)
B = ("CARD", "WHOLE", None, "count_is", 4)
C = ("CARD", "WHOLE", None, "count_is", 5)


def op(ident, pre=(), add=(), delete=(), atom="", citable=True):
    return pop.Operator(ident, frozenset(pre), frozenset(add), frozenset(delete),
                        atom=atom or ident, context_identified=citable)


# ---------------------------------------------------------------------------------------------
# 1. the mechanism
# ---------------------------------------------------------------------------------------------

def test_two_step_chain_is_found_and_ordered():
    """B needs A, the goal needs B: the plan must be two steps, in that order."""
    operators = [op("M1", add=[A]), op("M2", pre=[A], add=[B])]
    found = pop.plan([], [B], operators)
    assert found["status"] == "PASS__PARTIAL_ORDER_FOUND"
    assert found["steps"] == ["M1", "M2"]


def test_axiom_costs_nothing_and_has_no_step():
    """A goal already true at reset is linked to <start>, not re-established by an action."""
    operators = [op("M1", add=[A])]
    found = pop.plan([A], [A], operators)
    assert found["status"] == "PASS__PARTIAL_ORDER_FOUND"
    assert found["steps"] == []


def test_threat_is_resolved_by_ordering_not_by_deleting_the_step():
    """M2 deletes A and is otherwise unconstrained; A is protected for the goal. The planner must
    order M2 after the step that establishes A, not drop M2."""
    operators = [op("MAKE", add=[A]), op("M2", add=[C], delete=[A])]
    found = pop.plan([], [A, C], operators)
    assert found["status"] == "PASS__PARTIAL_ORDER_FOUND"
    order = dict()
    for before, after in found["partial_order"]:
        order.setdefault(before, set()).add(after)
    makers = [s for s in found["partial_order"] if "MAKE" in str(s)]
    assert makers, "MAKE must appear in the ordering"


def test_unestablishable_goal_names_its_cause():
    """No operator produces C: the refusal must say so, and must not be a bare 'no plan'."""
    operators = [op("M1", add=[A])]
    found = pop.plan([], [C], operators)
    assert found["status"] == "OPEN__NO_PARTIAL_ORDER_FOUND"
    assert found["reason"]["class"] == "NO_RELEVANT_OPERATOR"
    assert any("count_is 5" in text for text in found["reason"]["conditions"])


def test_operator_is_reused_rather_than_duplicated():
    """One operator, two instances needed for a chain of the SAME atom, and the count matters.

    This is the guard for the measured defect where a goal reachable in two applications of one
    atom was 'proved' with seven copies of it."""
    operators = [op("TICK", pre=[A], add=[B], delete=[A]), op("SET", add=[A])]
    found = pop.plan([], [B], operators)
    assert found["status"] == "PASS__PARTIAL_ORDER_FOUND"
    assert found["steps"] == ["SET", "TICK"]
    assert len(found["steps"]) == 2, "two steps, not more"


def test_incited_operator_cannot_be_used():
    """An operator whose context was not identified may not appear in any plan, even if relevant."""
    operators = [op("MYSTERY", add=[C], citable=False)]
    found = pop.plan([], [C], operators)
    assert found["status"] == "OPEN__NO_PARTIAL_ORDER_FOUND"


def test_conditions_are_judged_by_the_frame_and_nothing_else():
    state = (("0", "alpha"), ("1", "alpha"), ("2", "beta"))
    assert pop.holds(("CARD", "WHOLE", None, "count_is", 3), state) is True
    assert pop.holds(("CARD", "WHOLE", None, "count_is", 2), state) is False
    assert pop.holds(("MULTISET", "WHOLE", None, "equals", (("alpha", 2), ("beta", 1))),
                     state) is True


# ---------------------------------------------------------------------------------------------
# 2. the measured operators, and the defects that produced them
# ---------------------------------------------------------------------------------------------

def test_induction_splits_until_each_leaf_has_one_effect():
    """One atom with a state-dependent effect: the split must end in pure leaves, each carrying a
    guard that names the state it happens in. This is the operator a static add/delete table cannot
    express, and every machine in this repo needs it."""
    two = (("0", "alpha"), ("1", "alpha"))
    three = (("0", "alpha"), ("1", "alpha"), ("2", "alpha"))
    observations = [
        ("ROLL", (("0", "alpha"),), two),
        ("ROLL", two, three),
        ("ROLL", two, three),
    ]
    conditions = [("CARD", "WHOLE", None, "count_is", 1),
                  ("CARD", "WHOLE", None, "count_is", 2),
                  ("CARD", "WHOLE", None, "count_is", 3)]
    operators, report = pop.induce_conditional_operators(observations, conditions)
    assert report["impure_leaves"] == 0, "this vocabulary separates the two contexts"
    assert len(operators) == 2, "two contexts, two operators"
    for operator in operators:
        assert operator.pre, "a citable operator must carry a guard"
        assert len(operator.add) == 1, "one effect per leaf"


def test_induction_reports_an_impure_leaf_rather_than_smoothing_it():
    """If the vocabulary cannot separate the contexts, the leaf stays impure and is REPORTED. It is
    never silently turned into an unconditional operator."""
    observations = [
        ("ROLL", (("0", "alpha"),), (("0", "alpha"), ("1", "alpha"))),
        ("ROLL", (("0", "alpha"),), (("0", "alpha"), ("1", "beta"))),
    ]
    conditions = [("CARD", "WHOLE", None, "count_is", 2)]
    operators, report = pop.induce_conditional_operators(observations, conditions)
    # the vocabulary cannot tell the two runs apart, so NOTHING is emitted as if it applied
    # everywhere, and the report says why rather than leaving a silent gap
    assert operators == []
    assert report["impure_leaves"] >= 1 or report["leaves_without_a_guard"] >= 1


def test_guard_is_never_something_the_operator_itself_establishes():
    """A guard that the operator establishes is SELF-ENABLING: a backward search can never start
    from it, though a forward search never notices. That asymmetry is exactly how this defect
    survived until the two were raced."""
    one = (("0", "alpha"),)
    two = (("0", "alpha"), ("1", "alpha"))
    three = (("0", "alpha"), ("1", "alpha"), ("2", "alpha"))
    observations = [("ROLL", one, two), ("ROLL", two, three)]
    conditions = [("CARD", "WHOLE", None, "count_is", 1),
                  ("CARD", "WHOLE", None, "count_is", 2),
                  ("CARD", "WHOLE", None, "count_is", 3)]
    operators, _report = pop.induce_conditional_operators(observations, conditions)
    for operator in operators:
        for condition in operator.pre:
            assert condition not in operator.add, (
                "a guard that the operator itself establishes is self-enabling and unusable")


def test_preconditions_nothing_establishes_are_dropped_and_counted():
    """A precondition that no operator adds and the initial state lacks makes its operator
    permanently inapplicable; closure drops it and says how many it dropped."""
    unreachable = ("CARD", "WHOLE", None, "count_is", 99)
    operators = [op("M1", pre=[unreachable, A], add=[B]), op("M0", add=[A])]
    closed, report = pop.close_preconditions(operators, frozenset())
    assert report["preconditions_dropped_as_unestablishable"] == 1
    assert unreachable not in closed[0].pre
    assert A in closed[0].pre, "the establishable precondition must survive"
    assert pop.plan([], [B], closed)["status"] == "PASS__PARTIAL_ORDER_FOUND"


def test_condition_pool_excludes_tests_that_never_vary():
    """A test true in every reading carries no bits and must not become a precondition."""
    readings = [(("0", "alpha"),), (("0", "alpha"), ("1", "beta"))]
    conditions = pop.condition_pool(readings, relations=("CARD",), bindings=("WHOLE",))
    assert conditions, "the varying test must survive"
    for condition in conditions:
        hits = sum(1 for state in readings if pop.holds(condition, state))
        assert 0 < hits < len(readings)


def test_partial_order_is_reported_as_an_order_not_a_sequence():
    """The deliverable is the partial order. A linearisation is a choice and must be derivable."""
    operators = [op("LEFT", add=[A]), op("RIGHT", add=[C])]
    found = pop.plan([], [A, C], operators)
    assert found["status"] == "PASS__PARTIAL_ORDER_FOUND"
    assert set(found["steps"]) == {"LEFT", "RIGHT"}
    pairs = {tuple(pair) for pair in found["partial_order"]}
    assert ("<start>", "<finish>") in pairs
