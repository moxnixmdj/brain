"""Unseen STRUCTURE probe (sandbox measurement, no authority).

Training (fixed): three counterfactual starts (tag + junk name) -> invariant abstraction.
Test start: the user's edit is already STAGED (`git add`). Its root observation is not in the
training data. Ten seeds. For each seed the agent gets a budget of ONE walk (or one action)
on the new start, merged into the same abstract model. Two policies:

  open_loop   : plan once, execute the whole plan, check the goal.
  closed_loop : execute one step, observe the real state, record that transition, replan.

Reported: whether the goal (on main, clean, main content, user edit preserved) holds after
execution, and the trail. Plans that the abstract model predicts but the real repository does
not honour are counted as soundness failures.

Run: python3 canonical/runtime/environment_abstraction_shift_probe_v1.py --out <file>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))

from canonical.runtime.environment_abstraction_v1 import (  # noqa: E402
    abstract, akey, build_abstract_model, invariant_vocabulary, plan_in_abstraction)
from canonical.runtime.environment_abstraction_git_probe_v1 import (  # noqa: E402
    ACTIONS, GitInstance, _git)
from canonical.runtime.environment_learning_v1 import learn_model  # noqa: E402

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_ABSTRACTION_SHIFT_PROBE_V1"
TRAIN = [("tagT1", "junk_T1.txt"), ("tagT2", "junk_T2.txt"), ("tagT3", "junk_T3.txt")]


class StagedInstance(GitInstance):
    """Unseen structure: the user's edit is already staged when the agent arrives."""

    def reset(self):
        super().reset()
        _git(["add", "a.txt"], self.root)


def goal_fn(s) -> bool:
    return (s["head"] == "main" and s["dirty"] == [] and s["a"] is not None
            and s["a"].startswith("main ") and s["edit_survives"])


def add_edge(m, vocab, before, act, after):
    b, a = akey(abstract(before, vocab)), akey(abstract(after, vocab))
    m["model"].setdefault(b, {})[str(act)] = a
    m["model"].setdefault(a, {})
    if goal_fn(after):
        m["goal_states"] = sorted(set(m["goal_states"]) | {a})


def run_closed_loop(m, vocab, inst, max_steps=12):
    trail = []
    for _ in range(max_steps):
        cur = inst.state()
        if goal_fn(cur):
            return True, trail
        plan = plan_in_abstraction(m, cur, vocab)
        if not plan:
            return False, trail + ["NO_PLAN"]
        inst.act(plan[0])
        after = inst.state()
        add_edge(m, vocab, cur, plan[0], after)
        trail.append(plan[0])
    return goal_fn(inst.state()), trail


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-budget", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    work = tempfile.mkdtemp(prefix="abstraction_shift_")
    try:
        learned = []
        for i, (tag, junk) in enumerate(TRAIN):
            inst = GitInstance(os.path.join(work, f"T{i}"), tag, junk)
            learned.append(learn_model(inst, ACTIONS, budget=args.train_budget, seed=i))
        vocab = invariant_vocabulary([list(L["observations"].values()) for L in learned])
        base = build_abstract_model(learned, vocab, goal_fn)

        zero = StagedInstance(os.path.join(work, "Z"), "tagH", "stray_H.txt")
        zero.reset()
        zero_root = akey(abstract(zero.state(), vocab))
        zero_result = {
            "abstraction_status": base["status"],
            "root_known_without_experience": zero_root in base["model"] or zero_root in base["goal_states"],
            "plan_without_experience": plan_in_abstraction(base, zero.state(), vocab),
        }

        arms = {}
        for md, label in ((1, "one_action"), (6, "one_walk")):
            rows = []
            for seed in range(args.seeds):
                # open loop
                inst = StagedInstance(os.path.join(work, f"O_{label}_{seed}"), "tagH", "stray_H.txt")
                Lh = learn_model(inst, ACTIONS, budget=1, seed=seed, max_depth=md)
                m = build_abstract_model(learned + [Lh], vocab, goal_fn)
                inst.reset()
                plan = plan_in_abstraction(m, inst.state(), vocab)
                open_ok = False
                if plan is not None:
                    inst.reset()
                    for a in plan:
                        inst.act(a)
                    open_ok = goal_fn(inst.state())
                # closed loop, same learned experience
                inst2 = StagedInstance(os.path.join(work, f"C_{label}_{seed}"), "tagH", "stray_H.txt")
                Lh2 = learn_model(inst2, ACTIONS, budget=1, seed=seed, max_depth=md)
                m2 = build_abstract_model(learned + [Lh2], vocab, goal_fn)
                inst2.reset()
                closed_ok, trail = run_closed_loop(m2, vocab, inst2)
                rows.append({"seed": seed, "open_loop_plan": plan, "open_loop_goal": open_ok,
                             "closed_loop_trail": trail, "closed_loop_goal": closed_ok})
            arms[label] = {
                "open_loop_success": sum(r["open_loop_goal"] for r in rows),
                "closed_loop_success": sum(r["closed_loop_goal"] for r in rows),
                "rows": rows,
            }
    finally:
        shutil.rmtree(work, ignore_errors=True)

    receipt = {"schema": SCHEMA, "authority": "NONE__SANDBOX_MEASUREMENT", "model_calls": 0,
               "stored_parameters": 0, "actions": ACTIONS, "seeds": args.seeds,
               "train_starts": TRAIN, "zero_experience": zero_result, "arms": arms}
    text = json.dumps(receipt, indent=1, sort_keys=True)
    print(text)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
