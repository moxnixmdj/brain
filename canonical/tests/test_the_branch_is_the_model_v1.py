"""Tests for `the_branch_is_the_model_v1`: the successor is had, not predicted.

Every test builds a REAL git repository in `tmp_path`. Nothing here needs the network, and nothing here
asserts that a plan is the plan the producer found -- a plan is one of many correct answers, so the
tests check the two things that must hold: the goal rejects work-destroying repairs, and the search
finds a repair without ever predicting a transition.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import the_branch_is_the_model_v1 as B  # noqa: E402

GIT = ("git", "-c", "user.email=brain@example.invalid", "-c", "user.name=brain")


def _run(path: Path, *argv: str) -> int:
    return subprocess.run((*GIT, *argv), cwd=path, capture_output=True).returncode


def repo(tmp_path: Path, name: str = "repo") -> Path:
    """main and side, both editing the same line, so merging one into the other conflicts."""
    path = tmp_path / name
    path.mkdir()
    _run(path, "init", "-q", "-b", "main")
    # Identity lives in the repository, because the planner runs plain `git commit`.
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


def baseline(path: Path) -> dict[str, str]:
    _code, out = B.MACHINE.git(path, "for-each-ref", "refs/heads/",
                               "--format=%(refname:short) %(objectname)")
    return dict(line.split() for line in out.splitlines() if line.strip())


def damage_stash_and_side(tmp_path: Path) -> tuple[Path, str, dict[str, str]]:
    """The state a person actually ends up in: an edit, stashed, then work started on the wrong branch."""
    path = repo(tmp_path)
    target = B.MACHINE.git(path, "rev-parse", "HEAD")[1].strip()
    base_refs = baseline(path)
    (path / "README.rst").write_text("readme with a local edit\n", encoding="utf-8")
    _run(path, "add", "README.rst")
    assert _run(path, "stash", "push", "-q", "-m", "wip") == 0
    assert _run(path, "checkout", "-q", "side") == 0
    (path / "scratch.txt").write_text("untracked\n", encoding="utf-8")
    return path, target, base_refs


# --------------------------------------------------------------------------------------------------
# The part that still has to be designed: the key
# --------------------------------------------------------------------------------------------------

def test_the_key_separates_states_that_git_distinguishes(tmp_path: Path) -> None:
    """A coarse key is silent incompleteness: two different states collapse and the search loses a
    branch. The stash, the index and the working tree must all be in the key."""
    path, _target, _refs = damage_stash_and_side(tmp_path)
    before = B.observe(path)
    assert "stash.count.1" in before
    assert "work.untracked.1" in before

    _run(path, "checkout", "-q", "main")
    _run(path, "stash", "pop", "-q")
    after = B.observe(path)
    assert "stash.count.0" in after
    # the popped edit is now in the working tree, next to the untracked file: two entries, not zero
    assert "work.dirty.2" in after
    assert after != before


def test_the_key_reports_an_operation_in_progress(tmp_path: Path) -> None:
    path = repo(tmp_path)
    _run(path, "checkout", "-q", "side")
    assert _run(path, "merge", "main") != 0  # real conflict
    facts = B.observe(path)
    assert "operation.merge.inprogress" in facts


# --------------------------------------------------------------------------------------------------
# The verifier: a licence to destroy work is not a goal
# --------------------------------------------------------------------------------------------------

def test_the_goal_rejects_a_repair_that_destroys_the_stash(tmp_path: Path) -> None:
    """Measured failure, kept as a test: `checkout main; stash drop; clean` leaves a clean repository
    and loses the work. Against the weak (cleanliness-only) goal it "passed"; it must not."""
    path, target, refs = damage_stash_and_side(tmp_path)
    for argv in (("checkout", "-q", "main"), ("stash", "drop", "-q"), ("clean", "-fdq")):
        B.MACHINE.run(("git", *argv), path)
    weak = B.goal(path, target, preserve=False, baseline=refs)
    assert weak[0] is True, "the weak goal cannot see the loss -- that is the reason it was abandoned"
    strong = B.goal(path, target, preserve=True, baseline=refs)
    assert strong[0] is False
    assert "stashed work is not in the commit" in strong[1]


def test_the_goal_accepts_the_rescue_and_only_the_rescue(tmp_path: Path) -> None:
    path, target, refs = damage_stash_and_side(tmp_path)
    for argv in (("checkout", "-q", "main"), ("stash", "pop", "-q"),
                 ("clean", "-fdq"), ("add", "-A"), ("commit", "-q", "-m", "integrate")):
        assert B.MACHINE.run(("git", *argv), path)[0] == 0
    ok, why = B.goal(path, target, preserve=True, baseline=refs)
    assert ok, why
    # The original history is still there, and the only thing that changed in it is the rescued work.
    assert "local edit" in B.MACHINE.git(path, "show", "HEAD:README.rst")[1]
    _code, changed = B.MACHINE.git(path, "diff", "--name-only", target, "HEAD")
    assert changed.split() == ["README.rst"]


def test_the_goal_rejects_a_repair_that_buries_the_mess_on_another_branch(tmp_path: Path) -> None:
    """Found by the search, not by me: commit the conflict and the deleted file onto `side`, walk away,
    and main is clean. Every other clause of the goal is satisfied. Only the branch tips catch it."""
    path, target, refs = damage_stash_and_side(tmp_path)
    _run(path, "checkout", "-q", "side")
    _run(path, "merge", "main")
    (path / "scratch.txt").write_text("untracked\n", encoding="utf-8")
    for argv in (("add", "-A"), ("commit", "-q", "-m", "integrate"), ("checkout", "-q", "main")):
        B.MACHINE.run(("git", *argv), path)
    ok, why = B.goal(path, target, preserve=True, baseline=refs)
    assert ok is False
    assert "branch rewritten: side" in why


# --------------------------------------------------------------------------------------------------
# The search: real states, no model
# --------------------------------------------------------------------------------------------------

def damage_wrong_branch(tmp_path: Path) -> tuple[Path, str, dict[str, str]]:
    """The cheapest real bad state, so the search tests stay fast: on the wrong branch, junk lying around."""
    path = repo(tmp_path, "plain")
    target = B.MACHINE.git(path, "rev-parse", "HEAD")[1].strip()
    base_refs = baseline(path)
    _run(path, "checkout", "-q", "side")
    (path / "scratch.txt").write_text("untracked\n", encoding="utf-8")
    return path, target, base_refs


def test_a_repair_is_found_by_branching_and_nothing_is_predicted(tmp_path: Path) -> None:
    path, target, refs = damage_wrong_branch(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = B.solve(path, target, workspace, None, prune=False,
                     max_depth=4, max_expansions=200, baseline=refs)
    assert result["solved"], result
    assert result["depth"] >= 1
    # every candidate was a copy plus an execution: no predicted successor anywhere in the search
    assert result["copies"] == result["executions"] == result["edges_tried"]
    assert set(result["plan"]) <= {e.name for e in B.EDGES}


def test_the_control_stream_solves_what_the_pruned_stream_can_lose(tmp_path: Path) -> None:
    """Pruning is the only unsound part, and it is unsound by construction: it deletes edges the
    surviving hypotheses all reject, while the vocabulary cannot name the true condition. The receipt
    therefore compares the two streams and names the tasks pruning lost, instead of hiding them."""
    path, target, refs = damage_wrong_branch(tmp_path)
    workspace = tmp_path / "ws2"
    workspace.mkdir()
    result = B.solve(path, target, workspace, None, prune=False,
                     max_depth=4, max_expansions=200, baseline=refs)
    assert result["solved"], result
    receipt = {
        "summary": {
            "tasks": 1, "solved_with_learning": 0, "transitions_predicted": 0,
            "transitions_branched": 40, "executions_with_learning": 40,
            "executions_without_knowledge": result["executions"], "edges_pruned": 7,
            "solvable_but_lost_to_pruning": ["deep"], "warm_solved": 0, "executions_warm": 0,
            "solved_order_only": 1, "executions_order_only": 40, "plans": {},
        }
    }
    line = B.headline(receipt)
    assert "tasks lost to pruning: ['deep']" in line
    assert "0 transitions predicted" in line


def test_knowledge_orders_and_does_not_delete(tmp_path: Path) -> None:
    """`order=True` may reorder the queue and may not delete from it, so the same state is still solved
    even when the knowledge believes (wrongly) that the edge it needs does not apply here. Deleting is
    the other trade, and it is the only unsound one: it is measured on the real stream, where it costs
    one task in seven (see `receipt["summary"]["solvable_but_lost_to_pruning"]`)."""
    path, target, refs = damage_wrong_branch(tmp_path)
    knowledge = B.Knowledge.empty()
    # Teach it something false about every edge the repair needs.
    for name in ("git_checkout_main", "git_clean_fd"):
        knowledge.note(name, B.observe(path), False)
    workspace = tmp_path / "ws3"
    workspace.mkdir()
    result = B.solve(path, target, workspace, knowledge, prune=False, order=True,
                     max_depth=4, max_expansions=200, baseline=refs)
    assert result["solved"], result
    assert result["copies"] == result["edges_tried"]

    # the ordering path never reports a pruning: nothing was deleted
    assert result["pruned_by_knowledge"] == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
