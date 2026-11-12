"""Expressibility and the honesty of VERIFIED_ACTION, pinned.

Eleven rounds of hunting blockers and removing them changed nothing measurable. This round
tested the other hypothesis -- that the wrong thing was being measured -- and it holds:

  * 30 ordinary computer tasks: 15 expressible, 15 not, 15 AMBIGUOUS.
  * Of the 5 the machine reports as VERIFIED_ACTION, reading them says ONE answered its
    question. The other three answered a different question. One is unjudged.

The load-bearing assertion is `test_verified_action_is_not_the_same_claim_as_answered`.
`VERIFIED_ACTION` means the action met its own declared postcondition. It does not mean the
question was answered, and the gap is 3 of 4 judged.

A failure here means the numbers moved: re-measure and rewrite the document rather than
editing the assertions to fit.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import expressibility_of_ordinary_computer_tasks_v1 as E


@pytest.fixture(scope="module")
def report():
    return E.coverage()


@pytest.fixture(scope="module")
def honest(report):
    return E.honesty(report)


# ------------------------------------------------------------------------------------------
# Coverage: the machine cannot express half of what a person would ask for
# ------------------------------------------------------------------------------------------
def test_thirty_ordinary_tasks_are_measured(report):
    assert report["total"] == 30
    assert len(report["rows"]) == 30


def test_only_half_of_ordinary_computer_tasks_are_expressible(report):
    """15 of 30. This is coverage, not failure: ten of these have no capability at all."""
    assert report["expressible"] == 15, report["expressible"]
    assert report["unexpressible"] == 15


def test_every_unexpressible_task_is_ambiguous_not_routeless(report):
    """ALL FIFTEEN have candidates. NONE routes to an empty set.

    This corrects an earlier measurement in the same round: I reported "19 got nothing at
    all" from a hand-written script whose `routed_to` key was never populated for unrouted
    tasks, so `not r["routed_to"]` counted AMBIGUOUS rows as routeless. The instrument was
    wrong, not the machine. Every unexpressible task has survivors the gate could not
    separate -- which is a RANKING defect, not a REGISTRY-COVERAGE defect.
    """
    rows = report["rows"]
    ambiguous = [r for r in rows if r["status"] == "AMBIGUOUS"]
    routeless = [r for r in rows if r["status"] != "AMBIGUOUS" and not r["routed_to"]]
    assert len(ambiguous) == report["ambiguous"] > 0
    assert len(routeless) == 0, [r["task"] for r in routeless]
    # "unexpressible" is the sum of the two, not one of them -- they overlap only in
    # having no capability_id, which is exactly why counting them as one number hides the split.
    assert len(ambiguous) + len(routeless) == report["unexpressible"] == 15
    assert all(r.get("survivor_scores") for r in ambiguous)


# ------------------------------------------------------------------------------------------
# THE LOAD-BEARING TEST
# ------------------------------------------------------------------------------------------
def test_verified_action_is_not_the_same_claim_as_answered(honest):
    """FOUR OF FIVE VERIFIED TASKS WERE AUDITED BY READING THE RECEIPT. THREE WERE WRONG.

    `count the lines in README.md` returned 49943 definitions across 5479 files.
    `find files larger than one megabyte` returned 400 .py files with no size filter.
    `show me the last five git commits` returned one sha from a bisect.

    Each one satisfied its own postcondition and reported VERIFIED_ACTION. If this ever
    reports zero wrong, the machine has learned to answer its questions and this round's
    central finding no longer holds -- that would be good news and a reason to rewrite, not
    a reason to relax the test.
    """
    assert honest["verified"] == 5, honest["verified"]
    assert honest["not_an_answer"] == 3, honest["not_an_answer"]
    assert honest["honest"] == 1, honest["honest"]
    assert honest["verified"] > honest["honest"] + honest["not_an_answer"] - 1


def test_each_wrong_verdict_carries_what_it_actually_returned(honest):
    """A verdict without the receipt content is an opinion. Every wrong one records both."""
    wrong = [r for r in honest["rows"] if r["verdict"] == "NOT_AN_ANSWER"]
    assert len(wrong) == 3
    for row in wrong:
        assert row["audit"], row["task"]
        assert row["audit"]["returned"], row["task"]
        assert row["audit"]["why_wrong"], row["task"]


def test_the_one_honest_answer_is_really_an_answer(honest):
    """pdf text extraction: 43 bytes of real text out of a real PDF, reported as such."""
    good = [r for r in honest["rows"] if r["verdict"] == "HONEST"]
    assert len(good) == 1
    assert "pdf" in good[0]["routed_to"]
    assert "text" in good[0]["payload"]


# ------------------------------------------------------------------------------------------
# The forged-capability gate
# ------------------------------------------------------------------------------------------
def test_a_zero_score_row_cannot_make_a_decisive_match_ambiguous():
    """The forgery veto, measured on the case that exposed it.

    `show me the last five git commits` scored 26.3 for git.history.bisect_regression.v1 and
    was still refused AMBIGUOUS, because two forged capabilities appended with
    combined_score 0.0 survived into the ambiguity gate. With the gate fixed it is SELECTED.
    It is still the WRONG ANSWER (see above) -- which is the point: routing is not answering.
    """
    receipt = E.run_task("show me the last five git commits")
    assert receipt.get("capability_id") == "git.history.bisect_regression.v1", (
        "a zero-score row is gating a decisive match again -- the forge append in "
        "grounded_action_v1.act() is proposing rows it must only offer when nothing fits")
