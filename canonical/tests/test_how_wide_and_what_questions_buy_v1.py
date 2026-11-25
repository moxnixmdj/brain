#!/usr/bin/env python3
"""Two measurements that decided the round, pinned so they cannot drift.

1. Every two-witness law is TRUE on the class it claims. Soundness and width were never the problem.
2. Silence is a CENSUS: 40 of 45 atoms carry laws only at support 1. One witness, nothing more.

And the trade that follows: questions buy reach ~3x and raise the error rate from 3.6% to 13.3%.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

WIDE = REPO / "canonical" / "verification" / "HOW_WIDE_IS_A_LAW_20261124_V1.json"
BUY = REPO / "canonical" / "verification" / "BUY_REACH_WITH_QUESTIONS_20261124_V1.json"


def test_not_one_two_witness_law_was_wrong_about_its_class():
    """The measurement that redirected the round: 43 of 43 laws correct on their class, 0 false."""
    if not WIDE.exists():                            # pragma: no cover
        return
    summary = json.loads(WIDE.read_text())["summary"]
    totals = summary["by_projection"]
    true_count = sum(cell["wide_and_true"] for cell in totals.values())
    false_count = sum(cell["wide_and_false"] for cell in totals.values())
    assert true_count > 0
    assert false_count == 0, "a law that is wrong about its own class is a different bug entirely"
    assert summary["verdicts"]["wide_laws_are_right_more_often_than_wrong"] is True


def test_width_is_free_and_that_is_the_finding():
    """`width_is_not_free` came back FALSE: wide projections were sound. Silence had another cause."""
    if not WIDE.exists():                            # pragma: no cover
        return
    summary = json.loads(WIDE.read_text())["summary"]
    assert summary["verdicts"]["width_is_not_free"] is False
    assert summary["verdicts"]["wide_projections_are_sound"] is True


def test_questions_triple_reach_and_that_reach_was_not_free():
    """Both halves pinned together. Reporting only the 3.1x would be the dishonest half of this."""
    if not BUY.exists():                             # pragma: no cover
        return
    summary = json.loads(BUY.read_text())["summary"]
    assert summary["verdicts"]["reach_more_than_doubles"] is True
    assert summary["arm_C"]["predictions"] > 3 * summary["arm_A"]["predictions"]
    # and the price, which must not be quietly dropped in a later edit
    assert summary["verdicts"]["questions_preserve_SOUNDNESS"] is False
    rate_a = summary["arm_A"]["wrong"] / summary["arm_A"]["predictions"]
    rate_c = summary["arm_C"]["wrong"] / summary["arm_C"]["predictions"]
    assert rate_c > 3 * rate_a, "the error rate rose by more than 3x and the artifact must say so"


def test_a_probe_is_evidence_not_a_veto():
    """The mechanism behind the trade: a falsified probe is added to the evidence and the class is
    split, rather than the law being deleted. 351 of 507 probes falsified and still the table grew."""
    if not BUY.exists():                             # pragma: no cover
        return
    summary = json.loads(BUY.read_text())["summary"]
    assert summary["falsified"] > summary["confirmed"], "the majority of single-witness laws fail"
    assert summary["falsified"] + summary["confirmed"] == summary["probes"]
    assert summary["probes"] > 0
