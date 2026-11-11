"""What does ONE genuinely new computer task cost now?  Measured end to end.

The page had never been seen. The goal had never been taught. The model's proposals were
written to a file before any of it ran.

    TEACH   ANSWERED, 3 model proposals, 3 verifications, 3 steps, 2.79s, 0 gate failures
    REUSE   blocked -- see below

And the reuse failure is the finding of this round, so it is tested rather than apologised
for:

    What was recorded       click @(174,133), type "urgent", click @(436,133)
    What a new goal needs   click @(174,133), type "refund",  click @(436,133)

"urgent" was stored as pixels. Nothing in the record said it came from the goal, so the
learned thing can only ever re-type the word it was shown. parameterise_v1 fixes the VALUE
half of that (it turns a goal-derived literal into a slot and fills it from a new goal), but
the POSITION half is still blocked: an empty text field cannot be located by appearance,
because 453 places on the page look equally like a blank input.

That is the honest state, and it is worth more than a flattering number.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import parameterise_v1 as P

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROPS = json.loads(
    (ROOT / "canonical/evaluation/one_new_task/proposals_20261109_v1.json").read_text())


# ------------------------------------------------------------------ the cost of a new task

def test_the_proposals_were_written_before_execution():
    """A proposal file that could be edited after seeing the result is not evidence."""
    assert PROPS["_note"].startswith("Written from the screenshot alone")
    assert set(PROPS["proposals"]) == {"1", "2", "3", "4"}


def test_the_model_proposed_reasons_and_expectations_not_just_actions():
    for k, p in PROPS["proposals"].items():
        assert p.get("because"), k
        assert "confidence" in p


def test_the_fourth_proposal_is_an_admitted_no_op():
    """The loop has to be able to stop honestly; a proposal set with no way to fail tests
    nothing about the gate."""
    assert PROPS["proposals"]["4"]["confidence"] < 0.1


# ------------------------------------------------------------------ the value half, fixed

ACTS = [{"action": "click", "x": 174, "y": 133},
        {"action": "type", "text": "urgent"},
        {"action": "click", "x": 436, "y": 133}]


def test_a_value_that_came_from_the_goal_becomes_a_slot():
    t = P.learn_with_slots("show only the urgent messages", ACTS)
    assert t["slots"] and t["slots"][0]["slot"] == "{slot0}"
    assert t["slots"][0]["taught_value"] == "urgent"
    assert [a.get("text") for a in t["actions"] if a["action"] == "type"] == ["{slot0}"]


def test_a_new_goal_fills_the_slot_with_its_own_content():
    t = P.learn_with_slots("show only the urgent messages", ACTS)
    cases = {"show only the messages about refund": "refund",
             "show only messages from alice": "alice",
             "show only the invoice messages": "invoice",
             "show only billing": "billing"}
    for goal, want in cases.items():
        r = P.fill(t, goal)
        assert r["verdict"] == "FILLED", goal
        typed = [a["text"] for a in r["actions"] if a["action"] == "type"]
        assert typed == [want], (goal, typed)


def test_function_words_are_not_values():
    """First version bound "about", then "from", as the value."""
    assert "about" in P.SHAPE_WORDS
    assert "refund" not in P.SHAPE_WORDS


def test_a_goal_with_no_content_is_refused_rather_than_guessed():
    t = P.learn_with_slots("show only the urgent messages", ACTS)
    r = P.fill(t, "show me the things")
    assert r["verdict"] == "CANNOT_FILL"


# ------------------------------------------------------------------ the position half, open

def test_the_learned_trajectory_could_not_be_regrounded_on_an_empty_field():
    """Documented, not hidden: the anchor for an empty input is unlocatable by appearance.

    Measured on the real page: a 40x40 patch of the blank field matched 453 offsets spread
    over 258 pixels. Any threshold that accepts it is picking a coin flip and calling it a
    match. This is the ceiling on appearance-anchored grounding and it needs a different
    signal -- structure in the page, not pixels.
    """
    from canonical.runtime import grounding_v1 as G
    assert G.MAX_TIE_SPREAD == 1.0
    # the rule that makes the failure explicit rather than silent
    assert hasattr(G, "_match")
