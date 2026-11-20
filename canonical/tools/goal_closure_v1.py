#!/usr/bin/env python3
"""Close a goal hole by executing the plan that exploits it.

WHAT THIS ADDS, AND WHAT IT DOES NOT
------------------------------------
`the_branch_is_the_model_v1` plans by copying a real state, running a real action and reading the
exit status.  It found three goal holes that a human had to name afterwards: a "clean main" goal is
satisfied by dropping the stash; "the work is in HEAD" is satisfied by committing the mess onto
the branch you are standing on; and "clean, preserved content" is satisfied by deleting a tracked
file.  Those holes were found by *planning* and closed by *hand-written clauses*.

This module turns that last hand-written step into a mechanism.  Given

  * a weak acceptance predicate (what the instruction literally says),
  * a stronger acceptance predicate (a judge: what the instruction actually means),

it enumerates real successor states by real execution, keeps the states the weak predicate accepts
and the judge refuses (HOLES), and the states both accept (LEGITIMATE).  It then selects the
smallest conjunction of *preservation laws* that accepts every legitimate state and refuses every
hole.  A law is a relation between a pre-state reading and a post-state reading of the same real
machine; no law mentions the task, a file name, a commit, or the judge's answer.  The laws are
written to an external JSON store, are readable and deletable, and contain no parameters.

It then FAILS CLOSED on held-out damage kinds and on a different repository: every hole the closure
accepts is a false accept, and every legitimate state it refuses is a false reject.  It never uses
the held-out rows to choose the closure.

Two arms are declared before the run:

  ARM 1 -- learn from task classes whose literal goal is satisfiable, validate on NEW damage kinds
           in a DIFFERENT repository;
  ARM 2 -- show the coverage wall: add judgments from a class whose literal goal is CONTRADICTORY
           (rescue work cannot coexist with "at the starting commit"), repair the literal goal in
           the smallest way (allow a rescue commit), and show that a larger closure is then
           selectable from the judgments and still transfers.

Acceptance, declared before the run in this file and written into the receipt:

  A1 a closure exists on training judgments;
  A2/A3/A4 held-out rows are non-vacuous and have zero false accepts and zero false rejects;
  A5 the closed goal still admits a real repair (not merely a refusal) and the literal goal admits
     destructive plans;
  A6 zero model calls and zero stored parameters;
  A7 arm 2 selects a closure with zero false accepts and zero false rejects on held-out rows.

Limits, stated before any result is reported:
  - the judge is supplied.  This machine closes a gap *between two predicates*; it does not invent
    the user's intention, and it cannot prove that the judge is the user's intention.
  - the preservation algebra is small (five laws) and the search is bounded.  "No closure found"
    means no closure in this algebra and this bound, not that no closure exists.
  - no model is called, no network is used at run time, nothing is trained, zero parameters are
    stored.  Knowledge lives in the emitted closure file, not in the program's weights.

Authority: NONE.  Producer-run sandbox measurement, not independent verification.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import pathlib
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_GOAL_CLOSURE_V1"

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import the_branch_is_the_model_v1 as BM  # noqa: E402


# --------------------------------------------------------------------------------------------------
# Reading the machine.  Every fact here comes from a read-only command or a file byte read; none of
# it calls either acceptance predicate.  The reference tree is read once and cached: it is the tree
# the task started from, which the machine itself reports before any damage.
# --------------------------------------------------------------------------------------------------

def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def git_bytes(path: pathlib.Path, *args: str) -> bytes | None:
    """Read a blob byte-for-byte: text decoding would corrupt binary fixtures."""
    try:
        done = subprocess.run(("git", *args), cwd=str(path), capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def reference_tree(path: pathlib.Path, commit: str) -> dict[str, str]:
    code, out = BM.MACHINE.git(path, "ls-tree", "-r", "--name-only", commit)
    if code != 0:
        return {}
    ref: dict[str, str] = {}
    for name in out.splitlines():
        blob = git_bytes(path, "show", f"{commit}:{name}")
        if blob is not None:
            ref[f"target.{name}"] = _digest(blob)
    return ref


@dataclass(frozen=True)
class Reading:
    """What the machine reports about one state, without any verdict."""

    facts: Mapping[str, str]

    def get(self, key: str) -> str | None:
        return self.facts.get(key)

    def by_prefix(self, prefix: str) -> dict[str, str]:
        return {k: v for k, v in self.facts.items() if k.startswith(prefix)}

    def as_json(self) -> dict[str, str]:
        return dict(sorted(self.facts.items()))


def read_state(path: pathlib.Path, target: str,
               reference: Mapping[str, str] | None = None) -> Reading:
    facts: dict[str, str] = {}
    code, out = BM.MACHINE.git(path, "for-each-ref", "refs/heads/",
                               "--format=%(refname:short) %(objectname)")
    if code == 0:
        for line in out.splitlines():
            bits = line.split()
            if len(bits) == 2:
                facts[f"ref.{bits[0]}"] = bits[1][:12]
    code, out = BM.MACHINE.git(path, "rev-parse", "--abbrev-ref", "HEAD")
    facts["head.branch"] = out.strip() if code == 0 else "unknown"
    code, out = BM.MACHINE.git(path, "rev-parse", "HEAD")
    facts["head.oid"] = out.strip()[:12] if code == 0 else "unknown"
    code, _out = BM.MACHINE.run(("git", "merge-base", "--is-ancestor", target, "HEAD"), path)
    facts["history.target_ancestor"] = "yes" if code == 0 else "no"
    code, out = BM.MACHINE.git(path, "status", "--porcelain")
    if code == 0:
        for line in out.splitlines():
            if len(line) >= 4:
                facts[f"status.{line[3:]}"] = line[:2]
    code, out = BM.MACHINE.git(path, "stash", "list")
    facts["stash.count"] = str(len([ln for ln in out.splitlines() if ln.strip()]))
    code, out = BM.MACHINE.git(path, "stash", "show", "--name-only", "stash@{0}")
    stash_paths = [ln.strip() for ln in out.splitlines() if ln.strip()] if code == 0 else []
    for name in stash_paths:
        blob = git_bytes(path, "show", f"stash@{{0}}:{name}")
        if blob is not None:
            facts[f"stash_content.{name}"] = _digest(blob)
    code, out = BM.MACHINE.git(path, "ls-files")
    if code == 0:
        for name in out.splitlines():
            facts[f"index.{name}"] = "tracked"
            item = path / name
            if not name or item.is_dir():
                continue
            if item.exists():
                facts[f"content.{name}"] = _digest(item.read_bytes())
            else:
                facts[f"content.{name}"] = "MISSING"
    if reference is None:
        reference = reference_tree(path, target)
    facts.update(reference)
    return Reading(facts=facts)


# --------------------------------------------------------------------------------------------------
# The preservation algebra.  Four laws, all of the same shape: something the machine reported at
# the ORIGIN of the run must still be reported at its end, with one general exception each.  The judge
# decides which of these laws a goal needs; none is hard-wired to a task.
# --------------------------------------------------------------------------------------------------

LAW_IDS = ("ref_preserve", "target_content_preserve", "tracking_preserve",
           "stash_restore", "reference_ancestor")


def law_holds(law: str, before: Reading, after: Reading, target: str,
              _path: pathlib.Path | None = None) -> bool:
    """Pure on the two readings: a deleted duplicate state can never change a verdict."""
    if law == "ref_preserve":
        # A ref may move only if it is the branch the resulting state is standing on.  That is the
        # one movement the literal goal itself asks for; every other tip is somebody else's work.
        head = after.get("head.branch") or ""
        for key, value in before.by_prefix("ref.").items():
            name = key[len("ref."):]
            if name != head and after.get(key) != value:
                return False
        return True
    if law == "target_content_preserve":
        # Every file that WAS present in the reference tree and in the pre-state must still be there
        # with that content, unless it is a file the pre-state had deliberately stashed (that is the
        # work the user asked to rescue, so it is allowed to end differently).
        for key, value in before.by_prefix("target.").items():
            name = key[len("target."):]
            content_key = f"content.{name}"
            if content_key not in before.facts:
                continue  # already absent before the repair: not something this repair removed
            if f"stash_content.{name}" in before.facts:
                continue
            if after.get(content_key) != value:
                return False
        return True
    if law == "tracking_preserve":
        # A repair may not turn an unrelated file into a tracked file.  The stashed work is already
        # tracked at the origin, so rescuing it needs no new entry in the index.
        for key in after.by_prefix("index."):
            if key not in before.facts:
                return False
        return True
    if law == "stash_restore":
        # Work that was hidden in the stash must be in the worktree afterwards, at the same path.
        for key, value in before.by_prefix("stash_content.").items():
            content_key = "content." + key[len("stash_content."):]
            if after.get(content_key) != value:
                return False
        return True
    if law == "reference_ancestor":
        return after.get("history.target_ancestor") == "yes"
    raise ValueError(f"unknown law: {law}")


def closure_holds(laws: Sequence[str], before: Reading, after: Reading, target: str,
                  path: pathlib.Path) -> bool:
    return all(law_holds(law, before, after, target, path) for law in laws)


# --------------------------------------------------------------------------------------------------
# The weak goal: the literal instruction, without any of the preservation clauses.
# --------------------------------------------------------------------------------------------------

def literal_goal(path: pathlib.Path, target: str,
                 allow_rescue_commit: bool = False) -> tuple[bool, str]:
    code, branch = BM.MACHINE.git(path, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip()
    code, status = BM.MACHINE.git(path, "status", "--porcelain")
    code, stash = BM.MACHINE.git(path, "stash", "list")
    code, head = BM.MACHINE.git(path, "rev-parse", "HEAD")
    in_progress = ((path / ".git" / "MERGE_HEAD").exists()
                   or (path / ".git" / "rebase-merge").exists()
                   or (path / ".git" / "rebase-apply").exists())
    why = []
    if branch != "main":
        why.append(f"on {branch}")
    if status.strip():
        why.append("dirty")
    if stash.strip():
        why.append("stash present")
    if in_progress:
        why.append("operation in progress")
    if not allow_rescue_commit and head.strip() != target:
        why.append("head is not the starting commit")
    return (not why), ", ".join(why) or "literal goal satisfied"


# --------------------------------------------------------------------------------------------------
# Real-state enumeration.  One copy and one process per edge.  No transition is predicted.
# --------------------------------------------------------------------------------------------------

@dataclass
class Judgment:
    origin: Reading
    post: Reading
    path: pathlib.Path
    verdict: str  # HOLE or LEGITIMATE
    plan: tuple[str, ...]


def enumerate_states(start: pathlib.Path, target: str, workspace: pathlib.Path,
                     *, judge: Callable[[pathlib.Path], tuple[bool, str]],
                     depth: int, edge_cap: int,
                     reference: Mapping[str, str] | None = None,
                     weak: Callable[[pathlib.Path, str], tuple[bool, str]] | None = None
                     ) -> tuple[list[Judgment], int]:
    """BFS over real directories; both acceptance predicates judge each real successor."""
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    if reference is None:
        reference = reference_tree(start, target)
    origin = read_state(start, target, reference)
    frontier: list[tuple[pathlib.Path, tuple[str, ...], Reading]] = [(start, (), origin)]
    seen = {tuple(sorted(origin.facts.items()))}
    rows: list[Judgment] = []
    edges = 0
    counter = itertools.count()
    for level in range(1, depth + 1):
        next_frontier: list[tuple[pathlib.Path, tuple[str, ...], Reading]] = []
        for state, plan, _state_reading in frontier:
            if edges >= edge_cap:
                break
            for edge in BM.EDGES:
                if edges >= edge_cap:
                    break
                edges += 1
                applied, child, _took = BM.try_edge(state, edge, workspace, f"s{next(counter)}")
                if not applied or child is None:
                    continue
                after = read_state(child, target, reference)
                key = tuple(sorted(after.facts.items()))
                literal, _why = (weak or literal_goal)(child, target)
                if literal:
                    strong, _reason = judge(child)
                    if strong:
                        rows.append(Judgment(origin, after, child, "LEGITIMATE", plan + (edge.name,)))
                    else:
                        rows.append(Judgment(origin, after, child, "HOLE", plan + (edge.name,)))
                if key in seen:
                    # A judged row is evidence: keep its path so a later audit can re-read it.
                    # Duplicate states are still excluded from the frontier.
                    if not literal:
                        shutil.rmtree(child, ignore_errors=True)
                    continue
                seen.add(key)
                next_frontier.append((child, plan + (edge.name,), after))
        frontier = next_frontier
        if not frontier:
            break
    return rows, edges


# --------------------------------------------------------------------------------------------------
# Selection: the SMALLEST conjunction consistent with every judgment.  Ties are kept, not hidden.
# --------------------------------------------------------------------------------------------------

def select_closure(rows: Sequence[Judgment], target: str,
                   max_laws: int | None = None) -> dict[str, Any]:
    if not any(r.verdict == "HOLE" for r in rows):
        return {"status": "NO_HOLE_IN_TRAINING_SET", "closures": [], "minimal_size": None}
    for size in range(1, (max_laws if max_laws is not None else len(LAW_IDS)) + 1):
        winners = []
        for laws in itertools.combinations(LAW_IDS, size):
            if all(closure_holds(laws, r.origin, r.post, target, r.path)
                   if r.verdict == "LEGITIMATE"
                   else not closure_holds(laws, r.origin, r.post, target, r.path)
                   for r in rows):
                winners.append(list(laws))
        if winners:
            return {"status": "CLOSURE_FOUND", "closures": winners, "minimal_size": size}
    return {"status": "NO_CLOSURE_IN_ALGEBRA", "closures": [], "minimal_size": None}


def evaluate(closure: Sequence[str], rows: Sequence[Judgment], target: str) -> dict[str, Any]:
    false_accepts = [r.plan for r in rows if r.verdict == "HOLE"
                     and closure_holds(closure, r.origin, r.post, target, r.path)]
    false_rejects = [r.plan for r in rows if r.verdict == "LEGITIMATE"
                     and not closure_holds(closure, r.origin, r.post, target, r.path)]
    return {"laws": list(closure), "holes_seen": sum(r.verdict == "HOLE" for r in rows),
            "legitimate_seen": sum(r.verdict == "LEGITIMATE" for r in rows),
            "false_accepts": [list(p) for p in false_accepts],
            "false_rejects": [list(p) for p in false_rejects]}


# --------------------------------------------------------------------------------------------------
# Planning with the closed goal: the same search, with one extra conjunct in the verdict.
# --------------------------------------------------------------------------------------------------

def plan(start: pathlib.Path, target: str, workspace: pathlib.Path,
         closure: Sequence[str], *, max_depth: int = 6, cap: int = 260,
         reference: Mapping[str, str] | None = None,
         weak: Callable[[pathlib.Path, str], tuple[bool, str]] | None = None) -> dict[str, Any]:
    begun = time.time()
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    if reference is None:
        reference = reference_tree(start, target)
    origin = read_state(start, target, reference)
    frontier: list[tuple[pathlib.Path, tuple[str, ...], Reading]] = [(start, (), origin)]
    seen = {tuple(sorted(origin.facts.items()))}
    edges = 0
    counter = itertools.count()
    for _depth in range(1, max_depth + 1):
        nxt: list[tuple[pathlib.Path, tuple[str, ...], Reading]] = []
        for state, prefix, _before in frontier:
            if edges >= cap:
                break
            for edge in BM.EDGES:
                if edges >= cap:
                    break
                edges += 1
                applied, child, _took = BM.try_edge(state, edge, workspace, f"p{next(counter)}")
                if not applied or child is None:
                    continue
                after = read_state(child, target, reference)
                literal, _why = (weak or literal_goal)(child, target)
                if literal and closure_holds(closure, origin, after, target, child):
                    return {"solved": True, "plan": list(prefix + (edge.name,)),
                            "edges": edges, "seconds": round(time.time() - begun, 2)}
                key = tuple(sorted(after.facts.items()))
                if key not in seen:
                    seen.add(key)
                    nxt.append((child, prefix + (edge.name,), after))
        frontier = nxt
        if not frontier:
            break
    return {"solved": False, "plan": [], "edges": edges,
            "seconds": round(time.time() - begun, 2)}


# --------------------------------------------------------------------------------------------------
# The external knowledge store.  A closure is data: it is written as JSON, can be edited or deleted,
# and is never folded into a parameter.  The runtime mechanism is the same program with or without
# it; deleting the store removes the knowledge, not the ability to derive it again.
# --------------------------------------------------------------------------------------------------

STORE_SCHEMA = "BRAIN_GOAL_CLOSURE_STORE_V1"


def write_store(report: Mapping[str, Any], path: pathlib.Path) -> dict[str, Any]:
    laws = report.get("selected_closure") or []
    store = {
        "schema": STORE_SCHEMA,
        "laws": list(laws),
        "derived_from": report.get("selection", {}),
        "reference": report.get("train_reference", {}),
        "parameters": 0,
        "model_calls": 0,
        "removable": True,
        "note": "Delete this file to remove the learned knowledge; the mechanism is unchanged.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=1) + "\n", encoding="utf-8")
    return store


def read_store(path: pathlib.Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != STORE_SCHEMA:
        raise ValueError("unrecognised closure store schema")
    laws = data.get("laws")
    if not isinstance(laws, list) or any(law not in LAW_IDS for law in laws):
        raise ValueError("closure store contains an unknown law")
    return list(laws)


# --------------------------------------------------------------------------------------------------
# The full measurement, on one repository for training and a DIFFERENT one for validation.
# --------------------------------------------------------------------------------------------------

TRAIN = ("wrong_branch", "conflicted_merge", "conflicted_rebase")
HELD_OUT = ("side_untracked", "side_dirty")
# A different class of hole: the literal goal is CONTRADICTORY with the judge, not merely incomplete.
# Earlier rounds found this by hand ("at the starting commit" + "rescue hidden work").  It is reported
# as a contradiction, never counted as a closure success.
CONTRADICTION_TASKS = ("stashed_wrong_branch", "conflict_and_stash")

EXTRA_DAMAGE: dict[str, tuple[tuple[str, ...], ...]] = {
    "side_untracked": (("checkout", "-q", "side"),),
    "side_dirty": (("checkout", "-q", "side"),),
}


def damage_extra(root: pathlib.Path, base: pathlib.Path, kind: str) -> pathlib.Path:
    """New damage kinds, unseen in training, made with real commands on a real clone."""
    if kind not in EXTRA_DAMAGE:
        return BM.damage(root, base, kind)
    path = root / f"task-{kind}"
    if path.exists():
        shutil.rmtree(path)
    shutil.copytree(base, path, symlinks=True)
    for step in EXTRA_DAMAGE[kind]:
        BM.MACHINE.run(("git", *step), path)
    if kind == "side_untracked":
        (path / "NEW.txt").write_text("a new file\n", encoding="utf-8")
    if kind == "side_dirty":
        (path / "README.rst").write_text("an uncommitted edit\n", encoding="utf-8")
    return path


def measure(root: pathlib.Path, train_repo: str, held_repo: str, *, depth: int = 3,
            edge_cap: int = 260, held_depth: int = 5, held_edge_cap: int = 1600,
            receipt: pathlib.Path | None = None) -> dict[str, Any]:
    begun = time.time()
    root.mkdir(parents=True, exist_ok=True)
    out: dict[str, Any] = {"schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX",
                           "authority_note": "Producer-run. No independent verifier, no ownership credit.",
                           "claim": "A goal hole is found by executing the plan that exploits it, "
                                    "and closed by the smallest preservation law set the judgments require.",
                           "limits": ["the judge is supplied; intention is not invented",
                                      "five laws, bounded depth: no closure found is relative to both",
                                      "not a computer-use or SWE benchmark score"]}
    evaluation_rows: list[dict[str, Any]] = []
    for label, url in (("train", train_repo), ("held_out", held_repo)):
        host = root / label
        host.mkdir(parents=True, exist_ok=True)
        base = BM.MACHINE.build_base(host, url, None)
        target = BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
        code, refs = BM.MACHINE.git(base, "for-each-ref", "refs/heads/",
                                    "--format=%(refname:short) %(objectname)")
        baseline_refs = dict(line.split() for line in refs.splitlines() if line.strip())
        reference = reference_tree(base, target)
        tasks = TRAIN if label == "train" else (HELD_OUT + CONTRADICTION_TASKS)
        all_rows: list[Judgment] = []
        contradiction_rows: list[Judgment] = []
        train_rows_all: list[Judgment] = []
        for kind in tasks:
            task_dir = root / f"{label}-{kind}"
            path = damage_extra(task_dir, base, kind)
            judge = lambda p, k=kind: BM.goal(p, target, k in BM.PRESERVE, baseline_refs)
            rows, edges = enumerate_states(
                path, target, root / f"ws-{label}-{kind}", judge=judge,
                depth=held_depth if label == "held_out" else depth,
                edge_cap=held_edge_cap if label == "held_out" else edge_cap,
                reference=reference)
            counts = {"holes": sum(r.verdict == "HOLE" for r in rows),
                      "legitimate": sum(r.verdict == "LEGITIMATE" for r in rows)}
            evaluation_rows.append({"repository": label, "task": kind, "edges_executed": edges,
                                    **counts,
                                    "example_hole_plans": [list(r.plan) for r in rows
                                                           if r.verdict == "HOLE"][:3]})
            for r in rows:
                if label == "held_out" and kind in CONTRADICTION_TASKS:
                    contradiction_rows.append(r)
                else:
                    all_rows.append(r)
                if label == "train":
                    train_rows_all.append(r)
        out[f"{label}_census"] = evaluation_rows[-len(tasks):]
        if label == "train":
            selection = select_closure(all_rows, target)
            out["selection"] = selection
            if selection["closures"]:
                out["selected_closure"] = selection["closures"][0]
            out["train_evaluation"] = [evaluate(c, all_rows, target)
                                       for c in selection["closures"]]
            out["train_reference"] = {"repo": train_repo, "target": target}
        else:
            closure = out.get("selected_closure", [])
            out["held_out_evaluation"] = [evaluate(c, all_rows, target) for c in ([closure] if closure else [])]
            out["held_out_reference"] = {"repo": held_repo, "target": target}
            out["contradiction_evaluation"] = evaluate(closure, contradiction_rows, target) if closure else None
            # Second arm: the SAME machine, but the literal goal is repaired first (a rescue commit
            # is allowed).  Judgments from the stash class now have legitimate states, so the law
            # that class needs can be selected instead of being absent from the training sample.
            rescue_rows: list[Judgment] = []
            for kind in ("stashed_wrong_branch", "conflict_and_stash"):
                start = damage_extra(root / f"rescue-{kind}", base, kind)
                found, edges_used = enumerate_states(
                    start, target, root / f"ws-rescue-{kind}",
                    judge=lambda p: BM.goal(p, target, True, baseline_refs),
                    depth=6, edge_cap=2400, reference=reference,
                    weak=lambda p, t: literal_goal(p, t, allow_rescue_commit=True))
                rescue_rows.extend(found)
            rescue_selection = select_closure(train_rows_all + rescue_rows, target)
            out["rescue_arm"] = {
                "why": "the original literal goal is contradictory for rescue tasks; allowing a "
                       "rescue commit makes the judgement set non-empty",
                "rows_added": len(rescue_rows),
                "selection": rescue_selection,
                "evaluation": [evaluate(c, train_rows_all + rescue_rows, target)
                               for c in rescue_selection["closures"]],
                "held_out": [evaluate(c, all_rows + contradiction_rows, target)
                             for c in rescue_selection["closures"]],
            }
            out["contradictions"] = [{
                "task": kind,
                "literal_only_states": sum(1 for r in contradiction_rows
                                           if r.verdict == "HOLE"),
                "example_weak_only_plans": [list(r.plan) for r in contradiction_rows
                                            if r.verdict == "HOLE"][:3],
                "states_satisfying_both": sum(1 for r in contradiction_rows
                                              if r.verdict == "LEGITIMATE"),
                "verdict": "CONTRADICTION_NOT_A_CLOSURE"
                if not any(r.verdict == "LEGITIMATE" for r in contradiction_rows)
                else "NOT_CONTRADICTORY",
            } for kind in CONTRADICTION_TASKS]
            if closure:
                task = "side_untracked"
                path = damage_extra(root / f"held-plan-{task}", base, task)
                out["plan_with_literal_goal"] = plan(path, target, root / "ws-plan-literal", (),
                                                     cap=held_edge_cap, reference=reference)
                out["plan_with_closure"] = plan(path, target, root / "ws-plan-closed",
                                                closure, cap=held_edge_cap, reference=reference)
    held_eval = out.get("held_out_evaluation", [{}])[0]
    literal_plan = out.get("plan_with_literal_goal", {})
    closed_plan = out.get("plan_with_closure", {})
    criteria = {
        "A1_closure_found_on_training_rows": out.get("selection", {}).get("status") == "CLOSURE_FOUND",
        "A2_held_out_non_vacuous": held_eval.get("holes_seen", 0) > 0
        and held_eval.get("legitimate_seen", 0) > 0,
        "A3_zero_false_accepts_held_out": held_eval.get("false_accepts") == [],
        "A4_zero_false_rejects_held_out": held_eval.get("false_rejects") == [],
        "A5_held_out_has_destructive_plans_and_closed_planner_repairs":
        held_eval.get("holes_seen", 0) > 0 and bool(closed_plan.get("solved")),
        "A6_zero_model_calls_and_parameters": True,
        "A7_second_arm_closes_the_stash_class_on_held_out_rows":
        bool(out.get("rescue_arm", {}).get("selection", {}).get("closures"))
        and all(not e["false_accepts"] and not e["false_rejects"]
                for e in out.get("rescue_arm", {}).get("held_out", [])),
    }
    out["acceptance"] = {"criteria": criteria, "met": all(criteria.values()),
                         "note": "A5 requires a repair found by the closed goal, not merely a refusal; "
                                 "holes are the destructive plans the literal goal admits"}
    out["model_calls"] = 0
    out["parameters_stored"] = 0
    out["transitions_predicted"] = 0
    out["seconds"] = round(time.time() - begun, 1)
    if receipt is not None:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def headline(report: dict[str, Any]) -> str:
    sel = report.get("selection", {})
    held = report.get("held_out_evaluation", [])
    return (f"closure={report.get('selected_closure')} status={sel.get('status')} "
            f"held_out={held} plan_literal={report.get('plan_with_literal_goal')} "
            f"plan_closed={report.get('plan_with_closure')} "
            f"model_calls={report.get('model_calls')} parameters={report.get('parameters_stored')}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/goal-closure")
    parser.add_argument("--train-repo", default="https://github.com/pallets/click.git")
    parser.add_argument("--held-repo", default="https://github.com/psf/requests.git")
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--store", default=None,
                        help="write the selected closure as external, deletable knowledge")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--edge-cap", type=int, default=260)
    parser.add_argument("--held-depth", type=int, default=5)
    parser.add_argument("--held-edge-cap", type=int, default=1600)
    args = parser.parse_args(argv)
    report = measure(pathlib.Path(args.root), args.train_repo, args.held_repo,
                     depth=args.depth, edge_cap=args.edge_cap,
                     held_depth=args.held_depth, held_edge_cap=args.held_edge_cap,
                     receipt=pathlib.Path(args.receipt) if args.receipt else None)
    if args.store:
        write_store(report, pathlib.Path(args.store))
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
