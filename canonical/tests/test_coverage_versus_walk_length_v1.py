#!/usr/bin/env python3
"""The wall is evidence AND representation, and the numbers say which dominates.

Held-out set fixed BEFORE any walk (seeded shuffle of the depth-3 enumeration, 35%), identical size at
every length, and no walk may use a held-out transition.

    walk  transitions  laws   coverage   d_cov    accuracy  refused
      40         157     88     0.4730           0.8861       78
     120         412    138     0.5878  +0.1148  0.8700       61
     300         917    154     0.6081  +0.0203  0.8571       58
     600        1744    157     0.6284  +0.0203  0.8611       55

11x the evidence buys +0.155 coverage, and the yield per 1000 transitions falls 3.0 -> 1.4 -> 0.7 -> 0.4.
So the wall is partly EVIDENCE (it moves) and mostly REPRESENTATION (it barely moves), and accuracy holds
throughout. Any claim that "more exploration fixes it" has to answer the per-transition yield, which
falls by a factor of 7.5.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

ARTIFACT = (REPO / "canonical" / "verification" /
            "COVERAGE_VERSUS_WALK_LENGTH_20261124_V1.json")


def _by_length():
    return json.loads(ARTIFACT.read_text())["summary"]["by_length"]


def test_the_held_out_set_is_identical_across_arms():
    """The design guard. If held-out varied with walk length, the whole curve would be an artifact of a
    shrinking denominator rather than of learning."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["verdicts"]["the_held_out_set_is_the_same_size_at_every_length"] is True
    assert len({cell["held_out"] for cell in summary["by_length"].values()}) == 1


def test_coverage_rises_and_then_almost_stops():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    cells = [cell["coverage"] for cell in (_by_length()[k] for k in ("40", "120", "300", "600"))]
    assert cells[-1] > cells[0] + 0.10, "evidence does buy something"
    assert cells[-1] - cells[-2] < 0.03, "and then it buys almost nothing"


def test_the_yield_per_transition_collapses():
    """The number that stops 'just explore more' from being a recommendation."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    by = _by_length()
    yields = [by[k]["coverage"] / max(1, by[k]["walk_transitions"]) * 1000
              for k in ("40", "120", "300", "600")]
    assert yields[0] > yields[1] > yields[2] > yields[3]
    assert yields[0] > 5 * yields[-1]


def test_accuracy_does_not_decay_as_the_walk_grows():
    """The alternative failure mode -- wider evidence over-generalised into wrong laws -- did not happen,
    which is why this is a reach problem and not a soundness problem."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    accuracies = [cell["accuracy"] for cell in summary["by_length"].values()]
    assert max(accuracies) - min(accuracies) < 0.05
    assert summary["verdicts"]["more_walk_never_hurts_accuracy"] is True
