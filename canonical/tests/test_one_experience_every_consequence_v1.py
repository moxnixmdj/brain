#!/usr/bin/env python3
"""Tests for the safe action model.

Every test here is a defect that was actually measured while building this file. That is not a
style choice: the safe-model idea has exactly one property that matters -- it must never be wrong --
and each of the following was a way it WAS wrong, or a way the measurement lied about it.

  1. vacuity        a drop licensed by "no observation objects", with no observations to object
  2. vacuity again  the same trap after the first fix, because one group per atom has no peers
  3. projection     plans found by applying add/delete to a condition list, refuted on execution
  4. false zero     a coverage metric that reads 0.0 by definition rather than by measurement
  5. a control that searched nothing and reported "no plan"
  6. a stub probe that returned False and made every refusal look like evidence
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402

CONDITIONS = [
    ("CARD", "WHOLE", None, "count_is", 1),
    ("CARD", "WHOLE", None, "count_is", 2),
    ("CARD", "WHOLE", None, "count_is", 3),
    # content conditions, so a context can differ in something other than its length
    ("MULTISET", "WHOLE", None, "equals", (("alpha", 1),)),
    ("MULTISET", "WHOLE", None, "equals", (("alpha", 2),)),
    ("MULTISET", "WHOLE", None, "equals", (("beta", 1),)),
    ("MULTISET", "WHOLE", None, "equals", (("beta", 2),)),
]
ONE = (("0", "alpha"),)
TWO = (("0", "alpha"), ("1", "alpha"))
THREE = (("0", "alpha"), ("1", "alpha"), ("2", "alpha"))


def observation(atom, before, after):
    return sam.Observation.of(atom, before, after, CONDITIONS)


# ---------------------------------------------------------------------------------------------
# the sound core
# ---------------------------------------------------------------------------------------------

def test_one_observation_yields_an_operator_that_cannot_be_wrong():
    """The N-SAM* claim in its smallest form: a single recorded step becomes an operator whose guard
    names the state it came from, so predicting from it is remembering, not guessing."""
    table = sam.specific_table([observation("ROLL", ONE, TWO)], CONDITIONS)
    assert len(table) == 1
    outcome = sam.apply(table, "ROLL", ONE)
    assert outcome.status == "APPLIES"
    assert ("CARD", "WHOLE", None, "count_is", 2) in outcome.operator.added
    assert ("CARD", "WHOLE", None, "count_is", 1) in outcome.operator.deleted


def test_it_refuses_states_it_was_never_shown():
    """The price of safety, asserted so it cannot be quietly 'fixed' later: a specific guard does
    not apply in an unobserved state, and refusing is the correct behaviour."""
    table = sam.specific_table([observation("ROLL", ONE, TWO)], CONDITIONS)
    assert sam.apply(table, "ROLL", THREE).status == (
        "REFUSED__NO_OPERATOR_APPLIES_TO_THIS_STATE")


def test_a_conflicted_atom_is_excluded_not_averaged():
    """Same atom, same pre-state, two different effects: the table cannot contain a coin flip."""
    table = sam.specific_table([observation("ROLL", ONE, TWO), observation("ROLL", ONE, THREE)],
                               CONDITIONS)
    assert table == []
    assert sam.specific_table.last_conflicted == 1


def test_two_guards_matching_one_state_is_reported_as_ambiguous():
    """If the vocabulary does not separate two states with different effects, the table says so
    rather than picking the likelier one."""
    wide = sam.SafeOperator("ROLL", frozenset(), frozenset(), frozenset())
    narrow = sam.SafeOperator("ROLL", frozenset([CONDITIONS[1]]), frozenset(), frozenset())
    assert sam.apply([wide, narrow], "ROLL", TWO).status == "REFUSED__AMBIGUOUS_OPERATOR"


# ---------------------------------------------------------------------------------------------
# the generalization traps
# ---------------------------------------------------------------------------------------------

def test_dropping_a_guard_needs_a_positive_witness_not_an_absence():
    """Defect 1. With one observation there is no counterexample, so 'nothing objects' would strip
    the guard to nothing and assert one state's effect everywhere. JOURNAL measured that as 10 of
    11 predictions wrong. No witness, no drop."""
    table = sam.specific_table([observation("ROLL", ONE, TWO)], CONDITIONS)
    generalized, report = sam.generalize(table, [observation("ROLL", ONE, TWO)], CONDITIONS)
    assert generalized[0].guard == table[0].guard, "the guard must survive untouched"
    assert report["guard_literals_dropped_with_a_positive_witness"] == 0


def test_generalization_never_invents_reach_without_evidence():
    """The invariant that matters more than any single drop: whatever the fixture, generalization
    only ever REMOVES literals, never states, and never produces an operator whose guard mentions a
    condition that was not in the original guard. Reach comes from evidence, and the evidence is
    counted rather than assumed."""
    observations = [observation("ROLL", ONE, TWO), observation("ROLL", TWO, THREE)]
    table = sam.specific_table(observations, CONDITIONS)
    generalized, report = sam.generalize(table, observations, CONDITIONS)
    for before, after in zip(table, generalized):
        assert after.guard <= before.guard, "generalization may only drop literals"
        assert after.generalized_from == len(before.guard) - len(after.guard)
    assert report["guard_literals_dropped_with_a_positive_witness"] + \
        report["drops_refused_for_want_of_a_witness"] > 0


def test_an_operator_with_no_guard_is_never_produced_by_generalization():
    """The invariant behind defects 1 and 2, stated once and checked on every path: a table never
    contains an operator that claims to apply everywhere."""
    observations = [observation("ROLL", ONE, TWO), observation("ROLL", TWO, THREE),
                    observation("ROLL", THREE, THREE)]
    table = sam.specific_table(observations, CONDITIONS)
    generalized, _report = sam.generalize(table, observations, CONDITIONS)
    assert all(operator.guard for operator in generalized)


# ---------------------------------------------------------------------------------------------
# the measurements that must not lie
# ---------------------------------------------------------------------------------------------

def test_probe_generalization_executes_and_can_agree():
    """The metric that is allowed to move. It is handed an operator and a machine that agrees, and it
    must report a tested prediction rather than zero."""
    operator = sam.SafeOperator("ROLL", frozenset([CONDITIONS[1]]),
                                frozenset([CONDITIONS[2]]), frozenset([CONDITIONS[1]]),
                                origin=tuple(ONE))
    calls = []

    def probe(atom, state):
        calls.append(state)
        return (frozenset([CONDITIONS[2]]), frozenset([CONDITIONS[1]]))

    result = sam.generalization_under_fire([operator], [THREE, TWO], probe)
    assert result["generalized_predictions_tested"] == 1, "the metric must be able to move"
    assert result["generalized_predictions_RIGHT"] == 1
    assert result["generalized_predictions_WRONG"] == 0
    assert calls and tuple(calls[0]) != operator.origin, "never re-run the training state"


def test_probe_generalization_executes_and_can_refute():
    """And the same metric must be able to say NO, or it is not a test."""
    operator = sam.SafeOperator("ROLL", frozenset([CONDITIONS[1]]),
                                frozenset([CONDITIONS[2]]), frozenset([CONDITIONS[1]]),
                                origin=tuple(ONE))
    result = sam.generalization_under_fire(
        [operator], [THREE], lambda atom, state: (frozenset([CONDITIONS[0]]), frozenset()))
    assert result["generalized_predictions_WRONG"] == 1
    assert result["sound_under_generalization"] is False


def test_a_probe_that_cannot_reach_its_state_is_not_evidence():
    """Defect 6. `None` from a probe means the test could not be run; it must be counted as
    unreachable, never as agreement."""
    operator = sam.SafeOperator("ROLL", frozenset([CONDITIONS[1]]),
                                frozenset([CONDITIONS[2]]), frozenset([CONDITIONS[1]]),
                                origin=tuple(ONE))
    result = sam.generalization_under_fire([operator], [THREE], lambda atom, state: None)
    assert result["generalized_predictions_tested"] == 0
    assert result["unreachable_probe_states"] == 1
    assert result["generalized_predictions_RIGHT"] == 0


# ---------------------------------------------------------------------------------------------
# composition: the smallest form of the skill-algebra question
# ---------------------------------------------------------------------------------------------

def test_two_tables_compose_only_while_no_atom_becomes_ambiguous():
    first = sam.specific_table([observation("ROLL", ONE, TWO)], CONDITIONS)
    second = sam.specific_table([observation("ROLL", TWO, THREE)], CONDITIONS)
    merged = sam.merge(first, second)
    assert len(merged) == 2
    assert sam.apply(merged, "ROLL", ONE).status == "APPLIES"
    assert sam.apply(merged, "ROLL", TWO).status == "APPLIES"
    conflict = sam.merge(first, second, [sam.SafeOperator("ROLL", frozenset(), frozenset(),
                                                          frozenset())])
    assert sam.apply(conflict, "ROLL", ONE).status == "REFUSED__AMBIGUOUS_OPERATOR"
