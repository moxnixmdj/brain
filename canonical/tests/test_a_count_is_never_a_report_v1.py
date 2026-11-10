"""A counting question answered by a literature search is not a pass.

THE DEFECT THIS PINS (measured 2026-11-09)
------------------------------------------
`resolve("how many unique lines in data.txt")` on a root where `data.txt` DOES NOT EXIST
returned:

    pass=True, layer=UNDERSTAND_BUILT_ANSWER,
    answer={schema: PROJECT_BRAIN_INSPECT_V1, hits: [...40 grep matches...], ...}

No number anywhere. The door had answered "how many unique lines are in data.txt" by
searching the repository for the WORDS "unique" and "lines" and returning the matches as a
verified answer. That is the wrong question executed correctly and reported as success --
precisely the failure mode this project exists to refuse, and it survived round 33's
no-answer guard because that guard only fired when the answer was None, and an inspection
report is not None.

The guard must bind to the ANSWER'S SHAPE, not merely its presence.
"""
from __future__ import annotations

import pathlib

import pytest

from canonical.runtime import brain_one_model_v3 as model

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_a_phantom_file_count_does_not_pass_as_a_search_report():
    out = model.resolve("how many unique lines in data.txt", root=str(ROOT))
    assert out["pass"] is False, out.get("answer")
    assert out["status"] == "FAIL_CLOSED__EXECUTION_PRODUCED_NO_ANSWER"


def test_a_structured_report_is_never_accepted_as_a_count():
    out = model.resolve("how many unique lines in data.txt", root=str(ROOT))
    answer = out.get("answer")
    # A refusal carries no answer key at all, or None -- never a report standing in for one.
    assert "answer" not in out or answer is None


def test_a_question_naming_nothing_in_the_tree_refuses_by_name():
    out = model.resolve("how many unique lines in nonexistent_zzz.txt", root=str(ROOT))
    assert out["pass"] is False
    assert "INPUT_BINDING_REQUIRED" in (out.get("status") or "")


def test_the_real_count_still_answers_as_a_number(tmp_path):
    target = tmp_path / "pd.txt"
    target.write_text("a b\nc d\na b\n", encoding="utf-8")
    rel = target.relative_to(tmp_path)
    out = model.resolve(f"how many unique lines in {rel}", root=str(tmp_path))
    assert out["pass"] is True, out.get("status")
    assert out["answer"] == 2
    assert isinstance(out["answer"], int) and not isinstance(out["answer"], bool)


def test_a_stated_command_is_not_treated_as_a_counting_question(tmp_path):
    """The narrowest regression: `sort -u` has no query_kind, so the count rule must not
    touch it. Dropping the `_asked_to_count` conjunction once made every stated command
    with no extracted answer refuse -- this is the test that catches that edit."""
    (tmp_path / "data.txt").write_text("svc-0\nsvc-1\n", encoding="utf-8")
    out = model.resolve("sort -u data.txt", root=str(tmp_path), execute=True)
    assert out["pass"] is True, out.get("detail")
    assert out["layer"] == "ADMITTED_CONFINEMENT"
