#!/usr/bin/env python3
"""Does the question supply grow with exploration depth, or is ~14 a ceiling?

THE FINDING THIS TESTS
----------------------
`WHEN_TO_STOP_ASKING` measured that acquisition exhausts its questions at roughly 14 probes per machine
against a budget of 200, on all three stopping rules. A question is "(a support-1 law, a reachable state
it admits that no probe has visited)", and both halves are consumed by asking.

So the supply is bounded by `laws x unvisited states`. Depth is the parameter that sets unvisited
states, which gives a falsifiable prediction:

    H: the question supply grows with depth, and the accuracy of the acquired table does not fall as
       it does.

If the supply is flat in depth, then ~14 is a property of this machine family and the acquisition
approach is capped, permanently and recognisably, at a very small number of questions.
If it grows, then the rule for a real environment is "explore until the supply stops growing", and that
is a stopping rule about exploration rather than about accuracy -- which is the opposite of what the
last round built.

MEASURED, PER DEPTH
-------------------
  states        reachable states enumerated at this depth
  questions     probes the adaptive loop can spend before its supply runs out
  A             predictions / wrong from the walk alone
  C             predictions / wrong after acquisition
  per_100       questions per hundred enumerated states (the density of askable unknowns)
"""
from __future__ import annotations

import argparse
import json
import pathlib
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
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402

import acquire_the_second_witness_v1 as walker  # noqa: E402
import ask_instead_of_stare_v1 as oracle_module  # noqa: E402
import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_DOES_THE_SUPPLY_GROW_WITH_DEPTH_V1"
PROJECTION_ORDER = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS")


def measure(name: str, depth: int, walk_steps: int, budget: int, seed: int,
            pool: str = "walk") -> dict[str, Any]:
    """`pool` selects where the condition vocabulary comes from.

    "walk" (default, correct): only states the walk actually visited. The vocabulary must be something
        the learner could have observed. A real environment cannot be enumerated, so drawing the
        vocabulary from the full enumeration hands the learner knowledge it would not have -- that is
        the §2 forbidden shape, a parameter that warehouses world facts, smuggled in through the
        feature set rather than through the weights.
    "full": every enumerated state. Measured only to show what it changes; NOT the harness.

    Why this matters: the two pools disagree about the SIGN of the depth trend.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / name
        root.mkdir(parents=True)
        machine = room.all_machines()[name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        full = base.explore(machine, atoms, depth)
        states = sorted({tuple(before) for _i, before, _a in full}
                        | {tuple(after) for _i, _b, after in full})
        walked = walker.budgeted_walk(machine, atoms, walk_steps, seed)
        conditions = pop.condition_pool(
            [b for _i, b, _a in (walked if pool == "walk" else full)])
        seen = {before for _i, before, _a in walked}
        held = [(ident, before, after) for ident, before, after in full if before not in seen]

        observations = list(base.observe(walked, conditions))
        table_a = [law for law in width.learn_laws(observations)
                   if law.support >= width.MIN_SUPPORT]
        if held:
            held_obs = base.observe(held, conditions)
            score_a = width._score(table_a, held_obs)
        else:
            held_obs, score_a = [], {"predictions": 0, "wrong": 0, "refused": 0}

        oracle = oracle_module.make_oracle(machine, atoms)
        unknown = sorted({tuple(before) for _i, before, _a in full} - seen)
        probes = 0
        while probes < budget:
            candidates = sorted((law for law in width.learn_laws(observations)
                                 if law.support == 1 and law.projection in PROJECTION_ORDER),
                                key=lambda law: PROJECTION_ORDER.index(law.projection))
            picked = None
            for law in candidates:
                for state in unknown:
                    if law.admits(state):
                        picked = (law, state)
                        break
                if picked:
                    break
            if picked is None:
                break
            law, target = picked
            prefix = oracle_module.probe_for(target, full, idents)
            if prefix is None:
                unknown = [state for state in unknown if state != target]
                continue
            reached = oracle(prefix[0])
            after = oracle(list(prefix[0]) + [law.atom])
            probes += 1
            observations.append(sam.Observation.of(law.atom, reached, after, conditions))
            if reached in unknown:
                unknown = [state for state in unknown if state != reached]

        table_c = [law for law in width.learn_laws(observations)
                   if law.support >= width.MIN_SUPPORT]
        score_c = width._score(table_c, held_obs) if held_obs else {
            "predictions": 0, "wrong": 0, "refused": 0}

        return {
            "machine": name, "depth": depth, "pool": pool, "states": len(states),
            "transitions": len(full), "held_out": len(held),
            "questions": probes,
            "per_100_states": round(100.0 * probes / max(1, len(states)), 2),
            "arm_A": score_a, "arm_C": score_c,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depths", nargs="*", type=int, default=[2, 3, 4])
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--machines", nargs="*")
    parser.add_argument("--conditions", choices=["walk", "full"], default="walk")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    rows: list[dict[str, Any]] = []
    for depth in args.depths:
        for name in names:
            rows.append(measure(name, depth, args.walk_steps, args.budget, 13,
                                pool=args.conditions))

    by_depth: dict[int, dict[str, Any]] = {}
    for depth in args.depths:
        picked = [row for row in rows if row["depth"] == depth]
        by_depth[depth] = {
            "machines": len(picked),
            "states": sum(row["states"] for row in picked),
            "questions": sum(row["questions"] for row in picked),
            "questions_per_100_states": round(
                100.0 * sum(row["questions"] for row in picked)
                / max(1, sum(row["states"] for row in picked)), 2),
            "A_predictions": sum(row["arm_A"]["predictions"] for row in picked),
            "A_wrong": sum(row["arm_A"]["wrong"] for row in picked),
            "C_predictions": sum(row["arm_C"]["predictions"] for row in picked),
            "C_wrong": sum(row["arm_C"]["wrong"] for row in picked),
            "machines_out_of_questions": sum(1 for row in picked
                                             if row["questions"] < args.budget),
        }
        cell = by_depth[depth]
        cell["C_accuracy"] = round(cell["C_predictions"]
                                   / max(1, cell["C_predictions"] + cell["C_wrong"]), 4)

    depths_sorted = sorted(args.depths)
    grows = all(by_depth[b]["questions"] >= by_depth[a]["questions"]
                for a, b in zip(depths_sorted, depths_sorted[1:]))
    densest = max(depths_sorted, key=lambda d: by_depth[d]["questions_per_100_states"])
    summary = {
        "by_depth": {str(depth): cell for depth, cell in by_depth.items()},
        "condition_pool": args.conditions,
        "verdicts": {
            "the_supply_is_monotone_in_depth": grows,
            "the_supply_grows_by_more_than_a_third":
                by_depth[depths_sorted[-1]]["questions"]
                * 10 > by_depth[depths_sorted[0]]["questions"] * 13,
            "the_density_does_not_collapse":
                by_depth[depths_sorted[-1]]["questions_per_100_states"]
                >= 0.5 * by_depth[depths_sorted[0]]["questions_per_100_states"],
            "deeper_exploration_is_worth_more_questions":
                densest == depths_sorted[-1],
            # the practical rule a real environment needs
            "the_supply_is_finite_at_every_depth":
                all(cell["questions"] < args.budget for cell in by_depth.values()),
        },
        "budget": args.budget,
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
