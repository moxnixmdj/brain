#!/usr/bin/env python3
"""Does meeting more KINDS of environment make the next kind cheaper?

WHY THIS IS THE DEEPEST MEASUREMENT IN THE REPOSITORY
-----------------------------------------------------
Everything else measured here is a count of red tests or a per-kind transfer number. This asks the
only question that separates a *creature* from a very well-audited program:

    A program does what its code says. A creature gets better at NEW problems because it has met
    old ones.

Measured on 2026-11-03 (P1 §4b): a store holding **four other kinds** behaves **byte-identically**
to a store holding only its own kind -- 15/15, 8/15 one-trial, 22.4 trials, 182 acts, both arms.
Five environments did not make the sixth cheaper. That result is about the *transition-model*
mechanism: it is keyed per kind, so it cannot compound across kinds by construction.

This benchmark asks the question in a form that gives compounding its best chance, rather than
asking whether one particular mechanism compounds:

    For KIND k in an order of never-before-seen kinds, solve the same instance twice --
    once with an EMPTY store, once with a store that has already solved kinds 1..k-1.

If meeting more kinds helps at all, `grown_acts < cold_acts`. If it does not, the creature is a
skill cache: it remembers what it has done and learns nothing transferable from having done it.

METHOD, AND WHAT IT CANNOT SEE
------------------------------
* Every arm solves the SAME instance in the SAME process position; only the store differs.
* Instances are fresh per kind and never appear in the store used to solve them.
* `act_calls` counts every call through the environment interface, including structural probes and
  look-ahead, so a mechanism cannot look cheap by hiding work in a probe.
* The environment classes are imported from `transfer_learning_new_instance_probe_20261103.py`, so
  the semantics are the ones already measured -- not a new toy written to make this look good.

It cannot see: GUI environments, pixels, unbounded action sets, or any state that cannot be
written as a small hashable value. `state()` remains the whole difficulty in real computer use and
this file says nothing about it.

Run:
    python3 canonical/tools/cross_kind_compounding_benchmark_v1.py
    python3 canonical/tools/cross_kind_compounding_benchmark_v1.py --json out.json

Authority: NONE. A producer-run measurement on constructed environments.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "CROSS_KIND_COMPOUNDING_BENCHMARK_V1"
AUTHORITY = "NONE -- PRODUCER-RUN, CONSTRUCTED ENVIRONMENTS"


# --------------------------------------------------------------------------- #
# Kinds. Each is a (state type, action set, dynamics, goal shape) quadruple that
# shares NO declared structure with any other, so a prior keyed on kind identity
# cannot help the next one. Imported classes keep four of them identical to the
# semantics already published in the 2026-11-03 probe.
# --------------------------------------------------------------------------- #
from transfer_learning_new_instance_probe_20261103 import (  # noqa: E402
    Accum, Grid, Lock, Modulo, Toggles,
)


class Swap:
    """Reorder a 4-tuple of distinct symbols by swapping NEIGHBOURS."""

    TARGET = ("a", "b", "c", "d")

    def __init__(self, start):
        self.start = tuple(start)
        self.reset()

    def reset(self):
        self.v = list(self.start)

    def act(self, action):
        i = int(str(action).split("_")[1])
        self.v[i], self.v[i + 1] = self.v[i + 1], self.v[i]

    def state(self):
        return tuple(self.v)


class Jug:
    """Two jugs; fill, empty, or pour one into the other until one is full/empty."""

    def __init__(self, caps, goal, start=(0, 0)):
        self.caps, self.goal, self.start = tuple(caps), tuple(goal), tuple(start)
        self.reset()

    def reset(self):
        self.v = list(self.start)

    def act(self, action):
        a = str(action)
        cap_a, cap_b = self.caps
        if a == "fill_a":
            self.v[0] = cap_a
        elif a == "fill_b":
            self.v[1] = cap_b
        elif a == "empty_a":
            self.v[0] = 0
        elif a == "empty_b":
            self.v[1] = 0
        elif a == "pour_ab":
            m = min(self.v[0], cap_b - self.v[1])
            self.v[0] -= m
            self.v[1] += m
        elif a == "pour_ba":
            m = min(self.v[1], cap_a - self.v[0])
            self.v[1] -= m
            self.v[0] += m

    def state(self):
        return tuple(self.v)


class Rotate:
    """A queue; rotate left, rotate right, or drop the head."""

    def __init__(self, target, start):
        self.target, self.start = tuple(target), tuple(start)
        self.reset()

    def reset(self):
        self.v = list(self.start)

    def act(self, action):
        a = str(action)
        if not self.v:
            return
        if a == "rot_l":
            self.v = self.v[1:] + self.v[:1]
        elif a == "rot_r":
            self.v = self.v[-1:] + self.v[:-1]
        elif a == "drop":
            self.v = self.v[1:]

    def state(self):
        return tuple(self.v)


class Register:
    """An n-bit register; each action XORs one bit, one action shifts left."""

    def __init__(self, n, target, start=0):
        self.n, self.target, self.start = n, target, start
        self.reset()

    def reset(self):
        self.b = self.start

    def act(self, action):
        a = str(action)
        if a == "shift":
            self.b = (self.b << 1) & ((1 << self.n) - 1)
        else:
            i = int(a.split("_")[1])
            self.b ^= 1 << i

    def state(self):
        return self.b


def _kinds():
    """Ten kinds, each `make(instance)` -> (env, actions, is_goal, description)."""
    return {
        "append_letters": (lambda i: (Accum("abcde", ["", "ab", "abc"][i]),
                                      [f"put_{c}" for c in "abcde"],
                                      lambda st: st == "abcde",
                                      "append a letter until the word matches")),
        "grid_walk": (lambda i: (Grid(((3, 2), (0, 3), (2, 0))[i], [(0, 0), (1, 1), (3, 3)][i]),
                                 ["mv_r", "mv_l", "mv_u", "mv_d"],
                                 (lambda g: (lambda st: tuple(st) == g))(
                                     ((3, 2), (0, 3), (2, 0))[i]),
                                 "move on a clamped 4x4 grid")),
        "cyclic_counter": (lambda i: (Modulo((7, 9, 11)[i], (5, 4, 7)[i], i),
                                      ["add_1", "add_2", "add_3"],
                                      (lambda g: (lambda st: st == g))(((5, 4, 7)[i])),
                                      "add a step modulo m")),
        "dial_lock": (lambda i: (Lock((4, 5, 3)[i:i + 1] * 3 if False else ((4, 5, 3)[i],) * 3,
                                     ((1,) * 3 if i == 0 else (2, 1, 0) if i == 1 else (0, 3, 3)),
                                     (0, 0, 0) if i == 0 else (1, 0, 0) if i == 1 else (0, 1, 2)),
                                  [f"dial_{j}" for j in range(3)],
                                  (lambda t: (lambda st: list(st) == list(t)))(
                                      ((1, 1, 1), (2, 1, 0), (0, 3, 3))[i]),
                                  "increment each dial modulo its own size")),
        "toggle_bank": (lambda i: (Toggles(4, [bool((i + j) & 1) for j in range(4)]),
                                   [f"sw_{j}" for j in range(4)],
                                   lambda st: all(st),
                                   "flip switches until all are on")),
        "adjacent_sort": (lambda i: (Swap([("c", "a", "d", "b"), ("d", "c", "b", "a"),
                                           ("b", "d", "a", "c")][i]),
                                     [f"swap_{j}" for j in range(3)],
                                     lambda st: tuple(st) == ("a", "b", "c", "d"),
                                     "sort by swapping neighbours")),
        "two_jug_pour": (lambda i: (Jug((5, 3), ((4, 1), (2, 0), (0, 3))[i], (0, 0)),
                                    ["fill_a", "fill_b", "empty_a", "empty_b",
                                     "pour_ab", "pour_ba"],
                                    (lambda g: (lambda st: tuple(st) == g))(
                                        ((4, 1), (2, 0), (0, 3))[i]),
                                    "measure a volume between two jugs")),
        "queue_rotate": (lambda i: (Rotate(("a", "b", "c"),
                                           [("c", "a", "b"), ("b", "c", "a"), ("a", "c", "b")][i]),
                                    ["rot_l", "rot_r", "drop"],
                                    lambda st: tuple(st) == ("a", "b", "c"),
                                    "rotate a queue and drop its head")),
        "bit_register": (lambda i: (Register(4, (10, 5, 12)[i], (0, 3, 6)[i]),
                                    [f"xor_{j}" for j in range(4)] + ["shift"],
                                    (lambda t: (lambda st: st == t))(((10, 5, 12)[i])),
                                    "xor individual bits and shift left")),
        "string_affix": (lambda i: (Accum("xyz", ["x", "xy", "xy"][i]),
                                    [f"put_{c}" for c in "xyz"],
                                    lambda st: st == "xyz",
                                    "append letters to a different word")),
    }


# --------------------------------------------------------------------------- #
# Arm running
# --------------------------------------------------------------------------- #
def _store(transfer) -> None:
    transfer.STATE_PATH = os.path.join(tempfile.mkdtemp(prefix="brain_ckc_"), "episodes.json")


def _solve(transfer, env, actions, is_goal, goal_key, seed=0):
    result = transfer.drive(env, actions, is_goal=is_goal, goal_key=goal_key,
                            budget=200, seed=seed, max_depth=12, use_transfer=True)
    return {
        "pass": result.get("pass") is True,
        "status": result.get("status"),
        "authority": result.get("authority"),
        "trials": result.get("trials_spent"),
        "act_calls": (result.get("interactions") or {}).get("act_calls"),
    }


def run(order=None, json_out=None):
    from canonical.runtime import transfer_learning_v1 as transfer

    kinds = _kinds()
    order = order or list(kinds)
    rows = []
    # The GROWN store lives across kinds; the COLD arm gets a brand new store each time so it
    # can never benefit from the previous iteration.
    grown_path = os.path.join(tempfile.mkdtemp(prefix="brain_ckc_grown_"), "episodes.json")

    for index, name in enumerate(order):
        make = kinds[name]
        env, actions, is_goal, description = make(1)

        # COLD: empty store, fresh every time.
        _store(transfer)
        cold = _solve(transfer, env, actions, is_goal, name)

        # GROWN: the store that has already solved every EARLIER KIND and nothing else.
        #
        # A first version of this file also solved a same-kind sibling here, and it reported
        # "COMPOUNDING: YES" with 261 acts saved. That measurement was worthless: the sibling
        # gave the grown arm same-kind experience, so it measured the per-kind transfer already
        # known to work (8/15, P1) and labelled it compounding. The confound was in the design,
        # not the data. Here the arm meets THIS KIND FOR THE FIRST TIME, exactly as the cold arm
        # does; the only difference is that it has met other kinds.
        transfer.STATE_PATH = grown_path
        grown = _solve(transfer, env, actions, is_goal, name)

        rows.append({
            "index": index,
            "kind": name,
            "description": description,
            "cold": cold,
            "grown": grown,
            "kinds_before": index,
            "acts_saved": (cold["act_calls"] or 0) - (grown["act_calls"] or 0),
            "trials_saved": (cold["trials"] or 0) - (grown["trials"] or 0),
        })
        print(f"[{index + 1}/{len(order)}] {name:18} "
              f"cold acts={cold['act_calls']!s:>6} trials={cold['trials']!s:>4} | "
              f"grown acts={grown['act_calls']!s:>6} trials={grown['trials']!s:>4} | "
              f"saved={rows[-1]['acts_saved']:>5}", flush=True)

    total_cold = sum(r["cold"]["act_calls"] or 0 for r in rows)
    total_grown = sum(r["grown"]["act_calls"] or 0 for r in rows)
    improved = [r for r in rows if r["acts_saved"] > 0]
    worsened = [r for r in rows if r["acts_saved"] < 0]

    # THE COMPOUNDING QUESTION, stated as a number: does the saving grow with the number of
    # kinds already met? A creature that learns-to-learn shows a rising trend; a skill cache
    # shows noise around zero.
    late = rows[len(rows) // 2:]
    trend = {
        "early_mean_acts_saved": round(sum(r["acts_saved"] for r in rows[:len(rows) // 2])
                                       / max(1, len(rows[:len(rows) // 2])), 1),
        "late_mean_acts_saved": round(sum(r["acts_saved"] for r in late) / max(1, len(late)), 1),
    }

    doc = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "order": order,
        "rows": rows,
        "summary": {
            "kinds": len(rows),
            "total_cold_acts": total_cold,
            "total_grown_acts": total_grown,
            "kinds_improved_by_more_kinds": len(improved),
            "kinds_worsened_by_more_kinds": len(worsened),
            "kinds_unchanged": len(rows) - len(improved) - len(worsened),
            "net_act_saving": total_cold - total_grown,
            **trend,
        },
        "compounding": ("YES" if len(improved) > len(worsened) and trend["late_mean_acts_saved"]
                        > trend["early_mean_acts_saved"] else
                        "NO -- meeting more kinds does not make the next kind cheaper"),
        "cannot_see": ["GUI environments", "pixels", "unbounded action sets",
                       "any state that is not a small hashable value"],
    }
    if json_out:
        Path(json_out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print(f"\nwrote {json_out}")
    s = doc["summary"]
    print("\n" + "=" * 78)
    print(f"kinds={s['kinds']}  cold_acts={s['total_cold_acts']}  grown_acts={s['total_grown_acts']}  "
          f"net_saving={s['net_act_saving']}")
    print(f"improved={s['kinds_improved_by_more_kinds']}  worsened={s['kinds_worsened_by_more_kinds']}  "
          f"unchanged={s['kinds_unchanged']}")
    print(f"trend: early={s['early_mean_acts_saved']} late={s['late_mean_acts_saved']}")
    print(f"COMPOUNDING ACROSS KINDS: {doc['compounding']}")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json")
    args = ap.parse_args()
    run(json_out=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
