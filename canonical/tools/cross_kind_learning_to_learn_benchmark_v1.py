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
AUTHORITY = "NONE -- PRODUCER-RUN, CONSTRUCTED ENVIRONMENTS"

from canonical.tools.cross_kind_compounding_benchmark_v1 import _kinds  # noqa: E402
from canonical.runtime import learn_to_learn_v1 as l2l  # noqa: E402

# Kinds are split by name so no test kind is ever trained on. The split is fixed here, not
# chosen after seeing the numbers.
TRAIN_KINDS = ["append_letters", "grid_walk", "cyclic_counter", "dial_lock", "toggle_bank",
               "adjacent_sort"]
TEST_KINDS = ["two_jug_pour", "queue_rotate", "bit_register", "string_affix"]


def _fresh_ledger() -> None:
    path = os.path.join(tempfile.mkdtemp(prefix="brain_l2l_bench_"), "policy.json")
    os.environ["BRAIN_LEARN_TO_LEARN_STATE"] = path


def _solve_with(kind, make, policy, instance=1):
    env, actions, is_goal, _ = make(instance)
    meter = {"act_calls": 0}
    out = l2l.search(env, actions, is_goal=is_goal, policy=policy, max_depth=10,
                     node_budget=4000, meter=meter)
    return {"pass": out["pass"], "act_calls": out["act_calls"], "plan": out.get("plan"),
            "steps": len(out.get("plan") or []), "policy": policy}


def run(json_out=None):
    _fresh_ledger()
    kinds = _kinds()

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
        make = kinds[name]
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
