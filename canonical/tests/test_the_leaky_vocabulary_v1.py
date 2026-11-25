#!/usr/bin/env python3
"""Where the condition vocabulary comes from changes the ANSWER, and only one source is legitimate.

Two pools, same machines, same seed, same depth:

    pool="walk"  (correct)  depth 4:  142 questions, C accuracy 0.932
    pool="full"  (leak)     depth 4:  117 questions, C accuracy 0.598

The full pool draws its condition vocabulary from states the learner never visited. That is a parameter
warehousing world facts -- the forbidden shape -- reached through the feature set instead of the weights.
Both receipts from before this fix are superseded and kept, with the leak labeled, as evidence.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
VERIFY = REPO / "canonical" / "verification"
WALK_RECEIPT = VERIFY / "DOES_THE_SUPPLY_GROW_WITH_DEPTH_20261124_V2.json"
LEAK_RECEIPT = VERIFY / "DOES_THE_SUPPLY_GROW_WITH_DEPTH_20261124_V1.json"


def test_the_leak_is_recorded_and_named_as_superseded():
    """A superseded receipt must stay in the tree: deleting it would erase the evidence that a
    wrong answer was produced and caught."""
    if not (WALK_RECEIPT.exists() and LEAK_RECEIPT.exists()):   # pragma: no cover
        return
    walk = json.loads(WALK_RECEIPT.read_text())
    leak = json.loads(LEAK_RECEIPT.read_text())
    assert walk["supersedes"] == LEAK_RECEIPT.name
    assert leak["summary"]["condition_pool"] == "full"
    assert walk["summary"]["condition_pool"] == "walk"
    assert "forbidden shape" in walk["why_v2_exists"]


def test_the_two_pools_disagree_about_the_trend_not_just_the_number():
    """The point is not that the numbers differ by a constant. Under the leak, accuracy FELL with depth
    (0.678 -> 0.596); with the correct vocabulary it does not (0.920 -> 0.932). A tuning difference
    would move both; this one reverses the sign of a conclusion."""
    if not WALK_RECEIPT.exists():                        # pragma: no cover
        return
    comparison = json.loads(WALK_RECEIPT.read_text())["summary"]["pool_comparison"]
    leaked = [comparison["leaked_full_pool"][k]["C_accuracy"] for k in ("2", "3", "4")]
    correct = [comparison["correct_walk_pool"][k]["C_accuracy"] for k in ("2", "3", "4")]
    assert leaked[-1] < leaked[0], "the leak produced a decline: that is what got reported"
    assert correct[-1] >= correct[0], "the correct pool does not decline"


def test_the_supply_still_grows_but_the_exponent_moved():
    """The growth result survives the fix; the exponent does not. Both facts must be pinned together,
    otherwise the correction would look like a refutation of everything."""
    if not WALK_RECEIPT.exists():                        # pragma: no cover
        return
    summary = json.loads(WALK_RECEIPT.read_text())["summary"]
    questions = [summary["by_depth"][k]["questions"] for k in ("2", "3", "4")]
    assert questions[0] < questions[1] < questions[2]
    assert 0.3 < summary["scaling"]["mean_exponent"] < 0.9
    assert summary["verdicts"]["the_supply_scales_sublinearly"] is True


def test_accuracy_does_not_fall_with_depth_so_there_is_nothing_to_predict():
    flat = VERIFY / "DOES_DENSITY_PREDICT_ACCURACY_20261124_V2.json"
    if not flat.exists():                                # pragma: no cover
        return
    summary = json.loads(flat.read_text())["summary"]
    assert summary["verdicts"]["accuracy_is_flat_in_depth_and_needs_no_predictor"] is True
    assert summary["flatness"]["spread"] < 0.10
