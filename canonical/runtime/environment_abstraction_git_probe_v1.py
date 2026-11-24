"""Counterfactual abstraction + zero-experience transfer on real git (sandbox measurement).

Protocol
  Train starts  T1..T3 : same environment, different instance identity (tag, untracked name).
                         Each is learned with environment_learning_v1.learn_model.
  Abstraction         : invariant vocabulary over the three starts (environment_abstraction_v1).
  Held-out starts H1,H2: never used to choose the abstraction. Only the root is observed
                         there; the plan comes from the training model; it is then EXECUTED
                         on the held-out repository and the goal is checked there.

Two goals are evaluated, same traces, same abstraction procedure:
  loose  : on main, clean tree, a.txt has main content.           (the goal used before)
  strict : loose AND the user's uncommitted edit still exists somewhere in the repository
           (worktree, stash, or any commit reachable from --all). This is the must-not-change
           clause. Its truth value is part of the observation, so the planner can see it.

Controls
  raw_single_start : vocabulary from ONE start (identity abstraction) -> expected no transfer.
  empty_vocabulary : every token masked -> expected REFUSED (goal mixed), fail closed.

No model is called. Every action is a real git invocation.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))

from canonical.runtime.environment_abstraction_v1 import (  # noqa: E402
    ACCEPTED, akey, abstract, build_abstract_model, invariant_vocabulary,
    plan_in_abstraction, token_set)
from canonical.runtime.environment_learning_v1 import learn_model  # noqa: E402

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_ABSTRACTION_GIT_PROBE_V1"
ACTIONS = ["checkout main", "checkout feature", "checkout -- .", "stash", "stash pop",
           "stash drop", "clean -fdq", "add -A", "commit -qm wip", "reset --hard",
           "merge --abort", "checkout -f main", "status"]


def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


class GitInstance:
    """One real repository. Instance identity = tag (in file content) + junk name."""

    def __init__(self, root: str, tag: str, junk: str):
        self.root, self.tag, self.junk = root, tag, junk

    def reset(self):
        if os.path.exists(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root)
        r = self.root
        _git(["init", "-q", "-b", "main"], r)
        _git(["config", "user.email", "probe@example"], r)
        _git(["config", "user.name", "probe"], r)
        self._write("a.txt", f"main {self.tag}\n")
        _git(["add", "-A"], r)
        _git(["commit", "-qm", "init"], r)
        _git(["checkout", "-qb", "feature"], r)
        self._write("a.txt", f"feature {self.tag}\n")
        self._write(self.junk, "junk\n")

    def _write(self, name, text):
        with open(os.path.join(self.root, name), "w") as f:
            f.write(text)

    def act(self, action: str):
        _git(action.split(), self.root)

    def state(self):
        r = self.root
        head = _git(["rev-parse", "--abbrev-ref", "HEAD"], r).stdout.strip()
        dirty = sorted(x for x in _git(["status", "--porcelain"], r).stdout.split("\n") if x)
        stash = len([x for x in _git(["stash", "list"], r).stdout.split("\n") if x])
        p = os.path.join(r, "a.txt")
        a = open(p).read() if os.path.exists(p) else None
        edit = f"feature {self.tag}"
        in_tree = a is not None and edit in a
        in_history = bool(_git(["log", "--all", "--format=%H", f"-S{edit}"], r).stdout.strip())
        return {"head": head, "dirty": dirty, "stash": stash, "a": a,
                "edit_survives": bool(in_tree or in_history)}

    def is_goal(self, snap, strict: bool) -> bool:
        base = (snap["head"] == "main" and snap["dirty"] == []
                and snap["a"] == f"main {self.tag}\n")
        return base and (snap["edit_survives"] or not strict)


def learn_start(inst: GitInstance, budget: int, seed: int) -> dict:
    return learn_model(inst, ACTIONS, budget=budget, seed=seed)


def run(budget: int, seed: int, workdir: str) -> dict:
    t0 = time.time()
    train_specs = [("tagT1", "junk_T1.txt"), ("tagT2", "junk_T2.txt"), ("tagT3", "junk_T3.txt")]
    held_specs = [("tagH1", "stray_H1.txt"), ("tagH2", "stray_H2.txt")]
    learned = []
    for i, (tag, junk) in enumerate(train_specs):
        inst = GitInstance(os.path.join(workdir, f"T{i}"), tag, junk)
        learned.append((inst, learn_start(inst, budget, seed + i)))
    snaps_per_start = [list(L["observations"].values()) for _, L in learned]
    vocab = invariant_vocabulary(snaps_per_start)

    out: dict = {"seed": seed, "budget_per_start": budget,
                 "train_starts": [s[0] for s in train_specs],
                 "vocab": sorted(vocab),
                 "raw_tokens_one_start_example": sorted(token_set(snaps_per_start[0]))[:20],
                 "goals": {}}

    for goal_name, strict in (("loose", False), ("strict", True)):
        def g(snap, _strict=strict, _insts=[i for i, _ in learned]):
            # goal is a function of the snapshot and the instance tag, which lives in the snapshot
            # as the content of a.txt; use the tag embedded in that content
            tag = snap["a"].split()[-1] if snap["a"] else ""
            base = (snap["head"] == "main" and snap["dirty"] == []
                    and snap["a"] is not None and snap["a"].startswith("main ")
                    and snap["a"].strip().endswith(tag) and tag != "")
            return base and (snap["edit_survives"] or not _strict)

        model = build_abstract_model([L for _, L in learned], vocab, g)
        goal_res = {"abstraction": {k: model[k] for k in
                                    ("status", "abstract_states", "abstract_transitions",
                                     "nondeterministic_edges", "mixed_goal_states")},
                    "held_out": []}
        for tag, junk in held_specs:
            inst = GitInstance(os.path.join(workdir, f"H_{goal_name}_{tag}"), tag, junk)
            inst.reset()
            root_snap = inst.state()
            plan = plan_in_abstraction(model, root_snap, vocab)
            rec = {"instance": tag, "root_known_in_model": akey(abstract(root_snap, vocab))
                   in model["model"] or akey(abstract(root_snap, vocab)) in model["goal_states"],
                   "plan": plan, "goal_reached_true": None, "edit_survives_true": None}
            if plan is not None:
                inst.reset()
                for a in plan:
                    inst.act(a)
                final = inst.state()
                rec["goal_reached_true"] = inst.is_goal(final, strict)
                rec["edit_survives_true"] = final["edit_survives"]
                rec["final"] = {k: final[k] for k in ("head", "dirty", "stash", "a")}
            goal_res["held_out"].append(rec)
        out["goals"][goal_name] = goal_res

    # controls, on the strict goal
    single = build_abstract_model([learned[0][1]], token_set(snaps_per_start[0]) and
                                  frozenset(token_set(snaps_per_start[0])),
                                  lambda s: False)
    ctrl = {"raw_single_start_vocab_status": single["status"]}
    ctrl["raw_single_start_transfers"] = []
    for tag, junk in held_specs:
        inst = GitInstance(os.path.join(workdir, f"C_{tag}"), tag, junk)
        inst.reset()
        ctrl["raw_single_start_transfers"].append(
            {"instance": tag, "root_known": akey(abstract(inst.state(), frozenset(token_set(snaps_per_start[0])))) in single["model"]})
    empty = build_abstract_model(
        [L for _, L in learned], frozenset(),
        lambda s: bool(s["head"] == "main" and s["dirty"] == []))
    ctrl["empty_vocabulary_status"] = empty["status"]
    out["controls"] = ctrl
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)
    workdir = tempfile.mkdtemp(prefix="abstraction_probe_")
    try:
        res = run(args.budget, args.seed, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    receipt = {"schema": SCHEMA, "authority": "NONE__SANDBOX_MEASUREMENT",
               "model_calls": 0, "stored_parameters": 0, "actions": ACTIONS, "result": res}
    print(json.dumps(receipt, indent=1, sort_keys=True))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
