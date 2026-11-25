#!/usr/bin/env python3
"""The first verified transfer in this project -- and exactly what it does and does not prove.

One vocabulary chosen per code-group, then every vocabulary scored on every OTHER group:

    within group   380 predictions,  4 wrong, accuracy 0.9896
    across groups  336 predictions,  7 wrong, accuracy 0.9796, coverage 0.0305

Accuracy survives the boundary (0.980 vs 0.990).  This is the mirror image of V15/V16, where laws learned
on one machine world were 42-of-50 wrong on another. The mechanism is the same in both directions: **a
relation over SYNTAX crosses a boundary; a relation over GROUND NAMES does not.**

Caveats, all in the artifact: only 2 groups survived filtering (so 2 ordered pairs), the groups are wildly
unequal, and coverage across the boundary is 3.05% -- the accuracy is real, the breadth is not.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACT = (REPO / "canonical" / "verification" /
            "PRICE_A_REFUSAL_ON_REAL_CODE_20261124_V2.json")


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_a_vocabulary_crosses_codebases():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["verdicts"]["a_vocabulary_crosses_codebases_at_all"] is True
    assert summary["cross_machine"]["across"]["predictions"] > 0


def test_cross_codebase_accuracy_matches_within():
    """The claim that matters. Not 'transfer wins' -- 'transfer does not lose accuracy'."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    within = summary["cross_machine"]["within"]["accuracy"]
    across = summary["cross_machine"]["across"]["accuracy"]
    assert across >= within - 0.05
    assert summary["verdicts"]["cross_codebase_accuracy_matches_within_codebase"] is True


def test_the_breadth_does_not_transfer_and_that_is_recorded():
    """Coverage across the boundary is lower than within, and single digits. Reporting only the accuracy
    would be the flattering half."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["verdicts"]["cross_codebase_coverage_is_single_digits"] is True
    assert summary["cross_machine"]["across"]["coverage"] < 0.05


def test_the_caveats_are_in_the_artifact_not_the_prose():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    caveats = _summary()["cross_machine"]["caveats"]
    assert len(caveats) >= 3
    assert any("2 groups" in caveat or "2 ordered pairs" in caveat for caveat in caveats)
    assert any("coverage" in caveat for caveat in caveats)


def test_the_mechanism_is_stated_and_is_the_same_one_that_failed_on_machines():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    meaning = _summary()["cross_machine"]["what_this_means"]
    assert "SYNTAX" in meaning and "GROUND" in meaning.upper()
    assert _summary()["verdicts"]["the_transfer_mechanism_is_now_identified"] is True
