"""Gap-directed explorer on two UNSEEN start structures, with controls (sandbox measurement).

Training (fixed): three counterfactual starts (environment_abstraction_shift_probe_v1.TRAIN),
abstraction learned by environment_abstraction_v1 from their observations.

Unseen structures (never in training, differ from it in structure, not just tag):
  staged    : the user's edit is staged in the index.
  committed : the user's edit is already committed on `feature` (lives in history).

Arms (each on 10 seeds, budget 40 real actions per run):
  model+checkpoint      : learned abstraction + checkpointed must-not-change enforcement
  no_model+checkpoint   : same explorer, empty model (control for the transfer benefit)
  model+no_checkpoint   : learned abstraction, no enforcement (control for the safety mechanism)

must-not-change predicate (`keep`): the user's edit still exists (worktree, index or any commit
reachable from --all). It is an explicit spec, not learned.
Success: the real goal holds at the end (main, clean, main content, edit kept).

Checkpoint = full copy of the repository directory. A checkpoint is not counted as an action.
The restore cost is reported as `restores`. No model is called; no parameters are stored.
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
    abstract, akey, build_abstract_model, invariant_vocabulary)
from canonical.runtime.environment_abstraction_git_probe_v1 import (  # noqa: E402
    ACTIONS, GitInstance, _git)
from canonical.runtime.environment_abstraction_shift_probe_v1 import (  # noqa: E402
    StagedInstance, TRAIN, goal_fn)
from canonical.runtime.environment_learning_v1 import learn_model  # noqa: E402
from canonical.runtime.environment_gap_explorer_v1 import AbstractModel, explore  # noqa: E402

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_GAP_EXPLORER_PROBE_V1"


class CommittedInstance(GitInstance):
    """Unseen structure: the user's edit is already committed on `feature`."""

    def reset(self):
        super().reset()
        _git(["add", "-A"], self.root)
        _git(["commit", "-qm", "user wip"], self.root)


class Checkpointed:
    """Environment wrapper: directory checkpoint/restore around a real git instance."""

    def __init__(self, inst: GitInstance, work: str):
        self.inst, self.work = inst, work

    def state(self):
        return self.inst.state()

    def act(self, action):
        self.inst.act(action)

    def checkpoint(self):
        path = os.path.join(tempfile.mkdtemp(dir=self.work), "snap")
        shutil.copytree(self.inst.root, path, symlinks=True)
        return path

    def restore(self, path):
        shutil.rmtree(self.inst.root)
        shutil.copytree(path, self.inst.root, symlinks=True)
        shutil.rmtree(os.path.dirname(path))


def keep_edit(snap) -> bool:
    return bool(snap["edit_survives"])


def run_arm(learned_models, vocab, structure: str, seed: int, use_model: bool,
            enforce: bool, work: str) -> dict:
    cls = StagedInstance if structure == "staged" else CommittedInstance
    inst = cls(os.path.join(work, f"X_{structure}_{seed}_{use_model}_{enforce}"), "tagH", "stray_H.txt")
    inst.reset()
    env = Checkpointed(inst, work)
    base = build_abstract_model(learned_models, vocab, goal_fn)
    model = AbstractModel(base["model"], base["goal_states"]) if use_model else AbstractModel()
    key = lambda s: akey(abstract(s, vocab))  # noqa: E731
    keep = keep_edit if enforce else (lambda s: True)
    res = explore(env, ACTIONS, model, key=key, goal=goal_fn, keep=keep,
                  budget=40, seed=seed)
    res["must_not_change_holds_at_end"] = keep_edit(res["final"])
    res.pop("final")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-budget", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    work = tempfile.mkdtemp(prefix="gap_explorer_probe_")
    try:
        learned = []
        for i, (tag, junk) in enumerate(TRAIN):
            inst = GitInstance(os.path.join(work, f"T{i}"), tag, junk)
            learned.append(learn_model(inst, ACTIONS, budget=args.train_budget, seed=i))
        vocab = invariant_vocabulary([list(L["observations"].values()) for L in learned])
        arms = [("model_checkpoint", True, True), ("no_model_checkpoint", False, True),
                ("model_no_checkpoint", True, False)]
        out: dict = {}
        for structure in ("staged", "committed"):
            out[structure] = {}
            for name, use_model, enforce in arms:
                rows = [run_arm(learned, vocab, structure, s, use_model, enforce, work)
                        for s in range(args.seeds)]
                out[structure][name] = {
                    "success": sum(r["success"] for r in rows),
                    "of": len(rows),
                    "actions": [r["actions"] for r in rows],
                    "restores": sum(r["restores"] for r in rows),
                    "mismatches": sum(r["mismatches"] for r in rows),
                    "must_not_change_violated_at_end": sum(not r["must_not_change_holds_at_end"] for r in rows),
                    "rows": rows,
                }
                print(structure, name, "success", out[structure][name]["success"],
                      "/", args.seeds, flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    receipt = {"schema": SCHEMA, "authority": "NONE__SANDBOX_MEASUREMENT", "model_calls": 0,
               "stored_parameters": 0, "actions": ACTIONS, "budget_per_run": 40,
               "train_starts": TRAIN, "results": out}
    text = json.dumps(receipt, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    print(json.dumps({s: {a: {k: v[k] for k in ("success", "of", "restores", "must_not_change_violated_at_end")}
                          for a, v in arms_.items()} for s, arms_ in out.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
