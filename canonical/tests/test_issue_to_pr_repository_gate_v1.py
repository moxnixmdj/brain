# PROJECT_BRAIN
"""A PR verdict scoped to source_root must say so; a repository verdict must
run the repository's suite.

Pinned defect (2026-10-28): ``verified: true`` after a rename whose only
consumer test lived outside source_root.  Real pytest runs, no mocks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch

ROOT = Path(__file__).resolve().parents[2]


def _fixture(root: Path, outside_test: str | None) -> None:
    (root / "proj" / "src" / "tests").mkdir(parents=True)
    (root / "proj" / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "proj" / "src" / "tests" / "test_calc.py").write_text(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    (root / "proj" / "tests").mkdir()
    (root / "proj" / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n")
    if outside_test is not None:
        (root / "proj" / "tests" / "test_outside.py").write_text(outside_test)
    (root / "task.json").write_text(json.dumps({
        "issue_id": "SCOPE-1", "title": "Rename add to sum_values",
        "edits": [{"op": "rename_symbol", "module": "calc.py", "name": "add",
                   "new_name": "sum_values"}]}))


def _args(repository_root: str | None) -> dict:
    args = {"task_path": "task.json", "source_root": "proj/src", "worktree_path": "worktree",
            "output_path": "out/summary.json", "diff_path": "out/change.diff",
            "pr_intent_path": "out/pr.json", "python_executable": sys.executable, "timeout_s": 60}
    if repository_root:
        args["repository_root"] = repository_root
    return args


OUTSIDE = ("import sys, pathlib\n"
           "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))\n"
           "from calc import add\n\ndef test_outside_add():\n    assert add(1, 1) == 2\n")


def test_without_repository_root_the_verdict_is_scoped_and_labelled(tmp_path: Path):
    _fixture(tmp_path, OUTSIDE)
    result = orch.run(_args(None), tmp_path)
    assert result["verified"] is True
    assert result["verified_scope"] == "source_root"
    assert result["repository_gate"] == {"gate": "NOT_REQUESTED"}


def test_repository_root_catches_the_consumer_outside_source_root(tmp_path: Path):
    _fixture(tmp_path, OUTSIDE)
    result = orch.run(_args("proj"), tmp_path)
    assert result["edits_verified"] is True
    assert result["verified"] is False
    assert result["verified_scope"] == "none"
    gate = result["repository_gate"]
    assert gate["gate"] == "FAIL", gate
    assert gate["tests_failed"] >= 1
    report = json.loads((tmp_path / gate["output_path"]).read_text())
    assert any("test_outside" in t for t in report["failing_tests"])
    assert "tests/test_smoke.py" in report["test_files"]
    # the anchored diff addresses files relative to the repository root
    anchored = (tmp_path / gate["diff_path"]).read_text()
    assert "--- a/src/calc.py" in anchored and "+++ b/src/calc.py" in anchored
    # and the repository itself was never mutated
    assert (tmp_path / "proj" / "src" / "calc.py").read_text() == "def add(a, b):\n    return a + b\n"


def test_repository_root_passes_when_the_whole_suite_is_green(tmp_path: Path):
    _fixture(tmp_path, None)
    result = orch.run(_args("proj"), tmp_path)
    assert result["verified"] is True
    assert result["verified_scope"] == "repository"
    gate = result["repository_gate"]
    assert gate["gate"] == "PASS" and gate["tests_discovered"] >= 2
    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert summary["repository_gate"]["gate"] == "PASS"


def test_repository_root_that_does_not_contain_source_root_is_refused(tmp_path: Path):
    _fixture(tmp_path, None)
    (tmp_path / "elsewhere").mkdir()
    result = orch.run(_args("elsewhere"), tmp_path)
    assert result["verified"] is False
    assert result["repository_gate"]["gate"] == "REFUSED:SOURCE_ROOT_OUTSIDE_REPOSITORY_ROOT"
