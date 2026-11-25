#!/usr/bin/env python3
"""Tests for width: a law wider than its evidence, and the witness count that makes it honest.

The numbers these tests encode came from measurement, not from taste:

  * one witness  -> 42% accuracy on held-out states (38 predictions, 22 wrong)
  * two witnesses -> 100% accuracy (6 predictions, 0 wrong)

So the tests guard two things: that a law really is wider than the observations it came from, and
that the admission filter treats one witness as insufficient.
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
from canonical.tools import the_width_of_a_guard_v1 as width  # noqa: E402

CONDITIONS = [
    ("CARD", "WHOLE", None, "count_is", 1),
    ("CARD", "WHOLE", None, "count_is", 2),
    ("MULTISET", "WHOLE", None, "equals", (("alpha", 1),)),
    ("MULTISET", "WHOLE", None, "equals", (("zulu", 1),)),
]

# same two row identities, different contents: IDENT cannot tell them apart, ROWS can
ONE = (("0", "alpha"),)
ONE_OTHER = (("0", "zulu"),)
TWO = (("0", "alpha"), ("1", "beta"))


def obs(atom, before, after):
    return sam.Observation.of(atom, before, after, CONDITIONS)


def grows(state):
    return state + (("9", "new"),)


# ---------------------------------------------------------------------------------------------
# a law is wider than its evidence
# ---------------------------------------------------------------------------------------------

def test_a_law_admits_states_the_sample_never_contained():
    """The property that makes this not a description of a sample. A pure IDENT law fitted on one
    state must admit a DIFFERENT state with the same identities, or it has no width at all."""
    law = width.Law("ADD", "IDENT", ("0",), (frozenset(), frozenset()), support=2, witness=ONE)
    assert law.admits(ONE) is True
    assert law.admits(ONE_OTHER) is True, "same row identities, different content: the law is wider"
    assert law.admits(TWO) is False, "a different identity projection is outside the law"


def test_the_widest_consistent_projection_wins():
    """Two observations with the same identities but different contents, same effect: IDENT survives
    and is preferred to ROWS, because the narrower projection is the wider claim."""
    # two DIFFERENT contents, same row identity, and the same effect in both: nothing changes. The
    # effect has to be identical or the projection is not consistent, and an earlier version of this
    # fixture gave the two states different effects without noticing.
    observations = [obs("TOUCH", (("0", "alpha"),), (("0", "alpha"),)),
                    obs("TOUCH", (("0", "zulu"),), (("0", "zulu"),))]
    assert observations[0].effect == observations[1].effect == (frozenset(), frozenset())
    laws = width.learn_laws(observations)
    ident_laws = [law for law in laws if law.projection == "IDENT"]
    assert ident_laws, "one effect over every content means an IDENT law exists"
    assert ident_laws[0].support == 2


def test_a_projection_that_does_not_determine_the_effect_yields_no_law():
    """If the same projection carries two effects the projection is not sufficient, and no law may be
    stated over it. This is the check that stops a law becoming a coincidence."""
    # two genuinely different effects from one state: one row changed content, one row was added.
    # The earlier fixture used two different ADDED rows that the conditions could not see apart, so
    # both observations had the SAME effect and the test was asserting nothing.
    # SAME identity projection, DIFFERENT effects: identity is not sufficient, so no IDENT law.
    contradictory = [obs("ADD", (("0", "alpha"),), (("0", "alpha"), ("1", "b"))),
                     obs("ADD", (("0", "zulu"),), (("0", "zulu"),))]
    assert contradictory[0].effect != contradictory[1].effect, "fixture must really disagree"
    assert width.learn_laws(contradictory, projections=("IDENT",)) == [], (
        "two different effects under the same IDENT projection cannot be one law")
    # and under ROWS, which does determine the effect, there are two laws rather than none
    assert len(width.learn_laws(contradictory, projections=("ROWS",))) == 2


# ---------------------------------------------------------------------------------------------
# the witness count
# ---------------------------------------------------------------------------------------------

def test_one_witness_is_not_enough_and_two_is_the_threshold():
    """The measured split. The filter is an assertion about the world, so it is pinned: a single
    observation must NOT pass, and an identical claim with two supporting observations must."""
    single = width.Law("ADD", "IDENT", ("0",), (frozenset(), frozenset()), support=1, witness=ONE)
    double = width.Law("ADD", "IDENT", ("0",), (frozenset(), frozenset()), support=2, witness=ONE)
    assert single.support < width.MIN_SUPPORT
    assert double.support >= width.MIN_SUPPORT


def test_disagreeing_laws_refuse_rather_than_pick_a_winner():
    """Two laws admit one state and disagree about the effect. The width claim is not established, and
    refusing is the only sound answer -- picking the likelier one is the pattern this tree keeps
    having to remove."""
    narrow = width.Law("ADD", "IDENT", ("0",), (frozenset(), frozenset()), support=2, witness=ONE)
    wide_other = width.Law("ADD", "CARD", 1, (frozenset(), frozenset([("x", "y")])),
                           support=2, witness=ONE_OTHER)
    outcome = width.predict([narrow, wide_other], "ADD", ONE)
    assert outcome["status"] == "REFUSED__LAWS_DISAGREE"


def test_no_admitting_law_is_a_refusal_not_a_guess():
    law = width.Law("ADD", "IDENT", ("0",), (frozenset(), frozenset()), support=2, witness=ONE)
    assert width.predict([law], "OTHER_ATOM", ONE)["status"] == "REFUSED__NO_LAW_ADMITS_THIS_STATE"
    assert width.predict([law], "ADD", TWO)["status"] == "REFUSED__NO_LAW_ADMITS_THIS_STATE"
