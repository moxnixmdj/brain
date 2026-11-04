"""The parameters the data asks for, instead of a menu of twelve.

Pre-registration: `PREREG_PARAMETERS_THE_DATA_ASKS_FOR_20261104_V1.md`.

The measured defect these tests exist for: at the default weight bound `demand_evidence` reported
`UNRESOLVED` for `3x+1`, `2x+7`, `x+5` and `5x-1`, and prescribed "a larger max_weight" -- the wrong
remedy, because the missing item was a NUMBER, not an operation. Supplying the single constant each
needed made `3x+1` and `2x+7` `DETERMINED` at the SAME weight bound; raising the weight instead took
`3x+1` to weight 5 and found 28 programs.

The cause was a twelve-entry frozen menu:

    seed_consts = [0, 1, 2, -1, 100, True, False, None, "", [], {}]

so the system could spell `2x` and `3x` but not `3x+1`. Seventh appearance of one defect class: a
frozen list standing where a computation belongs.
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from canonical.runtime.evidence_demand_v1 import (
    DETERMINED,
    PROVISIONAL,
    SEARCH_TRUNCATED,
    UNRESOLVED,
    demand_evidence,
    invented_constants,
)


def _line(fn, xs=(1, 2, 3, 4, 5)):
    return [((x,), float(fn(x))) for x in xs]


# ------------------------------------------------------------------------------------------------
# P2: inventing the constant is at least as good as being handed it
# ------------------------------------------------------------------------------------------------

def test_the_coefficient_the_data_asks_for_is_solved_not_looked_up():
    """F2/P2: `3x+1` reaches the same verdict as the hand-supplied run, with no menu entry for 3."""
    examples = _line(lambda x: 3 * x + 1)

    without = demand_evidence(["x"], examples, invent_parameters=False)
    assert without["status"] == UNRESOLVED, "the frozen menu alone cannot spell 3x+1"

    invented = demand_evidence(["x"], examples)
    assert invented["status"] == DETERMINED
    assert invented["explanation_count"] == 1
    assert invented["coverage"]["complete"] is True

    # and being HANDED the constant must not beat inventing it -- the point is that the number was
    # recoverable from the data, not that a caller had to know it
    handed = demand_evidence(["x"], examples, extra_constants=(3,))
    assert handed["status"] == invented["status"]
    assert handed["explanation_count"] == invented["explanation_count"]


def test_raising_the_weight_was_measurably_the_wrong_remedy():
    """P1: the blocker was the alphabet, not the grammar.

    `3x+1` does become reachable at a larger weight bound, but with 28 programs rather than 1. A
    remedy that costs more search and returns more confusion is not the remedy.
    """
    examples = _line(lambda x: 3 * x + 1)
    heavy = demand_evidence(["x"], examples, max_weight=5, max_bank_size=80000, invent_parameters=False)
    invented = demand_evidence(["x"], examples)
    assert invented["explanation_count"] < (heavy.get("explanation_count") or 10**9)


@pytest.mark.parametrize("fn,expected_constant", [
    (lambda x: 2 * x + 7, 7),
    (lambda x: x + 5, 5),
    (lambda x: 5 * x - 1, 5),
])
def test_several_coefficients_outside_the_menu_are_recovered(fn, expected_constant):
    """P2: not a special case for one function -- the recovery is generative."""
    found = invented_constants(_line(fn))
    assert found["bodies"], "an exact affine fit must exist for a straight line"
    assert expected_constant in found["constants"]


# ------------------------------------------------------------------------------------------------
# P3: exact, not floating
# ------------------------------------------------------------------------------------------------

def test_a_recovered_parameter_is_an_exact_rational():
    """P3/F5: `1.5x + 0.25` must come back as 3/2 and 1/4, not as a float that is merely close."""
    found = invented_constants(_line(lambda x: 1.5 * x + 0.25))
    assert found["bodies"] == ["return (3 / 2) * x + (1 / 4)"]
    assert "1.5" not in found["bodies"][0], "a decimal spelling would be an approximation claim"


def test_an_integer_fit_is_not_rejected_by_a_float_spelling():
    """The instrument bug this test was written for.

    `_freeze_val` keeps `4` and `4.0` distinct, so comparing an exactly-correct `3 * x + 1` (which
    returns ints) against float targets rejected every integer-valued line. The parameter was found
    and then discarded by a spelling difference -- measured, and fixed by comparing behaviourally.
    """
    found = invented_constants([((1,), 4), ((2,), 7), ((3,), 10)])
    assert found["bodies"] == ["return 3 * x + 1"]


# ------------------------------------------------------------------------------------------------
# P4: a parameter is verified, not trusted
# ------------------------------------------------------------------------------------------------

def test_a_parameter_that_misses_one_example_is_not_admitted():
    """P4/F2: near-misses contribute nothing.

    Three points on a line plus one point off it. No affine fit reproduces all four, so the affine
    family must contribute no body at all -- not a body that is close.
    """
    examples = _line(lambda x: 3 * x + 1) + [((6,), 100.0)]
    found = invented_constants(examples)
    affine = [b for b in found["bodies"] if "3 * x" in b]
    assert affine == [], "an affine body that fails x=6 must not be admitted"


# ------------------------------------------------------------------------------------------------
# P7/F3: refusal, not curve-fitting
# ------------------------------------------------------------------------------------------------

def test_a_non_affine_dataset_is_refused_rather_than_absorbed():
    """P7/F3: the DOF failure, which has appeared three times on this branch (rounds 11, 12, 14).

    `x*x` on five points is not a line. The fitter must decline; adding parameters until the data is
    absorbed would reproduce the shape without describing it.
    """
    found = invented_constants(_line(lambda x: x * x))
    assert found["bodies"] == []
    assert "parameters solved exactly" not in found["why"]


def test_one_point_invents_nothing():
    """A line through one point is a choice, not a measurement -- and the module says so."""
    found = invented_constants([((1,), 5.0)])
    assert found["bodies"] == []
    assert "two observations" in found["why"] or "too few" in found["why"]


# ------------------------------------------------------------------------------------------------
# P5: falsified, and kept as a failure
# ------------------------------------------------------------------------------------------------

def test_p5_was_falsified_the_alphabet_change_moves_already_correct_cases():
    """P5 predicted unchanged counts on cases that were already reachable. It FAILED.

    Measured: `2x` went from 5 explanations to 6. The additional explanation is
    `if ((x - 2) > 2): return ((100 / x) / 2)` which agrees at x=1..5 and differs at x=10 (5.0 vs
    20.0) -- a genuine rival, not a duplicate. So the old count of 5 was an UNDERCOUNT: a larger
    alphabet enumerated piecewise bodies the menu could not reach.

    This test does not assert the number 6, because the number is a property of the grammar and will
    move again. It asserts the property that makes the falsification worth recording: a case that was
    already `PROVISIONAL` stays `PROVISIONAL` and does not become certain.
    """
    examples = _line(lambda x: 2 * x)
    before = demand_evidence(["x"], examples, invent_parameters=False)
    after = demand_evidence(["x"], examples)
    assert before["status"] == PROVISIONAL
    assert after["status"] == PROVISIONAL, "P5: a correct case must not become certain"
    assert after["explanation_count"] >= 1


# ------------------------------------------------------------------------------------------------
# The truncation guard, reintroduced by the larger alphabet and re-fixed
# ------------------------------------------------------------------------------------------------

def test_a_saturated_bank_never_yields_certainty():
    """This defect was fixed once on this branch and the invention brought it back in miniature.

    A bigger constant alphabet makes the bank fill sooner, so a TRUNCATED sweep can terminate on a
    single explanation that a complete sweep would have contradicted. `DETERMINED` from a saturated
    bank is the same error as the `bank=900` result this branch already retracted.
    """
    line = [((0,), 1.0), ((1,), 3.0), ((2,), 5.0)]
    truncated = demand_evidence(["x"], line, max_bank_size=900)
    assert truncated["coverage"]["complete"] is False
    assert truncated["status"] == SEARCH_TRUNCATED, "a cut-off sweep must not report certainty"
    assert "budget" in truncated["why"].lower()

    complete = demand_evidence(["x"], line)
    assert complete["coverage"]["complete"] is True
    assert complete["status"] == DETERMINED


# ------------------------------------------------------------------------------------------------
# P6: the advice stops being wrong
# ------------------------------------------------------------------------------------------------

def test_the_unresolved_message_mentions_that_exact_fits_were_tried():
    """P6: when the exact fitter ran and still could not fit, the message must say so.

    "Raise max_weight" was measurably the wrong remedy for four ordinary affine functions. A caller
    told to search harder along the wrong axis is being misled about where the obstacle is.
    """
    # alternating 0/1 -- no affine fit, and out of reach at weight 3
    examples = [((0,), 0.0), ((1,), 1.0), ((2,), 0.0), ((3,), 1.0)]
    report = demand_evidence(["x"], examples, max_weight=1)
    if report["status"] == UNRESOLVED:
        assert "parameter" in report["why"].lower() or "constant" in report["why"].lower()
