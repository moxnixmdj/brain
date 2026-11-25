#!/usr/bin/env python3
"""Syntax does NOT predict outcome. The vocabulary is a confident-pass detector with abstention.

Labels come from EXECUTION: 2,233 tests run in-process, pass/fail recorded from junit XML. 1,472 trained,
761 held out, split by file. 42 of the held-out tests fail.

    best vocabulary  97 predictions, 0 wrong, accuracy 1.0000, coverage 0.1205
    majority class (always pass, full coverage)          0.9448
    always pass AT THE VOCABULARY'S OWN COVERAGE         1.0000
    failures predicted                                   0   <- the decisive number
    held-out failures the vocabulary ever speaks about   0 of 42

It reaches accuracy 1.0 by refusing 708 of 761 tests and never saying "fail". Since 94.5% of tests pass,
"always pass, but only when confident" is free, and the vocabulary scores exactly it. Beating the majority
class at full coverage is therefore not a result; matching it at equal coverage with zero failure
predictions is the honest description.

This closes the gap the previous round left open. Syntax transfers across codebases (V24) -- but it
predicts syntax, and when pointed at an outcome it collapses into the base rate.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import does_syntax_predict_outcome_v1 as outcome  # noqa: E402

ARTIFACT = (REPO / "canonical" / "verification" /
            "DOES_SYNTAX_PREDICT_OUTCOME_20261124_V1.json")


def test_no_feature_is_derived_from_the_thing_that_produces_the_label():
    """The label comes from RUNNING the test, so no static feature can restate it by construction. The
    check here is narrower but necessary: features may read Assert nodes and must never read Return nodes,
    because that is the leak this project committed twice."""
    # `assert g() == 1` is a Compare, so its origin class is OPERATION -- the comparison, not the call.
    compared = ast.parse("def test_x():\n assert g() == 1\n").body[0]
    assert "COUNTS_ON_OPERATION" in outcome.counts_on_features(compared)
    # a bare call in an assert must show CALL
    bare = ast.parse("def test_x():\n assert g()\n").body[0]
    feats = outcome.counts_on_features(bare)
    assert "COUNTS_ON_CALL" in feats
    assert all(name.startswith(("COUNTS_ON_", "ASSERTS_")) for name in feats)
    # nothing anywhere in the feature set may be derived from a return
    assert all("RET" not in name for name in outcome.features_of(bare))


def test_the_vocabulary_never_predicts_a_failure():
    """The decisive measurement. If a future change makes it predict failures, this test fails and the
    report's conclusion no longer holds."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["detail"]["said_fail"] == 0
    assert summary["detail"]["said_fail_right"] == 0
    assert summary["verdicts"]["the_vocabulary_predicts_any_failure"] is False
    assert summary["verdicts"]["the_vocabulary_is_only_a_confident_pass_detector"] is True


def test_it_does_not_beat_always_pass_at_equal_coverage():
    """Accuracy 1.0 at 12% coverage sounds like a result until the equal-coverage baseline is computed."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["best"]["accuracy"] == summary["detail"]["same_coverage_always_pass_accuracy"]
    assert summary["verdicts"]["the_vocabulary_beats_always_pass_at_equal_coverage"] is False


def test_there_were_genuine_failures_to_find_and_none_were_found():
    """42 held-out failures existed. The vocabulary spoke about none of them. Recording both numbers stops
    'it predicted everything correctly' from being said about a set it never touched."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    detail = json.loads(ARTIFACT.read_text())["summary"]["detail"]
    assert detail["failures_in_held_out"] >= 20
    assert detail["failures_spoken_about"] == 0


def test_labels_come_from_execution_not_from_parsing():
    """A cheap structural check that the label source is the runner: the tool must contain a pytest
    invocation, or the labels became hand-assigned somewhere along the way."""
    source = (REPO / "canonical" / "tools" / "does_syntax_predict_outcome_v1.py").read_text()
    assert "junit-xml" in source and "pytest" in source
    assert "passed" in source
