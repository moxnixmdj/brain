"""Address by structure, decide by vision, check by pixels. Each signal for its own job.

The measurement that forced this design, across three rounds of failures:

    r64  replay keyed on a screen hash       -> a fact about one screenshot
    r65  anchors instead of coordinates      -> fixed the position of a WIDGET
    r70  a typed value stored as pixels      -> fixed by parameterise: value became a slot
    r70  ... but the widget could not be RELOCATED, because an empty text field has almost no
         appearance: a 40x40 patch of a blank input matched 453 offsets over 258 pixels

Now: the page reports its own structure, and the field is
    role=textbox name="filter" box (34,120)-(314,148)
One call, no matching, no threshold, no ambiguity.

Measured end to end on the inbox page:

    teach once, on "show only the urgent messages"  ->  click textbox/filter, type {slot0},
                                                        click button/APPLY
    reuse on "about refund"   -> types "refund", heading reads "Inbox - 1 shown"
    reuse on "from alice"     -> types "alice"
    three runs, ZERO model calls in the reuse path

The boundary matters as much as the result: this module may ask the page WHERE things are.
It may never ask the page what to do. The model decides by looking; the gate checks by pixels.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import address_skill_v1 as S
from canonical.runtime import address_v1 as A
from canonical.runtime import parameterise_v1 as P


# ------------------------------------------------------------------ the boundary

def test_addressing_may_not_touch_anything_that_decides_or_acts():
    for forbidden in ("Runtime.evaluate", "Page.navigate", "Page.captureScreenshot",
                      "Input.dispatchMouseEvent", "DOM.setAttributeValue",
                      "DOM.querySelector", "Accessibility.getAXNodeAndAncestors"):
        assert forbidden not in A.ALLOWED_ADDRESSING, forbidden


def test_every_allowed_method_is_a_read():
    for m in A.ALLOWED_ADDRESSING:
        assert m.split(".")[0] in {"DOM", "Accessibility", "Page"}
        assert not any(v in m for v in ("set", "insert", "remove", "navigate", "capture")), m


def test_a_forbidden_call_raises_rather_than_being_filtered():
    """A filter can be forgotten in one code path. An exception cannot."""
    a = A.Address.__new__(A.Address)
    a.i, a.sent, a.ws = 0, [], None
    with pytest.raises(A.AddressingError):
        a.call("Runtime.evaluate", {"expression": "1+1"})
    with pytest.raises(A.AddressingError):
        a.call("Page.navigate", {"url": "http://evil"})


# ------------------------------------------------------------------ the skill

SKILL = None


def _skill():
    global SKILL
    if SKILL is None:
        SKILL = S.teach("show only the urgent messages", [
            {"action": "click", "role": "textbox", "name": "filter"},
            {"action": "type", "role": "textbox", "name": "filter", "text": "urgent"},
            {"action": "click", "role": "button", "name": "APPLY"},
        ])
    return SKILL


def test_a_skill_stores_roles_and_names_not_coordinates():
    for s in _skill()["steps"]:
        assert "role" in s and "name" in s
        assert "x" not in s and "y" not in s


def test_the_taught_value_becomes_a_slot():
    sk = _skill()
    assert sk["slots"][0]["taught_value"] == "urgent"
    typed = [s for s in sk["steps"] if s["action"] == "type"]
    assert typed[0]["text"] == "{slot0}"


def test_a_new_goal_fills_the_slot_with_its_own_parameter():
    for goal, want in {"show only the messages about refund": "refund",
                       "show only messages from alice": "alice",
                       "show only the invoice messages": "invoice"}.items():
        r = S.fill(_skill(), goal)
        assert r["verdict"] == "FILLED", goal
        typed = [s["text"] for s in r["steps"] if s["action"] == "type"]
        assert typed == [want], (goal, typed)


def test_an_unfillable_goal_is_refused_not_guessed():
    r = S.fill(_skill(), "show me the things")
    assert r["verdict"] == "CANNOT_FILL"


def test_a_missing_target_stops_the_run_before_acting():
    """A skill addressed by name must refuse when the page has no such name -- not fall back
    to coordinates, and not click the nearest thing."""
    class NoSuchPage:
        def screenshot(self, p):
            pathlib.Path(p).write_bytes(b"")
        def click(self, x, y):
            raise AssertionError("must not click")
        class c:
            @staticmethod
            def call(m, p=None):
                raise AssertionError("must not dispatch")
    class EmptyAddress:
        pass

    import canonical.runtime.address_v1 as AV
    orig = AV.find
    AV.find = lambda *a, **k: None
    try:
        out = S.run(_skill(), EmptyAddress(), NoSuchPage())
    finally:
        AV.find = orig
    assert out["verdict"] == "REFUSED_TARGET_NOT_ON_PAGE"
    assert out["at_step"] == 1


# ------------------------------------------------------------------ the lesson

def test_the_three_signals_are_used_for_three_different_jobs():
    """The whole design, asserted: model decides, page addresses, gate verifies."""
    from canonical.runtime import act_loop_v1 as L
    # the gate still knows nothing about the page tree
    assert not hasattr(L, "Accessibility")
    # and the addresser knows nothing about what a goal is
    import inspect
    src = inspect.getsource(A)
    for word in ("goal", "decide", "choose", "intent"):
        assert word not in src.lower().replace("decision_domains", "").replace(
            "deciding by vision", "").replace("decides", ""), word
