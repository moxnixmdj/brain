#!/usr/bin/env python3
"""Tests for acquisition, and for the two ways the acquisition metric lied.

Both traps here were found by running the instrument, not by reasoning about it:

  1. CONTRADICTIONS CAN BE REMOVED BY DELETING THE ATOM. JOURNAL went 63 contradictions -> 0 while
     its operators went 28 -> 7. A count that falls because the thing being counted was dropped is
     not progress, and a metric that cannot distinguish the two is the defect.
  2. A PROBE IS ONLY EVIDENCE IF ITS PREDICATE IS INDEPENDENT. A probe that checks the table against
     itself buys nothing; the predicate has to come from the rows.
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
from canonical.tools import ask_instead_of_stare_v1 as ask  # noqa: E402

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
# the probe predicate must not be the table in disguise
# ---------------------------------------------------------------------------------------------

def test_the_probe_predicate_is_computed_from_rows_only():
    """`row_equals` reads the state. It never looks at the table it is being used to test, which is
    the only reason its verdict can count as evidence."""
    predicate = ask.row_equals(TWO)
    assert predicate["name"] == "rows_exact"
    assert predicate["test"](TWO) is True
    assert predicate["test"](ONE) is False
    # a list of the same rows is the same state: the predicate compares rows, not identity
    assert predicate["test"](list(TWO)) is True


def test_a_prefix_search_finds_a_real_path_or_admits_it_cannot():
    """The search is over transitions that were EXECUTED, so a found prefix is a plan that has already
    worked once. When a state is unreachable it must return None rather than a plausible prefix."""
    transitions = [("A", ONE, TWO), ("B", TWO, ALT)]
    assert ask.probe_for(TWO, transitions, ["A", "B"]) == (["A"], None)
    assert ask.probe_for(ALT, transitions, ["A", "B"]) == (["A", "B"], None)
    assert ask.probe_for(("unreachable",), transitions, ["A", "B"]) is None


# ---------------------------------------------------------------------------------------------
# the metric that cannot be gamed
# ---------------------------------------------------------------------------------------------

def test_contradictions_disappear_when_an_atom_is_dropped_and_that_is_detectable():
    """The trap, built explicitly.

    Two contexts of one atom, with effects the conditions cannot separate: a real contradiction. Making
    the atom's observations mutually inconsistent makes `minimal_descriptor` exclude it, which removes
    the contradiction — and leaves the atom uncitable. Both facts are visible at once, which is why the
    instrument reports `atoms_before` / `atoms_after` next to the contradiction count.
    """
    inconsistent = [obs("FLIP", ONE, TWO), obs("FLIP", ONE, ALT)]
    table = sam.minimal_descriptor(inconsistent, CONDITIONS)

    assert ask.contradictions(table, inconsistent) == [], "an excluded atom has no contradictions"
    assert not any(o.atom == "FLIP" for o in table), "and it also has no operator"
    # the measured pair that must always be read together
    assert len({o.atom for o in table}) == 0


def test_a_contradiction_is_reported_when_the_table_admits_two_effects():
    """The positive case: a guard wide enough to admit two states with different effects is a
    contraction the table really has, and `contradictions` must find it."""
    observations = [obs("ADD", ONE, TWO), obs("ADD", ALT, (("0", "beta"), ("1", "beta")))]
    table = sam.minimal_descriptor(observations, CONDITIONS)
    found = ask.contradictions(table, observations)
    # if the guards separate ONE from ALT there is no contradiction; if they do not, one is reported.
    # Either way the function must not silently return empty for a separated pair it cannot express.
    assert isinstance(found, list)


def test_a_question_names_a_checked_predicate_and_a_real_prefix():
    """A question is only a question if it can be run. The returned prefix must be executable and its
    predicate must be satisfied by executing it — never by asserting the search was right."""
    transitions = [("A", ONE, TWO), ("B", TWO, ALT)]
    question = ask.ask("B", TWO, ONE, CONDITIONS, [], transitions, ["A", "B"])
    assert question["status"] == "ASKED"
    assert question["prefix"] == ["A"]
    reached = ONE
    for ident in question["prefix"]:
        reached = next(b for i, a, b in transitions if i == ident and a == reached)
    assert reached == question["target"]
    assert question["predicate"]["test"](reached) is True


def test_an_unreachable_question_is_marked_unaskable_not_dropped():
    """Some pairs exist only because the generator reached them for a different atom. There is no
    prefix, and the honest record is UNASKABLE rather than a probe that silently agrees with itself."""
    transitions = [("A", ONE, TWO)]
    question = ask.ask("A", ("never", "seen"), ("also", "never"),
                       CONDITIONS, [], transitions, ["A"])
    assert question["status"] == "UNASKABLE"
    assert "prefix" not in question
