"""Zero-experience transfer probe on real git repositories (sandbox measurement, no authority).

Question: does a model learned by acting on repository A let the agent plan a repair on a
NEW repository B with zero new actions on B (other than observing its start state)?

Two state abstractions are compared, each learned by `learn_model` from real `git` runs:
  projected : state = (branch, dirty-set, stash depth, content CLASS of a.txt)
              The content class is a hand-written abstraction. This is where the
              generalisation actually lives; the probe measures that, it does not claim the
              learner discovered it.
  raw       : state = (branch, dirty-set, stash depth, literal content of a.txt)

Every action is a real `git` invocation. Nothing is predicted; the plan is executed on B and
the goal is checked afterwards on B.

Run:  python3 canonical/runtime/environment_transfer_git_probe_v1.py [--budget 300] [--seeds 0 1]
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

from canonical.runtime.environment_learning_v1 import (  # noqa: E402
    STATE_KEY_SCHEMA, learn_model, shortest_plan, state_key)

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_TRANSFER_GIT_PROBE_V1"

# A repertoire of real git actions. The learner is not told what any of them does.
ACTIONS = ["checkout main", "checkout feature", "checkout -- .", "stash", "stash pop",
           "stash drop", "clean -fdq", "add -A", "commit -qm wip", "reset --hard",
           "merge --abort", "checkout -f main", "status"]


def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


class GitEnv:
    """A real repository. reset() rebuilds the start state; act() runs real git."""

    def __init__(self, root: str, tag: str, mode: str):
        self.root, self.tag, self.mode = root, tag, mode

    def reset(self):
        if os.path.exists(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root)
        r = self.root
        _git(["init", "-q", "-b", "main"], r)
        _git(["config", "user.email", "probe@example"], r)
        _git(["config", "user.name", "probe"], r)
        with open(os.path.join(r, "a.txt"), "w") as f:
            f.write(f"main {self.tag}\n")
        _git(["add", "-A"], r)
        _git(["commit", "-qm", "init"], r)
        _git(["checkout", "-qb", "feature"], r)
        with open(os.path.join(r, "a.txt"), "w") as f:      # uncommitted edit on wrong branch
            f.write(f"feature {self.tag}\n")
        with open(os.path.join(r, "junk.txt"), "w") as f:   # untracked junk
            f.write("junk\n")

    def act(self, action: str):
        _git(action.split(), self.root)

    def state(self):
        r = self.root
        head = _git(["rev-parse", "--abbrev-ref", "HEAD"], r).stdout.strip()
        st = _git(["status", "--porcelain"], r).stdout
        dirty = tuple(sorted(line for line in st.split("\n") if line))
        stash = len([x for x in _git(["stash", "list"], r).stdout.split("\n") if x])
        p = os.path.join(r, "a.txt")
        a = open(p).read() if os.path.exists(p) else None
        if self.mode == "projected":
            content = ("main-content" if a == f"main {self.tag}\n"
                       else "feature-content" if a is not None else "missing")
            return (head, dirty, stash, content)
        return (head, dirty, stash, a)

    def is_goal(self, s) -> bool:
        head, dirty, stash, content = s
        if self.mode == "projected":
            return head == "main" and dirty == () and content == "main-content"
        return head == "main" and dirty == () and content == f"main {self.tag}\n"


def run_once(mode: str, seed: int, budget: int, workdir: str) -> dict:
    t0 = time.time()
    env_a = GitEnv(os.path.join(workdir, f"A_{mode}_{seed}"), "tagA", mode)
    learned = learn_model(env_a, ACTIONS, budget=budget, seed=seed)
    model_a = learned["model"]
    goal_keys_a = {k for k, snap in learned["observations"].items() if env_a.is_goal(snap)}

    env_b = GitEnv(os.path.join(workdir, f"B_{mode}_{seed}"), "tagB", mode)
    env_b.reset()
    root_b = state_key(env_b.state())
    root_in_model = root_b in model_a
    plan = shortest_plan({"model": model_a, "root": root_b}, lambda k: k in goal_keys_a)
    rec = {
        "mode": mode, "seed": seed, "budget_on_A": budget,
        "A_states": learned["state_count"], "A_transitions": learned["transition_count"],
        "A_goal_states": len(goal_keys_a),
        "B_root_in_A_model": root_in_model,
        "B_new_actions_before_plan": 0,
        "plan_on_B": plan,
        "goal_reached_on_B": None,
    }
    if plan is not None:
        env_b.reset()
        for a in plan:
            env_b.act(a)
        rec["goal_reached_on_B"] = bool(env_b.is_goal(env_b.state()))
    rec["seconds"] = round(time.time() - t0, 2)
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=300)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    workdir = tempfile.mkdtemp(prefix="env_transfer_probe_")
    runs = []
    try:
        for mode in ("projected", "raw"):
            for seed in args.seeds:
                rec = run_once(mode, seed, args.budget, workdir)
                runs.append(rec)
                print(json.dumps(rec))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    summary = {}
    for mode in ("projected", "raw"):
        rs = [r for r in runs if r["mode"] == mode]
        summary[mode] = {
            "runs": len(rs),
            "B_root_in_A_model": sum(r["B_root_in_A_model"] for r in rs),
            "zero_experience_goal_reached_on_B": sum(bool(r["goal_reached_on_B"]) for r in rs),
        }
    receipt = {"schema": SCHEMA, "state_key_schema": STATE_KEY_SCHEMA,
               "authority": "NONE__SANDBOX_MEASUREMENT", "model_calls": 0,
               "stored_parameters": 0, "actions": ACTIONS, "runs": runs, "summary": summary}
    print(json.dumps({"summary": summary}))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
