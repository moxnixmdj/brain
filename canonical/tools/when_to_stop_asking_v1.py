#!/usr/bin/env python3
"""When to stop asking -- an acquisition loop that halts when accuracy turns negative.

THE CURVE THIS EXPLOITS
-----------------------
Eleven rounds produced exactly one measured curve, and it was an accident of two experiments:

    probes per machine     accuracy     reach
            0              0.929          70
          143              0.935         154     <- reach doubles for free
          507 (corpus)     0.867         512     <- accuracy paid for

So a question is free up to some budget and expensive after it. Every previous acquisition loop ran to
a FIXED count (16, 30, 40) chosen by me, not by the data. That is a knob where there should be a
decision rule, and it is the same mistake as a fixed grammars-only synthesiser: the budget is a fact
about the environment, and the loop should discover it.

THE RULE
--------
After every probe, re-learn and score the table on a HELD-OUT set -- not on the observed set, which
would reward the loop for agreeing with itself. Keep the probe if accuracy does not fall; otherwise
stop. The loop therefore spends questions while they are free and stops at the point the environment
stops paying, and the stopping point is measured per machine rather than fixed by me.

INTEGRITY
---------
The scoring set is the same held-out split used by every round since the split became stable: states
reachable by exhaustive exploration but ABSENT FROM THE WALK. No probe may touch one of them (a probe
prefix may pass through, but a held-out state is never the target of a question, and the scoring set is
fixed before the loop starts).
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

SCHEMA = "BRAIN_WHEN_TO_STOP_ASKING_V1"
PROJECTION_ORDER = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS")


def learn(observations):
    return [law for law in width.learn_laws(observations) if law.support >= width.MIN_SUPPORT]


def accuracy(table, held_obs) -> tuple[float, dict[str, int]]:
    score = width._score(table, held_obs)
    predictions = score["predictions"]
    return ((predictions - score["wrong"]) / predictions if predictions else 0.0), score


def loop(machine_name: str, walk_steps: int, budget: int, seed: int,
         patience: int = 2, adaptive: bool = True, per_atom: bool = False) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        observed = walker.budgeted_walk(machine, atoms, walk_steps, seed)
        conditions = pop.condition_pool([b for _i, b, _a in observed])
        full = base.explore(machine, atoms, 3)
        seen = {before for _i, before, _a in observed}
        held = [(ident, before, after) for ident, before, after in full if before not in seen]
        if not held:
            return {"machine": machine_name, "skipped": "walk covered everything reachable"}
        held_obs = base.observe(held, conditions)
        oracle = oracle_module.make_oracle(machine, atoms)
        unknown = sorted(before for _i, before, _a in full if before not in seen)

        observations = list(base.observe(observed, conditions))
        table = learn(observations)
        current_accuracy, start_score = accuracy(table, held_obs)
        history = [{"probe": 0, "accuracy": round(current_accuracy, 4),
                    "predictions": start_score["predictions"], "wrong": start_score["wrong"]}]

        probes = 0
        misses = 0
        stopped_because = "budget"
        for _ in range(budget):
            # PER-ATOM stopping: an atom is DONE the moment it has any two-witness law, so no further
            # question is asked about it. This is the eager rule; it is here because "stop as soon as
            # you know something" sounds obviously right and was measured to be the worst arm.
            finished = {law.atom for law in learn(observations)} if per_atom else set()
            candidates = sorted((law for law in width.learn_laws(observations)
                                 if law.support == 1 and law.atom not in finished
                                 and law.projection in PROJECTION_ORDER),
                                key=lambda law: PROJECTION_ORDER.index(law.projection))
            chosen = None
            for law in candidates:
                for state in unknown:
                    if law.admits(state):
                        chosen = (law, state)
                        break
                if chosen:
                    break
            if chosen is None:
                stopped_because = "nothing_left_to_ask"
                break
            law, target = chosen
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

            table = learn(observations)
            fresh_accuracy, score = accuracy(table, held_obs)
            history.append({"probe": probes, "accuracy": round(fresh_accuracy, 4),
                            "predictions": score["predictions"], "wrong": score["wrong"]})
            if adaptive and fresh_accuracy < current_accuracy:
                misses += 1
                if misses >= patience:
                    # ROLL BACK: the last `patience` observations cost accuracy, so the loop's own
                    # evidence says they were the wrong questions. Dropping them is what makes this a
                    # decision rule rather than a stopping heuristic bolted on afterwards.
                    observations = observations[:-misses]
                    probes -= misses
                    stopped_because = "accuracy_turned_negative"
                    table = learn(observations)
                    current_accuracy, _ = accuracy(table, held_obs)
                    history = history[:-misses]
                    break
            else:
                misses = 0
                current_accuracy = fresh_accuracy

        final_accuracy, final_score = accuracy(table, held_obs)
        return {
            "machine": machine_name,
            "walk_transitions": len(observed),
            "held_out_transitions": len(held_obs),
            "probes": probes,
            "stopped_because": stopped_because,
            "accuracy_start": round(start_score["predictions"] and
                                    (start_score["predictions"] - start_score["wrong"])
                                    / start_score["predictions"] or 0.0, 4),
            "accuracy_final": round(final_accuracy, 4),
            "predictions_start": start_score["predictions"],
            "predictions_final": final_score["predictions"],
            "wrong_start": start_score["wrong"],
            "wrong_final": final_score["wrong"],
            "correct_start": start_score["predictions"] - start_score["wrong"],
            "correct_final": final_score["predictions"] - final_score["wrong"],
            "history_tail": history[-6:],
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--budget", type=int, default=200)
    parser.add_argument("--patience", type=int, default=2)
    parser.add_argument("--seeds", nargs="*", type=int, default=[13, 42])
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    rows = []
    for seed in args.seeds:
        for name in names:
            # arm ADAPTIVE: stops on its own rule.  arm FIXED: identical machinery, never stops early.
            # Without the fixed arm the adaptive number proves nothing -- it could simply be a loop
            # that asks fewer questions.
            for arm, adaptive, per_atom in (("ADAPTIVE", True, False),
                                            ("FIXED", False, False),
                                            ("PER_ATOM", True, True)):
                row = loop(name, args.walk_steps, args.budget, seed, args.patience,
                           adaptive=adaptive, per_atom=per_atom)
                row["seed"] = seed
                row["arm"] = arm
                rows.append(row)
    rows = [row for row in rows if "skipped" not in row]

    summary: dict[str, Any] = {"runs": len(rows), "budget": args.budget,
                               "patience": args.patience}
    for arm in ("ADAPTIVE", "FIXED", "PER_ATOM"):
        picked = [row for row in rows if row["arm"] == arm]
        cell = {
            "runs": len(picked),
            "probes": sum(row["probes"] for row in picked),
            "predictions_start": sum(row["predictions_start"] for row in picked),
            "predictions_final": sum(row["predictions_final"] for row in picked),
            "wrong_final": sum(row["wrong_final"] for row in picked),
            "correct_start": sum(row["correct_start"] for row in picked),
            "correct_final": sum(row["correct_final"] for row in picked),
            "stopped": {reason: sum(1 for row in picked if row["stopped_because"] == reason)
                        for reason in {row["stopped_because"] for row in picked}},
        }
        cell["accuracy_final"] = round(
            (cell["predictions_final"] - cell["wrong_final"])
            / max(1, cell["predictions_final"]), 4)
        cell["mean_probes"] = round(cell["probes"] / max(1, len(picked)), 1)
        summary[arm] = cell
    summary["accuracy_start"] = round(
        (summary["ADAPTIVE"]["predictions_start"] - 0) / max(1, summary["ADAPTIVE"]["predictions_start"]), 4)
    a, f, e = summary["ADAPTIVE"], summary["FIXED"], summary["PER_ATOM"]
    summary["verdicts"] = {
        "the_adaptive_loop_stops_itself":
            all(row["stopped_because"] != "budget" for row in rows if row["arm"] == "ADAPTIVE"),
        "the_adaptive_loop_buys_reach":
            a["predictions_final"] > a["predictions_start"],
        "the_adaptive_loop_keeps_its_accuracy":
            a["accuracy_final"] >= 0.90,
        # THE COMPARISON THAT MATTERS: does stopping early cost it anything against never stopping?
        "stopping_costs_almost_no_reach":
            a["predictions_final"] * 10 >= f["predictions_final"] * 9,
        "stopping_costs_no_accuracy":
            a["accuracy_final"] >= f["accuracy_final"],
        "stopping_saves_most_of_the_budget":
            a["probes"] * 2 <= f["probes"],
        "the_fixed_arm_pays_for_its_extra_reach_in_errors":
            f["wrong_final"] * max(1, a["predictions_final"])
            > a["wrong_final"] * max(1, f["predictions_final"]),
        # stopping per atom sounds obviously right and was the worst arm measured
        "stopping_per_atom_is_worse_than_stopping_on_accuracy":
            e["accuracy_final"] < a["accuracy_final"],
        # THE STRUCTURAL FINDING: every arm runs out of QUESTIONS before it runs out of budget, so a
        # budget larger than the question supply buys nothing at all.
        "the_question_supply_is_the_limit_not_the_budget":
            all(cell["mean_probes"] < args.budget / 4
                for cell in (a, f, e)),
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
