#!/usr/bin/env python3
"""Does instant learning transfer to a GENUINELY NEW instance of a known environment?

Why this file exists
--------------------
`transfer_learning_new_environment_probe_20261101.py` is cited by
`INSTANT_LEARNING_SCOPE_20261101_V1.md` section 0.7 as the load-bearing evidence for the
strongest claim in that document:

    "5/5 families, 10/10 new instances solved by recalled plan, several at 1 trial"

That probe is correct and reproducible, but in four of its five families the three "phases"
construct the SAME instance. Measured 2026-11-03:

    lock_3dial     seed0=(0,0,0)  seed1=(0,0,0)  seed2=(0,0,0)   IDENTICAL
    accum_word     seed0=''       seed1=''       seed2=''        IDENTICAL
    grid_reach     seed0=(0,0)    seed1=(0,0)    seed2=(0,0)     IDENTICAL
    modulo_counter seed0=0        seed1=0        seed2=0         IDENTICAL
    toggles_4      distinct (start bits come from `seed`)

So "NEW INSTANCE" there means "a second call on the same instance". The 1-trial rows are
real measurements of exact-episode replay: the stored plan was found, replayed, and the goal
observed. What they are NOT is evidence that the plan transfers to an instance the machine
has not solved before. Those are different abilities and this probe measures the second one.

What this measures
------------------
For each family and each of three seeds, in one fresh process with a disposable store:

    TEACH   solve a SOURCE instance with transfer off            -> what gets stored
    COLD    solve a TARGET instance with an EMPTY store, recall off
    WARM    solve the same TARGET with the store seeded from TEACH, recall on

TARGET differs from SOURCE in a parameter the family actually varies: dial sizes, target
values, and start state. COLD and WARM are handed the identical instance, so the pair is
controlled and the only difference is whether the lesson from TEACH was available.

Reported per case: trials and act() calls for each arm, and which authority finished, so a
direct plan replay is never counted as a win for a carried-over transition model.

`drive` labels any run that ends via the carried-over model `PASS__ENVIRONMENT_SOLVED_BY_
RECALLED_PLAN` with `transferred=True` -- the same label as a direct replay. That is why the
speedup columns, not the status string, are the finding, and why `authority` is printed.

No claim is made about arbitrary computer use, GUI environments, sentience, or permanence.
The five families are small constructed state spaces with a compact hashable `state()`.
A GUI reports pixels; `state()` is the whole difficulty there and this probe says nothing
about it.

Run (must be a fresh process; the state path is read at import time):

    python3 transfer_learning_new_instance_probe_20261103.py          # table
    python3 transfer_learning_new_instance_probe_20261103.py --json   # machine-readable
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEEDS = (0, 1, 2)


class Lock:
    """N dials, each incrementing mod its own size. Goal: the dial vector equals `target`."""

    def __init__(self, sizes, target, start=None):
        self.sizes, self.target, self.start = list(sizes), list(target), start
        self.reset()

    def reset(self):
        self.v = list(self.start) if self.start is not None else [0] * len(self.sizes)

    def act(self, action):
        i = int(str(action).split("_")[1])
        self.v[i] = (self.v[i] + 1) % self.sizes[i]

    def state(self):
        return tuple(self.v)


class Toggles:
    """N switches. Goal: all True. Each action flips exactly one switch."""

    def __init__(self, n, start=None):
        self.n, self.start = n, start
        self.reset()

    def reset(self):
        self.v = list(self.start) if self.start is not None else [False] * self.n

    def act(self, action):
        i = int(str(action).split("_")[1])
        self.v[i] = not self.v[i]

    def state(self):
        return tuple(self.v)


class Accum:
    """Append letters. Goal: the state equals a target word."""

    def __init__(self, target, start=""):
        self.target, self.start = target, start
        self.reset()

    def reset(self):
        self.s = self.start

    def act(self, action):
        self.s = (self.s + str(action).split("_")[1])[: len(self.target) + 2]

    def state(self):
        return self.s


class Grid:
    """Move on a 4x4 grid, clamped. Goal: reach a cell."""

    def __init__(self, goal, start=(0, 0)):
        self.goal, self.start = tuple(goal), tuple(start)
        self.reset()

    def reset(self):
        self.p = self.start

    def act(self, action):
        d = str(action).split("_")[1]
        x, y = self.p
        x = max(0, min(3, x + {"r": 1, "l": -1}.get(d, 0)))
        y = max(0, min(3, y + {"d": 1, "u": -1}.get(d, 0)))
        self.p = (x, y)

    def state(self):
        return self.p


class Modulo:
    """A counter mod m. Goal: reach a value."""

    def __init__(self, m, goal, start=0):
        self.m, self.goal, self.start = m, goal, start
        self.reset()

    def act(self, action):
        d = str(action).split("_")[1]
        self.c = (self.c + {"1": 1, "2": 2, "3": 3}[d]) % self.m

    def reset(self):
        self.c = self.start

    def state(self):
        return self.c


# Each family supplies, per seed, a SOURCE instance and a TARGET instance that differ in a
# parameter the family genuinely varies. `is_goal` is per-instance because the target moves.
FAMILIES = {
    "lock_3dial": {
        "actions": [f"dial_{i}" for i in range(3)],
        "source": lambda s: (Lock((4, 4, 4), (3, 3, 3)),
                             lambda st: list(st) == [3, 3, 3],
                             "lock sizes=(4,4,4) target=(3,3,3) start=None"),
        "target": lambda s: (
            # sizes, target and start all move; the goal stays "all dials equal target"
            Lock((5, 5, 5), ((1, 2, 4), (2, 0, 3), (4, 1, 0))[s],
                 [(0, 0, 0), (1, 0, 0), (0, 2, 0)][s]),
            (lambda t: (lambda st: list(st) == list(t)))(
                ((1, 2, 4), (2, 0, 3), (4, 1, 0))[s]),
            f"lock sizes=(5,5,5) target={((1, 2, 4), (2, 0, 3), (4, 1, 0))[s]} "
            f"start={[(0, 0, 0), (1, 0, 0), (0, 2, 0)][s]}",
        ),
    },
    "toggles_4": {
        "actions": [f"sw_{i}" for i in range(4)],
        "source": lambda s: (Toggles(4, [bool((s >> i) & 1) for i in range(4)]),
                             lambda st: all(st),
                             f"toggles start={[bool((s >> i) & 1) for i in range(4)]}"),
        "target": lambda s: (Toggles(4, [bool((s + 1 + i) & 1) for i in range(4)]),
                             lambda st: all(st),
                             f"toggles start={[bool((s + 1 + i) & 1) for i in range(4)]}"),
    },
    "accum_word": {
        "actions": [f"put_{c}" for c in "abc"],
        "source": lambda s: (Accum("abc", ["", "a", "ab"][s]), lambda st: st == "abc",
                             f'accum target="abc" start={["", "a", "ab"][s]!r}'),
        "target": lambda s: (Accum("abc", ["ab", "", "a"][s]), lambda st: st == "abc",
                             f'accum target="abc" start={["ab", "", "a"][s]!r}'),
    },
    "grid_reach": {
        "actions": ["mv_r", "mv_l", "mv_u", "mv_d"],
        "source": lambda s: (Grid((3, 2), [(0, 0), (1, 0), (0, 1)][s]),
                             lambda st: tuple(st) == (3, 2),
                             f"grid goal=(3,2) start={[(0, 0), (1, 0), (0, 1)][s]}"),
        "target": lambda s: (Grid(((0, 0), (2, 3), (3, 1))[s], [(3, 0), (0, 2), (1, 1)][s]),
                             (lambda g: (lambda st: tuple(st) == g))(
                                 ((0, 0), (2, 3), (3, 1))[s]),
                             f"grid goal={((0, 0), (2, 3), (3, 1))[s]} "
                             f"start={[(3, 0), (0, 2), (1, 1)][s]}"),
    },
    "modulo_counter": {
        "actions": ["add_1", "add_2", "add_3"],
        "source": lambda s: (Modulo(7, 5, s), lambda st: st == 5,
                             f"modulo m=7 goal=5 start={s}"),
        "target": lambda s: (Modulo((9, 11, 13)[s], (4, 7, 10)[s], (2, 1, 3)[s]),
                             (lambda g: (lambda st: st == g))(((4, 7, 10)[s])),
                             f"modulo m={(9, 11, 13)[s]} goal={(4, 7, 10)[s]} "
                             f"start={(2, 1, 3)[s]}"),
    },
}


def _fresh_store(transfer) -> None:
    """Point the module at a new empty store. transfer_learning_v1 reads it at import."""
    transfer.STATE_PATH = os.path.join(tempfile.mkdtemp(prefix="brain_new_instance_"),
                                       "episodes.json")


def _arm(transfer, env, actions, is_goal, goal_key, seed, use_transfer):
    result = transfer.drive(
        env, actions, is_goal=is_goal, goal_key=goal_key,
        budget=200, seed=seed, max_depth=12, use_transfer=use_transfer,
    )
    return {
        "pass": result.get("pass") is True,
        "status": result.get("status"),
        "authority": result.get("authority"),
        "transferred_flag": result.get("transferred"),
        "recall_candidates": result.get("recall_candidates"),
        "prior_transitions": result.get("prior_transitions"),
        "trials": result.get("trials_spent"),
        "act_calls": (result.get("interactions") or {}).get("act_calls"),
        "plan_length": len(result.get("plan") or []),
    }


def run() -> dict:
    if "canonical.runtime.transfer_learning_v1" in sys.modules:
        raise RuntimeError("PROBE_REQUIRES_FRESH_PROCESS")

    from canonical.runtime import transfer_learning_v1 as transfer

    # A caller may have pointed the module at its own store via the environment. Every arm
    # below rebinds BOTH the episode path and (through it) the fingerprint-cache path to a
    # disposable temp directory, so that store is neither read nor written. Measured
    # 2026-11-03: rebinding only the environment variable was not enough -- `STATE_PATH` is
    # read at import time, so a warm arm silently inherited the real store and reported a
    # 1-trial recall on an instance the store had never seen. The fingerprint cache is the
    # same trap: it survives across store swaps unless it is moved too.
    if not str(transfer.STATE_PATH).startswith(tempfile.gettempdir()):
        transfer.STATE_PATH = os.path.join(
            tempfile.mkdtemp(prefix="brain_new_instance_"), "episodes.json")
    assert str(transfer.STATE_PATH).startswith(tempfile.gettempdir()), transfer.STATE_PATH

    cases = []
    for name, spec in FAMILIES.items():
        for seed in SEEDS:
            src_env, src_goal, src_desc = spec["source"](seed)
            tgt_env, tgt_goal, tgt_desc = spec["target"](seed)
            # The instances really must differ, or this probe measures nothing.
            if src_desc == tgt_desc:
                raise ValueError(f"INSTANCES_NOT_DISTINCT:{name}:{seed}")
            if src_goal(src_env.state()) or tgt_goal(tgt_env.state()):
                raise ValueError(f"GOAL_ALREADY_TRUE:{name}:{seed}")
            goal_key = f"new-instance-probe:{name}"

            _fresh_store(transfer)
            teach = _arm(transfer, src_env, spec["actions"], src_goal, goal_key,
                         seed, use_transfer=False)

            # COLD and WARM get byte-identical instances. COLD gets an empty store;
            # WARM gets a store seeded by TEACH on the different SOURCE instance.
            _fresh_store(transfer)
            cold = _arm(transfer, tgt_env, spec["actions"], tgt_goal, goal_key,
                        seed, use_transfer=False)

            _fresh_store(transfer)
            _arm(transfer, src_env, spec["actions"], src_goal, goal_key,
                 seed, use_transfer=False)
            warm = _arm(transfer, tgt_env, spec["actions"], tgt_goal, goal_key,
                        seed, use_transfer=True)

            cases.append({
                "family": name, "seed": seed,
                "source_instance": src_desc,
                "target_instance": tgt_desc,
                "source_start_state": repr(src_env.state()),
                "target_start_state": repr(tgt_env.state()),
                "teach": teach, "cold": cold, "warm": warm,
            })

    def ratio(a, b):
        return round(a / b, 3) if b else None

    for case in cases:
        cold, warm = case["cold"], case["warm"]
        case["trial_speedup"] = ratio(cold["trials"] or 0, warm["trials"] or 0)
        case["act_speedup"] = ratio(cold["act_calls"] or 0, warm["act_calls"] or 0)
        # A genuine win is fewer trials AND no more work through the environment.
        case["genuine_saving"] = bool(
            warm["pass"] and cold["pass"]
            and (warm["trials"] or 0) < (cold["trials"] or 0)
            and (warm["act_calls"] or 0) <= (cold["act_calls"] or 0)
        )

    summary = {
        "cases": len(cases),
        "instances_distinct": sum(
            c["source_instance"] != c["target_instance"] for c in cases),
        "teach_solved": sum(c["teach"]["pass"] for c in cases),
        "cold_solved": sum(c["cold"]["pass"] for c in cases),
        "warm_solved": sum(c["warm"]["pass"] for c in cases),
        "warm_solved_with_fewer_trials": sum(
            (c["warm"]["trials"] or 0) < (c["cold"]["trials"] or 0) for c in cases),
        "warm_genuine_saving_trials_and_acts": sum(c["genuine_saving"] for c in cases),
        "warm_reached_goal_in_one_trial": sum(
            (c["warm"]["trials"] or 0) == 1 and c["warm"]["pass"] for c in cases),
        "mean_trial_speedup": round(
            sum(c["trial_speedup"] for c in cases) / len(cases), 3),
        "mean_act_speedup": round(
            sum(c["act_speedup"] for c in cases) / len(cases), 3),
        # The residual cost, measured rather than asserted: in the cases the carried model
        # cannot reach, the walk is pure overhead, so its size decides whether memory is a net
        # loss there. Trials may tie but the walk still spends act calls.
        "warm_more_act_calls_than_cold": sum(
            c["warm"]["act_calls"] > c["cold"]["act_calls"] for c in cases),
        "worst_act_call_overhead_ratio": round(max(
            (c["warm"]["act_calls"] or 0) / max(1, c["cold"]["act_calls"] or 1)
            for c in cases), 3),
        "warm_worse_on_trials": sum(
            (c["warm"]["trials"] or 0) > (c["cold"]["trials"] or 0) for c in cases),
    }
    return {
        "schema": "PROBE_TRANSFER_NEW_INSTANCE_V1",
        "scope": "five constructed families; source and target instances differ in a varied parameter",
        "authority": "AUTHORITY NONE -- PRODUCER-RUN SANDBOX MEASUREMENT, NOT INDEPENDENT VERIFICATION",
        "summary": summary,
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    report = run()
    if "--json" in argv:
        print(json.dumps(report, indent=2))
        return 0
    header = (f"{'family':15} {'seed':4} {'teach':>6} {'cold t/a':>13} "
              f"{'warm t/a':>13} {'gain':>13}  note")
    print(header)
    print("-" * len(header))
    for c in report["cases"]:
        cold, warm = c["cold"], c["warm"]
        note = "GENUINE SAVING" if c["genuine_saving"] else (
            "same or worse" if (warm["trials"] or 0) >= (cold["trials"] or 0) else "fewer trials, more acts")
        print(f"{c['family']:15} {c['seed']:<4} {c['teach']['trials']:>6} "
              f"{str(cold['trials']) + '/' + str(cold['act_calls']):>13} "
              f"{str(warm['trials']) + '/' + str(warm['act_calls']):>13} "
              f"{str(c['trial_speedup']) + 'x/' + str(c['act_speedup']) + 'x':>13}  {note}")
    print()
    s = report["summary"]
    print(f"cases: {s['cases']}   source != target instance: {s['instances_distinct']}/{s['cases']}")
    print(f"TEACH solved: {s['teach_solved']}   COLD solved: {s['cold_solved']}   "
          f"WARM solved: {s['warm_solved']}")
    print(f"WARM with fewer trials than COLD: {s['warm_solved_with_fewer_trials']}/{s['cases']}")
    print(f"WARM genuine saving (fewer trials AND no more act calls): "
          f"{s['warm_genuine_saving_trials_and_acts']}/{s['cases']}")
    print(f"WARM reached the goal in 1 trial: {s['warm_reached_goal_in_one_trial']}/{s['cases']}")
    print(f"WARM worse on trials than COLD: {s['warm_worse_on_trials']}/{s['cases']}"
          f"   (must be 0: carrying memory may cost act calls, never trials)")
    print(f"WARM spent more act calls: {s['warm_more_act_calls_than_cold']}/{s['cases']}"
          f"   worst act-call overhead: {s['worst_act_call_overhead_ratio']}x")
    print(f"mean trial speedup: {s['mean_trial_speedup']}x   "
          f"mean act-call speedup: {s['mean_act_speedup']}x")
    print()
    print("This is a producer-run measurement of five constructed environments.")
    print("It is not independent verification, and it says nothing about GUI or unbounded computer use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
