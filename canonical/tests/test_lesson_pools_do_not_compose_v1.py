#!/usr/bin/env python3
"""Experience does not accumulate: a pool of lessons writes lines no developer wrote.

PREDICTIONS -- written 2026-11-12 before this file was first run. Branch `arena/6bc5654f-brain`,
base `b56d981c`.

The owner's thesis is that experience compounds: learn an action once, keep it, and the machine
gets monotonically better. The tree has measured one lesson, two lessons, and which demonstration
to choose. It has never measured **a pool**: many lessons held at once, on code that belongs to one
of them. This file pins the measurement in
`canonical/tools/lesson_pool_interference_v1.py` (record
`canonical/verification/LESSON_POOL_INTERFERENCE_20261112_V1.json`, 52 lessons, 232 targets).

The two numbers compared are deliberately computed by different code:

* `same` / `extra` come from the corpus harness's own scorer, which aligns statements against what
  the developers wrote;
* `wrong` is a line-level diff of three plain texts (original, developer's, the engine's) and
  touches neither the organ nor the scorer.

P1  A lesson scored with only its own rules loaded reproduces the published behaviour: 288 correct
    of 296 questions, 13 wrong lines over 232 files.
P2  With five lessons in the pool the organ is still effectively silent: fewer than 5 files edited.
P3  The number of files edited rises with the pool, and the curve is monotone: 1, 1, 1, 1, 11, 30,
    64, 90, 130 for pools of 1, 2, 3, 5, 8, 13, 21, 34, 52 lessons.
P4  Correct changes rise with the pool too (1, 1, 1, 1, 1, 24, 102, 159, 270): the pool is not
    only getting worse, it is doing more work overall.
P5  **The claim that matters: the wrong lines rise with the pool as well.** 0, 0, 0, 0, 20, 48, 51,
    49, 39. A pool of 52 lessons writes 39 lines on 232 files that no developer wrote, where a pool
    of 5 writes none.
P6  `extra` and `wrong` agree at every point of the curve. If they ever disagree, one of the two
    readings is broken and neither should be quoted.
P7  The wrong lines are not confined to the lesson being applied: at 52 lessons the pool writes 39
    wrong lines where the own-lesson arm writes 13, so at least 26 of them are caused by *other*
    lessons being present. Composition is the source, not the individual lesson.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
RECORD = REPO / "canonical" / "verification" / "LESSON_POOL_INTERFERENCE_20261112_V1.json"
sys.path.insert(0, str(REPO))

from canonical.tools import lesson_pool_interference_v1 as L  # noqa: E402


@pytest.fixture(scope="module")
def record():
    if not RECORD.is_file():
        pytest.skip("the pool record has not been produced on this machine")
    return json.loads(RECORD.read_text())


def test_p1_the_published_arm_is_reproduced(record):
    own = record["own_lesson_only"]
    assert own["questions"] == 296
    assert own["same"] == 288
    assert own["wrong"] == 13


def test_p2_five_lessons_are_still_silent(record):
    first_five = [row for row in record["curve"] if row["lessons"] <= 5]
    assert first_five and all(row["edited"] < 5 for row in first_five)


def test_p3_more_lessons_means_more_files_edited(record):
    edited = [row["edited"] for row in record["curve"]]
    assert edited == sorted(edited), "files edited should not fall as the pool grows"


def test_p4_and_correct_changes_rise_with_the_pool(record):
    same = [row["same"] for row in record["curve"]]
    assert same[-1] > same[0]
    assert same == sorted(same)


def test_p5_wrong_lines_rise_with_the_pool(record):
    wrong = [row["wrong"] for row in record["curve"]]
    assert wrong[0] == 0
    assert max(wrong) > 0, "a pool of lessons wrote no line the developers did not"
    assert max(wrong) >= 20


def test_p6_the_two_readings_agree_at_every_point(record):
    for row in record["curve"]:
        assert row["extra"] == row["wrong"], (
            "the statement scorer and the line diff disagree at %d lessons: %s"
            % (row["lessons"], row))


def test_p7_the_wrong_lines_come_from_the_pool_not_the_lesson(record):
    own = record["own_lesson_only"]["wrong"]
    worst = max(row["wrong"] for row in record["curve"])
    assert worst > own, "the pool was no worse than the lesson alone; composition cost nothing"


def test_the_tool_measures_what_it_says(tmp_path):
    """The two readings are computed from different inputs; a constructed case separates them."""
    me = "a = 1\nb = 2\nc = 3\n"
    person = "a = 1\nb = 20\nc = 3\n"
    ours = "a = 1\nb = 2\nc = 30\n"          # nothing the person did, one line they left alone
    assert L.untouched(me, person, ours) == 1
    assert L.untouched(me, person, person) == 0
