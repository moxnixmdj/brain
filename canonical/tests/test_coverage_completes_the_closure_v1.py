"""Tests for coverage_completes_the_closure_v1: real git states, no network, no model.

The tests check the two new moves: a law that no judged hole violates is reported as UNCONSTRAINED,
and a contradictory literal goal is repaired by the smallest clause deletion that produces both a
hole and a legitimate state.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import coverage_completes_the_closure_v1 as C  # noqa: E402
from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import the_branch_is_the_model_v1 as BM  # noqa: E402

GIT = ("git", "-c", "user.email=brain@example.invalid", "-c", "user.name=brain")


def _run(path: Path, *argv: str) -> int:
    return subprocess.run((*GIT, *argv), cwd=path, capture_output=True).returncode


def repo(tmp_path: Path, name: str = "repo") -> Path:
    path = tmp_path / name
    path.mkdir()
    assert _run(path, "init", "-q", "-b", "main") == 0
    _run(path, "config", "user.email", "brain@example.invalid")
    _run(path, "config", "user.name", "brain")
    (path / "README.rst").write_text("shared line\n", encoding="utf-8")
    (path / "CHANGELOG.rst").write_text("changelog\n", encoding="utf-8")
    _run(path, "add", "-A")
    _run(path, "commit", "-q", "-m", "base")
    _run(path, "checkout", "-q", "-b", "side")
    (path / "README.rst").write_text("side line\n", encoding="utf-8")
    _run(path, "add", "-A")
    _run(path, "commit", "-q", "-m", "side")
    _run(path, "checkout", "-q", "main")
    (path / "README.rst").write_text("main line\n", encoding="utf-8")
    _run(path, "add", "-A")
    _run(path, "commit", "-q", "-m", "main")
    return path


def context(path: Path) -> tuple[str, dict[str, str]]:
    target = BM.MACHINE.git(path, "rev-parse", "HEAD")[1].strip()
    code, out = BM.MACHINE.git(path, "for-each-ref", "refs/heads/",
                               "--format=%(refname:short) %(objectname)")
    return target, dict(line.split() for line in out.splitlines() if line.strip())


def test_audit_names_a_law_no_hole_violated() -> None:
    origin = GC.Reading(facts={"stash_content.README.rst": "abc", "ref.main": "1", "ref.side": "2"})
    post = GC.Reading(facts={"content.README.rst": "abc", "ref.main": "1", "head.branch": "main"})
    rows = [GC.Judgment(origin, post, Path("."), "HOLE", ("a",))]
    report = C.audit(rows, "1")
    assert report["stash_restore"]["holes_violating"] == 0
    assert report["stash_restore"]["status"] == "UNCONSTRAINED"
    assert report["ref_preserve"]["status"] == "CONSTRAINED"


def test_literal_goal_clauses_can_be_dropped_one_at_a_time(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, _base = context(path)
    damaged = BM.damage(tmp_path / "tasks", path, "stashed_wrong_branch")
    assert C.literal_goal(damaged, target)[0] is False
    assert C.literal_goal(damaged, target, frozenset({"head"}))[0] is False
    assert C.literal_goal(damaged, target, frozenset({"head", "stash", "clean", "branch"}))[0] is True


def test_minimal_goal_repair_finds_a_one_clause_weakening(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, baseline = context(path)
    start = BM.damage(tmp_path / "tasks", path, "stashed_wrong_branch")
    ref = GC.reference_tree(start, target)
    repair = C.repair_goal(start, target, tmp_path / "ws",
                           lambda p: BM.goal(p, target, True, baseline),
                           ref, depth=6, cap=600)
    assert repair["verdict"] == "GOAL_REPAIRED"
    assert len(repair["drop"]) == 1
    assert repair["holes"] > 0 and repair["legitimate"] > 0


def test_refit_with_constructed_rows_selects_the_stash_law(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, baseline = context(path)
    start = BM.damage(tmp_path / "tasks", path, "stashed_wrong_branch")
    ref = GC.reference_tree(start, target)
    repair = C.repair_goal(start, target, tmp_path / "ws",
                           lambda p: BM.goal(p, target, True, baseline),
                           ref, depth=6, cap=600)
    assert repair["rows"]
    selection = GC.select_closure(repair["rows"], target)
    assert selection["status"] == "CLOSURE_FOUND"
    assert "stash_restore" in selection["closures"][0]
    for closure in selection["closures"]:
        evaluation = GC.evaluate(closure, repair["rows"], target)
        assert evaluation["false_accepts"] == []
        assert evaluation["false_rejects"] == []
