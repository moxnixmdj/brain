#!/usr/bin/env python3
"""Tests for the distinction machinery and for the two traps it walked into.

The tests are the measured defects again, because every one of these was found by running the
instrument and each is a way the result could have been wrong:

  1. a descriptor that rules out SIBLING contexts over-fits to one state (32/40 wrong);
  2. an UNCONDITIONAL operator emitted because no observed context disagreed, which is a statement
     about the sample and not about the state space (18 predicates added where the truth added none);
  3. a NO-OP atom dropped from the table entirely, then refused in states it had been run in;
  4. trimming a minimal descriptor reported as sound when it is only sound because an empty guard
     never cites anything.
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
from canonical.swe_kernel import the_distinction_is_created_v1 as distinct  # noqa: E402

CONDITIONS = [
    ("CARD", "WHOLE", None, "count_is", 1),
    ("CARD", "WHOLE", None, "count_is", 2),
    ("MULTISET", "WHOLE", None, "equals", (("alpha", 1),)),
    ("MULTISET", "WHOLE", None, "equals", (("beta", 1),)),
]

ONE = (("0", "alpha"),)
TWO = (("0", "alpha"), ("1", "alpha"))
ALT = (("0", "beta"),)


def obs(atom, before, after):
    return sam.Observation.of(atom, before, after, CONDITIONS)


# ---------------------------------------------------------------------------------------------
# the distinction machinery
# ---------------------------------------------------------------------------------------------

def test_discriminators_are_properties_of_rows_not_of_names():
    """Every candidate is computed from the rows alone, so it survives a change of literals. That is
    the whole reason a computed column can be created rather than written per environment."""
    rows = (("0", "gamma"), ("1", "gamma"), ("2", "zulu"))
    assert distinct.sorted_content(rows) is True
    assert distinct.unique_content(rows) is False
    assert distinct.content_tail(rows) == "zulu"
    assert distinct.runs_of_equal_content(rows) == 2
    assert distinct.inversions(rows) == 0
    assert distinct.duplicate_count(rows) == 1
    assert distinct.id_content_agree(rows) is True


def test_a_property_that_does_not_separate_is_not_a_distinction():
    """A candidate is only useful if it DIFFERS on the two states. Two rows that agree on every
    property cannot be separated by any of them, and the cover says so instead of inventing one."""
    alias = distinct.Alias("ROLL", (("0", "alpha"),), (("0", "alpha"),),
                           frozenset(), frozenset([CONDITIONS[0]]))
    assert not any(distinct.separates(name, alias) for name in distinct.DISCRIMINATORS)
    chosen, leftover, _report = distinct.minimal_extension([alias])
    assert chosen == []
    assert leftover == [alias]


def test_the_cover_separates_what_it_can_and_names_what_it_cannot():
    separable = distinct.Alias("ROLL", (("0", "a"), ("1", "b")), (("0", "b"), ("1", "a")),
                               frozenset(), frozenset([CONDITIONS[0]]))
    chosen, leftover, _report = distinct.minimal_extension([separable])
    assert chosen, "order differs, so a shape property must separate them"
    assert leftover == []


def test_derived_conditions_are_read_by_the_same_reader_as_everything_else():
    """A created column is a condition like any other: the table stores it, the planner reads it, and
    no second mechanism is introduced."""
    for name, function in distinct.DISCRIMINATORS.items():
        sam.register_derived(name, function)
    rows = (("0", "alpha"), ("1", "beta"))
    assert sam.holds(("DERIVED", "sorted_content", None, "equals", True), rows) is True
    assert sam.holds(("DERIVED", "content_tail", None, "equals", "beta"), rows) is True


# ---------------------------------------------------------------------------------------------
# the traps
# ---------------------------------------------------------------------------------------------

def test_a_descriptor_rules_out_different_effects_not_sibling_states():
    """Trap 1. Ruling out every other context of the atom forces the guard to name ONE state, which
    is exact on training data and wrong on everything else (measured: 32 of 40 held-out predictions
    wrong). The guard must separate EFFECTS."""
    observations = [obs("ROLL", ONE, TWO), obs("ROLL", TWO,
                                              (("0", "alpha"), ("1", "alpha"), ("2", "alpha")))]
    table = sam.minimal_descriptor(observations, CONDITIONS)
    rolling = [operator for operator in table if operator.atom == "ROLL"]
    assert rolling
    for operator in rolling:
        # both contexts add a row; the descriptor must not be so tight that it only names one of them
        assert len(operator.guard) <= 2


def test_a_no_op_atom_still_gets_an_operator():
    """Trap 3. An atom whose effect is empty has no contrasting context, so a set cover over
    contrasting effects produces nothing and the atom vanished from the table -- then it was refused
    in states it had actually been run in."""
    observations = [obs("NOOP", ONE, ONE), obs("ROLL", ONE, TWO)]
    table = sam.minimal_descriptor(observations, CONDITIONS)
    assert any(operator.atom == "NOOP" for operator in table), (
        "an atom that was executed and did nothing is still a fact about the environment")


def test_no_operator_claims_the_whole_state_space_unless_that_was_measured():
    """Trap 2. An empty guard asserts one context's effect in every state. That shortcut was removed;
    a guard may be empty only when the atom's effect was the same in every observed context AND the
    caller asked for a descriptor. Otherwise the operator must carry a guard."""
    observations = [obs("ROLL", ONE, TWO), obs("ROLL", ALT, (("0", "beta"), ("1", "beta")))]
    table = sam.minimal_descriptor(observations, CONDITIONS)
    for operator in table:
        if not operator.guard:
            assert operator.added or operator.deleted
            assert operator.origin, "an unguarded operator must still name the state it came from"


def test_an_atom_that_does_two_things_from_one_state_is_not_citable():
    """No guard over this vocabulary can separate two observations of the same state, so the atom is
    excluded rather than resolved by picking one."""
    observations = [obs("FLIP", ONE, TWO), obs("FLIP", ONE, ALT)]
    table = sam.minimal_descriptor(observations, CONDITIONS)
    assert not any(operator.atom == "FLIP" for operator in table)


def test_a_minimal_descriptor_is_exact_on_the_data_it_was_built_from():
    """The property that makes it worth having at all, and the one that makes the held-out failure
    meaningful rather than a bug: on its own observations it never predicts wrongly."""
    observations = [obs("ROLL", ONE, TWO),
                    obs("ROLL", TWO, (("0", "alpha"), ("1", "alpha"), ("2", "alpha")))]
    table = sam.minimal_descriptor(observations, CONDITIONS)
    for held in observations:
        outcome = sam.apply(table, held.atom, held.before)
        if outcome.status == "APPLIES":
            assert (outcome.operator.added, outcome.operator.deleted) == held.effect


def test_purity_counts_contexts_the_vocabulary_cannot_express():
    """The executive metric. A cell is (atom, signature) -> observed effects; more than one effect is
    a context the representation cannot state, and the number is computed, never asserted."""
    # pure: one state, one effect
    pure = distinct.purity([("ROLL", ONE, TWO)], CONDITIONS, sam.holds)
    assert pure["impure_cells"] == 0 and pure["pure_fraction"] == 1.0
    # impure: the same (atom, signature) carrying two different effects. Built by giving the second
    # transition a DIFFERENT after-state that the conditions can see, so the cell really has two
    # effects rather than one effect reported twice.
    impure = distinct.purity(
        [("ROLL", ONE, TWO), ("ROLL", ONE, (("0", "alpha"), ("9", "zulu")))],
        CONDITIONS + [("MULTISET", "WHOLE", None, "equals", (("alpha", 1), ("zulu", 1)))],
        sam.holds)
    assert impure["cells"] == 1, "one signature, one cell"
    assert impure["impure_cells"] == 1, "two effects in one cell is exactly the unstatable context"
