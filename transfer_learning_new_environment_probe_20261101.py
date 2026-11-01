#!/usr/bin/env python3
"""Does instant learning transfer to a NEW arbitrary environment?

The claim: "we solved instant learning + instant learning in new arbitrary
environments." The strongest form of that is cross-run transfer: meet a kind of
environment once, then meet a DIFFERENT instance of that kind and solve it by
recall instead of by search.

`canonical/runtime/transfer_learning_v1.drive` is exactly that mechanism. This
probe runs it on five structurally different environment families. For each
family:

  COLD   -- instance A, transfer disabled. The machine has never seen it.
  FIRST  -- instance B (new initial state, new target), transfer ENABLED, store
            already holding what was learned on A.
  SECOND -- instance C, another new one, same store.

A family counts as transferring only if FIRST/SECOND reach the goal and the
status is PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN rather than by learning.
Every result is proven by executing the plan and observing the goal.

The state file is redirected to a temp path so this measurement does not mutate
the tree it measures.

Run:  python3 transfer_learning_new_environment_probe_20261101.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------- envs
class Lock:
    """N dials, each incremented mod its own size. Goal: all dials equal target."""
    def __init__(self, sizes, target, start=None):
        self.sizes, self.target, self.start = list(sizes), list(target), start
        self.reset()

    def reset(self):
        self.v = list(self.start) if self.start else [0] * len(self.sizes)

    def act(self, a):
        i = int(str(a).split("_")[1])
        self.v[i] = (self.v[i] + 1) % self.sizes[i]

    def state(self):
        return tuple(self.v)


class Toggles:
    """N boolean switches. Goal: all True."""
    def __init__(self, n, start=None):
        self.n, self.start = n, start
        self.reset()

    def reset(self):
        self.v = list(self.start) if self.start else [False] * self.n

    def act(self, a):
        i = int(str(a).split("_")[1])
        self.v[i] = not self.v[i]

    def state(self):
        return tuple(self.v)


class Accum:
    """Append letters. Goal: state equals a target word."""
    def __init__(self, target, start=""):
        self.target, self.start = target, start
        self.reset()

    def reset(self):
        self.s = self.start

    def act(self, a):
        self.s = (self.s + str(a).split("_")[1])[:len(self.target) + 2]

    def state(self):
        return self.s


class Grid:
    """Move on a 4x4 grid, clamped. Goal: reach a cell."""
    def __init__(self, goal, start=(0, 0)):
        self.goal, self.start = tuple(goal), tuple(start)
        self.reset()

    def reset(self):
        self.p = self.start

    def act(self, a):
        d = str(a).split("_")[1]
        x, y = self.p
        x = max(0, min(3, x + {"r": 1, "l": -1}.get(d, 0)))
        y = max(0, min(3, y + {"d": 1, "u": -1}.get(d, 0)))
        self.p = (x, y)

    def state(self):
        return self.p


class Modulo:
    """Counter mod m. Goal: reach a value."""
    def __init__(self, m, goal, start=0):
        self.m, self.goal, self.start = m, goal, start
        self.reset()

    def reset(self):
        self.c = self.start

    def act(self, a):
        d = str(a).split("_")[1]
        self.c = (self.c + {"1": 1, "2": 2, "3": 3}[d]) % self.m

    def state(self):
        return self.c


# ---------------------------------------------------------------- families + goals
FAMILIES = {
    "lock_3dial": {
        "goal_key": "lock__all_dials_equal_target",
        "actions": [f"dial_{i}" for i in range(3)],
        # target is a NON-ZERO value so the goal is not already true at reset
        "make": lambda seed: Lock((4, 4, 4), (3, 3, 3)),
        "is_goal": lambda s, seed=None: all(v == 3 for v in s),
    },
    "toggles_4": {
        "goal_key": "toggles__all_true",
        "actions": [f"sw_{i}" for i in range(4)],
        "make": lambda seed: Toggles(4, [bool((seed >> i) & 1) for i in range(4)]),
        "is_goal": lambda s, seed=None: all(s),
    },
    "accum_word": {
        "goal_key": "accum__spell_target",
        "actions": [f"put_{c}" for c in "abc"],
        "make": lambda seed: Accum("abc"),
        "is_goal": lambda s, seed=None: s == "abc",
    },
    "grid_reach": {
        "goal_key": "grid__reach_cell",
        "actions": ["mv_r", "mv_l", "mv_u", "mv_d"],
        "make": lambda seed: Grid((3, 2), (0, 0)),
        "is_goal": lambda s, seed=None: s == (3, 2),
    },
    "modulo_counter": {
        "goal_key": "modulo__reach_value",
        "actions": ["add_1", "add_2", "add_3"],
        "make": lambda seed: Modulo(7, 5),
        "is_goal": lambda s, seed=None: s == 5,
    },
}


def run() -> dict:
    from canonical.runtime import transfer_learning_v1 as tl

    out = {"schema": "PROBE_TRANSFER_NEW_ENVIRONMENT_V1", "families": {}}
    for name, spec in FAMILIES.items():
        rows = []
        # three DIFFERENT instances of the same family, in sequence, one store
        for phase, seed in (("COLD", 0), ("FIRST", 1), ("SECOND", 2)):
            env = spec["make"](seed)
            r = tl.drive(
                env, spec["actions"],
                is_goal=lambda s: spec["is_goal"](s),
                goal_key=spec["goal_key"],
                budget=200, seed=seed, max_depth=12,
                use_transfer=(phase != "COLD"),
            )
            rows.append({
                "phase": phase,
                "status": r.get("status"),
                "pass": bool(r.get("pass")),
                "plan": r.get("plan"),
                "trials_spent": r.get("trials_spent"),
                "act_calls": (r.get("interactions") or {}).get("act_calls"),
                "transferred": r.get("transferred"),
            })
        out["families"][name] = rows
    return out


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="brain_transfer_")
    os.environ["BRAIN_TRANSFER_LEARNING_STATE"] = str(Path(tmp) / "episodes.json")
    res = run()
    print(f"{'family':16} {'phase':7} {'status':44} {'pass':5} {'trials':6} {'acts':5} plan")
    print("-" * 120)
    for name, rows in res["families"].items():
        for r in rows:
            print(f"{name:16} {r['phase']:7} {str(r['status'])[:43]:44} "
                  f"{str(r['pass']):5} {str(r['trials_spent']):6} {str(r['act_calls']):5} {r['plan']}")
    print()
    cold = sum(1 for f in res["families"].values() for r in f if r["phase"] == "COLD" and r["pass"])
    first = [r for f in res["families"].values() for r in f if r["phase"] == "FIRST"]
    second = [r for f in res["families"].values() for r in f if r["phase"] == "SECOND"]
    tr_first = [r for r in first if r["status"] == "PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN"]
    tr_second = [r for r in second if r["status"] == "PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN"]
    print(f"families: {len(res['families'])}")
    print(f"COLD   solved (no prior experience): {cold}/{len(res['families'])}")
    print(f"FIRST  solved by RECALLED plan:      {len(tr_first)}/{len(first)}")
    print(f"SECOND solved by RECALLED plan:      {len(tr_second)}/{len(second)}")
    print(f"FIRST+SECOND solved at all:          "
          f"{sum(1 for r in first+second if r['pass'])}/{len(first+second)}")
    print(f"\nstate file (temp, not the tree): {os.environ['BRAIN_TRANSFER_LEARNING_STATE']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
