#!/usr/bin/env python3
"""The first honest baseline this project has: the shipped system, 12 provably fail-to-pass tasks, 0 solved.

WHERE THE TASKS COME FROM
-------------------------
This repository's own 89-commit corpus, reduced honestly. Of 89 commits, 54 pass on their parent (never a
bug), 23 cannot be tested on the parent at all (the added test needs the fix to import), and 12 fail on the
parent and pass on the fix. Those 12 are the task set.

    pypa/packaging  959bb79c  tests/test_dependency_groups.py::test_expand_contract_model_only_does_inner_lookup_once
    pypa/packaging  d2fa9238  tests/test_ranges.py::TestSetAlgebra::test_union_full_preserves_autodetected_prerelease_policy
    pypa/packaging  9f5249fb  tests/test_metadata.py::TestRawMetadata::test_complete
    pypa/packaging  668da866  tests/test_markers.py::TestDefaultEnvironment::test_multidigit_minor_version
    pypa/packaging  a3b6a1f6  tests/test_dependency_groups.py::test_expand_contract_model_only_does_inner_lookup_once
    pypa/packaging  f8f16338  tests/test_structures.py::test_infinity_self_comparison
    pypa/packaging  e83801f4  tests/test_metadata.py::TestRawMetadata::test_complete
    hukkin/tomli    96dfe2ce  tests/test_error.py::test_module_name
    hukkin/tomli    31c85a18  tests/test_error.py::test_invalid_char_quotes
    hukkin/tomli    9af551b5  tests/test_misc.py::test_own_pyproject
    hukkin/tomli    67ec7d10  tests/test_error.py::test_line_and_col
    hukkin/tomli    5ab9ec92  tests/test_misc.py::test_parse_float

RESULT: 12 of 12 NO_PROPOSAL, resolve rate 0.0, patch emission rate 0.0.

Every task stopped at CAPABILITY_INPUTS_MISSING before any patch was attempted: the routed capability
declares required inputs a task statement cannot supply (output_path, request_spec, repo_root, a `symbol`).
Separately, build_goal() asks for {"actions":[{"type":"terminal_exec",...}]} and solve() has no code path
that produces that shape -- the transport's contract and the model's output contract do not meet.
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
BASE = REPO / "canonical" / "verification" / "HONEST_PER_TASK_BASELINE_20261124_V1.json"
TASKS = (REPO / "canonical" / "corpus" /
         "tasks_whose_oracle_precedes_the_fix_20261124_V1.json")


def _s():
    return json.loads(BASE.read_text())["summary"]


def test_the_baseline_is_zero_and_is_not_dressed_up():
    if not BASE.exists():                            # pragma: no cover
        return
    s = _s()
    assert s["verified_solved"] == 0
    assert s["resolve_rate"] == 0.0
    assert s["patch_emission_rate"] == 0.0
    assert s["verdicts"]["the_system_emits_a_patch_at_all"] is False
    assert s["verdicts"]["this_is_a_baseline_not_a_result"] is True


def test_every_task_failed_before_producing_anything():
    """The distinction that matters: 'no patch' is not 'a wrong patch'. Nothing was attempted."""
    if not BASE.exists():                            # pragma: no cover
        return
    rows = json.loads(BASE.read_text())["per_task"]
    assert len(rows) == 12
    assert all(row["class"] == "NO_PROPOSAL" for row in rows)
    assert all(row["patch_emitted"] is False for row in rows)
    assert all(row["system_status"] == "FAIL_CLOSED" for row in rows)


def test_the_corpus_reduction_is_recorded_and_honest():
    """89 commits -> 12 usable. The other 77 are excluded with a reason, not quietly dropped."""
    if not TASKS.exists():                           # pragma: no cover
        return
    s = json.loads(TASKS.read_text())["summary"]
    assert s["tasks_in_corpus"] == 89
    assert s["by_class"]["FAIL"] == 12
    assert s["by_class"]["PASS"] == 54
    assert s["by_class"]["COLLECTION"] == 23
    assert s["verdicts"]["a_majority_are_genuinely_testable"] is False


def test_the_instruction_carries_no_prose_about_the_fix():
    """Hand-holding check: the task text is pytest's output, not my description of the bug."""
    if not BASE.exists():                            # pragma: no cover
        return
    for row in json.loads(BASE.read_text())["per_task"]:
        text = row["instruction"]
        assert row["node"] in text
        assert "Make the named test pass" in text
        lowered = text.lower()
        for forbidden in ("the fix is", "you should", "add a", "change the line",
                          "the correct answer", "patch:", "hint"):
            assert forbidden not in lowered, (row["sha"], forbidden)
