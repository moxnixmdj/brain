"""Tests for deriving a verifier from one observed origin: no supplied task predicate."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import one_origin_derives_the_judge_v1 as O  # noqa: E402
from canonical.tools import the_branch_is_the_model_v1 as BM  # noqa: E402

GIT = ("git", "-c", "user.email=brain@example.invalid", "-c", "user.name=brain")


def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    assert subprocess.run((*GIT, "init", "-q", "-b", "main"), cwd=path).returncode == 0
    subprocess.run((*GIT, "config", "user.email", "brain@example.invalid"), cwd=path, check=True)
    subprocess.run((*GIT, "config", "user.name", "brain"), cwd=path, check=True)
    (path / "README.rst").write_text("original\n", encoding="utf-8")
    (path / "CHANGELOG.rst").write_text("changelog\n", encoding="utf-8")
    subprocess.run((*GIT, "add", "-A"), cwd=path, check=True)
    subprocess.run((*GIT, "commit", "-q", "-m", "base"), cwd=path, check=True)
    subprocess.run((*GIT, "checkout", "-q", "-b", "side"), cwd=path, check=True)
    (path / "README.rst").write_text("side line\n", encoding="utf-8")
    subprocess.run((*GIT, "add", "-A"), cwd=path, check=True)
    subprocess.run((*GIT, "commit", "-q", "-m", "side"), cwd=path, check=True)
    subprocess.run((*GIT, "checkout", "-q", "main"), cwd=path, check=True)
    return path


def context(path: Path) -> tuple[str, dict[str, str]]:
    target = BM.MACHINE.git(path, "rev-parse", "HEAD")[1].strip()
    code, out = BM.MACHINE.git(path, "for-each-ref", "refs/heads/",
                               "--format=%(refname:short) %(objectname)")
    return target, dict(line.split() for line in out.splitlines() if line.strip())


def _apply(start: Path, steps: tuple[str, ...], workspace: Path, label: str) -> Path:
    current = start
    for name in steps:
        edge = next(e for e in BM.EDGES if e.name == name)
        applied, child, _ = BM.try_edge(current, edge, workspace, f"{label}-{name}")
        assert applied and child is not None
        current = child
    return current


def test_derived_judge_rejects_dropped_stash_and_accepts_restored_work(tmp_path: Path) -> None:
    base = repo(tmp_path)
    target, _baseline = context(base)
    start = BM.damage(tmp_path / "task", base, "stashed_wrong_branch")
    reference = GC.reference_tree(start, target)
    origin = GC.read_state(start, target, reference)
    judge = O.derived_judge(origin, target)
    assert judge(start)[0] is False

    dropped = _apply(start, ("git_stash_drop", "git_checkout_main"), tmp_path / "ws-drop", "drop")
    restored = _apply(start, ("git_checkout_main", "git_stash_pop", "git_clean_fd", "git_add_all",
                              "git_commit"), tmp_path / "ws-restore", "restore")
    assert judge(dropped)[0] is False
    assert judge(restored)[0] is True


def test_derived_judge_repairs_the_contradictory_goal_without_a_task_name(tmp_path: Path) -> None:
    base = repo(tmp_path)
    target, _baseline = context(base)
    start = BM.damage(tmp_path / "task", base, "stashed_wrong_branch")
    reference = GC.reference_tree(start, target)
    repair = O._origin_rows(start, target, tmp_path / "ws", reference)
    assert repair["verdict"] == "GOAL_REPAIRED"
    assert repair["drop"] == ["head"]
    assert repair["holes"] > 0 and repair["legitimate"] > 0
    selection = GC.select_closure(repair["rows"], target)
    assert "stash_restore" in selection["closures"][0]
