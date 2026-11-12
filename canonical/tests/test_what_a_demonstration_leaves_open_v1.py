#!/usr/bin/env python3
"""The intuitive predictor fails, and the tool must say so rather than bury it.

I went into this pass expecting to show that a demonstration which leaves 200 element
descriptions open transfers worse than one that leaves 2. The recorded run says the opposite
(r = +0.175, wrong sign, most-open third at 0.840 against least-open at 0.608), and controlling
for the cost of finding the first success it collapses to +0.116.

So these tests hold the tool to three things: it computes the confound check, it refuses to call
a confounded relationship a predictor, and it reports an inability to re-run as BLOCKED rather
than as agreement.
"""
from __future__ import annotations

import json

import pytest

from canonical.tools import what_a_demonstration_leaves_open_v1 as W


# ---------------------------------------------------------------------------
# reading the recorded run
# ---------------------------------------------------------------------------
def test_the_run_is_read_from_disk_and_the_steps_are_found():
    result = W.report()
    assert result["run"].startswith("MINIWOB_ONE_SUCCESS_GENERALISATION_")
    assert result["pages_with_a_skill"] > 0
    assert result["pages_scored"] > 0


def test_descriptions_left_is_extracted_per_page():
    rows = W.table(json.loads(W.newest_run().read_text()))
    with_steps = [r for r in rows if r["descriptions_open_median"] is not None]
    assert with_steps
    assert all(r["steps"] >= 1 for r in with_steps)
    assert all(r["descriptions_open_max"] >= r["descriptions_open_median"] for r in with_steps)


# ---------------------------------------------------------------------------
# the finding, pinned so it cannot be quietly reversed later
# ---------------------------------------------------------------------------
def test_openness_does_not_predict_failure_the_way_intuition_says():
    rel = W.report()["relationships"]
    assert rel["verdict"] == "NO_EFFECT"
    # the naive hypothesis predicts a negative correlation; the data gives a positive one
    assert rel["openness"]["r_with_success"] > 0
    assert rel["most_open_third_success"] > rel["least_open_third_success"]


def test_the_confound_check_runs_and_shrinks_the_effect():
    rel = W.report()["relationships"]
    raw = abs(rel["openness"]["r_with_success"])
    partial = abs(rel["openness"]["partial_r_controlling_for_cost"])
    assert partial < raw, "controlling for first-success cost must reduce the openness effect"


def test_the_predictor_that_survives_is_the_cost_of_the_first_success():
    rel = W.report()["relationships"]
    assert rel["cost"]["r_with_success"] < 0, "hard-won demonstrations transfer worse"
    assert abs(rel["cost"]["r_with_success"]) > abs(rel["openness"]["partial_r_controlling_for_cost"])


# ---------------------------------------------------------------------------
# judge()
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,partial,expected", [
    (0.05, 0.05, "NO_EFFECT"),
    (-0.45, -0.05, "CONFOUNDED_BY_FIRST_SUCCESS_COST"),
    (0.45, 0.44, "SURVIVES_THE_CONFOUND"),
    (0.31, 0.31, "SURVIVES_THE_CONFOUND"),
    (0.10, 0.33, "SURVIVES_THE_CONFOUND"),
    (None, 0.5, "UNMEASURABLE"),
])
def test_the_judge_names_the_confound_instead_of_hiding_it(raw, partial, expected):
    assert W._judge(raw, partial) == expected


def test_a_confounded_effect_is_never_reported_as_a_predictor():
    verdict = W._judge(-0.6, 0.05)
    assert "CONFOUND" in verdict
    assert "SURVIVES" not in verdict


# ---------------------------------------------------------------------------
# a re-run that cannot happen must not be reported as one that agreed
# ---------------------------------------------------------------------------
def test_feasibility_is_measured_not_assumed():
    feas = W.feasibility()
    assert feas["status"] in ("RUNNABLE", "BLOCKED")
    assert isinstance(feas["blocked_by"], list)
    if feas["status"] == "BLOCKED":
        assert feas["blocked_by"], "a block must name its cause"
        assert "not a re-run" in feas["note"]
    assert feas["can_rerun_on_fresh_seeds"] is (feas["status"] == "RUNNABLE")


def test_this_environment_reports_blocked_with_a_reason(monkeypatch):
    """Pin the sandbox's actual condition: no browser, so no fresh-seed claim from here."""
    monkeypatch.setattr(W.shutil, "which", lambda name: None)
    feas = W.feasibility()
    assert feas["status"] == "BLOCKED"
    assert "NO_BROWSER_BINARY" in feas["blocked_by"]


def test_a_missing_library_without_root_is_reported_as_both(monkeypatch):
    monkeypatch.setattr(W.shutil, "which", lambda name: "/usr/bin/chromium")
    monkeypatch.setattr(W.pathlib.Path, "exists", lambda self: False)
    import os
    monkeypatch.setattr(os, "geteuid", lambda: 1001, raising=False)
    feas = W.feasibility()
    assert feas["status"] == "BLOCKED"
    assert any(b.startswith("MISSING_SHARED_LIBRARIES") for b in feas["blocked_by"])
    assert "NO_ROOT_TO_INSTALL_THEM" in feas["blocked_by"]


def test_the_cli_runs_and_names_the_verdict():
    assert W.main([]) == 0
