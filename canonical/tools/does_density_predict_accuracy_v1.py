#!/usr/bin/env python3
"""Can density alone predict how accurate an acquired table will be -- before spending a single probe?

WHY THIS MATTERS
----------------
`DOES_THE_SUPPLY_GROW_WITH_DEPTH` produced a correlation: as depth rises, questions-per-100-states falls
(66 -> 31 -> 17) and accuracy after acquisition falls (0.678 -> 0.618 -> 0.596). A correlation of three
aggregate points is not an instrument.

An instrument would be: from the enumeration ALONE -- states, transitions, laws, no probes, no held-out
labelling -- predict the accuracy an acquisition run would reach. If that holds, a real environment can
be assessed for "how much can be learned from this, and at what error" before it is ever touched.

The predictor under test is built only from things the walk already knows:
    support1_share = fraction of laws with exactly one witness   (the atom census from the earlier round)
    density        = support-1 laws per hundred enumerated states
Both are free: they need the enumeration and the walk, which the system does anyway.

HONESTY GUARD
-------------
The prediction is fitted on depths 2-3 and tested on depth 4, which it has never seen. A predictor that
needs the answer to predict the answer is not an instrument.
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

import acquire_the_second_witness_v1 as walker  # noqa: E402
import ask_instead_of_stare_v1 as oracle_module  # noqa: E402
import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_DENSITY_PREDICTS_ACCURACY_V1"
PROJECTION_ORDER = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS")


def features(name: str, depth: int, walk_steps: int, budget: int, seed: int,
             pool: str = "walk", run_acquisition: bool = True) -> dict[str, Any]:
    """`pool` selects which states the condition vocabulary is drawn from.

    "walk" = the established harness (every earlier receipt uses this).
    "full" = the whole depth enumeration. Widening the pool is the obvious-looking improvement and it
    CHANGED THE ANSWER: on GIT at walk 120, pool="walk" gives 24 predictions / 0 wrong, pool="full"
    gives 7 predictions / 6 wrong. Both must be measurable or the difference is a mystery rather than a
    result.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / name
        root.mkdir(parents=True)
        machine = room.all_machines()[name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        full = base.explore(machine, atoms, depth)
        states = {before for _i, before, _a in full} | {after for _i, _b, after in full}
        walked = walker.budgeted_walk(machine, atoms, walk_steps, seed)
        conditions = pop.condition_pool(
            [b for _i, b, _a in (walked if pool == "walk" else full)])
        seen = {before for _i, before, _a in walked}
        held = [(ident, before, after) for ident, before, after in full if before not in seen]

        observations = list(base.observe(walked, conditions))
        laws = width.learn_laws(observations)
        support1 = [law for law in laws if law.support == 1]
        table_a = [law for law in laws if law.support >= width.MIN_SUPPORT]
        held_obs = base.observe(held, conditions) if held else []
        score_a = width._score(table_a, held_obs) if held_obs else {
            "predictions": 0, "wrong": 0, "refused": 0}

        free = {
            "states": len(states),
            "transitions": len(full),
            "held_out": len(held),
            "laws": len(laws),
            "support1_laws": len(support1),
            "support1_share": round(len(support1) / max(1, len(laws)), 4),
            "density": round(100.0 * len(support1) / max(1, len(states)), 3),
            "A_predictions": score_a["predictions"],
            "A_wrong": score_a["wrong"],
            "A_accuracy": round(score_a["predictions"]
                                / max(1, score_a["predictions"] + score_a["wrong"]), 4),
        }

        free["condition_pool_size"] = len(conditions)
        result = {"machine": name, "depth": depth, "pool": pool, **free, "questions": 0,
                  "C_accuracy": None}
        if not run_acquisition:
            return result

        from canonical.swe_kernel import safe_action_model_v1 as sam
        oracle = oracle_module.make_oracle(machine, atoms)
        unknown = sorted({before for _i, before, _a in full} - seen)
        opened = list(observations)
        probes = 0
        while probes < budget:
            candidates = sorted((law for law in width.learn_laws(opened)
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
            opened.append(sam.Observation.of(law.atom, reached, after, conditions))
            if reached in unknown:
                unknown = [state for state in unknown if state != reached]

        table_c = [law for law in width.learn_laws(opened)
                   if law.support >= width.MIN_SUPPORT]
        score_c = width._score(table_c, held_obs) if held_obs else {
            "predictions": 0, "wrong": 0, "refused": 0}
        result["questions"] = probes
        result["C_predictions"] = score_c["predictions"]
        result["C_wrong"] = score_c["wrong"]
        result["C_accuracy"] = round(score_c["predictions"]
                                     / max(1, score_c["predictions"] + score_c["wrong"]), 4)
        return result


def fit(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Least squares on one feature. No library, no hyperparameter."""
    if len(points) < 2:
        return 0.0, 0.0
    mx = sum(x for x, _ in points) / len(points)
    my = sum(y for _, y in points) / len(points)
    sxx = sum((x - mx) ** 2 for x, _ in points)
    if sxx == 0:
        return 0.0, my
    slope = sum((x - mx) * (y - my) for x, y in points) / sxx
    return slope, my - slope * mx


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depths", nargs="*", type=int, default=[2, 3, 4])
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--conditions", choices=["walk", "full"], default="walk")
    args = parser.parse_args(argv)

    started = time.time()
    names = sorted(room.all_machines())
    rows: list[dict[str, Any]] = []
    for name in names:
        for depth in args.depths:
            rows.append(features(name, depth, args.walk_steps, args.budget, 13,
                                 pool=args.conditions))

    train = [row for row in rows if row["depth"] < max(args.depths) and row["C_accuracy"] is not None]
    test = [row for row in rows if row["depth"] == max(args.depths) and row["C_accuracy"] is not None]

    def evaluate(feature: str) -> dict[str, Any]:
        slope, intercept = fit([(row[feature], row["C_accuracy"]) for row in train])
        errors = [abs(slope * row[feature] + intercept - row["C_accuracy"]) for row in test]
        return {
            "feature": feature, "slope": round(slope, 6), "intercept": round(intercept, 4),
            "train_n": len(train), "test_n": len(test),
            "test_mean_abs_error": round(sum(errors) / max(1, len(errors)), 4),
            "test_max_abs_error": round(max(errors) if errors else 0.0, 4),
        }

    predictions = {feature: evaluate(feature)
                   for feature in ("density", "support1_share", "A_accuracy")}
    # density is only discriminating if it beats the trivial baseline: predict the training mean
    mean_train = sum(row["C_accuracy"] for row in train) / max(1, len(train))
    baseline_errors = [abs(mean_train - row["C_accuracy"]) for row in test]
    baseline = {
        "feature": "always_predict_training_mean", "value": round(mean_train, 4),
        "test_mean_abs_error": round(sum(baseline_errors) / max(1, len(baseline_errors)), 4),
        "test_max_abs_error": round(max(baseline_errors) if baseline_errors else 0.0, 4),
    }

    best = min(predictions.values(), key=lambda cell: cell["test_mean_abs_error"])
    summary = {
        "by_depth": {str(depth): {
            "machines": sum(1 for row in rows if row["depth"] == depth),
            "questions": sum(row["questions"] for row in rows if row["depth"] == depth),
            "mean_density": round(sum(row["density"] for row in rows if row["depth"] == depth)
                                  / max(1, sum(1 for row in rows if row["depth"] == depth)), 3),
            # POOLED, not mean-of-ratios: a machine that predicts nothing at all would otherwise count
            # as an undefined ratio or as 0.0 and drag a mean without contributing a transition.
            "C_predictions": sum(row.get("C_predictions", 0) for row in rows
                                 if row["depth"] == depth),
            "C_wrong": sum(row.get("C_wrong", 0) for row in rows if row["depth"] == depth),
            "pooled_C_accuracy": round(
                sum(row.get("C_predictions", 0) for row in rows if row["depth"] == depth)
                / max(1, sum(row.get("C_predictions", 0) for row in rows if row["depth"] == depth)
                      + sum(row.get("C_wrong", 0) for row in rows if row["depth"] == depth)), 4),
            "A_predictions": sum(row["A_predictions"] for row in rows if row["depth"] == depth),
            "A_wrong": sum(row["A_wrong"] for row in rows if row["depth"] == depth),
        } for depth in args.depths},
        "predictions": predictions,
        "baseline": baseline,
        "verdicts": {
            "a_free_feature_predicts_accuracy": best["test_mean_abs_error"] < 0.10,
            "density_beats_the_training_mean": (
                predictions["density"]["test_mean_abs_error"]
                < baseline["test_mean_abs_error"]),
            "the_walk_accuracy_alone_is_enough": (
                predictions["A_accuracy"]["test_mean_abs_error"] < 0.10),
            "density_is_the_weakest_free_feature": (
                predictions["density"]["test_mean_abs_error"]
                >= max(predictions["support1_share"]["test_mean_abs_error"],
                       predictions["A_accuracy"]["test_mean_abs_error"])),
        },
        "protocol": "fit on depths below the deepest, test on the deepest, never seen during fitting",
        "condition_pool": args.conditions,
        "note_on_features": {
            "density": "support-1 laws per hundred enumerated states -- free, needs no probes",
            "support1_share": "fraction of learned laws with a single witness -- free",
            "A_accuracy": "accuracy of the walk table BEFORE any probe -- free, but nearly the answer,"
                          " so it is a ceiling on what a predictor can do, not a discovery",
        },
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
