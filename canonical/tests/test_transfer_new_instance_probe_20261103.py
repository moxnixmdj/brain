"""The new-instance probe must compare genuinely different instances in both arms.

`transfer_learning_new_environment_probe_20261101.py` labelled a second call on the same
instance a "new instance". This test exists so the replacement cannot drift back into
that, and so its cold/warm pair is pinned as a controlled comparison: identical target
instance in both arms, and the only difference is the store seeded by the source lesson.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "transfer_learning_new_instance_probe_20261103.py"


def _run(tmp_path: Path) -> dict:
    caller_state = tmp_path / "caller-state.json"
    caller_state.write_text('"do not overwrite"\n', encoding="utf-8")
    env = dict(os.environ, BRAIN_TRANSFER_LEARNING_STATE=str(caller_state))
    completed = subprocess.run(
        [sys.executable, str(PROBE), "--json"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=180, check=True,
    )
    assert caller_state.read_text(encoding="utf-8") == '"do not overwrite"\n'
    return json.loads(completed.stdout)


def test_every_source_target_pair_is_a_distinct_instance(tmp_path):
    report = _run(tmp_path)
    assert report["schema"] == "PROBE_TRANSFER_NEW_INSTANCE_V1"
    cases = report["cases"]
    assert len(cases) == 15
    for case in cases:
        # The whole point: the thing handed to COLD/WARM is not the thing that was taught.
        assert case["source_instance"] != case["target_instance"], case["family"]
    assert report["summary"]["instances_distinct"] == len(cases)


def test_both_arms_are_solved_and_the_goal_is_not_true_at_reset(tmp_path):
    report = _run(tmp_path)
    for case in report["cases"]:
        assert case["teach"]["pass"] is True, case["family"]
        assert case["cold"]["pass"] is True, (case["family"], case["seed"])
        assert case["warm"]["pass"] is True, (case["family"], case["seed"])
        # A goal already true at reset would make a 1-trial result meaningless.
        assert case["cold"]["plan_length"] > 0
        assert case["cold"]["act_calls"] > 0
        assert case["warm"]["act_calls"] > 0


def test_the_summary_is_derived_from_the_cases_not_asserted(tmp_path):
    report = _run(tmp_path)
    cases, summary = report["cases"], report["summary"]
    assert summary["teach_solved"] == sum(c["teach"]["pass"] for c in cases)
    assert summary["cold_solved"] == sum(c["cold"]["pass"] for c in cases)
    assert summary["warm_solved"] == sum(c["warm"]["pass"] for c in cases)
    assert summary["warm_solved_with_fewer_trials"] == sum(
        c["warm"]["trials"] < c["cold"]["trials"] for c in cases)
    # A genuine saving needs fewer trials AND no more environment interaction.
    assert summary["warm_genuine_saving_trials_and_acts"] == sum(
        c["warm"]["pass"] and c["cold"]["pass"]
        and c["warm"]["trials"] < c["cold"]["trials"]
        and c["warm"]["act_calls"] <= c["cold"]["act_calls"]
        for c in cases)
    assert summary["warm_reached_goal_in_one_trial"] == sum(
        c["warm"]["trials"] == 1 and c["warm"]["pass"] for c in cases)


def test_carrying_a_lesson_actually_saves_work(tmp_path):
    """The number this probe exists to move, pinned as a floor in both directions.

    History, in the open, because this assertion has now moved once and the move was the point:

      2026-11-03, before P1: `warm_genuine_saving` = 1/15, mean act speedup 0.977x.
        `drive` replayed exact plans, then spent the full trial budget searching with the
        carried model as a hint. The stored lesson could already plan 7 of 15 targets, but
        nothing asked it to.
      2026-11-03, after P1: = 8/15, mean trial speedup 6.33x, mean act speedup 2.26x, and
        `warm_worse_on_trials` = 0/15.

    The floor is 8 so a regression shows up as a failure rather than as a quietly slower warm
    arm. The `warm_worse_on_trials == 0` assertion is the one that must never be relaxed: a
    carried model may cost act calls on a miss, and may never cost trials.
    """
    report = _run(tmp_path)
    summary = report["summary"]
    assert summary["cold_solved"] == summary["cases"], "the cold arm must not regress"
    assert summary["warm_solved"] == summary["cases"]
    assert summary["warm_genuine_saving_trials_and_acts"] >= 8
    assert summary["warm_reached_goal_in_one_trial"] >= 8
    assert summary["mean_trial_speedup"] > 3.0
    assert summary["mean_act_speedup"] > 1.5
    # Carrying memory may cost act calls on a miss. It may never cost trials.
    assert summary["warm_worse_on_trials"] == 0


def test_a_warm_run_records_which_authority_did_the_work(tmp_path):
    """Two different wins, two different labels -- so neither can be read as the other.

    `drive` used to print `PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN` for an exact plan replay
    AND for a run that merely inherited the prior model and then searched. Both now carry
    distinct authorities, and this asserts both actually occur, so the distinction is live
    rather than decorative. (A third, `MODEL_LEARNED_…`, covers the runs that are no faster.)
    """
    report = _run(tmp_path)
    authorities = {c["warm"]["authority"] for c in report["cases"]}
    assert "RECALLED_PLAN_EXECUTED_GOAL_OBSERVED" in authorities
    assert "CARRIED_MODEL_PLAN_EXECUTED_GOAL_OBSERVED" in authorities
    for case in report["cases"]:
        warm = case["warm"]
        if warm["authority"] == "CARRIED_MODEL_PLAN_EXECUTED_GOAL_OBSERVED":
            assert warm["status"] == "PASS__ENVIRONMENT_SOLVED_BY_CARRIED_MODEL"
            # A carried-model win is a one-trial win by construction: it is a plan, not a search.
            assert warm["trials"] == 1
        if warm["authority"] == "MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED":
            assert warm["status"] == "PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN"
