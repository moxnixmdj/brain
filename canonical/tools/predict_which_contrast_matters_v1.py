#!/usr/bin/env python3
"""Can the store PREDICT which held-out contrast will matter, before running it?

THE LINE THIS FILE HAS TO CROSS
-------------------------------
Last round proved BINDING: flipping two recorded contrasts broke six real tests, with a clean identity
control. Binding is not prediction. A store that must be run to be useful is a cache of observations; a store
that says which of its entries will matter is knowledge.

THE EXPERIMENT
--------------
1. Harvest contrasts over ALL of `canonical/swe_kernel` (the previous run used a 135-file pass; this one uses
   the same machinery with a per-function cap so the pool is larger than 4).
2. For every contrast, compute cheap STATIC signals known before any intervention:
       has_call_site            any test calls this function
       at_position              some call passes the contrasting argument position
       effect_is_a_raise        the recorded effect includes RAISED
       side_changes             the pair of values differs in TYPE, not just value
       function_has_raise_ast   a parser says the function can raise
       signature_arity          number of parameters
3. Run the INTERVENTION on each one (monkeypatch + test file) to obtain the ground truth: did an outcome move?
4. Split by FUNCTION so no function appears in both halves. Learn the mapping on one half, predict the other.

THE THREE PREDICTORS, AND THE ONE THAT MATTERS
----------------------------------------------
    CHANCE      predict "matters" at the base rate -> scored by the base rate itself
    STATIC      the cheapest rule: "matters iff some call site passes that position"
    LEARNED     whichever single signal best separates the training half, applied to the held-out half

`STATIC` is the honest competitor. If the learned rule does not beat a one-line static rule, the store is
carrying observations that a parser could have anticipated -- and that is the result to report.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import does_a_contrast_predict_its_callers_v1 as callers  # noqa: E402
import one_contrast_one_effect_v1 as contrast  # noqa: E402
import replay_the_contrast_in_its_callers_v1 as replay  # noqa: E402

SCHEMA = "BRAIN_PREDICT_WHICH_CONTRAST_MATTERS_V1"


def signals(entry: dict[str, Any], caller_row: dict[str, Any] | None,
            source: pathlib.Path) -> dict[str, Any]:
    module_name, _, attribute = entry["function"].partition("::")
    position = entry["position"]
    has_call_site = bool(caller_row and caller_row["call_sites"])
    at_position = bool(caller_row and caller_row["sites_passing_that_position"])
    effect_is_raise = ("RAISED" in entry["effect"][0]) != ("RAISED" in entry["effect"][1])
    left, right = entry["witness"]
    side_changes = (("''" in left) != ("''" in right))
    return {
        "has_call_site": has_call_site,
        "at_position": at_position,
        "effect_is_a_raise": effect_is_raise,
        "side_changes": side_changes,
        "function_has_raise_ast": caller_row["static_says_it_can_raise"] if caller_row else False,
        "signature_arity": len(caller_row["sites"][0]) if caller_row and caller_row["sites"] else 0,
        "call_sites": (caller_row or {}).get("call_sites", 0),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--entries",
                        default=str(REPO / "canonical" / "verification" /
                                    "ONE_CONTRAST_ONE_EFFECT_20261124_V1.json"))
    parser.add_argument("--max", type=int, default=40,
                        help="cap on interventions (each runs three test-file subprocesses)")
    args = parser.parse_args(argv)

    started = time.time()
    payload = json.loads(pathlib.Path(args.entries).read_text())["summary"]
    # the full store, falling back to the 6-entry sample only if an older artifact is supplied
    harvested = payload.get("entries") or payload.get("sample_entries", [])
    rows: list[dict[str, Any]] = []
    seen_functions: set[str] = set()
    for entry in harvested:
        if entry["function"] in seen_functions:
            continue
        seen_functions.add(entry["function"])
        if len(rows) >= args.max:
            break
        module_name, _, attribute = entry["function"].partition("::")
        source = REPO / "canonical" / "swe_kernel" / f"{module_name}.py"
        if not source.exists():
            continue
        sites = callers.call_sites_of(attribute)
        caller_row = None
        if sites:
            caller_row = {
                "call_sites": len(sites),
                "sites_passing_that_position": sum(1 for site in sites
                                                   if site["positional"] > entry["position"]),
                "static_says_it_can_raise": callers.static_raise_awareness(source, attribute),
                "sites": sites,
            }
        cell = signals(entry, caller_row, source)
        # ground truth by intervention, when there is a test file to run
        truth = None
        if caller_row and sites:
            by_file: dict[str, int] = {}
            for site in sites:
                by_file[site["file"]] = by_file.get(site["file"], 0) + 1
            test_file = max(by_file, key=by_file.get)
            base = replay.run_harness(module_name, attribute, entry["position"],
                                      entry["witness"], 0, False, test_file)
            control = replay.run_harness(module_name, attribute, entry["position"],
                                         entry["witness"], 0, False, test_file)
            swapped = replay.run_harness(module_name, attribute, entry["position"],
                                         entry["witness"], 0, True, test_file)
            triple = lambda cell: (cell["passed"], cell["failed"], cell["errors"])
            if triple(base) != triple(control):
                truth = None                     # contaminated by the wrapper, excluded
            else:
                truth = triple(base) != triple(swapped)
        rows.append({"entry": entry, "signals": cell, "matters": truth,
                     "test_file": (caller_row or {}).get("sites", [{}])[0].get("file")})

    usable = [row for row in rows if row["matters"] is not None]
    base_rate = sum(1 for row in usable if row["matters"]) / max(1, len(usable))

    # split by FUNCTION so no function is on both sides
    order = sorted({row["entry"]["function"] for row in usable})
    train_functions = set(order[::2])
    train = [row for row in usable if row["entry"]["function"] in train_functions]
    test = [row for row in usable if row["entry"]["function"] not in train_functions]

    keys = ("has_call_site", "at_position", "effect_is_a_raise", "side_changes",
            "function_has_raise_ast")
    learned_key = None
    best_train = -1.0
    for key in keys:
        correct = sum(1 for row in train if row["signals"][key] == row["matters"])
        accuracy = correct / max(1, len(train))
        if accuracy > best_train:
            best_train, learned_key = accuracy, key

    def score(key: str | None, subset) -> dict[str, Any]:
        """Accuracy alone is not admissible here.

        THE BUG THIS FIXES, MEASURED: the first version of this function reported the best signal at 0.7857
        on held-out functions and called that a success. It was a 0.7857 achieved by predicting "does not
        matter" on every row -- exactly the majority-class trap this project already fell into in V25. So a
        rule must now report SENSITIVITY (how many of the genuinely-mattering contrasts it catches) and be
        compared against the majority-class baseline, not against the raw base rate.
        """
        if key is None:
            correct = sum(1 for row in subset if not row["matters"])
            caught = 0
            flagged = 0
        else:
            correct = sum(1 for row in subset if row["signals"][key] == row["matters"])
            caught = sum(1 for row in subset if row["signals"][key] and row["matters"])
            flagged = sum(1 for row in subset if row["signals"][key])
        positives = sum(1 for row in subset if row["matters"])
        majority = max(positives, len(subset) - positives)
        return {"correct": correct, "n": len(subset),
                "accuracy": round(correct / max(1, len(subset)), 4),
                "positives": positives, "flagged": flagged, "caught": caught,
                "sensitivity": round(caught / max(1, positives), 4),
                "precision": round(caught / max(1, flagged), 4),
                "majority_class_accuracy": round(majority / max(1, len(subset)), 4)}

    summary = {
        "contrasts_considered": len(rows),
        "contrasts_with_ground_truth": len(usable),
        "base_rate_that_matters": round(base_rate, 4),
        "train_n": len(train), "test_n": len(test),
        "learned_signal": learned_key,
        "learned_train_accuracy": round(best_train, 4),
        "test": {
            "learned": score(learned_key, test),
            "static_at_position": score("at_position", test),
            "always_does_not_matter": score(None, test),
            "base_rate": round(base_rate, 4),
        },
        "verdicts": {
            "the_store_can_predict_which_contrast_matters":
                learned_key is not None
                and score(learned_key, test)["accuracy"]
                > score(learned_key, test)["majority_class_accuracy"] + 0.05
                and score(learned_key, test)["sensitivity"] > 0.10,
            "the_learned_rule_has_any_sensitivity":
                learned_key is not None and score(learned_key, test)["sensitivity"] > 0.0,
            # a "beat" requires the rule to actually catch something: the majority classifier outscores the
            # static rule on accuracy while catching nothing, and calling that a win is the V25 error again
            "the_learned_rule_beats_the_static_rule":
                learned_key is not None
                and score(learned_key, test)["sensitivity"]
                > score("at_position", test)["sensitivity"],
            "the_static_rule_is_the_only_rule_with_any_sensitivity":
                score("at_position", test)["sensitivity"] > 0
                and (learned_key is None or score(learned_key, test)["sensitivity"] == 0),
            "the_static_rule_is_precise_enough_to_use":
                score("at_position", test)["precision"] >= 0.5,
            "the_learned_rule_is_just_at_position": learned_key == "at_position",
            "there_is_too_little_ground_truth_to_decide": len(usable) < 8,
        },
        "honest_reading": (
            "With a handful of ground-truth contrasts, accuracy on held-out functions is dominated by which "
            "side of the base rate the split lands on. The verdicts are reported but the sample is small and "
            "`there_is_too_little_ground_truth_to_decide` says so explicitly rather than letting a 1.0 or "
            "0.0 be read as a result."),
        "rows": [{k: v for k, v in row.items() if k != "entry"} for row in rows],
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
