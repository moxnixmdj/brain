"""Tests for goal_closure_v1: real git states, no network, no model, no answer key.

The tests use tiny real repositories built with real git commands.  They check the two things
that matter: a literal goal is exploitable by a real plan, and the closure selected from one
task's judgments refuses the exploit on a different task without refusing a legitimate repair.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    baseline = dict(line.split() for line in out.splitlines() if line.strip())
    assert code == 0
    return target, baseline


def judge_for(target: str, baseline: dict[str, str], preserve: bool):
    return lambda p: BM.goal(p, target, preserve, baseline)


def test_reading_reports_facts_without_judging(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, _base = context(path)
    reading = GC.read_state(path, target)
    assert reading.get("ref.main") is not None
    assert reading.get("stash.count") == "0"
    assert reading.get("head.branch") == "main"
    assert reading.get("history.target_ancestor") == "yes"
    assert reading.get("content.README.rst") is not None
    assert reading.get("target.CHANGELOG.rst") is not None
    assert "verdict" not in reading.facts


def test_literal_goal_is_satisfied_by_dropping_the_stash(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, baseline = context(path)
    # Use the exact damaged clone the planner uses.
    task = BM.damage(tmp_path / "tasks", path, "stashed_wrong_branch")
    assert _run(task, "checkout", "-q", "main") == 0
    assert _run(task, "stash", "drop", "-q") == 0
    assert _run(task, "clean", "-fdq") == 0
    assert GC.literal_goal(task, target)[0] is True
    assert BM.goal(task, target, True, baseline)[0] is False


def test_stash_restore_rejects_the_exploit_and_accepts_a_rescue(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, baseline = context(path)
    start = BM.damage(tmp_path / "tasks", path, "stashed_wrong_branch")
    before = GC.read_state(start, target)

    exploit = tmp_path / "exploit"
    shutil_copy(start, exploit)
    assert _run(exploit, "checkout", "-q", "main") == 0
    assert _run(exploit, "stash", "drop", "-q") == 0
    assert GC.law_holds("stash_restore", before, GC.read_state(exploit, target), target, exploit) is False

    rescue = tmp_path / "rescue"
    shutil_copy(start, rescue)
    assert _run(rescue, "checkout", "-q", "main") == 0
    assert _run(rescue, "stash", "pop", "-q") == 0
    assert GC.law_holds("stash_restore", before, GC.read_state(rescue, target), target, rescue) is True


def shutil_copy(src: Path, dst: Path) -> None:
    import shutil
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)


def test_enumeration_finds_a_hole_and_selects_a_closure(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, baseline = context(path)
    start = BM.damage(tmp_path / "tasks", path, "stashed_wrong_branch")
    rows, edges = GC.enumerate_states(
        start, target, tmp_path / "ws", judge=judge_for(target, baseline, True),
        depth=3, edge_cap=120)
    plain = BM.damage(tmp_path / "plain-tasks", path, "wrong_branch")
    plain_rows, _ = GC.enumerate_states(
        plain, target, tmp_path / "plain-ws", judge=judge_for(target, baseline, False),
        depth=2, edge_cap=40)
    rows.extend(plain_rows)
    assert edges > 0
    assert any(r.verdict == "HOLE" for r in rows), "a literal goal must be exploitable"
    assert any(r.verdict == "LEGITIMATE" for r in rows), "a legitimate repair must be reachable"
    selection = GC.select_closure(rows, target)
    assert selection["status"] == "CLOSURE_FOUND"
    assert any("stash_restore" in c for c in selection["closures"])
    for closure in selection["closures"]:
        report = GC.evaluate(closure, rows, target)
        assert report["false_accepts"] == []
        assert report["false_rejects"] == []


def test_closure_selected_on_one_task_refuses_the_hole_on_another(tmp_path: Path) -> None:
    path = repo(tmp_path)
    target, baseline = context(path)
    rows = []
    for kind, preserve in (("stashed_wrong_branch", True),
                           ("conflict_and_stash", True), ("wrong_branch", False)):
        start = BM.damage(tmp_path / f"tasks-{kind}", path, kind)
        found, _edges = GC.enumerate_states(
            start, target, tmp_path / f"ws-{kind}", judge=judge_for(target, baseline, preserve),
            depth=3 if preserve else 2, edge_cap=120)
        rows.extend(found)
    assert any(r.verdict == "HOLE" for r in rows)
    selection = GC.select_closure(rows, target)
    assert selection["status"] == "CLOSURE_FOUND"
    for closure in selection["closures"]:
        report = GC.evaluate(closure, rows, target)
        assert report["false_accepts"] == []
        assert report["false_rejects"] == []


def test_law_verdicts_are_pure_when_the_duplicate_state_is_deleted(tmp_path: Path) -> None:
    """A deduplicated child directory is removed; its Reading must still decide the same way."""
    path = repo(tmp_path)
    target, _base = context(path)
    start = BM.damage(tmp_path / "tasks", path, "stashed_wrong_branch")
    before = GC.read_state(start, target)
    clone = tmp_path / "clone"
    shutil_copy(start, clone)
    assert _run(clone, "checkout", "-q", "main") == 0
    assert _run(clone, "stash", "drop", "-q") == 0
    after = GC.read_state(clone, target)
    verdicts = {law: GC.law_holds(law, before, after, target, clone) for law in GC.LAW_IDS}
    import shutil
    shutil.rmtree(clone)
    assert {law: GC.law_holds(law, before, after, target, clone) for law in GC.LAW_IDS} == verdicts
    assert verdicts["stash_restore"] is False


def test_closure_store_is_external_editable_and_deletable(tmp_path: Path) -> None:
    store = tmp_path / "store.json"
    report = {"selected_closure": ["ref_preserve"],
              "selection": {"status": "CLOSURE_FOUND"},
              "train_reference": {"repo": "local"}}
    written = GC.write_store(report, store)
    assert written["parameters"] == 0 and written["removable"] is True
    assert GC.read_store(store) == ["ref_preserve"]
    edited = json.loads(store.read_text())
    edited["laws"] = []
    store.write_text(json.dumps(edited))
    assert GC.read_store(store) == []
    store.unlink()
    with pytest.raises(FileNotFoundError):
        GC.read_store(store)


def test_no_hole_no_closure_and_unknown_law_fails_closed(tmp_path: Path) -> None:
    assert GC.select_closure([], "x")["status"] == "NO_HOLE_IN_TRAINING_SET"
    with pytest.raises(ValueError):
        GC.law_holds("made_up_law", GC.read_state(repo(tmp_path, "one"), "x"),
                     GC.read_state(repo(tmp_path, "two"), "x"), "x", tmp_path)
