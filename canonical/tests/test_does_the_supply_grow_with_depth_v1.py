#!/usr/bin/env python3
"""How the question supply scales -- the first law in this body of work with an exponent.

Measured across depths 2, 3, 4 on ten machines:

    depth  states  questions  per 100 states  accuracy after acquisition
      2      77       51         66.2            0.678
      3     231       72         31.2            0.618
      4     767      131         17.1            0.596

questions ~ states ** 0.41   (exponents 0.314 then 0.499)

Supply grows without bound but SUBLINEARLY, and accuracy after acquisition FALLS with depth, because
each new question lands in a region where the walk has less evidence.
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
            "DOES_THE_SUPPLY_GROW_WITH_DEPTH_20261124_V1.json")


def test_the_supply_grows_but_the_density_collapses():
    """Both halves, together. Reporting only the growth would hide that deeper exploration is a worse
    return per state -- which is the part that matters for a real environment."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    by_depth = summary["by_depth"]
    assert by_depth["4"]["questions"] > by_depth["2"]["questions"]
    assert by_depth["4"]["questions_per_100_states"] < by_depth["2"]["questions_per_100_states"] / 3
    assert summary["verdicts"]["the_density_does_not_collapse"] is False


def test_the_exponent_is_measured_and_sublinear():
    """A sublinear exponent means each additional state costs MORE questions to reach, which is the
    opposite of the intuition that more exploration buys proportionally more understanding."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    scaling = json.loads(ARTIFACT.read_text())["summary"]["scaling"]
    assert 0.2 < scaling["mean_exponent"] < 0.7
    assert all(0.0 < e < 1.0 for e in scaling["exponents"]), "no exponent may be superlinear"


def test_accuracy_after_acquisition_falls_with_depth():
    """The measurement that stops 'explore deeper' from being a free recommendation."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    by_depth = json.loads(ARTIFACT.read_text())["summary"]["by_depth"]
    accuracies = [by_depth[k]["C_accuracy"] for k in ("2", "3", "4")]
    assert accuracies[0] > accuracies[1] > accuracies[2], (
        "each extra depth costs accuracy, and that must stay visible")


def test_the_supply_is_finite_at_every_depth():
    """No depth made the supply exceed the 400-probe budget: it is always exhaustible, which is what
    makes 'explore until the supply stops growing' a usable rule."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["verdicts"]["the_supply_is_finite_at_every_depth"] is True
    assert summary["budget"] == 400
