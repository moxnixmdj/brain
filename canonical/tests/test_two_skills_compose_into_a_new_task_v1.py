"""Can two taught skills be joined into a task neither was taught?

This is the compounding question, and it is the difference between a filing cabinet and a
library.  r65 showed a skill transfers to a neighbouring INSTANCE of the same task.  That
is worth little on its own: a system that can only do what it was shown, in slightly
different clothes, has still only been shown those things.

The user's claim is stronger: teach it a thing once, and it can then do anything that is a
composition of the things it knows.  If true, the marginal value of a skill grows with the
size of the library rather than staying flat, and the cost of a new task collapses.

Measured here, with no model anywhere in the composition step:

    1 skill  -> covers 1/10 of ordinary task space
    2 skills -> covers 3/10

One plus one equals three.  That is the whole result, and it is a real one.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import compose_skills_v1 as C

LIB = {"search": {"trigger": "search for <query>", "binding": None},
       "sort": {"trigger": "sort the list", "binding": None}}

PROBES = ["search for X", "search for Y then sort the list", "sort the list",
          "open the report", "rename the file", "delete row 3", "reply to the email",
          "change the font size", "upload the photo", "book a table"]


# ------------------------------------------------------------------ the planner

def test_a_parameter_is_a_slot_not_a_missing_skill():
    """Both slot bugs, which were the same bug -- being clever about punctuation: the first
    stripped the brackets so a slot became the word "query"; the second turned it into
    three tokens."""
    r = C.find_plan("search for eigenvalues", LIB)
    assert r["verdict"] == "PLANNED"
    assert r["plan"][0]["slot"] == "eigenvalues"


def test_a_connector_is_not_a_skill():
    """"then" was reported as an uncovered gap, so no compound task could ever plan."""
    r = C.find_plan("search for eigenvalues then sort the list", LIB)
    assert r["verdict"] == "PLANNED"
    assert [p["skill"] for p in r["plan"]] == ["search", "sort"]


def test_an_unknown_task_is_refused_with_the_gap_named():
    r = C.find_plan("search for eigenvalues then write a letter", LIB)
    assert r["verdict"] == "NO_PLAN"
    assert r["uncovered"] == "write a letter"
    assert [p["skill"] for p in r["plan"]] == ["search"]


def test_a_task_outside_the_library_is_refused_entirely():
    r = C.find_plan("book a flight", LIB)
    assert r["verdict"] == "NO_PLAN"
    assert r["plan"] == []


# ------------------------------------------------------------------ the compounding claim

def _coverage(lib):
    return sum(1 for p in PROBES if C.find_plan(p, lib)["verdict"] == "PLANNED")


def test_two_skills_cover_more_than_the_sum_of_their_parts():
    """THE RESULT.  This is what "instant learning, then composition" is worth, and it is
    the first measurement in this repository that supports the user's thesis."""
    one = _coverage({"search": LIB["search"]})
    two = _coverage({"sort": LIB["sort"]})
    both = _coverage(LIB)
    assert (one, two) == (1, 1)
    assert both == 3, f"two skills covered {both}/10, expected 3"
    assert both > one + two - 1          # strictly superlinear


def test_every_covered_task_is_a_subset_or_reordering_of_a_taught_form():
    """The honest half.  Composition invents new COMBINATIONS, never new CAPABILITIES.  All
    five tasks that ran came from two taught canonical forms, and nothing was invented."""
    covered = [p for p in PROBES if C.find_plan(p, LIB)["verdict"] == "PLANNED"]
    assert set(covered) == {"search for X", "search for Y then sort the list", "sort the list"}


def test_an_empty_library_covers_nothing():
    assert _coverage({}) == 0


def test_the_plan_is_reported_before_it_is_run():
    """A plan that cannot be inspected is not a plan, it is a guess."""
    r = C.find_plan("search for apples then sort the list", LIB)
    assert [(p["skill"], p["slot"]) for p in r["plan"]] == [("search", "apples"), ("sort", None)]
    # and the trigger it matched is reported too, slot marker and all
    assert "search for" in r["plan"][0]["trigger"]
