"""The oracle could not see a GUI. Now it can -- exactly, not approximately.

Measured 2026-11-09: verify_postcondition had 10 kinds, all byte/row equality
(file, json, sqlite, http, stdout). None could read a screen. That is the reason
the computer-use family, compressed to the single leaf
BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001, has a verified mechanism and zero
terminal results.

The fix is not vision. It is the accessibility tree: exact, cheap, deterministic,
diffable. External convergence in 2026 is total -- Vercel agent-desktop acts on UIA
refs and re-snapshots to confirm; Playwright MCP's stated design rule is that every
state-changing action carries a postcondition checked against the a11y snapshot.

These tests are the false-positive tests. A verifier that only accepts is not one.
"""
from __future__ import annotations

import copy
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    _sabotage_world,
    _ui_nodes,
    verify_postcondition,
)

TREE = {"nodes": [
    {"role": "window", "name": "Settings", "automation_id": "w1"},
    {"role": "button", "name": "Save", "automation_id": "b1", "enabled": True},
    {"role": "textbox", "name": "Search", "automation_id": "t1", "value": "quarterly report"},
    {"role": "checkbox", "name": "Enable sync", "automation_id": "c1", "checked": True},
    {"role": "heading", "name": "Order confirmed #4471", "automation_id": "h1"},
]}


def _check(pc, tree=TREE):
    pc = dict(pc)
    if tree is not None:
        pc.setdefault("ui_tree", tree)
    return verify_postcondition(pc)


# ---- true positives: the oracle must ACCEPT real states --------------------

def test_element_present():
    ok, why = _check({"kind": "ui_element_present", "match": {"role": "button", "name": "Save"}})
    assert ok, why


def test_element_absent():
    ok, why = _check({"kind": "ui_element_absent", "match": {"role": "button", "name": "Delete"}})
    assert ok, why


def test_value_equals():
    ok, why = _check({"kind": "ui_value_equals",
                      "match": {"role": "textbox", "name": "Search"}, "equals": "quarterly report"})
    assert ok, why


def test_text_contains():
    ok, why = _check({"kind": "ui_text_contains", "contains": "Order confirmed"})
    assert ok, why


def test_state_equals():
    ok, why = _check({"kind": "ui_element_state_equals",
                      "match": {"automation_id": "c1"}, "state": "checked", "equals": True})
    assert ok, why


# ---- false positives: the oracle must REFUSE ------------------------------

def test_absent_element_is_not_reported_present():
    ok, why = _check({"kind": "ui_element_present", "match": {"role": "button", "name": "Delete"}})
    assert not ok and why == "POSTCONDITION_UI_ELEMENT_ABSENT"


def test_present_element_is_not_reported_absent():
    ok, why = _check({"kind": "ui_element_absent", "match": {"role": "button", "name": "Save"}})
    assert not ok and why == "POSTCONDITION_UI_ELEMENT_STILL_PRESENT"


def test_stale_value_is_rejected():
    ok, why = _check({"kind": "ui_value_equals",
                      "match": {"role": "textbox", "name": "Search"}, "equals": "old value"})
    assert not ok and why.startswith("POSTCONDITION_UI_VALUE_MISMATCH")


def test_wrong_state_is_rejected():
    ok, why = _check({"kind": "ui_element_state_equals",
                      "match": {"automation_id": "c1"}, "state": "checked", "equals": False})
    assert not ok and why.startswith("POSTCONDITION_UI_STATE_MISMATCH")


def test_absent_text_is_rejected():
    ok, why = _check({"kind": "ui_text_contains", "contains": "Payment failed"})
    assert not ok and why == "POSTCONDITION_UI_TEXT_MISSING"


# ---- blindness must be reported, never passed -----------------------------

def test_missing_tree_is_unavailable_not_success():
    ok, why = verify_postcondition({"kind": "ui_element_present", "match": {"name": "Save"}})
    assert not ok and why == "POSTCONDITION_UI_TREE_UNAVAILABLE"


def test_a_string_is_not_an_empty_tree():
    """str IS a Sequence. Accepting one turns 'could not look' into 'found nothing'."""
    assert _ui_nodes({"ui_tree": "oops"}, None) is None
    assert _ui_nodes({"ui_tree": b"oops"}, None) is None
    assert _ui_nodes({"ui_tree": None}, None) is None


def test_an_empty_tree_is_a_real_observation():
    """Distinct from blindness: looking and finding nothing is a finding."""
    assert _ui_nodes({"ui_tree": []}, None) == []
    ok, why = _check({"kind": "ui_element_present", "match": {"name": "Save"}}, tree=[])
    assert not ok and why == "POSTCONDITION_UI_ELEMENT_ABSENT"


# ---- the sabotage control: the oracle must be able to say NO --------------

def test_sabotage_makes_a_present_element_vanish_and_the_oracle_notices():
    pc = {"kind": "ui_element_present", "match": {"role": "button", "name": "Save"},
          "ui_tree": copy.deepcopy(TREE)}
    assert verify_postcondition(pc)[0] is True
    assert _sabotage_world(pc, pathlib.Path("/tmp")) is True
    assert verify_postcondition(pc)[0] is False


def test_sabotage_makes_an_absent_element_appear_and_the_oracle_notices():
    pc = {"kind": "ui_element_absent", "match": {"role": "button", "name": "Delete"},
          "ui_tree": copy.deepcopy(TREE)}
    assert verify_postcondition(pc)[0] is True
    assert _sabotage_world(pc, pathlib.Path("/tmp")) is True
    assert verify_postcondition(pc)[0] is False


def test_matching_is_on_semantics_never_coordinates():
    """A tree node with coordinates but no role/name must not match a semantic selector."""
    nodes = [{"role": "button", "name": "Save", "x": 100, "y": 200}]
    pc = {"kind": "ui_element_present", "match": {"x": 100}, "ui_tree": {"nodes": nodes}}
    ok, _ = verify_postcondition(pc)
    assert not ok, "coordinate matching must never satisfy a semantic selector"


# ---- the whole loop: record pixels -> compile to semantics -> verify ------

PORTAL_DOM = [
    {"role": "textbox", "name": "Amount", "automation_id": "amt",
     "bbox": {"x": 400, "y": 220, "width": 120, "height": 30}},
    {"role": "button", "name": "Submit", "automation_id": "sub",
     "bbox": {"x": 800, "y": 630, "width": 80, "height": 24}},
]


def test_a_pixel_trace_elevates_to_a_stable_semantic_program():
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import elevate_trace_to_fastest_layer
    out = elevate_trace_to_fastest_layer({
        "goal": "submit the expense report",
        "steps": [
            {"type": "click", "x": 412, "y": 236, "layer": "pixel_ui"},
            {"type": "type", "text": "412.18", "layer": "pixel_ui", "target_label": "Amount"},
            {"type": "click", "x": 812, "y": 640, "layer": "pixel_ui"},
        ],
        "dom_elements": PORTAL_DOM,
    })
    assert out["dominant_layer"] == "semantic_dom"
    steps = out["elevated_steps"]
    assert [s.get("op") for s in steps] == ["CLICK_SEMANTIC", "FILL_SEMANTIC", "CLICK_SEMANTIC"]
    # no coordinate may survive into the compiled program
    for s in steps:
        assert "x" not in s and "y" not in s
    # the stable automation id must survive, or the skill breaks on relayout
    assert steps[0]["selector"]["automation_id"] == "amt"
    assert steps[1]["value"] == "412.18"


def test_a_keystroke_with_no_coordinates_still_keeps_its_semantics():
    """A `type` step has no x/y. Dropping to pixel_ui there loses the whole program."""
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import elevate_trace_to_fastest_layer
    out = elevate_trace_to_fastest_layer({
        "steps": [{"type": "type", "text": "hello", "layer": "pixel_ui", "target_label": "Search"}],
        "dom_elements": [{"role": "textbox", "name": "Search", "automation_id": "s1"}],
    })
    assert out["elevated_steps"][0]["layer"] == "semantic_dom"
    assert out["elevated_steps"][0]["selector"]["automation_id"] == "s1"


def test_the_compiled_program_can_be_verified_semantically_end_to_end():
    """Record once -> compile -> run -> CHECK. The check is what closes the loop."""
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import elevate_trace_to_fastest_layer
    out = elevate_trace_to_fastest_layer({
        "steps": [
            {"type": "type", "text": "412.18", "layer": "pixel_ui", "target_label": "Amount"},
            {"type": "click", "x": 812, "y": 640, "layer": "pixel_ui"},
        ],
        "dom_elements": PORTAL_DOM,
    })
    assert out["dominant_layer"] == "semantic_dom"

    post_run = {"nodes": [
        {"role": "textbox", "name": "Amount", "automation_id": "amt", "value": "412.18"},
        {"role": "banner", "name": "Report submitted", "automation_id": "ok"},
    ]}
    ok, why = verify_postcondition({"kind": "ui_value_equals", "match": {"automation_id": "amt"},
                                    "equals": "412.18", "ui_tree": post_run})
    assert ok, why
    ok, why = verify_postcondition({"kind": "ui_element_present",
                                    "match": {"role": "banner", "name": "Report submitted"},
                                    "ui_tree": post_run})
    assert ok, why

    # And the same checks must FAIL against the pre-run tree.
    pre_run = {"nodes": [{"role": "textbox", "name": "Amount", "automation_id": "amt", "value": ""}]}
    ok, _ = verify_postcondition({"kind": "ui_value_equals", "match": {"automation_id": "amt"},
                                  "equals": "412.18", "ui_tree": pre_run})
    assert not ok
    ok, _ = verify_postcondition({"kind": "ui_element_present",
                                  "match": {"role": "banner", "name": "Report submitted"},
                                  "ui_tree": pre_run})
    assert not ok
