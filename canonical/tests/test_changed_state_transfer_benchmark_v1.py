"""The transfer benchmark must compare changed inputs, not recreated instances."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_changed_state_benchmark_uses_distinct_states_and_real_observations(tmp_path):
    # A caller's state must not be used or overwritten by this disposable benchmark.
    caller_state = tmp_path / "caller-state.json"
    caller_state.write_text('"do not overwrite"\n', encoding="utf-8")
    env = dict(os.environ, BRAIN_TRANSFER_LEARNING_STATE=str(caller_state))
    completed = subprocess.run(
        [sys.executable, "-m", "canonical.tools.changed_state_transfer_benchmark_v1"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30, check=True,
    )
    assert caller_state.read_text(encoding="utf-8") == '"do not overwrite"\n'
    report = json.loads(completed.stdout)
    assert len(report["families"]) == 5
    rows = [target for family in report["families"].values() for target in family["targets"]]
    assert report["summary"]["target_cases"] == len(rows)
    assert report["summary"]["cold_solved"] == sum(row["cold"]["pass"] for row in rows)
    assert report["summary"]["transfer_solved"] == sum(row["transfer"]["pass"] for row in rows)
    assert report["summary"]["direct_plan_replays"] == sum(
        row["transfer"]["authority"] == "RECALLED_PLAN_EXECUTED_GOAL_OBSERVED" for row in rows
    )
    for family in report["families"].values():
        assert family["source"]["pass"] is True
        assert len(family["targets"]) == 2
        states = [family["source_state"], *(row["initial_state"] for row in family["targets"])]
        assert len({json.dumps(value, sort_keys=True) for value in states}) == 3
        for target in family["targets"]:
            for arm in ("cold", "transfer"):
                outcome = target[arm]
                assert outcome["pass"] is True
                assert outcome["authority"] in {
                    "RECALLED_PLAN_EXECUTED_GOAL_OBSERVED",
                    "MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED",
                }
                assert outcome["elapsed_ms"] >= 0
                assert outcome["action_calls"] > 0
            # The disabled arm must not be reported as direct recall.
            assert target["cold"]["authority"] == "MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED"
