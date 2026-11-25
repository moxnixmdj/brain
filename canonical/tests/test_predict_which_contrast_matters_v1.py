#!/usr/bin/env python3
"""The store carries evidence, not inference. Binding was proven; prediction is refused by the data.

40 contrasts considered, 28 with ground truth from intervention, 4 of 28 (14%) moved a test outcome.

    rule (on held-out functions)          accuracy  sensitivity  precision
    learned single signal                  0.7857       0.00       0.00
    always "does not matter"               0.7857       0.00       0.00
    STATIC: at_position                    0.5000       1.00       0.30
    majority-class baseline                0.7857

The learned rule flags NOTHING and ties the majority classifier exactly. The static one-line rule is the
only one that catches any positive (3 of 3) and its precision of 0.30 makes it useless for acting on.

An earlier version of this metric called 0.7857 a success. That was the majority class -- the V25 error,
reproduced in my own evaluation code one round after writing the report about it. Sensitivity and precision
are now mandatory in the score.
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACT = (REPO / "canonical" / "verification" /
            "PREDICT_WHICH_CONTRAST_MATTERS_20261124_V1.json")


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_the_learned_rule_has_no_sensitivity():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    learned = summary["test"]["learned"]
    assert learned["sensitivity"] == 0.0
    assert learned["flagged"] == 0
    assert summary["verdicts"]["the_learned_rule_has_any_sensitivity"] is False


def test_the_learned_rule_only_ties_the_majority_class():
    """The check that stops a majority-class tie from being reported as prediction."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    learned = _summary()["test"]["learned"]
    assert learned["accuracy"] == learned["majority_class_accuracy"]
    assert _summary()["verdicts"]["the_store_can_predict_which_contrast_matters"] is False


def test_the_static_rule_catches_all_positives_but_is_imprecise():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    static = _summary()["test"]["static_at_position"]
    assert static["sensitivity"] == 1.0
    assert static["precision"] < 0.5
    assert _summary()["verdicts"]["the_static_rule_is_precise_enough_to_use"] is False


def test_the_ground_truth_is_small_and_says_so():
    """28 of 40 with truth, 4 positive. Reporting 4 as if it were a distribution would be dishonest."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert 20 <= summary["contrasts_with_ground_truth"] <= 40
    positives = summary["test"]["learned"]["positives"]
    assert positives <= 5
    assert "NOT INFERENCE" in summary["honest_reading"]
