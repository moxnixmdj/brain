"""The unified front door teaches from one showing and applies the lesson to a file it never saw.

THE GAP THIS PINS
-----------------
Two things were each tested, never together:

  * ``solve_or_learn`` (the unified closed-loop entry every recent round calls the
    live path) has no test asserting its Tier-0 outcome ``PASS__TIER0_COMPILED_SKILL_RECALL``.
    The older ``door.solve`` branch returns ``PASS__COMPILED_WORKFLOW_SKILL`` and is
    covered elsewhere; the controller's Tier-0 branch is not.
  * The lesson pair shipped in the tracked bundle (``remember in ... the way ... was
    changed into ...`` then ``edit ... the way ... remembers``) is exercised by tests
    that talk to ``recall_and_execute_workflow`` directly, never through the door.

So a checkout could break the front door's Tier-0 route or the shipped pair and every
existing test would still pass. This file teaches one showing through the door itself,
applies it to a file created after the teaching, and refuses a showing whose change
cannot be repeated one place at a time -- each with the door's own words.

STATE THIS TOUCHES
------------------
A skill database seeded from the tracked bundle into a temp path (the same isolation
``taught_door`` uses), and scratch files under ``canonical/astra_runtime/tmp/``. The
live default database is not read or written.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sqlite3

import pytest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical/astra_runtime/tmp/test_front_door_bundle_loop"
needs_sandbox = pytest.mark.skipif(
    compiler._sandbox_for_taught_programs() is None,
    reason="this machine cannot start the namespace sandbox",
)


@pytest.fixture
def isolated_door(monkeypatch, tmp_path):
    """The front door whose skill store is a fresh import of the tracked bundle."""
    database = tmp_path / "skills.sqlite"
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(database))
    imported = compiler.import_workflow_bundle(
        compiler.default_workflow_bundle_path(), db_path=database
    )
    assert imported.get("accepted", 0) >= 2, imported
    # learn=True writes associative memory; keep the tracked state file as it was.
    memory = ROOT / "canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json"
    held_memory = memory.read_bytes() if memory.is_file() else None
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True)
    yield database
    shutil.rmtree(SCRATCH, ignore_errors=True)
    if held_memory is None:
        if memory.is_file():
            memory.unlink()
    else:
        memory.write_bytes(held_memory)


def _hit_counts(database: pathlib.Path) -> dict[str, int]:
    connection = sqlite3.connect(str(database))
    try:
        return {
            str(skill_id): int(hits)
            for skill_id, hits in connection.execute(
                "SELECT skill_id, hit_count FROM compiled_workflow_skills"
            )
        }
    finally:
        connection.close()


@needs_sandbox
def test_one_showing_becomes_a_lesson_and_edits_a_never_seen_file(isolated_door) -> None:
    before = "def total(items):\n    acc = 0\n    for x in items:\n        acc += x\n    return acc\n"
    after = "def total(items):\n    acc = 0\n    for x in items:\n        acc += int(x)\n    return acc\n"
    ex_before, ex_after = SCRATCH / "ex_before.py", SCRATCH / "ex_after.py"
    target = SCRATCH / "never_seen.py"
    ex_before.write_text(before, encoding="utf-8")
    ex_after.write_text(after, encoding="utf-8")
    target.write_text(before, encoding="utf-8")
    lesson = SCRATCH / "one_showing.lesson"

    rel = lambda p: p.relative_to(ROOT).as_posix()  # noqa: E731 - the goal grammar wants repo-relative paths
    teach_goal = (
        f"remember in {rel(lesson)} also the way {rel(ex_before)} "
        f"was changed into {rel(ex_after)}"
    )
    taught = door.solve_or_learn(
        {"task_id": "FRONT_DOOR_TEACH_1", "goal": teach_goal}, learn=True
    )
    assert taught.get("pass") is True, taught.get("status")
    assert taught.get("status") == "PASS__TIER0_COMPILED_SKILL_RECALL", taught
    assert taught.get("tier_used") == "tier0_compiled_skill_recall", taught
    assert taught.get("from_memory") is True, taught
    assert str(taught.get("answer") or "").startswith("remembered in "), taught

    assert lesson.is_file(), "the showing left no lesson behind"
    held = json.loads(lesson.read_text(encoding="utf-8"))
    assert held.get("format") == "CHANGE_LEARNED_FROM_EXAMPLES_V1", held.get("format")
    assert len(held.get("examples") or []) == 1, len(held.get("examples") or [])

    apply_goal = f"edit {rel(target)} the way {rel(lesson)} remembers"
    applied = door.solve_or_learn(
        {"task_id": "FRONT_DOOR_APPLY_1", "goal": apply_goal}, learn=True
    )
    assert applied.get("pass") is True, applied.get("status")
    assert applied.get("status") == "PASS__TIER0_COMPILED_SKILL_RECALL", applied
    assert applied.get("tier_used") == "tier0_compiled_skill_recall", applied
    assert str(applied.get("answer") or "").startswith("edited "), applied

    assert target.read_text(encoding="utf-8") == after, (
        "the lesson did not reach a file the teaching never saw"
    )

    hits = _hit_counts(isolated_door)
    taught_id = str(taught.get("skill_id") or "")
    applied_id = str(applied.get("skill_id") or "")
    assert taught_id and hits.get(taught_id, 0) >= 1, (taught_id, hits)
    assert applied_id and hits.get(applied_id, 0) >= 1, (applied_id, hits)
    assert taught_id != applied_id, "teaching and applying ran the same skill"


@needs_sandbox
def test_a_showing_that_cannot_repeat_one_place_at_a_time_is_refused_with_its_reason(
    isolated_door,
) -> None:
    # A coordinated rename changes which names are assigned on several lines; the taught
    # action applies rules one place at a time, so it must decline rather than guess.
    before = "def total(items):\n    acc = 0\n    for x in items:\n        acc += x\n    return acc\n"
    after = "def total(items):\n    total_ = 0\n    for x in items:\n        total_ += x\n    return total_\n"
    ex_before, ex_after = SCRATCH / "rename_before.py", SCRATCH / "rename_after.py"
    ex_before.write_text(before, encoding="utf-8")
    ex_after.write_text(after, encoding="utf-8")
    lesson = SCRATCH / "refused.lesson"

    rel = lambda p: p.relative_to(ROOT).as_posix()  # noqa: E731
    goal = (
        f"remember in {rel(lesson)} also the way {rel(ex_before)} "
        f"was changed into {rel(ex_after)}"
    )
    refusals: list[dict] = []
    result = compiler.recall_and_execute_workflow(
        goal, cwd=ROOT, db_path=isolated_door, refusals=refusals
    )
    assert result is None, "a change that cannot repeat one place at a time was taught"
    assert refusals, "the refusal carried no reason"
    reason = str(refusals[0].get("reason") or "")
    assert "cannot be repeated one place at a time" in reason, reason
    assert not lesson.exists(), "a refused showing left a lesson behind"
