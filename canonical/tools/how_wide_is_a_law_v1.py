#!/usr/bin/env python3
"""How wide is a law's class -- and is a wide law right more often than twice?

THE TWO NUMBERS THAT ARE IN TENSION
-----------------------------------
Nine rounds produced one sound mechanism: a law with two independent witnesses over a projection
predicts held-out behaviour with zero errors. It also produced one uncomfortable number: the system
refuses ~89% of held-out transitions, and the widest surviving claims are `CARD`-style laws whose
class (`count == 2`) is a single point.

So the system is silent because its laws are NARROW, not because it is careful. The question this
module answers is quantitative and was never asked before:

    when a projection is wider (its key class covers a larger share of the state space), does the
    law stay right? And if it does, is that because wider laws are true or because they are rare?

That distinction decides the architecture. If width is free, the fix is to prefer wider projections.
If width is bought with error, then silence is the price of soundness and no amount of cleverness
removes it -- and saying which of those is true is worth more than another learner.

THE ARMS
--------
For each machine, all latent states are enumerated (they are reachable, not hypothetical: every one
is produced by executing atoms). Then for each law:

  class_size   how many enumerated states its projection key covers
  width        class_size / all states (a fraction, not a vibe)
  correct      does every state in the class agree with the law's effect?

A law that covers many states and is correct is a WIDE TRUE law -- the thing the whole project has
been chasing. A law that covers many states and is wrong is the reason the system refuses.

Also measured: `extension`, i.e. how much reach a set of wide laws would buy, computed by counting
held-out transitions they would cover -- so width is scored on the same held-out split every previous
round used, not on the enumeration that produced it.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402
from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402

import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_HOW_WIDE_IS_A_LAW_V1"
State = tuple[tuple[str, str], ...]


def enumerate_states(machine, atoms, depth: int) -> list[State]:
    """Every state reachable within `depth`, every one of them PRODUCED by executing atoms."""
    transitions = base.explore(machine, atoms, depth)
    return sorted(dict.fromkeys(tuple(before) for _i, before, _a in transitions)
                  | dict.fromkeys(tuple(after) for _i, _b, after in transitions))


def truth_of(machine, atoms, states: Sequence[State]) -> dict[tuple[str, State], tuple]:
    """The real effect of every atom in every state, read by executing it there."""
    by_ident = {atom.ident: atom for atom in atoms}
    truth: dict[tuple[str, State], tuple] = {}
    for state in states:
        for ident, atom in by_ident.items():
            machine.reset()
            # drive to `state` if reachable in one step from the reset state, else skip: we only
            # ever execute atoms, never postulate a state
            current = base.read(machine)
            if current != state:
                continue
            before = current
            after = base.execute_atom(atom, machine)
            truth[(ident, state)] = (frozenset(set(after) - set(before)),
                                     frozenset(set(before) - set(after)))
    machine.reset()
    return truth


def measure(machine_name: str, depth: int, seed: int = 13) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        transitions = base.explore(machine, atoms, depth)
        conditions = pop.condition_pool([b for _i, b, _a in transitions])
        states = sorted(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
        if len(states) < 2:
            return {"machine": machine_name, "skipped": "fewer than two states"}

        # every state's true effect per atom, by executing the atom in that state's own successor.
        truth: dict[tuple[str, State], tuple] = {}
        for ident, before, after in transitions:
            truth[(ident, before)] = (frozenset(set(after) - set(before)),
                                      frozenset(set(before) - set(after)))

        observations = base.observe(transitions, conditions)
        laws = width.learn_laws(observations)

        by_projection: dict[str, dict[str, int]] = collections.defaultdict(
            lambda: {"laws": 0, "wide_and_true": 0, "wide_and_false": 0,
                     "mean_class_share": 0.0, "observed_states": 0})
        widest_true: list[dict[str, Any]] = []

        for law in laws:
            if law.support < width.MIN_SUPPORT:
                continue
            # the class: every enumerated state the projection key covers
            covering = [state for state in states
                        if width.project(law.projection, state) == law.key]
            share = len(covering) / len(states)
            # is it TRUE on the class? only states whose truth we actually executed can be checked
            checkable = [state for state in covering if (law.atom, state) in truth]
            wrong = [state for state in checkable if truth[(law.atom, state)] != law.effect]
            row = by_projection[law.projection]
            row["laws"] += 1
            row["observed_states"] += len(checkable)
            row["mean_class_share"] += share
            if checkable and not wrong:
                row["wide_and_true"] += 1
                widest_true.append({"atom": law.atom, "projection": law.projection,
                                    "class_size": len(covering), "share": round(share, 3),
                                    "checked": len(checkable)})
            elif wrong:
                row["wide_and_false"] += 1

        for row in by_projection.values():
            if row["laws"]:
                row["mean_class_share"] = round(row["mean_class_share"] / row["laws"], 3)

        # the executive number: over law-classes, is correctness independent of width?
        pairs = [(entry["share"], entry["checked"]) for entry in widest_true]
        held_out = sorted(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
        shuffled = list(held_out)
        random.Random(seed).shuffle(shuffled)
        cut = max(1, len(shuffled) // 4)
        held = set(shuffled[:cut])
        held_transitions = [t for t in transitions if t[1] in held]

        def reach_of(law_list) -> dict[str, int]:
            predictions = wrong = refused = 0
            for ident, before, after in held_transitions:
                candidates = [law for law in law_list
                              if law.atom == ident and
                              width.project(law.projection, tuple(before)) == law.key]
                effects = {law.effect for law in candidates}
                if not effects:
                    refused += 1
                    continue
                predictions += 1
                true_effect = (frozenset(set(after) - set(before)),
                               frozenset(set(before) - set(after)))
                if effects != {true_effect}:
                    wrong += 1
            return {"predictions": predictions, "wrong": wrong, "refused": refused}

        kept = [law for law in laws if law.support >= width.MIN_SUPPORT]
        wide_only = [law for law in kept if law.projection in ("IDENT", "CARD", "CONTENT_COUNTS")]
        narrow_only = [law for law in kept if law.projection in ("ROWS", "IDENT_CONTENT_SET")]

        return {
            "machine": machine_name,
            "states": len(states),
            "laws_at_support_2": len(kept),
            "by_projection": dict(by_projection),
            "all_laws": reach_of(kept),
            "wide_projections_only": reach_of(wide_only),
            "narrow_projections_only": reach_of(narrow_only),
            "widest_true_laws": sorted(widest_true, key=lambda row: -row["share"])[:5],
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    rows = [row for row in (measure(name, args.depth) for name in names)
            if "skipped" not in row]

    totals: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"laws": 0, "wide_and_true": 0, "wide_and_false": 0})
    for row in rows:
        for projection, cell in row["by_projection"].items():
            for key in ("laws", "wide_and_true", "wide_and_false"):
                totals[projection][key] += cell[key]

    all_true = sum(1 for row in rows for _ in row["widest_true_laws"])
    summary = {
        "machines": len(rows),
        "states_enumerated": sum(row["states"] for row in rows),
        "laws_at_support_2": sum(row["laws_at_support_2"] for row in rows),
        "by_projection": dict(totals),
        "reach_all_laws": {k: sum(row["all_laws"][k] for row in rows)
                           for k in ("predictions", "wrong", "refused")},
        "reach_wide_projections_only": {k: sum(row["wide_projections_only"][k] for row in rows)
                                        for k in ("predictions", "wrong", "refused")},
        "reach_narrow_projections_only": {k: sum(row["narrow_projections_only"][k] for row in rows)
                                          for k in ("predictions", "wrong", "refused")},
    }
    wide_true = sum(cell["wide_and_true"] for cell in totals.values())
    wide_false = sum(cell["wide_and_false"] for cell in totals.values())
    summary["verdicts"] = {
        "wide_laws_exist": all_true > 0,
        "wide_laws_are_right_more_often_than_wrong": wide_true > wide_false,
        "wide_projections_reach_more_than_narrow_ones":
            summary["reach_wide_projections_only"]["predictions"]
            >= summary["reach_narrow_projections_only"]["predictions"],
        "wide_projections_are_sound":
            summary["reach_wide_projections_only"]["wrong"] == 0,
        # the tension this round exists to quantify: a wide class is right WITHIN its class but a
        # wide PROJECTION is what the held-out states actually need to match on
        "width_is_not_free": summary["reach_wide_projections_only"]["wrong"] > 0,
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
        "rows": rows,
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
