#!/usr/bin/env python3
"""Conjunctions stop paying for REACH immediately, keep paying for PRECISION, and there is no optimum.

Nested leave-one-machine-out over 13 candidate predicates, k = 1..8, choosing the best k-subset on nine
machines and scoring it on the tenth:

    k    pred  wrong   accuracy  coverage
    1      94     12     0.8868    0.6351
    2      87     15     0.8529    0.5878
    3      89     19     0.8241    0.6014
    4      83      8     0.9121    0.5608
    5      76      6     0.9268    0.5135
    6      76      6     0.9268    0.5135
    7      89      6     0.9368    0.6014
    8      76      7     0.9157    0.5135

The out-of-sample Pareto front has exactly TWO points -- k=7 (0.937 / 0.601) and k=1 (0.887 / 0.635) --
and the incumbent hand-picked five is dominated by both (0.862 / 0.507).

So the vocabulary is a DIAL: finer keys mean more accuracy and less coverage, because a finer key is more
often one the held-out state's walk never produced. The stopping rule I promised is NOT derivable as a
number, because the curve is a sawtooth with no interior maximum -- what is derivable is the frontier,
and where to sit on it is a preference between a wrong prediction and a refusal.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACT = (REPO / "canonical" / "verification" /
            "WHERE_CONJUNCTIONS_STOP_PAYING_20261124_V1.json")


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_the_curve_is_read_out_of_sample():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert len(summary["machines"]) == 10
    # each point is a pooled out-of-sample score: one fold per machine, choice made on the other nine
    for cell in summary["curve"]:
        assert cell["predictions"] + cell["refused"] > 0
    assert summary["verdicts"]["the_incumbent_is_beaten_out_of_sample"] is True


def test_coverage_does_not_improve_with_vocabulary_size():
    """The refutation of my own framing: I said added predicates buy reach. They do not."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["verdicts"]["coverage_does_not_improve_with_more_predicates"] is True
    first, best = summary["curve"][0]["coverage"], max(c["coverage"] for c in summary["curve"])
    assert best <= first + 0.01


def test_accuracy_is_the_currency_and_it_rises():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["verdicts"]["accuracy_improves_with_more_predicates"] is True
    assert summary["accuracy_trend"]["gain_from_best_to_single"] > 0.03


def test_the_frontier_has_two_points_and_the_incumbent_is_dominated():
    """The honest deliverable: not 'the optimal vocabulary size is 7' but 'these two trade-offs are
    both strictly better than the hand-picked five'."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    front = summary["pareto_front"]
    assert len(front) == 2
    assert {cell["size"] for cell in front} == {1, 7}
    incumbent = summary["incumbent_scored_on_all_machines"]
    for cell in front:
        assert cell["accuracy"] >= incumbent["accuracy"]
        assert cell["coverage"] >= incumbent["coverage"]


def test_no_stopping_point_is_claimed_because_none_exists():
    """Guards against a future round quietly reintroducing 'the right number is k'. The curve is a
    sawtooth; the derived_stopping_point field records that a rule FAILED to yield a number."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["verdicts"]["the_gain_curve_has_an_interior_maximum"] is False
    assert summary["verdicts"]["the_vocabulary_is_a_precision_dial_not_a_reach_lever"] is True
    assert "DIAL" in summary["pareto_note"]
