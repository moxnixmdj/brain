#!/usr/bin/env python3
"""Buy reach with questions -- and price it honestly.

WHERE THE SILENCE COMES FROM, MEASURED
--------------------------------------
`HOW_WIDE_IS_A_LAW` answered a question this tree had only guessed at. Across ten machines, 81
enumerated states, 43 laws at support >= 2:

    CARD 14/14 true · CONTENT_COUNTS 10/10 · IDENT 11/11 · IDENT_CONTENT_COUNTS 8/8
    wide_and_false = 0

**Not one law was wrong about the class it claimed.** Soundness was never the problem, and neither was
width. Then a census of every atom:

    atoms with a two-witness law .........  5 of 45
    atoms with laws, ALL at support 1 .... 40 of 45
    atoms with no law at all .............  0 of 45

So the system is silent because **40 of 45 atoms have a single witness and nothing else.** The
evidence, not the reasoning, is the binding term. That is exactly what an acquisition policy is for,
and it means the earlier finding that "asking does not buy reach" was measured under a budget too small
to matter (16 laws, 40 steps).

WHAT THIS MODULE MEASURES
-------------------------
  A  learn from the walk only, keep support >= 2                     (the honest baseline)
  C  A, then BUY: for each support-1 law find a reachable state outside the walk that it admits,
     run its atom there, and ADD THE OBSERVATION TO THE EVIDENCE before re-learning
  (a falsified probe resolves a contradiction instead of discarding it: the class gets split, and
   the surviving laws are narrower and true)

Scored on held-out transitions -- states reachable by exhaustive exploration but absent from the walk,
so every held-out state is one the learner never saw and never probed.

COST IS PART OF THE RESULT
--------------------------
Every probe is an executed atom. `probes`, `confirmed`, `falsified` and `predictions bought per probe`
are all reported, because a policy that triples reach by spending a thousand queries has not solved
anything; the number that matters is predictions per question.
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

SCHEMA = "BRAIN_BUY_REACH_WITH_QUESTIONS_V1"

#: widest projections first: a law supported once over IDENT is a stronger claim than over ROWS, so it
#: is the one worth a question. Kept explicit so the ordering is inspectable.
PROJECTION_ORDER = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS")


def acquire(machine_name: str, walk_steps: int, budget: int, seed: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        observed = walker.budgeted_walk(machine, atoms, walk_steps, seed)
        conditions = pop.condition_pool([b for _i, b, _a in observed])
        full = base.explore(machine, atoms, 3)          # the whole reachable space at depth 3
        seen = {before for _i, before, _a in observed}
        held = [(ident, before, after) for ident, before, after in full if before not in seen]
        if not held:
            return {"machine": machine_name, "skipped": "the walk covered every reachable state"}
        held_obs = base.observe(held, conditions)
        truth_oracle = oracle_module.make_oracle(machine, atoms)
        unknown_states = [before for _i, before, _a in full if before not in seen]

        observations = base.observe(observed, conditions)
        arm_a = [law for law in width.learn_laws(observations)
                 if law.support >= width.MIN_SUPPORT]
        score_a = width._score(arm_a, held_obs)

        probes = confirmed = falsified = 0
        for _round in range(budget):
            candidates = sorted(
                (law for law in width.learn_laws(observations)
                 if law.support == 1 and law.projection in PROJECTION_ORDER),
                key=lambda law: PROJECTION_ORDER.index(law.projection))
            progressed = False
            for law in candidates:
                targets = [state for state in unknown_states if law.admits(state)]
                if not targets:
                    continue
                prefix = oracle_module.probe_for(targets[0], full, idents)
                if prefix is None:
                    continue
                reached = truth_oracle(prefix[0])
                if not law.admits(reached):
                    continue
                after = truth_oracle(list(prefix[0]) + [law.atom])
                probes += 1
                effect = (frozenset(set(after) - set(reached)),
                          frozenset(set(reached) - set(after)))
                # THE ANSWER IS EVIDENCE, NOT A VETO. A falsification is worth more than a rejection
                # because it splits the class the law claimed, and the split is what makes the
                # surviving laws narrow and true.
                observations = observations + [sam.Observation.of(law.atom, reached, after, conditions)]
                if effect == law.effect:
                    confirmed += 1
                else:
                    falsified += 1
                progressed = True
                break
            if not progressed:
                break

        arm_c = [law for law in width.learn_laws(observations) if law.support >= width.MIN_SUPPORT]
        score_c = width._score(arm_c, held_obs)

        return {
            "machine": machine_name,
            "walk_transitions": len(observed),
            "held_out_transitions": len(held_obs),
            "arm_A": score_a,
            "arm_C": score_c,
            "probes": probes,
            "confirmed": confirmed,
            "falsified": falsified,
            "predictions_bought_per_probe":
                round((score_c["predictions"] - score_a["predictions"]) / probes, 3)
                if probes else 0.0,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walks", nargs="*", type=int, default=[40, 120])
    parser.add_argument("--budget", type=int, default=40)
    parser.add_argument("--seeds", nargs="*", type=int, default=[13])
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    rows: list[dict[str, Any]] = []
    for walk_steps in args.walks:
        for seed in args.seeds:
            for name in names:
                row = acquire(name, walk_steps, args.budget, seed)
                row["walk_steps"] = walk_steps
                row["seed"] = seed
                rows.append(row)
    rows = [row for row in rows if "skipped" not in row]

    summary: dict[str, Any] = {"runs": len(rows)}
    for key in ("arm_A", "arm_C"):
        summary[key] = {
            "predictions": sum(row[key]["predictions"] for row in rows),
            "wrong": sum(row[key]["wrong"] for row in rows),
            "refused": sum(row[key]["refused"] for row in rows),
            "held_out_transitions": sum(row["held_out_transitions"] for row in rows),
        }
    summary["probes"] = sum(row["probes"] for row in rows)
    summary["confirmed"] = sum(row["confirmed"] for row in rows)
    summary["falsified"] = sum(row["falsified"] for row in rows)
    by_walk: dict[int, dict[str, int]] = {}
    for walk_steps in {row["walk_steps"] for row in rows}:
        picked = [row for row in rows if row["walk_steps"] == walk_steps]
        by_walk[walk_steps] = {
            "A_predictions": sum(row["arm_A"]["predictions"] for row in picked),
            "A_wrong": sum(row["arm_A"]["wrong"] for row in picked),
            "C_predictions": sum(row["arm_C"]["predictions"] for row in picked),
            "C_wrong": sum(row["arm_C"]["wrong"] for row in picked),
            "probes": sum(row["probes"] for row in picked),
        }
    summary["by_walk"] = by_walk
    bought = summary["arm_C"]["predictions"] - summary["arm_A"]["predictions"]
    summary["verdicts"] = {
        "questions_buy_reach": bought > 0,
        "reach_more_than_doubles":
            summary["arm_C"]["predictions"] > 2 * summary["arm_A"]["predictions"],
        "questions_preserve_the_error_RATE":
            summary["arm_C"]["wrong"] * max(1, summary["arm_A"]["predictions"])
            <= summary["arm_A"]["wrong"] * max(1, summary["arm_C"]["predictions"]),
        "questions_preserve_SOUNDNESS": summary["arm_C"]["wrong"] == 0,
        "questions_pay_for_themselves": bought > summary["probes"],
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
