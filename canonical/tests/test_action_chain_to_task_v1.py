"""A task is not a lesson: the arithmetic of a job that needs several actions to land.

The instrument these tests pin is `canonical/tools/action_chain_to_task_20261114_v1.py`. The unit
tests below use two-line sources because they are testing arithmetic, not difficulty -- the difficulty
lives in `canonical/verification/ACTION_CHAIN_TO_TASK_20261114_V1.json`, which is 8 real pull requests
nobody designed anything on, and which one test here pins so the document's numbers cannot drift away
from the record.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.tools import action_chain_to_task_20261114_v1 as chain   # noqa: E402

RECORD = Path(__file__).resolve().parents[1] / "verification" / "ACTION_CHAIN_TO_TASK_20261114_V1.json"


def _pull(name: str, files: list[tuple[str, str]]) -> dict:
    """A pull request whose files are (before, after) pairs; `before == after` means untouched."""
    return {"name": name, "files": [
        {"path": f"f{index}.py", "before": before, "after": after}
        for index, (before, after) in enumerate(files)]}


def test_a_job_where_every_file_lands_exactly_is_solved():
    """The only case that may be called done. Both files share one demonstrable edit, so a lesson
    taught on either one reproduces the other."""
    changed = ("def f(x):\n    return x < 10\n", "def f(x):\n    return x < 100\n")
    report = chain.measure([_pull("easy", [changed, changed])])
    assert report["per_pull"][0]["files_exact"] == 2
    assert report["per_pull"][0]["solved"] is True
    assert report["per_task_completion"] == 1.0


def test_one_file_right_is_not_a_solved_job():
    """The compounding, in the smallest form that can hold it.

    A person who has to redo the second file has not had the job done for them, whatever the first
    file scored. If this ever reports `solved` with a file outstanding, the instrument is measuring a
    lesson and calling it a task.
    """
    landing = ("def f(x):\n    return x < 10\n", "def f(x):\n    return x < 100\n")
    unreachable = ("class A:\n    def m(self, y):\n        return y\n",
                   "class A:\n    def m(self, y):\n        return y + 1\n")
    # Two files carry the same demonstrable edit, so one of them reproduces the other exactly; the
    # third is a class body the lesson has nothing to say about. One file lands, the job does not.
    report = chain.measure([_pull("one_of_three", [landing, landing, unreachable])])
    row = report["per_pull"][0]
    assert row["changed_files"] == 3
    # Both landing files reproduce each other exactly, so two of three land -- and the job is still
    # not done, because the class body was never touched.
    assert row["files_exact"] == 2
    assert row["files_edited"] == 2
    assert row["solved"] is False
    assert report["per_task_completion"] == 0.0
    # The per-file number is the generous one, and it is reported separately so the gap is visible.
    assert report["per_file_exactness"] == round(2 / 3, 4)


def test_a_pull_request_with_nothing_changed_is_not_a_free_success():
    """An untouched file is not evidence of a landed action. A job with no work in it must not be
    counted as a job the organ completed."""
    report = chain.measure([_pull("noop", [("def f():\n    return 1\n", "def f():\n    return 1\n")])])
    assert report["per_pull"][0]["solved"] is False
    assert report["per_task_completion"] == 0.0


def test_the_compounding_is_reported_from_the_measured_rate_not_a_guess():
    """`p**k` must be computed from the corpus's own per-file rate. Reporting a hand-typed curve would
    let the forecast drift away from the measurement it claims to follow."""
    report = chain.measure([_pull("easy", [
        ("def f(x):\n    return x < 10\n", "def f(x):\n    return x < 100\n")])])
    p = report["per_file_exactness"]
    assert report["the_compounding"]["measured_p"] == p
    assert report["the_compounding"]["at_k_2"] == round(p ** 2, 4)
    assert report["the_compounding"]["at_k_3"] == round(p ** 3, 4)


def test_the_committed_record_still_says_zero_of_eight():
    """Pins the document to the record.

    If a later round changes the organ, this test is allowed to fail -- and then the document's
    headline has to be rewritten to match, rather than the record being quietly re-run until it agrees.
    """
    if not RECORD.exists():                       # pragma: no cover - record is committed
        return
    record = json.loads(RECORD.read_text())
    assert record["authority"] == "NONE"
    assert record["pulls"] == 8
    assert record["tasks_solved"] == 0
    assert record["changed_files"] == 47
    assert record["files_exact"] == 1
    assert record["per_file_exactness"] == 0.0213
    assert record["per_task_completion"] == 0.0
