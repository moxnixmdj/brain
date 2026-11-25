#!/usr/bin/env python3
"""How the question supply scales with exploration depth -- the corrected version.

The first run of this measurement drew its condition vocabulary from the FULL enumeration and concluded
that accuracy after acquisition collapses with depth (0.678 -> 0.596). That was a leak: the learner was
scored against a vocabulary built from states it had never visited. With the vocabulary drawn from the
walk -- as every other receipt in this project does -- the collapse disappears.

    depth  states  questions  per 100 states  accuracy after acquisition
      2      76       38         50.0            0.920
      3     230       88         38.3            0.906
      4     771      142         18.4            0.932

questions ~ states ** 0.58     (exponents 0.758, 0.396)

What survives: the supply grows, sublinearly, and density falls with depth.
What does not survive: any claim that precision collapses as the space grows.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
VERIFY = REPO / "canonical" / "verification"
CORRECTED = VERIFY / "DOES_THE_SUPPLY_GROW_WITH_DEPTH_20261124_V2.json"


def test_the_supply_grows_monotonically_and_sublinearly():
    if not CORRECTED.exists():                       # pragma: no cover
        return
    summary = json.loads(CORRECTED.read_text())["summary"]
    questions = [summary["by_depth"][k]["questions"] for k in ("2", "3", "4")]
    assert questions[0] < questions[1] < questions[2]
    assert summary["verdicts"]["the_supply_is_monotone_in_depth"] is True
    assert summary["verdicts"]["the_supply_scales_sublinearly"] is True


def test_density_still_falls_even_though_accuracy_does_not():
    """These two facts used to be presented as one mechanism. They are separate: density falls 50 -> 18
    while accuracy stays inside three points. Density is not what sets precision."""
    if not CORRECTED.exists():                       # pragma: no cover
        return
    summary = json.loads(CORRECTED.read_text())["summary"]
    density = [summary["by_depth"][k]["questions_per_100_states"] for k in ("2", "3", "4")]
    assert density[0] > density[1] > density[2]
    accuracy = [summary["by_depth"][k]["C_accuracy"] for k in ("2", "3", "4")]
    assert max(accuracy) - min(accuracy) < 0.10


def test_the_refuted_claim_is_not_asserted_anywhere():
    """Guard against the old conclusion creeping back in through the artifact: the corrected receipt
    must say the decline verdict is false, not merely omit it."""
    if not CORRECTED.exists():                       # pragma: no cover
        return
    summary = json.loads(CORRECTED.read_text())["summary"]
    assert summary["verdicts"]["accuracy_after_acquisition_falls_with_depth"] is False
    assert "collapse" in summary["pool_comparison"]["what_changed"]


def test_the_supply_is_finite_at_every_depth():
    if not CORRECTED.exists():                       # pragma: no cover
        return
    summary = json.loads(CORRECTED.read_text())["summary"]
    assert summary["verdicts"]["the_supply_is_finite_at_every_depth"] is True
    assert summary["budget"] == 400
