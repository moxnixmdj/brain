#!/usr/bin/env python3
"""Two walls, measured separately. The one that is closed decides what is worth building.

Wall 1, the front door: `solve(goal, mode="EPISTEMIC")` refuses a goal whose tokens the model does not
recognise, before any work happens. On 80 real SWE-bench Verified issue texts it refuses 52 (65%), and a
goal with NO content scores higher than any real issue:

    "In more_itertools, chunked(iterable, n) raises ZeroDivisionError when n=0 ..."   coverage 0.000  REFUSED
    "Fix the bug in the function so the test passes."                                 coverage 0.833  ROUTED

Wall 2, the back door: with no container attached the transport returns before any action can exist.

The measured consequence, which is the point of the artifact: because wall 2 is closed, raising wall-1
acceptance from 28/80 to 80/80 would change no outcome. Therefore the next object to work on is the
generator, not the gate.

A hypothesis I had and the data refuted: that the refusal was caused by reporters' environment vocabulary
(paths, tracebacks, hashes, code spans). That share is 7.95% of the ask, and excluding it entirely lifts
acceptance by only 3 instances. The refusal is not about the reporter's noise; it is about the model's
vocabulary -- 1,729 index terms across 447 capabilities, a median of 7 per capability.
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
WALL = REPO / "canonical" / "verification" / "WHICH_WALL_IS_CLOSED_20261124_V1.json"
GATE = REPO / "canonical" / "verification" / "IS_THE_GATE_MEASURING_THE_TASK_20261124_V1.json"


def _wall():
    return json.loads(WALL.read_text())["summary"]


def _gate():
    return json.loads(GATE.read_text())["summary"]


def test_the_front_door_refuses_a_majority_of_real_issues():
    if not WALL.exists():                            # pragma: no cover
        return
    front = _wall()["wall_1_front_door"]
    assert front["refused"] > front["accepted"]
    assert front["refusal_rate"] > 0.5
    assert _wall()["verdicts"]["the_front_door_refuses_a_majority_of_real_issues"] is True


def test_the_router_is_a_small_decision_wearing_many_arms():
    if not WALL.exists():                            # pragma: no cover
        return
    conc = _wall()["routing_concentration"]
    assert conc["capabilities"] == 447
    assert conc["capabilities_that_never_win_a_real_issue"] > 400
    assert conc["share_that_never_win"] > 0.9
    assert conc["median_terms_per_capability"] <= 8


def test_the_back_door_is_measured_and_closed_without_a_container():
    """If this ever stops being BLOCKED, wall 2 is open and the front door becomes worth fixing first."""
    if not WALL.exists():                            # pragma: no cover
        return
    back = _wall()["wall_2_back_door"]
    assert str(back["status"]).startswith("BLOCKED")
    assert back["patch_emitted"] is False


def test_my_environment_vocabulary_hypothesis_stays_refuted():
    """The defect is the model's vocabulary, not the reporter's. Recorded so it is not re-proposed."""
    if not GATE.exists():                            # pragma: no cover
        return
    gate = _gate()
    assert gate["verdicts"]["environmental_vocabulary_is_a_material_part_of_a_real_ask"] is False
    assert gate["B_cause"]["median_share_of_ask_tokens_rooted_in_the_reporters_environment"] < 0.15
    assert gate["C_candidate_gate"]["additional_requests_accepted"] <= 5


def test_no_improvement_is_claimed_from_raising_acceptance():
    if not GATE.exists():                            # pragma: no cover
        return
    assert _gate()["verdicts"]["improvement_is_established"] is False
    # the phrase is "what this does NOT show" -- assert on its content, not on a word I hoped for
    assert "no patch was produced" in _gate()["what_this_does_not_show"].lower()
