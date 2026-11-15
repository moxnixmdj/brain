"""Selection, expression, composition: three failures that look identical and need different fixes.

The unit tests are arithmetic on hand-built files. The difficulty lives in
`canonical/verification/COMPOSITION_GAP_20261114_V1.json` -- 47 real changed files from 8 repositories,
each offered every other changed file as a demonstration -- and one test pins that record so the
document's headline cannot drift away from the measurement.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.tools import the_composition_gap_20261114_v1 as gap   # noqa: E402

RECORD = Path(__file__).resolve().parents[1] / "verification" / "COMPOSITION_GAP_20261114_V1.json"


def _pull(name: str, files: list[tuple[str, str]]) -> dict:
    return {"name": name, "files": [
        {"path": f"f{index}.py", "before": before, "after": after}
        for index, (before, after) in enumerate(files)]}


def test_several_separate_places_count_as_several_hunks():
    """The unit the whole record is built on. `@@` headers from a zero-context diff are the count."""
    before = "a = 1\nb = 2\nc = 3\n"
    after = "a = 10\nb = 2\nc = 30\n"
    assert gap._hunks(before, after) == 2
    assert gap._hunks(before, before) == 0


def test_one_landing_lesson_is_measured_as_exact_not_as_shaped():
    """Two files carrying the same substitution: the pool can produce the target exactly."""
    changed = ("def f(x):\n    return x < 10\n", "def f(x):\n    return x < 100\n")
    report = gap.measure([_pull("easy", [changed, changed])])
    assert report["oracle_selector"]["exact"] == 2
    assert report["shaped_not_filled"] == 0
    assert report["produced_nothing"] == 0


def test_a_coordinated_edit_is_measured_as_partial_not_as_a_refusal():
    """The distinction the record turns on.

    A target that needs two separate substitutions, with a lesson that supplies one of them, is not a
    refusal -- the organ changed the file. It is a *partial render*, and if this ever counts as
    `produced_nothing` the record's 30/14 split is meaningless.
    """
    lesson = ("def f(x):\n    return x < 10\n", "def f(x):\n    return x < 100\n")
    # The second change is on a line the lesson's shape cannot reach, and it is separated from the
    # first by an untouched line -- two adjacent changed lines are ONE hunk in any diff, which is
    # correct and would make this test measure the wrong unit.
    target = ("def f(x):\n    return x < 10\n\nLIMIT = 5\n",
              "def f(x):\n    return x < 100\n\nLIMIT = 50\n")
    report = gap.measure([_pull("partial", [lesson, target])])
    row = [r for r in report["per_target"] if r["path"] == "f1.py"][0]
    assert row["dev_hunks"] == 2, row
    assert row["org_hunks"] == 1, row
    assert row["org_hunks"] < row["dev_hunks"]
    assert row["shaped_not_filled"] is True
    assert report["organ_applied_fewer_changes_than_the_developers"] == 1


def test_a_refusal_is_counted_as_producing_nothing():
    """The other arm. A class body the lesson has no form for must not be counted as shaped."""
    lesson = ("def f(x):\n    return x < 10\n", "def f(x):\n    return x < 100\n")
    target = ("class A:\n    def m(self, y):\n        return y\n",
              "class A:\n    def m(self, y):\n        return y + 1\n")
    report = gap.measure([_pull("refused", [lesson, target])])
    row = [r for r in report["per_target"] if r["path"] == "f1.py"][0]
    assert row["produced_nothing"] is True
    assert row["shaped_not_filled"] is False
    # The lesson file is itself a target here, and the only demonstration offered to it is the class
    # body, so it refuses too. The unit under test is the row, not this aggregate.
    assert report["shaped_not_filled"] == 0


def test_the_committed_record_still_says_the_pool_cannot_fill_the_corpus():
    """Pins the document to the record.

    If a later round changes the organ, this is allowed to fail -- and then the document is rewritten
    to match, rather than the record being re-run until it agrees.
    """
    if not RECORD.exists():                       # pragma: no cover - record is committed
        return
    record = json.loads(RECORD.read_text())
    assert record["authority"] == "NONE"
    assert record["targets"] == 47
    assert record["oracle_selector"]["exact"] == 3
    assert record["oracle_selector"]["share"] == 0.0638
    assert record["shaped_not_filled"] == 30
    assert record["produced_nothing"] == 14
    assert record["coordinated_edits"] == 41
    assert record["single_substitution_edits"] == 6
    assert record["organ_applied_fewer_changes_than_the_developers"] == 29
