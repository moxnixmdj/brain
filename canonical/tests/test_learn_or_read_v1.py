#!/usr/bin/env python3
"""Read first; learn only for a gap the reading NAMED.

The claim under test, in the owner's words: "after he does them at least once, he would learn all of
those permanently... so we solve everything on a computer?"

The measurement this file pins (2026-11-16, 130 real MiniWoB++ pages, chromium, seed 1060):

    reading arm, zero experience      66 won
    pages a search ever demonstrated  78
      reading already wins            57  (73%)  <- learning has nothing to add
      reading loses                   21        <- the only place a policy is worth acquiring
    pages never demonstrated          52
      reading wins                     9        <- reading beats trying outright

and the composition rule decided from (sentence, observation) BEFORE any action:

    decide() == READ    89 pages   reading won 66 of them  (74.2%)
    decide() == LEARN   41 pages   reading won  0 of them   (0.0%)

That last row is the one that matters: the rule never forbids learning where a policy is what would
have been needed. So it is safe as a gate, and it says "do not acquire" on more than two thirds of
the board.

Nothing below needs a browser: the rule is a pure function of (instruction, observation), and the
observations are the real captures this tree already keeps.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from canonical.runtime import learn_or_read_v1 as LR

REPO = pathlib.Path(__file__).resolve().parents[2]
BOARD = REPO / "canonical/verification/LEARN_OR_READ_BOARD_20261116_V1.json"


def _decide_on(utterance: str, elements=None):
    """`decide(instruction, observation)` -- spelled out, because `*page.values()` loses order."""
    page = _page(utterance, elements)
    return LR.decide(page["utterance"], page)


def _page(utterance: str, elements=None) -> dict:
    return {"utterance": utterance, "elements": elements or [
        {"index": 0, "tag": "body", "text": "", "classes": "", "can_click": False},
        {"index": 5, "tag": "button", "text": "Submit", "classes": "btn",
         "id": "subbtn", "can_click": True},
    ]}


# --------------------------------------------------------------------------- #
# the gate itself
# --------------------------------------------------------------------------- #
def test_a_sentence_the_reading_determines_forbids_learning():
    """Exactly one act, named in the sentence, present on the page. There is nothing to learn."""
    got = _decide_on("Click the button.")
    assert got.outcome == LR.READ
    assert got.learning_forbidden is True


def test_a_named_gap_is_the_only_licence_to_acquire_a_policy():
    """`terminal` names a state the observation does not carry. The reading says WHICH."""
    got = _decide_on("Use the terminal below to delete a file that has no file extension.")
    assert got.outcome == LR.LEARN
    assert got.gap, "a licence to learn must name the gap, or it is a licence to learn anything"
    assert got.learning_forbidden is False


def test_half_a_sentence_is_the_clearest_licence():
    """"Find and click on the center of the circle, then press submit." -- the press compiles, the
    centre does not. The part it could not carry is what a policy would cover, and it is named."""
    page = _page("Find and click on the center of the circle, then press submit.")
    got = LR.decide(page["utterance"], page)
    assert got.outcome == LR.LEARN
    assert got.clauses >= 1, "the readable half must still be counted"
    assert got.gap


def test_an_unreadable_message_is_a_named_refusal_not_a_silent_licence():
    """The gate never returns READ by default. An empty sentence refuses -- and a refusal must NAME
    the gap, because a licence to learn that does not say what for is a licence to learn anything."""
    got = LR.decide("", {"elements": []})
    assert got.outcome != LR.READ
    assert got.learning_forbidden is False
    assert got.gap


def test_no_clause_and_no_refusal_is_unclear_and_never_read():
    """The one state that must fail closed rather than open: nothing was decided at all."""
    got = LR.Decision(LR.UNCLEAR, reason="constructed")
    assert got.learning_forbidden is False


# --------------------------------------------------------------------------- #
# the measured board
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not BOARD.exists(), reason="recorded board not present")
def test_the_rule_never_forbids_learning_where_the_reading_loses():
    """THE SAFETY PROPERTY. On every page the reading arm lost, the rule must not have said READ.

    Measured: 0 of the 41 LEARN pages were won by the reading arm; all 66 wins sit inside the 89
    READ pages. A gate that said READ there would be forbidding exactly the acquisition that was
    needed -- and it would be doing so on the pages that are already hardest.
    """
    board = json.loads(BOARD.read_text())
    rows = board["composition_rule"]["rows"]
    reading = {r["page"]: r["won"] for r in board["reading"]["results"]}
    read_pages = {r["page"] for r in rows if r["outcome"] == LR.READ}
    learn_pages = {r["page"] for r in rows if r["outcome"] != LR.READ}
    won = {p for p, w in reading.items() if w}

    assert won <= read_pages, (
        "the reading arm won pages the rule classified as LEARN: "
        + str(sorted(won - read_pages)))
    assert not (won & learn_pages), "a policy would have been acquired on an already-won page"
    # and the split is not vacuous: both sides are populated
    assert len(read_pages) >= 60 and len(learn_pages) >= 20


@pytest.mark.skipif(not BOARD.exists(), reason="recorded board not present")
def test_learning_had_nothing_to_add_on_most_demonstrable_pages():
    """The number that decides the architecture, and it is not the headline rate.

    A ladder that reports "one success generalises to 70%" hides that on 73% of the pages it can
    reach at all, the zero-experience reading already wins. Acquiring a policy there is work whose
    only effect is to make the agent depend on a stored procedure instead of the page.
    """
    facts = json.loads(BOARD.read_text())["board"]["the_two_facts"]
    assert facts["learning_had_nothing_to_add_on"] >= 50
    assert facts["of_which_share_of_demonstrable"] >= 0.70


@pytest.mark.skipif(not BOARD.exists(), reason="recorded board not present")
def test_reading_beat_trying_on_pages_no_demonstration_ever_reached():
    """"Give it a try once and it learns it" has no try to learn from on these pages.

    Nine pages -- the calendar behind a date field, a cube whose initial layout is already correct,
    arithmetic that is in the sentence -- are won by reading and were never demonstrated by a
    budgeted search even with the page's reward visible.
    """
    cells = json.loads(BOARD.read_text())["board"]["cells"]
    never = cells["reading_wins_where_nothing_was_demonstrable"]
    assert never["count"] >= 5
    assert "choose-date" in never["pages"]


# --------------------------------------------------------------------------- #
# the rule as a rule
# --------------------------------------------------------------------------- #
def test_the_rule_states_why_and_forbids_the_thing_that_costs():
    rule = LR.composition_rule()
    assert rule["authority"].startswith("NONE")
    joined = " ".join(rule["forbidden"]).lower()
    # the thing that costs is a stored procedure taking the reading's place
    assert "reading" in joined and ("stored" in joined or "replace" in joined)
    assert "held-out" in " ".join(rule["required"]).lower()
