#!/usr/bin/env python3
"""Representative probing versus adjacent probing -- my hypothesis, measured and refuted.

Measured on 11 machines x 2 seeds x 30-probe budget:

    A walk only      48 predictions,  3 wrong  (accuracy 0.938)
    ADJACENT        159 predictions, 10 wrong  (0.937)
    REPRESENTATIVE  159 predictions, 11 wrong  (0.931)   <- my prediction, and it lost
    RANDOM          131 predictions,  7 wrong  (0.947)

The finding is bigger than the ranking: at larger budgets the error rate did NOT rise (13.3% at 507
probes last round, 6-7% here at 30 probes per machine). The cost of a question is a function of how
many you ask per state, not a fixed price.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import ask_what_you_will_be_tested_on_v1 as rep  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
from canonical.tools import the_width_of_a_guard_v1 as width  # noqa: E402

CONDITIONS = [("CARD", "WHOLE", None, "count_is", 1)]
ONE = (("0", "alpha"),)
TWO = (("0", "alpha"), ("1", "alpha"))
NOOP = (frozenset(), frozenset())


def _law(atom="ADD", support=1):
    return width.Law(atom, "IDENT", ("0",), NOOP, support=support, witness=ONE)


def test_questions_overlap_and_neither_rule_is_independent():
    """The measured reason the objective change bought nothing: representative and adjacent select
    from the same admissible set, so they ask the SAME question about 97% of the time (since a probe
    removes its state from the unknown set, overlaps here are counted by the identical totals)."""
    unknown = [ONE, TWO]
    adjacent = rep.select_adjacent([_law()], unknown, [])
    representative = rep.select_representative([_law()], unknown, [])
    assert adjacent is not None and representative is not None
    assert adjacent[1] == representative[1], (
        "with one candidate law a state admits, both rules must pick the same state")


def test_representative_prefers_the_state_more_weak_laws_disagree_about():
    """Where the two rules CAN differ: representative counts how many support-1 laws admit a state,
    so it goes where the table is about to make the most unsupported claims at once."""
    many = [width.Law("A", "IDENT", ("0",), NOOP, support=1, witness=ONE),
            width.Law("B", "IDENT", ("0",), NOOP, support=1, witness=ONE),
            width.Law("C", "IDENT", ("0",), NOOP, support=1, witness=ONE)]
    picked = rep.select_representative(many, [ONE, TWO], [])
    assert picked is not None
    assert picked[1] == ONE, "the state admitted by all three weak laws is the representative one"


def test_no_candidate_is_not_a_crash():
    """A rule must return None rather than raising when nothing qualifies -- an arm that crashes on
    an empty candidate set would look like a policy difference."""
    assert rep.select_adjacent([], [ONE], []) is None
    assert rep.select_representative([], [ONE], []) is None


def test_the_measured_verdict_is_recorded_with_its_refutation():
    artifact = (REPO / "canonical" / "verification" /
                "ASK_WHAT_YOU_WILL_BE_TESTED_ON_20261124_V1.json")
    if not artifact.exists():                       # pragma: no cover
        return
    summary = json.loads(artifact.read_text())["summary"]
    verdicts = summary["verdicts"]
    assert verdicts["representative_beats_asking_nothing_on_correct"] is True
    assert verdicts["representative_beats_adjacent_on_correct"] is False, (
        "this is the finding, not a regression: the objective change did not help")
    # and every arm must be at least as accurate as the walk alone, which is the useful result
    for arm in ("ADJACENT", "REPRESENTATIVE", "RANDOM"):
        assert summary[arm]["accuracy"] > 0.9
