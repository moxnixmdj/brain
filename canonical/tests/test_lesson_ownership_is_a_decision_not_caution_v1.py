#!/usr/bin/env python3
"""Naming the changed symbol is a real ownership rule — and the corpus cannot evidence weights.

PREDICTIONS -- written 2026-11-12 before this file was first run. Branch `arena/6fe0e35a-brain`,
base `d314e2fe`.

The previous round measured that a pool of 52 lessons writes 39 lines no developer wrote, and named
the next move: scope by the changed name. That move is measured in
`canonical/tools/lesson_ownership_measure_v1.py` (record
`canonical/verification/LESSON_OWNERSHIP_20261112_V1.json`).

The risk this file exists to catch is that "do less" looks like "do better". A filter that refuses
more work writes fewer wrong lines for the trivial reason that it writes fewer lines. So the
headline claim is **not** the wrong-line count; it is **wrong lines per edit**, and it is only
credited because a blind control at comparable volume is worse.

P1  The symbol scope halves the damage at the full pool: 39 wrong lines unscoped, 20 scoped, on the
    same 232 targets.
P2  It is not free: correct changes fall 270 -> 231 over the same pool. The scope is a trade, and the
    record must show both numbers or neither means anything.
P3  At 13 lessons the scope writes **zero** wrong lines where the unscoped arm writes 5.
P4  **The scope is a decision, not caution.** Wrong lines per edit is 0.19 scoped against 0.43 to
    0.49 for blind random lessons at comparable volume. The edit counts are comparable (106 scoped
    against 81 to 85 blind), so volume does not explain the difference.
P5  **The scope is NOT a solution, and the record must say so.** It leaves exactly one lesson standing
    on 36 of 232 targets — 15.5%. A rule that decides on one target in six is a beginning.
P6  A weight-update experiment **cannot be evidenced on this corpus**: 207 commits across 205
    projects, with **zero** projects contributing three or more commits. There is no same-project
    stream to hold anything out of, so no claim about training weights can be tested here.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
RECORD = REPO / "canonical" / "verification" / "LESSON_OWNERSHIP_20261112_V1.json"
sys.path.insert(0, str(REPO))

from canonical.tools import lesson_ownership_measure_v1 as M  # noqa: E402


@pytest.fixture(scope="module")
def record():
    if not RECORD.is_file():
        pytest.skip("the ownership record has not been produced on this machine")
    return json.loads(RECORD.read_text())


def row(record, count, arm):
    for entry in record["curve"]:
        if entry["lessons"] == count:
            return entry[arm]
    raise AssertionError("no row for %d lessons" % count)


def test_p1_the_scope_halves_the_damage(record):
    last = record["curve"][-1]
    assert last["unscoped"]["wrong"] == 39
    assert last["symbol_scoped"]["wrong"] == 20


def test_p2_the_scope_is_a_trade_and_both_numbers_are_reported(record):
    last = record["curve"][-1]
    assert last["symbol_scoped"]["same"] < last["unscoped"]["same"]
    assert last["symbol_scoped"]["same"] == 231
    assert last["unscoped"]["same"] == 270


def test_p3_at_thirteen_lessons_the_scope_writes_nothing_wrong(record):
    assert row(record, 13, "symbol_scoped")["wrong"] == 0
    assert row(record, 13, "unscoped")["wrong"] == 5


def test_p4_the_scope_is_a_decision_not_caution(record):
    control = record["control_matched_volume"]
    scoped = control["symbol_scoped"]
    blind = control["blind_random"]
    assert scoped["wrong_per_edit"] < min(entry["wrong_per_edit"] for entry in blind)
    # and the volumes are comparable, or the comparison would be volume in disguise
    assert scoped["edited"] >= min(entry["edited"] for entry in blind)


def test_p5_the_scope_is_not_a_solution_and_says_so(record):
    power = record["control_discriminating_power"]
    assert power["unique"] == 36
    assert power["targets"] == 232
    assert power["unique_share"] < 0.25
    assert "not a tautology" in power["reading"]


def test_p6_weights_cannot_be_evidenced_on_this_corpus(record):
    shape = record["question_2_weight_training_evidencable"]
    assert shape["commits"] == 207
    assert shape["projects"] == 205
    assert shape["projects_with_three_or_more_commits"] == 0
    assert shape["projects_with_two_or_more_lessons"] <= 2


def test_the_scope_is_computed_from_the_file_and_not_from_the_answer():
    """The ownership rule may not look at the target's content: only at which names it mentions."""
    here = "import threading\n\ndef f():\n    return threading.currentThread().ident\n"
    assert "currentThread" in M.symbols(here)
    assert "threading" in M.symbols(here)
    # a name the file does not mention is not owned by a lesson about it
    assert "safe_load" not in M.symbols(here)


def test_a_lesson_names_what_its_example_changed():
    before = "import yaml\n\ndef read(p):\n    return yaml.load(p)\n"
    after = "import yaml\n\ndef read(p):\n    return yaml.safe_load(p)\n"
    assert M.changed_symbols(before, after) == {"load", "safe_load"}
