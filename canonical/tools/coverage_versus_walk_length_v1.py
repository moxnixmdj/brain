#!/usr/bin/env python3
"""Is the 0.70 wall the walk's SIZE or the representation's REACH?

Three mechanisms have failed to move coverage past 0.70 in this project -- acquisition by questions, the
accuracy-gated stop, and the guard -- and all three shared one property: they re-read the same 120-step
walk. `walk_steps` has never been varied. This varies it and nothing else.

DESIGN, AND WHY IT IS NOT CIRCULAR
----------------------------------
The held-out set must be held out for EVERY walk length, or longer walks get an easier problem and the
curve means nothing. So the split is fixed first, by a seeded shuffle of all enumerated transitions, and
every arm is scored on the same held-out transitions, which no walk is allowed to visit.

This matters: `base.explore` enumerates depth 3, and a 600-step walk will see most of it. If held-out
were defined as "states this walk did not visit", coverage would rise simply because the denominator
shrinks. It does not shrink here -- the test set is the same size for every arm.

ARMS
----
  walk length in {40, 120, 300, 600}, identical everything else.
  Reported: predictions, wrong, accuracy, coverage, walk transitions.

WHAT EACH OUTCOME WOULD MEAN
----------------------------
  coverage rises with walk length and saturates  -> the wall is EVIDENCE, and it is a wall of walk size
  coverage flat while walk grows                  -> the wall is REPRESENTATION, and no walk fixes it
  accuracy falls as walk grows                    -> wider evidence is being over-generalised into laws
"""
from __future__ import annotations

import argparse
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

import acquire_the_second_witness_v1 as walker  # noqa: E402
import lift_the_keys_v1 as lift  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_COVERAGE_VERSUS_WALK_LENGTH_V1"
LENGTHS = (40, 120, 300, 600)
HELD_OUT_SHARE = 0.35


def fixed_split(machine_name: str, machine, atoms, seed: int) -> list[tuple[str, lift.State, lift.State]]:
    """A held-out set fixed before any walk runs, identical for every arm."""
    full = base.explore(machine, atoms, 3)
    order = [(ident, tuple(before), tuple(after)) for ident, before, after in full]
    order.sort()
    random.Random(seed).shuffle(order)
    cut = max(1, int(len(order) * HELD_OUT_SHARE))
    return order[:cut]


def arm(machine_name: str, held: list[tuple[str, lift.State, lift.State]], steps: int,
        seed: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        walked = walker.budgeted_walk(machine, atoms, steps, seed)
        # the walk may not use any held-out transition: drop it rather than let evidence leak
        held_keys = {(ident, before) for ident, before, _a in held}
        walked = [(ident, before, after) for ident, before, after in walked
                  if (ident, tuple(before)) not in held_keys]
        laws = lift.lift(walked, idents)
        result = lift.score(laws, idents, held)
        return {**result, "walk_transitions": len(walked), "laws": len(laws)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--lengths", nargs="*", type=int, default=list(LENGTHS))
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)

    started = time.time()
    names = sorted(room.all_machines())
    rows: list[dict[str, Any]] = []
    for name in names:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / name
            root.mkdir(parents=True)
            machine = room.all_machines()[name](root)
            machine.reset()
            atoms = list(machine.atoms)
            held = fixed_split(name, machine, atoms, args.seed)
            if not held:
                rows.append({"machine": name, "skipped": "nothing enumerated"})
                continue
        for steps in args.lengths:
            cell = arm(name, held, steps, args.seed)
            rows.append({"machine": name, "steps": steps, "held_out": len(held), **cell})

    live = [row for row in rows if "skipped" not in row]
    summary: dict[str, Any] = {"lengths": args.lengths, "held_out_share": HELD_OUT_SHARE,
                               "by_length": {}}
    for steps in args.lengths:
        picked = [row for row in live if row["steps"] == steps]
        predictions = sum(row["predictions"] for row in picked)
        wrong = sum(row["wrong"] for row in picked)
        refused = sum(row["refused"] for row in picked)
        summary["by_length"][str(steps)] = {
            "machines": len(picked),
            "held_out": sum(row["held_out"] for row in picked),
            "walk_transitions": sum(row["walk_transitions"] for row in picked),
            "laws": sum(row["laws"] for row in picked),
            "predictions": predictions, "wrong": wrong, "refused": refused,
            "accuracy": round(predictions / max(1, predictions + wrong), 4),
            "coverage": round(predictions / max(1, predictions + refused), 4),
        }

    cells = [summary["by_length"][str(steps)] for steps in args.lengths]
    coverage = [cell["coverage"] for cell in cells]
    accuracy = [cell["accuracy"] for cell in cells]
    gain = coverage[-1] - coverage[0]
    summary["verdicts"] = {
        "the_held_out_set_is_the_same_size_at_every_length":
            len({cell["held_out"] for cell in cells}) == 1,
        "coverage_rises_with_walk_length": gain > 0.05,
        "coverage_saturates_before_the_longest_walk":
            coverage[-1] - coverage[-2] < 0.5 * max(1e-9, coverage[1] - coverage[0]) or
            coverage[-1] - coverage[-2] < 0.03,
        "the_wall_is_evidence_not_representation": gain > 0.05,
        "accuracy_holds_as_the_walk_grows": accuracy[-1] >= accuracy[0] - 0.05,
        "more_walk_never_hurts_accuracy": all(b >= a - 0.02 for a, b in zip(accuracy, accuracy[1:])),
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
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
