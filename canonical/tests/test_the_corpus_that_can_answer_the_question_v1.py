"""The corpus builder's own tests: the selection must be blind, and the gate must be the project's.

Nothing here measures a fix. These tests pin the two properties the measurement depends on:

  * a candidate is chosen by STRUCTURE -- one source file, one test file, one removed and one added
    line -- and the builder never runs, imports or judges the code it selects;
  * a task is admitted only by the project's OWN verdict: the commit's test fails on the parent and
    the same tests pass at the commit. A file that already passed on the parent is rejected with the
    reason, not admitted because the commit touched a test.

The git fixture is a throw-away two-commit repository built by the test itself. It is a test of the
instrument, not a corpus: every number in the round's receipts comes from real project history.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(TOOLS.parents[1]) not in sys.path:
    sys.path.insert(0, str(TOOLS.parents[1]))

import the_corpus_that_can_answer_the_question_v1 as corpus  # noqa: E402


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def _commit(repo: pathlib.Path, message: str) -> str:
    _git(repo, "add", "-A")
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "commit", "-q", "-m", message], check=True, capture_output=True)
    return _git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture()
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "proj").mkdir()
    (root / "tests").mkdir()
    (root / "proj" / "__init__.py").write_text("")
    (root / "proj" / "core.py").write_text("def twice(x):\n    return x + x\n")
    (root / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(2) == 4\n")
    _commit(root, "first")
    return root


def test_a_test_is_recognised_by_where_the_project_keeps_it() -> None:
    assert corpus.is_test("tests/test_core.py")
    assert corpus.is_test("proj/test_inner.py")
    assert not corpus.is_test("proj/core.py")
    assert corpus.is_source("proj/core.py")
    assert not corpus.is_source("tests/test_core.py")


def test_one_changed_expression_is_a_candidate(repo: pathlib.Path) -> None:
    (repo / "proj" / "core.py").write_text("def twice(x):\n    return x * x\n")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(3) == 9\n")
    commit = _commit(repo, "square")
    entry, stage = corpus.shape_candidate(repo, commit)
    assert stage == "CANDIDATE", stage
    assert entry is not None
    assert entry["sources"] == ["proj/core.py"]
    assert entry["tests"] == ["tests/test_core.py"]
    # `    return x * x` is not an expression under `mode="eval"`; the site is the expression inside the
    # same statement kind, and that is what this flag records.
    assert entry["expression_pair"] is True
    assert entry["new_line"] == "return x * x"
    assert entry["old_line"] == "return x + x"


def test_two_changed_lines_are_refused_with_the_line_count(repo: pathlib.Path) -> None:
    (repo / "proj" / "core.py").write_text("def twice(x):\n    y = x\n    return y + y\n")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(3) == 9\n")
    commit = _commit(repo, "two lines")
    entry, stage = corpus.shape_candidate(repo, commit)
    assert entry is None
    assert stage.startswith("NOT_ONE_LINE"), stage


def test_a_source_change_without_a_test_change_is_refused(repo: pathlib.Path) -> None:
    (repo / "proj" / "core.py").write_text("def twice(x):\n    return x * 2\n")
    commit = _commit(repo, "source only")
    entry, stage = corpus.shape_candidate(repo, commit)
    assert entry is None
    assert stage == "NO_TEST_FILE", stage


def test_a_statement_form_change_is_admitted_and_marked_not_an_expression_pair(
        repo: pathlib.Path) -> None:
    """The engine decides the class; the miner only records whether the form changed."""
    (repo / "proj" / "core.py").write_text("def twice(x):\n    raise ValueError(x)\n")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(3) == 9\n")
    commit = _commit(repo, "raise instead of return")
    entry, stage = corpus.shape_candidate(repo, commit)
    assert stage == "CANDIDATE", stage
    assert entry["expression_pair"] is False


def test_the_gate_admits_only_what_the_project_repairs_and_names_what_it_does_not(
        repo: pathlib.Path) -> None:
    # A commit whose test fails on the parent and passes at the commit is a task.
    (repo / "proj" / "core.py").write_text("def twice(x):\n    return x * x\n")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(3) == 9\n")
    commit = _commit(repo, "square")
    entry, stage = corpus.shape_candidate(repo, commit)
    assert stage == "CANDIDATE"
    admitted, verdict = corpus._gate_one_file(repo, dict(entry), seconds=60)
    assert verdict == "ADMITTED", verdict
    assert admitted["failing"], "the failing node must be recorded, not inferred later"

    # A commit whose test already passes on the parent is refused, and the reason is the verdict.
    (repo / "proj" / "core.py").write_text("def twice(x):\n    return x + x\n")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(2) == 4\n")
    commit2 = _commit(repo, "no behavioural change")
    entry2, stage2 = corpus.shape_candidate(repo, commit2)
    assert stage2 == "CANDIDATE", stage2
    _entry, verdict2 = corpus._gate_one_file(repo, dict(entry2), seconds=60)
    assert verdict2 == "PARENT_PASSES", verdict2


def test_the_gate_reads_every_test_file_the_commit_changed(repo: pathlib.Path) -> None:
    """The first test file a commit changed is not necessarily the one that carries the failure."""
    (repo / "proj" / "core.py").write_text("def twice(x):\n    return x * x\n")
    (repo / "tests" / "test_other.py").write_text("def test_other():\n    assert True\n")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(3) == 9\n")
    commit = _commit(repo, "triple, with an unrelated test")
    entry, stage = corpus.shape_candidate(repo, commit)
    assert stage == "CANDIDATE", stage
    assert len(entry["tests"]) == 2
    _entry, verdict = corpus.gate_one(repo.parent, dict(entry), seconds=60)
    assert verdict == "ADMITTED", verdict


def test_the_written_corpus_keeps_the_selection_reasons(repo: pathlib.Path) -> None:
    (repo / "proj" / "core.py").write_text("def twice(x):\n    return x * 2\n")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import twice\n\n\ndef test_twice():\n    assert twice(3) == 9\n")
    commit = _commit(repo, "triple")
    out = repo.parent / "corpus.json"
    receipt = repo.parent / "receipt.json"
    code = corpus.main(["--stage", "shape", "--repos", str(repo), "--repos-root", str(repo.parent),
                        "--scan", "10", "--cap", "10", "--out", str(out), "--receipt", str(receipt)])
    assert code == 0
    payload = json.loads(out.read_text())
    assert payload["schema"] == corpus.SCHEMA
    assert any(row["commit"] == commit for row in payload["tasks"])
    assert "shape_stages" in json.loads(receipt.read_text())["totals"]
