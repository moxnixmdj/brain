"""The plan is judged by what it left behind, not by the string it printed.

The external benchmark this project was measured against lived in a scratch directory and was
lost with it. A score that cannot be re-derived is not evidence, so the question is asked here in
a form that lives in the repository: for each task, a request a person would write and the state
that must hold afterwards. The plan is produced by the planner alone, run against the real
program, and the world is inspected.

No task states a command. A task states a goal and an effect, so the suite cannot reward a
memorised spelling -- only a plan that changes the world the way the request asked.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from canonical.runtime import require_survey_plan_v1 as R  # noqa: E402
from canonical.tests.programs import tasks_v1  # noqa: E402


def _planner(program: str, instruction: str) -> dict:
    return R.require_survey_plan_sequence(program, instruction, probes=16)


@pytest.mark.parametrize("task", tasks_v1.TASKS, ids=[t["id"] for t in tasks_v1.TASKS])
def test_the_plan_changes_the_world_the_request_asked_for(task, tmp_path):
    row = tasks_v1.run_task(task, _planner, tmp_path)
    assert row["ok"], (row["problems"], row["commands"])


def test_every_task_is_a_goal_and_an_effect_and_names_no_command():
    """A task that names a command would be testing the fixture's spelling, not the planner."""
    for task in tasks_v1.TASKS:
        assert "expect_command_contains" in task or "expect_collection" in task, task["id"]
        # the request itself must never spell a flag: it is what a person would say
        assert "--" not in task["instruction"], task["id"]
