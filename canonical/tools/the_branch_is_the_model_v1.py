#!/usr/bin/env python3
"""The branch is the model: one execution yields both the decision and the successor state.

WHAT THIS DELETES. `environment_learning_v1` learns a transition model `(state, action) -> state` by
acting, then plans a shortest path over the model. The model is the expensive part: it needs coverage,
it is wrong wherever it has not been tried, and 2026's own agents build one anyway -- WEVA carries a
learned world model and reports verified lookahead as the gain, NSPI puts a learned verifier in front of
every mutating step. All of that is machinery for *predicting* a consequence.

On a computer you do not have to predict. You can **branch**: copy the state, run the action, read the
exit status. That single execution answers two questions at once --

    does this action apply here?    (the exit status)
    what state does it produce?    (the copy you are holding)

so the successor is not predicted, it is *had*, exactly. The planner therefore needs no model at all: it
searches over real states, and every edge costs one copy and one execution. "The best part is no part"
applied to planning -- the part that is deleted is the world model.

WHAT IT COSTS, AND WHERE IT SAVES. The price per edge is measured (copy + execution). The saving comes
from the conditions learned in earlier tasks: an action whose condition is known not to hold here is
skipped without a copy, so the branching factor falls as the same environment is met again. That is the
"learn once, use permanently" claim, measured end to end rather than asserted -- and it has a known cost,
because pruning on learned conditions can make a planner INCOMPLETE. So every task is solved twice, once
with pruning and once without, and the two answers are compared. If pruning ever turns a solvable task
unsolvable, that is the finding, and it is counted.

THE TASK. Not a fixture. A real repository is put into a real bad state by running real commands, and the
goal is checked by the repository's own queries -- on `main`, nothing in progress, no stash, clean tree,
at the commit it started from. No annotation says how many steps it takes or which they are.

Authority NONE. Producer-run measurement; no model, no parameters, no network beyond one clone.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Any, Sequence

SCHEMA = "BRAIN_THE_BRANCH_IS_THE_MODEL_V1"

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.tools import the_precondition_is_not_in_the_trace_v1 as MACHINE  # noqa: E402
from canonical.tools.what_a_decision_costs_v1 import decisive  # noqa: E402


@dataclass(frozen=True)
class Edge:
    """One real action the planner may take."""

    name: str
    argv: tuple[str, ...]


#: The agent's repertoire. Real programs, no wrappers, no dry runs: each one changes the state, and the
#: exit status is the only thing that says whether it applied.
EDGES: tuple[Edge, ...] = (
    Edge("git_merge_abort", ("git", "merge", "--abort")),
    Edge("git_rebase_abort", ("git", "rebase", "--abort")),
    Edge("git_checkout_main", ("git", "checkout", "-q", "main")),
    Edge("git_stash_pop", ("git", "stash", "pop", "-q")),
    Edge("git_stash_drop", ("git", "stash", "drop", "-q")),
    Edge("git_checkout_discard", ("git", "checkout", "--", ".")),
    Edge("git_clean_fd", ("git", "clean", "-fdq")),
    Edge("git_add_all", ("git", "add", "-A")),
    Edge("git_commit", ("git", "commit", "-q", "-m", "integrate")),
    Edge("git_branch_force_delete", ("git", "branch", "-D", "feature")),
)


# --------------------------------------------------------------------------------------------------
# The state, as the agent can see and check it
# --------------------------------------------------------------------------------------------------

def observe(path: pathlib.Path) -> tuple[str, ...]:
    """Everything the agent can read about a state with cheap commands. Not the goal test."""
    facts = set(MACHINE.sense(path))
    code, out = MACHINE.git(path, "rev-parse", "--abbrev-ref", "HEAD")
    facts.add("head." + (out.strip() or "unknown"))
    code, out = MACHINE.git(path, "rev-parse", "HEAD")
    facts.add("commit." + out.strip()[:12])
    # The dedup key has to distinguish the states the planner is trying to tell apart. A coarse key is a
    # silent incompleteness: two different states (stash present vs dropped, staged vs unstaged) collapse
    # into one and a whole branch of the search disappears. This is the one part that still has to be
    # designed, and it is designed from what git itself reports.
    code, status = MACHINE.git(path, "status", "--porcelain")
    lines = [ln for ln in status.splitlines() if ln.strip()]
    facts.add(f"work.dirty.{min(len(lines), 9)}")
    staged = sum(1 for ln in lines if ln[:1] not in (" ", "?"))
    untracked = sum(1 for ln in lines if ln.startswith("??"))
    facts.add(f"index.staged.{min(staged, 9)}")
    facts.add(f"work.untracked.{min(untracked, 9)}")
    code, stash = MACHINE.git(path, "stash", "list")
    facts.add(f"stash.count.{min(len([x for x in stash.splitlines() if x.strip()]), 9)}")
    for marker, name in (("MERGE_HEAD", "merge"), ("rebase-merge", "rebase"),
                         ("rebase-apply", "rebase"), ("CHERRY_PICK_HEAD", "cherry")):
        if (path / ".git" / marker).exists():
            facts.add(f"operation.{name}.inprogress")
    return tuple(sorted(facts))


#: Tasks whose damage hides work in a stash must be repaired WITHOUT losing it: the store's content has
#: to end up in the commit. That turns a two-step reset into a sequence whose order matters.
PRESERVE = ("stashed_wrong_branch", "conflict_and_stash", "deep")


def goal(path: pathlib.Path, target_commit: str, preserve: bool = False,
         baseline: dict[str, str] | None = None) -> tuple[bool, str]:
    """The repository's own answer, not mine. This is the verifier."""
    code, branch = MACHINE.git(path, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip()
    code, status = MACHINE.git(path, "status", "--porcelain")
    code, stash = MACHINE.git(path, "stash", "list")
    code, head = MACHINE.git(path, "rev-parse", "HEAD")
    in_progress = ((path / ".git" / "MERGE_HEAD").exists()
                   or (path / ".git" / "rebase-merge").exists()
                   or (path / ".git" / "rebase-apply").exists())
    reasons = []
    if branch != "main":
        reasons.append(f"on {branch}")
    if status.strip():
        reasons.append(f"{len(status.splitlines())} modified/untracked")
    if stash.strip():
        reasons.append("stash present")
    if in_progress:
        reasons.append("operation in progress")
    # Nothing else may change. Without this, a repair that commits a DELETED tracked file passes: the
    # tree is clean, the branch is main, the stash is empty, and the work is gone. The goal has to be a
    # statement about the content, so it is: the only difference from the commit we started at is the
    # work that was hidden.
    allowed = {"README.rst"} if preserve else set()
    _c, changed = MACHINE.git(path, "diff", "--name-only", target_commit, "HEAD")
    unexpected = sorted(set(changed.split()) - allowed)
    if unexpected:
        reasons.append(f"{len(unexpected)} file(s) changed that nobody asked about")
    # No other branch may be rewritten. Without this, a repair that COMMITS the mess onto the branch it
    # was on and then walks away passes: main is clean, the work is rescued, and the damage is now
    # permanent history somewhere else. The goal has to say what must NOT happen, too.
    if baseline:
        _c, refs_now = MACHINE.git(path, "for-each-ref", "refs/heads/",
                                   "--format=%(refname:short) %(objectname)")
        tips_now = dict(ln.split() for ln in refs_now.splitlines() if ln.strip())
        moved = sorted(name for name, sha in tips_now.items()
                       if name != "main" and name in baseline and sha != baseline[name])
        if moved:
            reasons.append(f"branch rewritten: {','.join(moved)}")
    if preserve:
        # Rescuing hidden work ADDS a commit, so "the commit you started from" cannot be the tip. What
        # must hold instead is stronger and is the point: the original history is still there, and the
        # work that was hidden is now part of it.
        code, _o = MACHINE.run(("git", "merge-base", "--is-ancestor", target_commit, "HEAD"), path)
        if code != 0:
            reasons.append("the original history is no longer an ancestor")
    elif head.strip() != target_commit:
        reasons.append(f"head {head.strip()[:8]} != {target_commit[:8]}")
    if preserve:
        code, content = MACHINE.git(path, "show", "HEAD:README.rst")
        if "local edit" not in content:
            reasons.append("the stashed work is not in the commit")
    return (not reasons), ", ".join(reasons) or "at goal"


# --------------------------------------------------------------------------------------------------
# Damage: real states a computer actually ends up in
# --------------------------------------------------------------------------------------------------

DAMAGE: dict[str, tuple[tuple[str, ...], ...]] = {
    "wrong_branch": (("checkout", "-q", "side"),),
    "conflicted_merge": (("checkout", "-q", "side"), ("merge", "main")),
    "conflicted_rebase": (("checkout", "-q", "side"), ("rebase", "main")),
    "stashed_wrong_branch": (("stash", "push", "-q", "-m", "wip"), ("checkout", "-q", "side")),
    "conflict_and_stash": (("stash", "push", "-q", "-m", "wip"), ("checkout", "-q", "side"),
                           ("merge", "main")),
    # Five real things wrong at once. Nothing about the repair is told to the planner, and the shortest
    # way out is four actions in a fixed order.
    # Four real things wrong at once, and one of them is a trap: `git checkout -- .` discards unstaged
    # work, so it destroys the rescued stash if it is run AFTER the pop. The order is not decoration.
    "deep": (("stash", "push", "-q", "-m", "wip"), ("checkout", "-q", "side"), ("merge", "main"),
             ("rm", "-q", "CHANGELOG.rst")),
}


def damage(root: pathlib.Path, base: pathlib.Path, kind: str) -> pathlib.Path:
    path = root / f"task-{kind}"
    if path.exists():
        shutil.rmtree(path)
    shutil.copytree(base, path, symlinks=True)
    steps = DAMAGE[kind]
    if kind in ("stashed_wrong_branch", "conflict_and_stash", "deep"):
        # a real edit that really gets stashed
        (path / "README.rst").write_text("readme with a local edit\n", encoding="utf-8")
        MACHINE.git(path, "add", "README.rst")
    if kind in ("wrong_branch", "conflicted_merge", "conflicted_rebase",
                "stashed_wrong_branch", "conflict_and_stash", "deep"):
        (path / "scratch.txt").write_text("untracked\n", encoding="utf-8")
    codes = []
    for step in steps:
        code, _out = MACHINE.run(("git", *step), path)
        codes.append(f"{' '.join(step)} -> {code}")
    (root / f".damage-{kind}.json").write_text(json.dumps({"kind": kind, "steps": codes}) + "\n",
                                             encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------------------
# The planner: no model, one copy and one execution per edge
# --------------------------------------------------------------------------------------------------

@dataclass
class Knowledge:
    """Conditions learned so far, per action, from every edge this agent has ever tried."""

    evidence: dict[str, list[tuple[tuple[str, ...], bool]]]
    boundaries: dict[str, Any]

    @classmethod
    def empty(cls) -> "Knowledge":
        return cls(evidence={}, boundaries={})

    def boundary(self, name: str):
        return self.boundaries.get(name) or APP.learn(self.evidence.get(name, []))

    def note(self, name: str, facts: Sequence[str], applied: bool) -> None:
        self.evidence.setdefault(name, []).append((tuple(sorted(facts)), bool(applied)))
        self.boundaries[name] = APP.learn(self.evidence[name])


def try_edge(path: pathlib.Path, edge: Edge, workspace: pathlib.Path,
             label: str) -> tuple[bool, pathlib.Path | None, float]:
    """Copy, run, keep the copy if it applied. One execution answers decides AND produces."""
    child = workspace / label
    if child.exists():
        shutil.rmtree(child)
    begin = time.perf_counter()
    shutil.copytree(path, child, symlinks=True)
    code, _out = MACHINE.run(edge.argv, child)
    took = time.perf_counter() - begin
    if code == 0:
        return True, child, took
    shutil.rmtree(child, ignore_errors=True)
    return False, None, took


def solve(start: pathlib.Path, target_commit: str, workspace: pathlib.Path,
          knowledge: Knowledge | None, prune: bool, preserve: bool = False, max_depth: int = 7,
          max_expansions: int = 900, baseline: dict[str, str] | None = None,
          order: bool = False) -> dict[str, Any]:
    """Breadth-first over REAL states. The frontier holds directories, not descriptions of them."""
    begun = time.time()
    start_facts = observe(start)
    ok, why = goal(start, target_commit, preserve, baseline)
    if ok:
        return {"solved": True, "depth": 0, "plan": [], "expansions": 0, "edges_tried": 0,
                "executions": 0, "copies": 0, "pruned_by_knowledge": 0, "seconds": 0.0,
                "note": "already at goal"}

    frontier: list[tuple[pathlib.Path, list[str], tuple[str, ...]]] = [(start, [], start_facts)]
    seen: set[tuple[str, ...]] = {start_facts}
    expansions = edges_tried = executions = copies = pruned = 0
    index = 0

    for depth in range(1, max_depth + 1):
        next_frontier: list[tuple[pathlib.Path, list[str], tuple[str, ...]]] = []
        for path, plan, _facts in frontier:
            if expansions >= max_expansions:
                break
            expansions += 1
            facts = observe(path)
            edges = EDGES
            if order and knowledge is not None:
                # The consensus is used to ORDER, never to delete: the edges every surviving hypothesis
                # rejects go to the back of the queue. That keeps the search complete while still
                # spending the knowledge -- the opposite trade from pruning.
                rank = {e.name: (0 if decisive(knowledge.boundary(e.name), facts) is True else
                                 2 if decisive(knowledge.boundary(e.name), facts) is False else 1)
                        for e in EDGES}
                edges = tuple(sorted(EDGES, key=lambda e: rank[e.name]))
            for edge in edges:
                if prune and knowledge is not None:
                    known = decisive(knowledge.boundary(edge.name), facts)
                    if known is False:
                        pruned += 1
                        continue
                index += 1
                applied, child, _took = try_edge(path, edge, workspace, f"{start.name}-e{index}")
                edges_tried += 1
                copies += 1
                executions += 1
                if knowledge is not None:
                    knowledge.note(edge.name, facts, applied)
                if not applied:
                    continue
                child_facts = observe(child)
                if child_facts in seen:
                    shutil.rmtree(child, ignore_errors=True)
                    continue
                seen.add(child_facts)
                deeper = plan + [edge.name]
                ok, _why = goal(child, target_commit, preserve, baseline)
                if ok:
                    return {"solved": True, "depth": depth, "plan": deeper, "expansions": expansions,
                            "edges_tried": edges_tried, "executions": executions, "copies": copies,
                            "pruned_by_knowledge": pruned,
                            "seconds": round(time.time() - begun, 2)}
                next_frontier.append((child, deeper, child_facts))
        frontier = next_frontier
        if not frontier:
            break
    return {"solved": False, "depth": None, "plan": [], "expansions": expansions,
            "edges_tried": edges_tried, "executions": executions, "copies": copies,
            "pruned_by_knowledge": pruned, "seconds": round(time.time() - begun, 2)}


def measure(root: pathlib.Path, repo: str, commit: str | None, tasks: Sequence[str] | None = None,
            receipt_path: pathlib.Path | None = None, warm: bool = True,
            cap: int = 420) -> dict[str, Any]:
    started = time.time()
    root.mkdir(parents=True, exist_ok=True)
    base = MACHINE.build_base(root, repo, commit)
    target = MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
    _c, base_refs = MACHINE.git(base, "for-each-ref", "refs/heads/",
                                "--format=%(refname:short) %(objectname)")
    baseline = dict(ln.split() for ln in base_refs.splitlines() if ln.strip())
    kinds = list(tasks or ["wrong_branch", "conflicted_merge", "conflicted_rebase",
                           "stashed_wrong_branch", "conflict_and_stash", "deep",
                           "wrong_branch"])

    rows: list[dict[str, Any]] = []
    # Two identical streams: one agent that learns and prunes, one that never prunes. The second is the
    # control that decides whether the learned conditions ever cost a solution.
    learning = Knowledge.empty()
    for kind in kinds:
        workspace = root / f"ws-learn-{kind}"
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True)
        path = damage(root, base, kind)
        before = {name: len(rows_) for name, rows_ in learning.evidence.items()}
        result = solve(path, target, workspace, learning, prune=True,
                       preserve=kind in PRESERVE, max_expansions=cap, baseline=baseline)
        result.update({"task": kind, "mode": "LEARNING_AND_PRUNING",
                       "preserve": kind in PRESERVE,
                       "goal_reason_at_start": goal(path, target, kind in PRESERVE, baseline)[1],
                       "knowledge_before": sum(before.values()),
                       "knowledge_after": sum(len(v) for v in learning.evidence.values())})
        rows.append(result)
        if receipt_path is not None:
            print(f"[learn] {kind:22s} solved={result['solved']} depth={result['depth']} "
                  f"exec={result['executions']} pruned={result['pruned_by_knowledge']} "
                  f"{result['seconds']}s", flush=True)

    for kind in kinds:
        workspace = root / f"ws-control-{kind}"
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True)
        path = damage(root, base, kind)
        result = solve(path, target, workspace, None, prune=False,
                       preserve=kind in PRESERVE, max_expansions=cap, baseline=baseline)
        result.update({"task": kind, "mode": "NO_KNOWLEDGE_CONTROL"})
        rows.append(result)
        if receipt_path is not None:
            print(f"[ctrl ] {kind:22s} solved={result['solved']} depth={result['depth']} "
                  f"exec={result['executions']} {result['seconds']}s", flush=True)

    # The same six tasks again, in the same order, with the conditions learned in the first pass and
    # nothing else changed. This is the only honest form of "learn once": the environment repeats, the
    # conditions do not have to be discovered twice.
    ordering = Knowledge.empty()
    for kind in kinds:
        workspace = root / f"ws-order-{kind}"
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True)
        path = damage(root, base, kind)
        result = solve(path, target, workspace, ordering, prune=False, order=True,
                       preserve=kind in PRESERVE, max_expansions=cap, baseline=baseline)
        result.update({"task": kind, "mode": "ORDER_ONLY_NO_DELETION",
                       "preserve": kind in PRESERVE,
                       "goal_reason_at_start": goal(path, target, kind in PRESERVE, baseline)[1]})
        rows.append(result)
        if receipt_path is not None:
            print(f"[order] {kind:22s} solved={result['solved']} depth={result['depth']} "
                  f"exec={result['executions']} {result['seconds']}s", flush=True)

    if warm:
        for kind in kinds:
            workspace = root / f"ws-warm-{kind}"
            if workspace.exists():
                shutil.rmtree(workspace)
            workspace.mkdir(parents=True)
            path = damage(root, base, kind)
            result = solve(path, target, workspace, learning, prune=True,
                           preserve=kind in PRESERVE, max_expansions=cap, baseline=baseline)
            result.update({"task": kind, "mode": "WARM_SECOND_PASS",
                           "preserve": kind in PRESERVE,
                           "goal_reason_at_start": goal(path, target, kind in PRESERVE, baseline)[1]})
            rows.append(result)
            if receipt_path is not None:
                print(f"[warm ] {kind:22s} solved={result['solved']} depth={result['depth']} "
                      f"exec={result['executions']} pruned={result['pruned_by_knowledge']} "
                      f"{result['seconds']}s", flush=True)

    learned = [r for r in rows if r["mode"] == "LEARNING_AND_PRUNING"]
    control = [r for r in rows if r["mode"] == "NO_KNOWLEDGE_CONTROL"]
    summary = {
        "tasks": len(kinds),
        "solved_with_learning": sum(1 for r in learned if r["solved"]),
        "solved_without_knowledge": sum(1 for r in control if r["solved"]),
        "executions_with_learning": sum(r["executions"] for r in learned),
        "executions_without_knowledge": sum(r["executions"] for r in control),
        "edges_pruned": sum(r["pruned_by_knowledge"] for r in learned),
        "solvable_but_lost_to_pruning": [
            r["task"] for r in learned
            if not r["solved"] and any(c["task"] == r["task"] and c["solved"] for c in control)
        ],
        "plans": {r["task"]: r["plan"] for r in learned if r["solved"]},
        "depths": {r["task"]: r["depth"] for r in learned if r["solved"]},
        "solved_order_only": sum(1 for r in rows if r["mode"] == "ORDER_ONLY_NO_DELETION"
                                 and r["solved"]),
        "executions_order_only": sum(r["executions"] for r in rows
                                     if r["mode"] == "ORDER_ONLY_NO_DELETION"),
        "warm_solved": sum(1 for r in rows if r["mode"] == "WARM_SECOND_PASS" and r["solved"]),
        "executions_warm": sum(r["executions"] for r in rows if r["mode"] == "WARM_SECOND_PASS"),
        "identified_conditions": {
            name: sorted(str(x) for x in kb.survivors) if kb.identified else "UNDETERMINED"
            for name, kb in learning.boundaries.items()
        },
        "seconds": round(time.time() - started, 1),
        "parameters_stored": 0,
        "model_calls": 0,
        "transitions_predicted": 0,
        "transitions_branched": sum(r["copies"] for r in learned),
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-28",
        "environment": {"kind": "real machine: git", "base_repo": repo, "target_commit": target,
                        "edges": [e.name for e in EDGES], "damage_kinds": kinds},
        "claim": "the successor of an edge is not predicted, it is had: one copy plus one execution per edge",
        "summary": summary,
        "rows": rows,
    }
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def headline(receipt: dict[str, Any]) -> str:
    s = receipt["summary"]
    return (f"{s['solved_with_learning']}/{s['tasks']} real tasks solved with no world model "
            f"({s['transitions_predicted']} transitions predicted, {s['transitions_branched']} branched); "
            f"{s['executions_with_learning']} executions with learning vs "
            f"{s['executions_without_knowledge']} without; {s['edges_pruned']} edges pruned; "
            f"tasks lost to pruning: {s['solvable_but_lost_to_pruning'] or 'none'}; "
            f"order-only {s['solved_order_only']}/{s['tasks']} solved in "
            f"{s['executions_order_only']} exec; warm second pass {s['warm_solved']}/{s['tasks']} solved in {s['executions_warm']} exec; "
            f"plans {s['plans']}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/branch-model")
    parser.add_argument("--repo", default="https://github.com/pypa/packaging.git")
    parser.add_argument("--commit", default=None)
    parser.add_argument("--tasks", default=None, help="comma separated damage kinds")
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--no-warm", action="store_true")
    parser.add_argument("--cap", type=int, default=900)
    args = parser.parse_args(argv)
    receipt = measure(pathlib.Path(args.root), args.repo, args.commit,
                      tasks=args.tasks.split(",") if args.tasks else None,
                      receipt_path=pathlib.Path(args.receipt) if args.receipt else None,
                      warm=not args.no_warm, cap=args.cap)
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
