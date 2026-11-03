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


def test_carrying_a_lesson_never_silently_costs_more_than_it_saves(tmp_path):
    """The finding this probe records, pinned so a regression in `drive` shows up as a change
    in this number rather than as a silently slower warm arm. If a future change makes prior
    experience actually save work, this assertion is expected to move -- update it with the
    new measurement, in the open, and say so."""
    report = _run(tmp_path)
    summary = report["summary"]
    # Observed 2026-11-03: 1/15. Carrying the lesson was a net cost in 14/15 cases because
    # the prior model is injected but the search budget is not reduced, and recall replays up
    # to three stored plans through env.act() before the search starts.
    assert summary["warm_genuine_saving_trials_and_acts"] <= 2
    assert summary["mean_act_speedup"] is not None
    assert summary["mean_act_speedup"] < 1.25
