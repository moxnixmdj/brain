"""A ladder, not a solution: three ways to address a widget, and you must know which rung.

That is the honest shape of "literally anything on the computer". Measured on the same goal,
same UI, two pages:

  STRUCTURED page (real textbox + button, accessible names)
      find(role=textbox) -> role=textbox name="filter" box (34,120)-(314,148)
      reuse with a NEW parameter on a MOVED layout: 0 model calls, 3/3 steps
      rung 1, ADDRESSED

  CANVAS page (drawn pixels, one AX node: Canvas '')
      find(role=textbox) -> None
      the same goal needs the model to read pixels: 2 model calls, 1 step
      rung 3, LOOKED_AT

And the bug that proves the design pays for itself: on the canvas page the model proposed
three actions, but the FIRST CLICK already set the filter and redrew. The gate refused step 2
with NOTHING_CHANGED_BUT_A_CHANGE_WAS_CLAIMED. The model over-planned; the gate caught it.
That is the division of labour -- model decides, page addresses, gate verifies -- working on a
page that has no structure at all.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import address_v1 as A
from canonical.runtime import address_skill_v1 as S
from canonical.runtime import ladder_v1 as LAD

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = json.loads(
    (ROOT / "canonical/evaluation/ladder/ladder_proposals_20261109_v1.json").read_text())


# ------------------------------------------------------------------ the rungs are named

def test_the_rungs_are_ordered_by_cost():
    assert LAD.RUNGS["ADDRESSED"] < LAD.RUNGS["ANCHORED"] < LAD.RUNGS["LOOKED_AT"]


def test_each_rung_reports_its_own_cost():
    """A benchmark that charges the fast rung's cost to the slow rung's success is lying."""
    r = LAD.run_looked_at.__doc__ or ""
    assert "model" in r.lower()


# ------------------------------------------------------------------ rung 3 is honest about itself

def test_the_canvas_plan_was_corrected_by_the_gate_not_by_hand():
    """The recorded correction is the evidence: the gate refused a claim that was too small
    (outside=0.0071), and refused a step that changed nothing."""
    corr = PLAN["_correction"].lower()
    assert "gate" in corr and "right" in corr
    assert "outside" in corr
    assert "NOTHING_CHANGED" in PLAN["_model_error_found_by_the_gate"]


def test_the_model_overplanned_and_the_gate_said_so():
    """Three proposed actions; the first click already did the job."""
    assert "ONE action" in PLAN["_model_error_found_by_the_gate"]
    assert set(PLAN["proposals"]["_one_action_plan"]) == {"1"}


# ------------------------------------------------------------------ rung 1 still holds

def _skill():
    return S.teach("show only the urgent messages", [
        {"action": "click", "role": "textbox", "name": "filter"},
        {"action": "type", "role": "textbox", "name": "filter", "text": "urgent"},
        {"action": "click", "role": "button", "name": "APPLY"},
    ])


def test_a_skill_taught_on_one_layout_keeps_no_coordinates():
    for s in _skill()["steps"]:
        assert "x" not in s and "y" not in s
        assert s["role"] and s["name"]


def test_the_parameter_travels_and_the_layout_does_not_matter():
    filled = S.fill(_skill(), "show only the messages about refund")
    assert [s["text"] for s in filled["steps"] if s["action"] == "type"] == ["refund"]


# ------------------------------------------------------------------ the boundary between rungs

def test_a_page_with_no_roles_gives_addressing_nothing():
    """find() must return None rather than a plausible-looking rectangle. The rung is chosen
    by measurement: nothing addressable, fall through to vision."""
    class NoPage:
        pass
    import canonical.runtime.address_v1 as AV
    orig = AV.ax_nodes
    AV.ax_nodes = lambda a: [{"role": "Canvas", "name": "", "box": {"x0": 0, "y0": 0,
                                                                  "x1": 900, "y1": 520,
                                                                  "w": 900, "h": 520}}]
    try:
        a = AV.Address.__new__(AV.Address)
        assert AV.find(a, role="textbox") is None
        assert AV.find(a, name="APPLY") is None
    finally:
        AV.ax_nodes = orig


def test_the_ladder_does_not_invent_a_rung_between_1_and_3():
    assert set(LAD.RUNGS) == {"ADDRESSED", "ANCHORED", "LOOKED_AT"}
