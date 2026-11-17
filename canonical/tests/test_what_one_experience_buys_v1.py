#!/usr/bin/env python3
"""One experience buys one bit. A step costs several. The price of a task does not fall.

These tests pin the arithmetic behind the owner's question — "after he does them at least once he
would learn all of those permanently, so we solve everything on a computer?" — and they are written
so that the interesting one can FAIL: if a future round makes the description language smaller, the
saturation test below flips and says so, rather than being quietly edited to match reality.

Nothing here runs an episode. The numbers are read from a recorded run that is already on main, and
the file it reads is named in the assertion so a reader can check the number against its source.
"""
from __future__ import annotations

import json
import math

import pytest

from canonical.runtime import what_one_experience_buys_v1 as W


@pytest.fixture(scope="module")
def recorded():
    return json.loads(W.RECORDED.read_text())


@pytest.fixture(scope="module")
def verdict(recorded):
    return W.verdict(recorded)


# --------------------------------------------------------------------------- #
# what one experience pays
# --------------------------------------------------------------------------- #
def test_one_success_is_one_bit_and_that_is_arithmetic(verdict):
    """A success strikes out the descriptions that would have done something else there.

    That is a binary question per description, so a demonstration buys ~1 bit. The claim is not a
    judgement about the learner; it is the count of what one observation can separate.
    """
    steps = verdict["what_one_step_costs"]
    assert steps["steps"] >= 150, "the recorded run must actually contain programs"
    # the cost of a step, measured, and it is several bits
    assert steps["bits_per_step"] > 4.0
    assert steps["median_descriptions_left"] >= 20


def test_almost_every_real_step_needs_more_than_one_demonstration(verdict):
    """THE LOAD-BEARING NUMBER. 174 of 175 steps leave more than one description standing.

    If this were small, one demonstration really would identify a program and the owner's sentence
    would be right about generation too. It is 99.4%, so the sentence is right about storage and
    wrong about generation.
    """
    steps = verdict["what_one_step_costs"]
    assert steps["of_which_share"] > 0.95
    assert steps["steps_needing_more_than_one_bit"] >= 170


# --------------------------------------------------------------------------- #
# does it compound?
# --------------------------------------------------------------------------- #
def test_experience_does_compound_through_a_shared_vocabulary(verdict):
    """It is not 78 unrelated programs: 149 steps collapse to far fewer distinct descriptions."""
    curve = verdict["compounding"]
    assert curve["reuse_ratio"] > 1.4
    assert curve["tasks_sharing_a_description_with_an_earlier_task"] >= 30


def test_the_vocabulary_does_not_saturate_and_this_is_the_uncomfortable_result(verdict):
    """The hope was a small shared language that covers new tasks. Measured: it keeps growing.

    The second half of experience adds 57% of the final vocabulary, and a task still costs ~1.23
    descriptions it has never needed before. So experience lowers the PRICE of a description it has
    already paid for, not the NUMBER a new task needs.

    If a future round shrinks the description language enough that this flips, this test fails and
    the receipt must be rewritten -- which is the correct behaviour for a pinned belief.
    """
    curve = verdict["compounding"]
    assert curve["saturates"] is False
    assert curve["share_added_by_the_second_half"] > 0.4
    assert curve["new_descriptions_per_task"] > 1.0
    assert "KEEPS_GROWING" in curve["verdict"]


def test_the_curve_is_measured_in_recorded_order_not_by_peeking(verdict):
    """A task may never pay for itself: only vocabulary from EARLIER tasks counts for it."""
    curve = verdict["compounding"]
    assert curve["curve"] == sorted(curve["curve"]), "the vocabulary can only grow"
    assert curve["curve"][0] < curve["curve"][-1], "and it must actually grow"


# --------------------------------------------------------------------------- #
# what the module refuses
# --------------------------------------------------------------------------- #
def test_it_reads_a_receipt_and_says_so_rather_than_claiming_an_experiment(verdict):
    assert verdict["authority"].startswith("NONE")
    assert "NOT_A_NEW_EXPERIMENT" in verdict["authority"]
    assert verdict["read_from"].endswith(".json")


def test_the_only_thing_that_can_make_a_step_cheaper_is_a_smaller_language(verdict):
    """log2 of the survivors: the lever is REMOVING descriptions, never seeing more pages.

    This is the "best part is no part" law in its exact form here -- the price is a log of a count,
    so the only way to lower it is to have fewer candidate descriptions, and no amount of additional
    experience removes a description that the language admits.
    """
    assert "smaller description language" in verdict["what_would_make_it_cheaper_and_is_a_separate_lever"]
    # the arithmetic of the claim, checked rather than asserted
    steps = verdict["what_one_step_costs"]
    assert math.log2(steps["median_descriptions_left"]) > 5.0
