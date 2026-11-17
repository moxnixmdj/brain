#!/usr/bin/env python3
"""Pins the separation between an operation and the plan that realised it.

The laws these tests hold down, from `canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json`:

  * a plan replayed onto the state it was made for reproduces that state exactly;
  * the same plan replayed onto a state that moved under it does not, and can produce a file that
    still parses while the edit it claims did not happen;
  * whether a replay is safe is decided by whether the earlier step moved the plan's lines, not by
    whether the operation is still legal there -- legality survived in 80 of 80 measured pairs.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import wiring
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import action_replay_under_change_v1 as replay  # noqa: E402

# One file, two operations that both apply. In one order the plan survives, in the other it does
# not: the first step moves the lines the second plan addresses.
WITNESS_PATH = "canonical/runtime/generic_goal_tool_effect_planner_v2.py"
MOVES_LINES = ("_resource_overlap", "right")
DOES_NOT_MOVE = ("build_planning_problem", "rows")


def _module() -> str:
    return (
        "import os\n"
        "import sys\n"
        "\n"
        "def first(path):\n"
        "    text = path.read_text()\n"
        "    return text\n"
        "\n"
        "\n"
        "def second(path):\n"
        "    payload = path.read_bytes()\n"
        "    return payload\n"
    )


def test_a_plan_replayed_on_its_own_state_reproduces_that_state() -> None:
    before = _module()
    after = before.replace("    text = path.read_text()\n    return text\n",
                           "    return path.read_text()\n")
    plan = replay.plan_of(before, after)
    assert plan, "a real rewrite must produce at least one replacement"
    assert replay.replay_plan(plan, before) == after


def test_a_plan_shifted_by_one_line_lands_on_the_wrong_statement() -> None:
    before = _module()
    after = before.replace("    text = path.read_text()\n    return text\n",
                           "    return path.read_text()\n")
    plan = replay.plan_of(before, after)
    # One line disappeared above the function between the proof and the replay.
    shifted = before.replace("import sys\n", "")
    live = shifted.replace("    text = path.read_text()\n    return text\n",
                           "    return path.read_text()\n")
    landed = replay.replay_plan(plan, shifted)
    assert landed != live
    # It still parses, and the binding the plan was supposed to remove is still bound:
    # this is the dangerous class, not a loud failure.
    compile(landed, "<replayed>", "exec")
    assert replay.edit_landed(landed, "first", "text") is False
    assert replay.edit_landed(live, "first", "text") is True


def test_edit_landed_reads_the_binding_the_edit_was_supposed_to_remove() -> None:
    assert replay.edit_landed(_module(), "first", "text") is False
    assert replay.edit_landed(_module().replace("    text = path.read_text()\n"
                                                "    return text\n",
                                                "    return path.read_text()\n"),
                               "first", "text") is True
    # A name bound in another function is not this function's binding.
    assert replay.edit_landed(_module(), "second", "text") is True


def test_first_changed_index_counts_the_first_line_that_moved() -> None:
    before = _module()
    assert replay.first_changed_index(before, before) is None
    assert replay.first_changed_index(before, before.replace("    text =", "    other =")) == 4
    assert replay.first_changed_index(before, "import collections\n" + before) == 0


def test_the_first_step_decides_the_replay_not_the_legality_of_the_second() -> None:
    skill = replay.inline_skill()
    moves = replay.measure_pair(skill, {"path": WITNESS_PATH, "function": MOVES_LINES[0],
                                        "variable": MOVES_LINES[1]},
                                {"path": WITNESS_PATH, "function": DOES_NOT_MOVE[0],
                                 "variable": DOES_NOT_MOVE[1]})
    # The second operation is legal before and after, so the pair is replayable at all.
    assert moves["eligible_before"] is True
    assert moves["eligible_after"] is True
    assert moves["status"] == "SILENT_CORRUPTION"
    assert moves["replay_parses"] is True
    assert moves["replay_claims_the_edit"] is False
    assert moves["drift"] != 0

    other = replay.measure_pair(skill, {"path": WITNESS_PATH, "function": DOES_NOT_MOVE[0],
                                        "variable": DOES_NOT_MOVE[1]},
                                {"path": WITNESS_PATH, "function": MOVES_LINES[0],
                                 "variable": MOVES_LINES[1]})
    assert other["status"] == "REPLAY_MATCHES_LIVE"
    assert other["drift"] == 0

    # Same two operations, opposite order: one order is safe and the other silently wrong.
    assert (moves["status"] == "SILENT_CORRUPTION"
            and other["status"] == "REPLAY_MATCHES_LIVE")
