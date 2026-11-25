#!/usr/bin/env python3
"""The first emission point in this project: from a failing test to a unified diff, no model, no container.

    v32 baseline   0 of 12 solved   0 of 12 emitted   0 patches
    v33            0 of 12 solved   1 of 12 emitted   1 patch

One number moved: emission. Resolution did not. That is the honest result and the suite pins it.

Two mechanisms survived contact with real code:
    MISSING_KEYWORD    add the keyword to the entry point and thread it to the state class that consumes it
    MISSING_ATTRIBUTE  initialise the missing attribute from the sibling collection the class maintains

Everything else refused, with a reason per task. The refusals are the finding: five of the twelve state a fact
about a VALUE the code produced, and a structural mechanism cannot express a change to what code computes.

THE INTEGRITY DEFECT, RECORDED RATHER THAN DELETED
--------------------------------------------------
The first version of this generator edited `tests/test_misc.py` and `benchmarks/resolver.py`, because pytest's
short traceback names the test frame and my localiser accepted any project frame. A patch to the test is a
patch to the oracle -- the exact violation this project refuses. It also reported `git diff` across the whole
tree, which included the oracle patch applied to make the node runnable, so the "produced patch" contained the
test it was supposed to pass. Both are now guarded at the writer, and the tests below fail if either returns.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "canonical" / "tools"), str(REPO)]
import emission_point_v1 as emit  # noqa: E402

ARTIFACT = REPO / "canonical" / "corpus" / "emission_point_20261124_V1.json"


def _s():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_it_emits_where_the_baseline_emitted_nothing():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    s = _s()
    assert s["verdicts"]["the_system_emits_a_patch"] is True
    assert s["emitted"] if "emitted" in s else s["emission_rate"] > 0


def test_it_solves_nothing_and_does_not_claim_otherwise():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    s = _s()
    assert s["solved"] == 0
    assert s["resolve_rate"] == 0.0
    assert s["verdicts"]["it_beats_the_zero_baseline"] is False
    assert s["verdicts"]["it_generalises"] is False


def test_the_writer_refuses_any_patch_to_the_oracle(tmp_path):
    """The integrity guard, tested directly rather than trusted."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    (tmp_path / "src.py").write_text("x = 1\n")
    assert emit.is_writable(tmp_path / "src.py", tmp_path) is True
    assert emit.is_writable(tmp_path / "tests" / "test_x.py", tmp_path) is False
    assert emit.is_writable(tmp_path / "conftest.py", tmp_path) is False


def test_no_recorded_task_edit_lives_under_tests():
    """The v32/v33 artifact must contain no diff inside a test file."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    for row in json.loads(ARTIFACT.read_text())["per_task"]:
        diff = row.get("diff") or ""
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                target = line[len("+++ b/"):]
                assert not target.startswith("tests/"), (row["sha"], target)
                assert "test_" not in target.split("/")[-1], (row["sha"], target)


def test_every_task_has_a_recorded_outcome_and_reason():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    rows = json.loads(ARTIFACT.read_text())["per_task"]
    assert len(rows) == 12
    for row in rows:
        assert row["class"] in {"SOLVED", "EMITTED__STILL_FAILING", "REFUSED", "APPLY_FAILED",
                                "CLONE_FAILED", "ERROR"}
        assert row.get("why"), row["sha"]


def test_the_conclusion_names_the_real_wall():
    """Not 'the generator cannot reach the program' but 'it has no operator that expresses the change'."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    text = _s()["the_honest_conclusion"]
    assert "operator" in text
    assert "behavioural" in text
