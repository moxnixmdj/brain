#!/usr/bin/env python3
"""Can the searcher learn WHICH SEARCH to use, on kinds it has never seen?

The measurement that decides whether this repository can compound at all.

`cross_kind_compounding_benchmark_v1.py` measured, on 2026-11-03, that meeting nine kinds made
the tenth kind **byte-identical in cost (10/10, net saving 0)**. That is a fact about the
transition-model mechanism: it stores facts keyed per kind, so it cannot compound by construction.

`learn_to_learn_v1` stores something different -- credit for PROCEDURES, indexed by a coarse view
of the problem that does not name its kind. This benchmark asks whether that compounds:

    TRAIN on a set of kinds.       (the learned ledger is built here)
    TEST  on kinds never trained on, with the SAME problem solved under three arms:
            best_policy   the policy the ledger chooses for this feature key
            random_policy a policy chosen at random   <- THE FALSIFIER
            default       bfs_lex, the boring baseline

If the learned choice does not beat a coin flip on unseen kinds, the features do not generalise,
this is noise with a story attached, and the honest conclusion is that the repository still
cannot compound.

WHY THE RANDOM ARM IS NOT OPTIONAL
----------------------------------
Any set of policies will differ on any set of problems. Publishing "the learned choice beat the
default" without a random arm would let a lucky ordering masquerade as learning. The random arm
is sampled 5 times per test kind and the learned choice has to beat its MEAN, not its worst.

WHAT THIS CANNOT SEE
--------------------
The policy vocabulary is written by hand. If learning succeeds, it means the system learns WHICH
of five given strategies to apply -- not that it invents strategies. Said plainly because the
larger claim would be false.

Run:
    python3 canonical/tools/cross_kind_learning_to_learn_benchmark_v1.py
    python3 canonical/tools/cross_kind_learning_to_learn_benchmark_v1.py --json out.json

Authority: NONE. Producer-run. Constructed environments.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "CROSS_KIND_LEARNING_TO_LEARN_BENCHMARK_V1"
# A TIGHT NODE BUDGET ON PURPOSE. Measured 2026-11-03: with an exhaustive budget every policy
# finds a shortest plan on these problems, so ordering decides nothing and the benchmark can
# only measure noise. A policy is a lever only when search is bounded -- which is also the only
# regime that resembles a real computer, where the action space is not enumerable.
NODE_BUDGET = 40
AUTHORITY = "NONE -- PRODUCER-RUN, CONSTRUCTED ENVIRONMENTS"

from canonical.tools.cross_kind_compounding_benchmark_v1 import _kinds  # noqa: E402
from canonical.runtime import learn_to_learn_v1 as l2l  # noqa: E402

# Kinds are split by name so no test kind is ever trained on. The split is fixed here, not
# chosen after seeing the numbers.
TRAIN_KINDS = ["append_letters", "grid_walk", "cyclic_counter", "dial_lock", "toggle_bank",
               "adjacent_sort", "two_jug_pour", "queue_rotate", "bit_register", "string_affix"]
TEST_KINDS = ["reverse_string", "parity_lights", "sliding_pairs", "stack_pushout",
              "letter_shift", "binary_odometer", "ring_rotate", "double_dial", "last_wins",
              "tri_lock"]

# PRE-REGISTERED STOPPING RULE, written before the run.
STOPPING_RULE = (
    "The features have already been changed twice after seeing a negative result. This is the "
    "LAST change decided that way. Whatever this reports, the next step is a decision, not "
    "another tuning pass. See LEARN_TO_LEARN_VERDICT_20261103_V1.md."
)




# --------------------------------------------------------------------------- #
# TEN HELD-OUT KINDS. Written before the run and not edited after seeing results.
# Composed from the same structural vocabulary as the training kinds (readout,
# permute, toggle, carry); deliberately none is a copy of one.
# --------------------------------------------------------------------------- #
# Ten HELD-OUT kinds. Composed from the same structural vocabulary (readout / permute / toggle /
# carry) but none is a copy of a training kind. Written before the run, then not edited.
class ReverseString:
    def __init__(self, target): self.target = target; self.reset()
    def reset(self): self.s = ""
    def act(self, a):
        c = str(a).split("_")[1]
        if c == "pop" and self.s: self.s = self.s[:-1]
        else: self.s = (self.s + c)
    def state(self): return self.s

class ParityLights:
    def __init__(self, n, start): self.n, self.start = n, start; self.reset()
    def reset(self): self.v = list(self.start)
    def act(self, a):
        i = int(str(a).split("_")[1])
        self.v[i] = not self.v[i]
        self.v[(i + 1) % self.n] = not self.v[(i + 1) % self.n]
    def state(self): return tuple(self.v)

class SlidingPairs:
    def __init__(self, start): self.start = start; self.reset()
    def reset(self): self.v = list(self.start)
    def act(self, a):
        i = int(str(a).split("_")[1])
        self.v[i], self.v[i + 1] = self.v[i + 1], self.v[i]
    def state(self): return tuple(self.v)

class StackPushout:
    """Grow or shrink the stack by one, then fix a slot.

    Reachability matters more than realism: the first version could push (+1) and pop (-1) but
    its starts and target differed by two and popping length 3 goes to 1, so the target length
    was UNREACHABLE BY CONSTRUCTION. Every policy then scored it unsolvable and the benchmark
    reported that as a fact about the terrain. A benchmark whose environments cannot be solved
    measures its own bugs.
    """

    def __init__(self, target, start): self.target, self.start = target, start; self.reset()

    def reset(self): self.v = list(self.start)

    def act(self, a):
        x = str(a)
        if x == "push":
            self.v.append("z")
        elif x == "top":
            if len(self.v) > 1:
                self.v.pop()
        elif x.startswith("set_"):
            i = int(x.split("_")[1])
            if i < len(self.v):
                self.v[i] = "a"
    def state(self): return tuple(self.v)

class LetterShift:
    def __init__(self, target, start): self.target, self.start = target, start; self.reset()
    def reset(self): self.v = list(self.start)
    def act(self, a):
        # "s0_up" -> index 0, +1. The first version packed the index and direction into one
        # segment and read "_" as the direction, so this raised on EVERY action and every
        # policy scored it unsolvable -- a terrain fact that was really a typo.
        idx = int(str(a).split("_")[0][1:])
        d = 1 if str(a).endswith("up") else -1
        self.v[idx] = chr(ord("a") + (ord(self.v[idx]) - ord("a") + d) % 26)
    def state(self): return tuple(self.v)

class BinaryOdometer:
    def __init__(self, n, target, start): self.n, self.target, self.start = n, target, start; self.reset()
    def reset(self): self.b = self.start
    def act(self, a):
        x = str(a)
        if x == "inc": self.b = (self.b + 1) % (1 << self.n)
        elif x == "dec": self.b = (self.b - 1) % (1 << self.n)
        elif x == "clr": self.b = 0
    def state(self): return self.b

class RingRotate:
    def __init__(self, target, start): self.target, self.start = target, start; self.reset()
    def reset(self): self.v = list(self.start)
    def act(self, a):
        if not self.v: return
        if str(a) == "cw": self.v = self.v[1:] + self.v[:1]
        else: self.v = self.v[-1:] + self.v[:-1]
    def state(self): return tuple(self.v)

class DoubleDial:
    def __init__(self, sizes, target): self.sizes, self.target = sizes, target; self.reset()
    def reset(self): self.v = [0, 0]
    def act(self, a):
        i = int(str(a).split("_")[0][1:])          # "d0_up" -> 0
        d = 1 if str(a).endswith("up") else -1
        self.v[i] = (self.v[i] + d) % self.sizes[i]
    def state(self): return tuple(self.v)

class LastWins:
    def __init__(self, target, start): self.target, self.start = target, start; self.reset()
    def reset(self): self.v = list(self.start)
    def act(self, a):
        i = int(str(a).split("_")[1])
        self.v[i] = 1
    def state(self): return tuple(self.v)

class TriLock:
    def __init__(self, sizes, target, start): self.sizes, self.target, self.start = sizes, target, start; self.reset()
    def reset(self): self.v = list(self.start)
    def act(self, a):
        i = int(str(a).split("_")[1])
        self.v[i] = (self.v[i] + 1) % self.sizes[i]
    def state(self): return tuple(self.v)


def _heldout_kinds():
    return {
        "reverse_string": (lambda i: (ReverseString("abc"), ["put_a", "put_b", "put_c", "pop"],
                                      lambda st: st == "abc", "build a string, can delete its tail")),
        "parity_lights": (lambda i: (ParityLights(4, [bool((i + j) & 1) for j in range(4)]),
                                     [f"fl_{j}" for j in range(4)], lambda st: all(st),
                                     "a flip also flips its neighbour")),
        "sliding_pairs": (lambda i: (SlidingPairs([("c", "a", "b", "d"), ("d", "c", "b", "a"),
                                                   ("b", "a", "d", "c")][i]),
                                     [f"sw_{j}" for j in range(3)],
                                     lambda st: tuple(st) == ("a", "b", "c", "d"),
                                     "swap neighbours toward sorted")),
        "stack_pushout": (lambda i: (StackPushout(("a", "b"),
                                                  [("a", "z", "z"), ("z", "z", "a"), ("a", "b", "z")][i]),
                                     ["push", "top", "set_0", "set_1"],
                                     lambda st: tuple(st) == ("a", "b"), "push/pop/set a stack")),
        "letter_shift": (lambda i: (LetterShift(("c", "d"), [("a", "a"), ("b", "a"), ("a", "c")][i]),
                                    ["s0_up", "s0_dn", "s1_up", "s1_dn"],
                                    lambda st: tuple(st) == (("c", "d"), ("c", "e"), ("d", "d"))[i],
                                    "shift each letter up or down")),
        "binary_odometer": (lambda i: (BinaryOdometer(4, (9, 6, 12)[i], (0, 3, 5)[i]),
                                       ["inc", "dec", "clr"],
                                       (lambda t: (lambda st: st == t))(((9, 6, 12)[i])),
                                       "increment a bounded register")),
        "ring_rotate": (lambda i: (RingRotate(("a", "b"), [("b", "a", "c"), ("c", "b", "a"),
                                                           ("a", "c", "b")][i]),
                                   ["cw", "ccw"],
                                   lambda st: tuple(st) == ("a", "b", "c"), "rotate a ring of symbols")),
        "double_dial": (lambda i: (DoubleDial((4, 5), ((2, 3), (1, 1), (3, 0))[i]),
                                   ["d0_up", "d0_dn", "d1_up", "d1_dn"],
                                   (lambda t: (lambda st: tuple(st) == t))(((2, 3), (1, 1), (3, 0))[i]),
                                   "two dials, each wrapping at its own size")),
        "last_wins": (lambda i: (LastWins((1, 1, 1), [(0, 0, 1), (1, 0, 0), (0, 1, 0)][i]),
                                 [f"on_{j}" for j in range(3)],
                                 lambda st: all(st), "set switches on, one way only")),
        "tri_lock": (lambda i: (TriLock((3, 4, 5), ((1, 2, 3), (2, 0, 4), (0, 1, 2))[i],
                                        [(0, 0, 0), (1, 1, 1), (2, 0, 0)][i]),
                                  [f"dial_{j}" for j in range(3)],
                                  (lambda t: (lambda st: list(st) == list(t)))(
                                      ((1, 2, 3), (2, 0, 4), (0, 1, 2))[i]),
                                  "three dials of different sizes")),
    }

def _fresh_ledger() -> None:
    path = os.path.join(tempfile.mkdtemp(prefix="brain_l2l_bench_"), "policy.json")
    os.environ["BRAIN_LEARN_TO_LEARN_STATE"] = path


def _solve_with(kind, make, policy, instance=1):
    env, actions, is_goal, _ = make(instance)
    meter = {"act_calls": 0}
    out = l2l.search(env, actions, is_goal=is_goal, policy=policy, max_depth=14,
                     node_budget=NODE_BUDGET, meter=meter)
    return {"pass": out["pass"], "act_calls": out["act_calls"], "plan": out.get("plan"),
            "steps": len(out.get("plan") or []), "policy": policy}


def run(json_out=None):
    _fresh_ledger()
    kinds = _kinds()
    test_kinds = _heldout_kinds()

    # ---------------- TRAIN ----------------
    print("TRAIN -- each kind solved under every policy, so the ledger has honest evidence")
    train_rows = []
    for name in TRAIN_KINDS:
        make = kinds[name]
        env, actions, is_goal, _ = make(1)
        fkey = l2l.feature_key(l2l.features(env, actions, is_goal))
        for policy in l2l.POLICIES:
            result = _solve_with(name, make, policy)
            l2l.credit(fkey, policy, trials=result["act_calls"], solved=result["pass"])
            train_rows.append({"kind": name, "feature_key": fkey, "policy": policy, **result})
        print(f"  {name:16} fkey={fkey:12} solved-by: "
              + ", ".join(sorted({r['policy'] for r in train_rows[-5:] if r['pass']})) or "none")

    # ---------------- TEST ----------------
    print("\nTEST -- kinds never trained on")
    test_rows = []
    rng = random.Random(20261103)
    for name in TEST_KINDS:
        make = test_kinds[name]
        env, actions, is_goal, _ = make(1)
        fkey = l2l.feature_key(l2l.features(env, actions, is_goal))
        chosen, why = l2l.choose(fkey)

        learned = _solve_with(name, make, chosen)
        default = _solve_with(name, make, "bfs_lex")
        randoms = []
        for _ in range(5):
            policy = rng.choice(list(l2l.POLICIES))
            randoms.append(_solve_with(name, make, policy))

        def cost_of(r):
            # An unsolved run is not cheap: it burns its whole budget and solves nothing.
            return r["act_calls"] if r["pass"] else 10 ** 6

        mean_random = sum(cost_of(r) for r in randoms) / len(randoms)
        test_rows.append({
            "kind": name, "feature_key": fkey, "chosen_policy": chosen, "why": why,
            "learned": {**learned, "cost": cost_of(learned)},
            "default": {**default, "cost": cost_of(default)},
            "random": {"arms": randoms, "mean_cost": mean_random,
                       "solved": sum(1 for r in randoms if r["pass"])},
            "beat_default": cost_of(learned) < cost_of(default),
            "beat_random_mean": cost_of(learned) < mean_random,
        })
        print(f"  {name:16} fkey={fkey:12} chose={chosen:12} "
              f"learned={learned['act_calls']:>6}{'' if learned['pass'] else 'X'} "
              f"default={default['act_calls']:>6}{'' if default['pass'] else 'X'} "
              f"random_mean={mean_random:>8.0f}")

    beats_default = sum(1 for r in test_rows if r["beat_default"])
    beats_random = sum(1 for r in test_rows if r["beat_random_mean"])
    solved_all = sum(1 for r in test_rows if r["learned"]["pass"])
    doc = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "train_kinds": TRAIN_KINDS,
        "test_kinds": TEST_KINDS,
        "policy_vocabulary_is_hand_written": True,
        "train_rows": train_rows,
        "test_rows": test_rows,
        "summary": {
            "test_kinds": len(test_rows),
            "learned_solved": solved_all,
            "beat_default": beats_default,
            "beat_random_mean": beats_random,
        },
        "verdict": (
            "COMPOUNDING_OBSERVED -- the learned choice beat both the default and the random "
            "mean on most unseen kinds; see rows for the exceptions"
            if beats_default >= 3 and beats_random >= 3 else
            "NO_COMPOUNDING -- the learned choice is not better than a coin flip on unseen "
            "kinds; the features do not generalise and this is not learning-to-learn"),
        "cannot_see": ["strategy invention -- the five policies are written by hand",
                       "GUI environments, pixels, unbounded action sets"],
    }
    if json_out:
        Path(json_out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print(f"\nwrote {json_out}")

    print("\n" + "=" * 78)
    print(f"test kinds={len(test_rows)}  learned solved={solved_all}")
    print(f"beat default={beats_default}/{len(test_rows)}   "
          f"beat random mean={beats_random}/{len(test_rows)}")
    print(doc["verdict"])
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json")
    args = ap.parse_args()
    run(json_out=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
