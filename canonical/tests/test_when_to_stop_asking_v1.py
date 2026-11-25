#!/usr/bin/env python3
"""When to stop asking -- three stopping rules, and the finding that none of them bind.

Measured, 11 machines x 2 seeds, 200-probe budget:

    FIXED       157 probes, 156 predictions, 9 wrong  (0.9423 accuracy)
    ADAPTIVE     84 probes, 136 predictions, 8 wrong  (0.9371)   <- the rule I built
    PER_ATOM     62 probes,  84 predictions, 7 wrong  (0.9167)   <- "stop as soon as you know",
                                                                     the worst arm

The structural result: **every arm ran out of QUESTIONS, not budget**, at ~14 probes against a budget
of 200. So "when to stop asking" was the wrong question -- a bigger budget buys nothing, because the
supply of askable questions is what is finite.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import when_to_stop_asking_v1 as stop  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
from canonical.tools import the_width_of_a_guard_v1 as width  # noqa: E402

CONDITIONS = [("CARD", "WHOLE", None, "count_is", 1)]
ONE = (("0", "alpha"),)
NOOP = (frozenset(), frozenset())
ARTIFACT = REPO / "canonical" / "verification" / "WHEN_TO_STOP_ASKING_20261124_V1.json"


def test_accuracy_of_an_empty_table_is_zero_not_a_crash():
    """A loop that scores before it has any law must not divide by zero -- an arm that crashed would
    look like a policy difference."""
    value, score = stop.accuracy([], [])
    assert value == 0.0
    assert score["predictions"] == 0


def test_accuracy_ignores_what_the_table_refuses():
    """Accuracy is over what the table actually SAYS, so refusals must not be counted as errors --
    otherwise a silent table scores zero and honesty is punished."""
    table = [width.Law("ADD", "IDENT", ("0",), NOOP, support=2, witness=ONE)]
    observation = sam.Observation.of("ADD", ONE, ONE, CONDITIONS)
    assert observation.effect == NOOP
    value, score = stop.accuracy(table, [observation])
    assert score["predictions"] == 1 and score["wrong"] == 0 and value == 1.0


def test_every_stopping_arm_ran_out_of_questions_not_budget():
    """The structural finding, pinned. If a future change makes an arm spend its whole budget, this
    test fails and the report's claim is no longer the claim."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    budget = summary["budget"]
    for arm in ("ADAPTIVE", "FIXED", "PER_ATOM"):
        cell = summary[arm]
        assert cell["mean_probes"] < budget / 4, (
            f"{arm} spent {cell['mean_probes']} of {budget}: the question supply was the limit")
        assert cell["stopped"].get("nothing_left_to_ask", 0) > 0


def test_the_adaptive_beats_the_eager_rule_and_the_baseline_is_honest():
    """'Stop as soon as you know something' is intuitively right and measures worst. And stopping
    early must be compared against never stopping, which is why the FIXED arm exists."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    verdicts = summary["verdicts"]
    assert verdicts["stopping_per_atom_is_worse_than_stopping_on_accuracy"] is True
    assert summary["PER_ATOM"]["accuracy_final"] < summary["ADAPTIVE"]["accuracy_final"]
    # and the honest half: stopping did NOT match the fixed arm on every axis
    assert verdicts["the_fixed_arm_pays_for_its_extra_reach_in_errors"] is False
    assert summary["FIXED"]["accuracy_final"] >= summary["ADAPTIVE"]["accuracy_final"]
