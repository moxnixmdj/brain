"""The ranking of blockers, pinned — and the refutation of three of my own rounds.

The numbers are pinned deliberately. If the registry or the front door changes,
these tests fail and the accompanying document becomes visibly stale instead of
quietly wrong. A failure here means "re-read WHAT_ACTUALLY_BLOCKS_THE_FRONT_DOOR",
not "the code broke".

The load-bearing assertion is the LAST one. It says that closing every premise
nobody can decide does not, on its own, make a single capability work. Three of
my own rounds named that as the highest-value work item. It is not, and this is
the measurement that says so.

These tests run the real front door over the real registry, so they are slow
(about a minute). That is the honest cost of a census; a synthetic shortcut would
measure the shortcut.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import what_actually_blocks_the_front_door_20261112 as B


@pytest.fixture(scope="module")
def census():
    return B.census()


@pytest.fixture(scope="module")
def counterfactual(census):
    return B.unwedge_unknown_premises()


# --------------------------------------------------------------------------------------------
# The shape of the population
# --------------------------------------------------------------------------------------------
def test_the_registry_the_front_door_sees_is_pinned(census):
    assert census["total"] == 155, (
        "the front-door registry changed size; the document quotes 155")


def test_binding_is_the_largest_blocker_by_far(census):
    """Not by a little. 61 against 9 is the whole argument of the round."""
    not_bindable = census["counts"].get("3_NOT_BINDABLE", 0)
    unknown = census["counts"].get("4_BLOCKED_BY_UNKNOWN", 0)
    assert not_bindable == 61, not_bindable
    assert unknown == 9, unknown
    assert not_bindable > 6 * unknown


def test_blocked_by_false_is_small_and_kept_separate(census):
    """A premise the world says is FALSE is a correct refusal, not a defect."""
    assert census["counts"].get("5_BLOCKED_BY_FALSE", 0) == 2


def test_the_buckets_account_for_every_row(census):
    assert sum(census["counts"].values()) == census["total"]


def test_unknown_and_false_are_not_the_same_bucket(census):
    unknown = set(census["buckets"].get("4_BLOCKED_BY_UNKNOWN") or [])
    false = set(census["buckets"].get("5_BLOCKED_BY_FALSE") or [])
    assert unknown and false
    assert not (unknown & false)


# --------------------------------------------------------------------------------------------
# THE REFUTATION
# --------------------------------------------------------------------------------------------
def test_closing_every_blind_premise_does_not_make_anything_work(counterfactual):
    """Three rounds of my own work said this was the highest-value item.

    Measured: assuming every undecidable precondition TRUE lifts 3 of 9 into
    SELECTED, and **none of the three then runs without an error**. The premise
    was never the binding constraint; binding is.
    """
    assert counterfactual["unknown_blocked"] == 9
    assert counterfactual["became_selected"] == 3
    assert counterfactual["became_selected_and_ran_without_error"] == 0, (
        "a capability now works once its blind premise is assumed -- that would "
        "mean the blind premises ARE load-bearing after all, and this round's "
        "conclusion is wrong")


def test_the_six_that_stay_blocked_are_blocked_for_a_different_reason(counterfactual):
    """They do not become usable; they become BINDABLE failures instead."""
    stayed = [r for r in counterfactual["rows"] if r["then"] != "SELECTED"]
    assert len(stayed) == 6
    assert all(r["then"] == "NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES" for r in stayed)
    assert all(r.get("missing") for r in stayed)


def test_the_three_that_are_selected_still_fail(counterfactual):
    """Selection is not success. A capability can be chosen and still be unable."""
    selected = [r for r in counterfactual["rows"] if r["then"] == "SELECTED"]
    assert len(selected) == 3
    assert all(str(r.get("status")).startswith("ACTION_FAILED") for r in selected)
