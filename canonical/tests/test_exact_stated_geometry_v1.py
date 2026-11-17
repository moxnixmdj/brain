"""Exact stated geometry: the unrounded rectangle and canvas attributes the bridge now carries,
the pointer proprioception that measures the page's own click offset, the operators that read
them, their refusals on old observations, and the additivity that keeps every previously
measured hand byte-identical."""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import aimed_action_v1 as aimed  # noqa: E402
from canonical.tools import aimed_action_measure_v1 as aim_measure  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402
from canonical.tools import exact_stated_geometry_measure_v1 as exact_measure  # noqa: E402

BRIDGE = REPO / "canonical" / "tools" / "miniwob_chromium_bridge_v1.mjs"


def element(index: int, parent: int, tag: str, **kw):
    rec = {"index": index, "parent": parent, "tag": tag, "text": "",
           "box": [0, 0, 10, 10], "can_click": False, "can_type": False}
    rec.update(kw)
    return rec


def exact_circle_observation():
    """circle-center as the bridge now reports it: one black mark stating its canvas geometry,
    the svg stating its origin, and no pointer yet (nothing has been pressed)."""
    return {
        "utterance": "Find and click on the center of the circle, then press submit.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360], box_f=[0.0, 0.0, 480.0, 360.0]),
            element(1, 0, "div", id="area", box=[0, 50, 164, 164],
                    box_f=[0.0, 50.0, 164.0, 164.0]),
            element(2, 1, "svg", id="svg-grid", box=[2, 52, 150, 130],
                    box_f=[2.0, 52.0, 150.0, 130.0]),
            element(3, 2, "circle", classes="black-circle", colour="white",
                    box=[24, 83, 74, 74], box_f=[24.0, 83.0, 74.0, 74.0],
                    geom={"cx": "59", "cy": "68", "r": "37"}, can_click=True),
            element(4, 0, "button", text="Submit", box=[30, 175, 98, 34],
                    box_f=[30.0, 175.0, 98.0, 34.0], can_click=True),
        ]}


def exact_midpoint_observation():
    return {
        "utterance": "Find the mid-point between the two points, then press submit.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360], box_f=[0.0, 0.0, 480.0, 360.0]),
            element(1, 0, "svg", id="svg-grid", box=[0, 50, 150, 130],
                    box_f=[0.0, 50.0, 150.0, 130.0]),
            element(2, 1, "circle", classes="black-circle",
                    box=[10, 70, 7, 7], box_f=[10.5, 70.5, 7.0, 7.0],
                    geom={"cx": "14", "cy": "24", "r": "3.5"}, can_click=True),
            element(3, 1, "circle", classes="black-circle",
                    box=[50, 110, 7, 7], box_f=[50.5, 110.5, 7.0, 7.0],
                    geom={"cx": "54", "cy": "64", "r": "3.5"}, can_click=True),
            element(4, 0, "button", text="Submit", box=[30, 175, 98, 34],
                    box_f=[30.0, 175.0, 98.0, 34.0], can_click=True),
        ]}


def exact_right_angle_observation():
    return {
        "utterance": "Add a third point to create a right angle, then press submit.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360], box_f=[0.0, 0.0, 480.0, 360.0]),
            element(1, 0, "svg", id="svg-grid", box=[0, 50, 480, 300],
                    box_f=[0.0, 50.0, 480.0, 300.0]),
            element(2, 1, "circle", id="init-black", classes="black-circle",
                    box=[196, 226, 7, 7], box_f=[196.5, 226.5, 7.0, 7.0],
                    geom={"cx": "200", "cy": "180", "r": "3.5"}, can_click=True),
            element(3, 1, "circle", id="init-blue", classes="black-circle",
                    box=[256, 286, 7, 7], box_f=[256.5, 286.5, 7.0, 7.0],
                    geom={"cx": "260", "cy": "240", "r": "3.5"}, can_click=True),
            element(4, 0, "button", text="Submit", box=[30, 175, 98, 34],
                    box_f=[30.0, 175.0, 98.0, 34.0], can_click=True),
        ]}


def test_exact_centre_offers_the_page_offset_the_frame_can_ask_for():
    rows = [r for r in aimed.aimed_rows(exact_circle_observation())
            if r["rule"] == "EXACT_CENTER_OF"]
    assert rows, "the exact canvas centre must be offered"
    # The page maps clicks by its own printed y-offset (50 here, under the svg top of 52) and
    # scores the mark's box against cx - RADIUS_PADDING; the optimum is (59.5, 118.5) and the
    # reachable press is its integer floor (59, 118) -- the DOM truncates pageX/pageY to long.
    assert any(r["action"] == "pressat@59,118" and r["witness"]["offset"] == 50
               for r in rows)
    offsets = {r["witness"]["offset"] for r in rows}
    assert offsets == {52, 51, 50}
    assert len(rows) <= 16, "one rule cannot drown the search in offers"


def test_exact_candidates_are_tied_to_the_input_not_stored():
    """A can-fail mutation: move the mark on the canvas, every exact candidate moves with it."""
    moved = exact_circle_observation()
    moved["elements"][3]["geom"] = {"cx": "99", "cy": "68", "r": "37"}
    rows = [r for r in aimed.aimed_rows(moved)
            if r["rule"] == "EXACT_CENTER_OF" and r["witness"]["offset"] == 50
            and r["witness"]["nudge"] == [0.0, 0.0]]
    assert rows and rows[0]["action"] == "pressat@99,118"


def test_old_observations_produce_no_exact_rows():
    """Every observation measured before this change lacks box_f/geom/pointer; there the
    operators refuse, so the previously measured hands are unchanged."""
    old = exact_circle_observation()
    for el in old["elements"]:
        el.pop("box_f", None)
        el.pop("geom", None)
    old.pop("pointer", None)
    assert not [r for r in aimed.aimed_rows(old) if r["rule"].startswith("EXACT_")]


def test_exact_midpoint_is_the_canvas_midpoint_at_each_offset():
    rows = [r for r in aimed.aimed_rows(exact_midpoint_observation())
            if r["rule"] == "EXACT_MIDPOINT_OF_TWO_POINTS"]
    # canvas centres (14, 24) and (54, 64) -> midpoint (34, 44); the page's offset 50 -> 94
    assert any(r["action"] == "pressat@34,94" and r["witness"]["offset"] == 50
               for r in rows)
    assert all(r["witness"]["points"] == [2, 3] for r in rows)
    assert len(rows) <= 16


def test_exact_right_angle_lands_on_a_perpendicular_vertex_in_canvas_coordinates():
    rows = [r for r in aimed.aimed_rows(exact_right_angle_observation())
            if r["rule"] == "EXACT_RIGHT_ANGLE_VERTEX"
            and r["witness"]["nudge"] == [0.0, 0.0]]
    assert len(rows) == 4 * 3, "four vertices at each plausible page offset"
    endpoints = [(200.0, 180.0), (260.0, 240.0)]
    offsets = set(r["witness"]["offset"] for r in rows)
    assert offsets == {50, 49, 48}   # svg top 50 and the printed constants under it
    for row in rows:
        x = float(row["action"].partition("@")[2].split(",")[0])
        y = float(row["action"].partition("@")[2].split(",")[1]) - row["witness"]["offset"]
        perpendicular = False
        for vertex in endpoints:
            other = endpoints[1] if vertex == endpoints[0] else endpoints[0]
            dot = (x - vertex[0]) * (other[0] - vertex[0]) + (y - vertex[1]) * (other[1] - vertex[1])
            if abs(dot) < 1e-9:
                perpendicular = True
        assert perpendicular, row


def test_the_page_offset_is_measured_from_the_mark_the_page_showed():
    """After one press the page shows its blue mark; with the bridge's pointer proprioception
    the printed offset is a measurement, not a guess: 52 + 120 - 119 - 3.5 = 50."""
    obs = exact_circle_observation()
    obs["pointer"] = [60.0, 120.0]
    # pressed at page y=120 with the page's offset 50: the mark sits at canvas y=70, so its
    # unrounded client top is 52 + 70 - 3.5 = 118.5 and the measurement returns 50 exactly
    obs["elements"].append(
        element(5, 2, "circle", id="blue-circle", classes="blue",
                box=[59, 119, 7, 7], box_f=[58.5, 118.5, 7.0, 7.0],
                geom={"cx": "60", "cy": "70", "r": "3.5"}, can_click=True))
    assert aimed._measured_y_offset(obs) == 50.0
    rows = aimed.aimed_rows(obs)
    nudges = [r for r in rows if r["rule"] == "EXACT_CENTER_NUDGE"]
    # the measured offset refines the family: a value the printed set did not contain
    assert any(r["witness"]["offset"] == 49.0 for r in nudges)
    # the exact floor of the optimum is offered by the family at the printed offset 50
    assert any(r["action"] == "pressat@59,118" and r["rule"] == "EXACT_CENTER_OF"
               for r in rows)


def test_rule_of_round_trips_the_exact_rules():
    rule = aimed.rule_of(exact_circle_observation(), "pressat@59,118")
    assert rule and rule["rule"] == "EXACT_CENTER_OF"
    assert rule["witness"]["offset"] == 50


def test_shipped_offered_actions_are_untouched_by_the_new_fields():
    """Additivity: the shipped hand reads neither box_f, geom nor pointer; its list is
    identical with and without them."""
    plain = exact_circle_observation()
    rich = exact_circle_observation()
    rich["pointer"] = [60.0, 120.0]
    for el in plain["elements"]:
        el.pop("box_f", None)
        el.pop("geom", None)
    assert (tool.offered_actions(plain, tool.HAND_TIER)
            == tool.offered_actions(rich, tool.HAND_TIER))


def test_decoy_stays_the_same_size_as_the_aimed_set_including_exact():
    obs = exact_circle_observation()
    aimed_rows = aimed.aimed_actions(obs)
    decoy = aimed.decoy_actions(obs, seed=exact_measure.SEED)
    assert len(decoy) == len(aimed_rows)
    assert any(a.startswith("pressat@") for a in decoy)


def test_exact_prices_lead_without_a_mark_and_finalize_closes_with_one():
    prices = exact_measure.ExactGeometryPrices()
    obs = exact_circle_observation()
    # no mark yet: the exact derivation leads, finalize waits
    assert prices(obs, "pressat@59,118") == (0, 0)
    shipped = tool.offered_actions(obs, tool.HAND_TIER)[0]
    base = tool.GuidedPrices()
    assert prices(obs, shipped) == base(obs, shipped)
    # the older derivations are paid: they can never steal a working hand's search
    old_derived = next(a for a in aimed.aimed_actions(obs)
                       if (aimed.rule_of(obs, a) or {}).get("rule") == "CENTER_OF")
    assert prices(obs, old_derived) == (1, 1)
    finalize = next(a for a in aimed.aimed_actions(obs) if a.startswith("click@")
                    and aimed.rule_of(obs, a)["rule"] == "FINALIZE_BUTTON")
    # without a mark, finalize keeps its shipped price exactly
    assert prices(obs, finalize) == base(obs, finalize)
    # a mark exists: finalize is free and every press that would move it is paid
    marked = exact_circle_observation()
    marked["elements"].append(
        element(5, 2, "circle", id="blue-circle", classes="blue",
                box=[59, 119, 7, 7], box_f=[58.5, 118.5, 7.0, 7.0],
                geom={"cx": "60", "cy": "70", "r": "3.5"}, can_click=True))
    assert prices(marked, finalize if finalize in aimed.aimed_actions(marked) else
                 next(a for a in aimed.aimed_actions(marked)
                      if (aimed.rule_of(marked, a) or {}).get("rule") == "FINALIZE_BUTTON")) == (0, 0)
    assert prices(marked, "pressat@59,118") == (1, 2)


def test_declared_tasks_and_pass_kill_are_in_the_measure_module():
    assert exact_measure.PRIMARY_TASKS == ["circle-center", "find-midpoint", "right-angle"]
    assert exact_measure.SECONDARY_TASKS == ["draw-circle", "bisect-angle"]
    assert len(exact_measure.REGRESSION_TASKS) >= 10
    declared = exact_measure.DECLARED
    assert declared["pass_primary"].startswith("on circle-center and right-angle")
    assert "even-parity seed" in declared["pass_full_reward"]
    assert "verdict regression" in declared["kill"]
    assert exact_measure.CEILING_TASKS == ["circle-center", "right-angle"]
    assert "run 3" in declared["amendment"] and "PRICES only" in declared["amendment"]


def test_bridge_declares_the_additive_fields():
    source = BRIDGE.read_text()
    assert "rec.box_f" in source and "rec.geom" in source
    assert "reply.pointer" in source and "lastPoint" in source
    # `box` stays rounded: every previously measured hand depends on it
    assert "Math.round(r.left)" in source


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_bridge_parses_under_node():
    subprocess.run(["node", "--check", str(BRIDGE)], check=True, capture_output=True)
