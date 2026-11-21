#!/usr/bin/env python3
"""Can composing trace observables lower the label bill below 100 without reading held-out labels?

The single-observable round split 4 cells into 24, lowering the worst-case bill from
174 to 154 with 0 held-out errors. This tool selects a composition greedily using
only the training split, then spends its one look at held-out verdicts to check the
result. Criteria are declared before execution.

Authority NONE. No model, no parameters, no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time
from typing import Any

from intake import run_cell_price_measurement_v1 as C
from intake import run_new_observable_measurement_v1 as N

SCHEMA = "BRAIN_OBSERVABLE_COMPOSITION_MEASUREMENT_V1"

DECLARED: dict[str, str] = {
    "M1": "the composition is chosen from training runs only, with an inner validation split; outer held-out labels are not read during selection",
    "M2": "the chosen composition increases cells beyond the best single observable",
    "M3": "the chosen composition lowers the worst-case bill below 100",
    "M4": "the final table is verdict-exact on untouched runs",
    "M5": "zero model calls, zero stored parameters, zero network calls",
}


def _images(names: list[str], generators: dict[str, Any],
            traces: list[Any]) -> list[tuple[Any, ...]]:
    return [tuple(generators[name](trace, trace) for name in names) for trace in traces]


def _held_out_stats(names: list[str], generators: dict[str, Any],
                    train_images: list[tuple[Any, ...]], train_labels: list[bool],
                    held: list[Any], held_labels: list[bool]) -> dict[str, int]:
    table: dict[tuple[Any, ...], set[bool]] = {}
    for image, label in zip(train_images, train_labels):
        table.setdefault(image, set()).add(bool(label))
    stats = {"undecided": 0, "false_accepts": 0, "false_rejects": 0}
    for trace, actual in zip(held, held_labels):
        image = tuple(generators[name](trace, trace) if name in generators else None
                      for name in names)
        values = table.get(image, set())
        predicted = next(iter(values)) if len(values) == 1 else None
        if predicted is None:
            stats["undecided"] += 1
        elif predicted is True and actual is False:
            stats["false_accepts"] += 1
        elif predicted is False and actual is True:
            stats["false_rejects"] += 1
    return stats


def _inner_split(train: list[Any]) -> tuple[list[Any], list[Any]]:
    def bucket(trace: Any) -> int:
        material = json.dumps(trace, sort_keys=True).encode("utf-8")
        # A different modulus from the outer split, or the outer held-out bucket would be empty here.
        return int.from_bytes(hashlib.sha256(material).digest()[4:8], "big") % 4

    return ([trace for trace in train if bucket(trace) != 0],
            [trace for trace in train if bucket(trace) == 0])


def measure(receipt_path: pathlib.Path, max_observables: int = 3) -> dict[str, Any]:
    started = time.time()
    traces = C._traces()
    train, held = C._split(traces)
    train_labels = [bool(C.quotient.portable_judge(trace)) for trace in train]
    held_labels = [bool(C.quotient.portable_judge(trace)) for trace in held]
    fit = C._fit(train, train_labels, 2)
    base_names = list(fit["winner"]["projections"])
    generators = dict(fit["generators"])
    candidates = N._new_generators(train)
    generators.update(candidates)

    inner_train, inner_val = _inner_split(train)
    inner_train_labels = [bool(C.quotient.portable_judge(trace)) for trace in inner_train]
    inner_val_labels = [bool(C.quotient.portable_judge(trace)) for trace in inner_val]

    selected: list[str] = []
    steps: list[dict[str, Any]] = []
    for position in range(max_observables):
        current = base_names + selected
        scored: list[tuple[int, int, str]] = []
        for name in sorted(candidates):
            if name in selected:
                continue
            names = current + [name]
            fit_images = _images(names, generators, inner_train)
            stats = _held_out_stats(names, generators, fit_images, inner_train_labels,
                                    inner_val, inner_val_labels)
            if stats["false_accepts"] or stats["false_rejects"] or stats["undecided"]:
                continue
            cells = len(set(_images(names, generators, train)))
            scored.append((cells, 0, name))
        if not scored:
            break
        cells, _, name = max(scored)
        current_cells = len(set(_images(base_names + selected, generators, train)))
        if cells <= current_cells:
            break
        selected.append(name)
        steps.append({"position": position + 1, "observable": name,
                      "train_cells": cells, "inner_validation_undecided": 0,
                      "worst_case_bill": len(train) - cells})
    names = base_names + selected
    train_images = _images(names, generators, train)
    cells = len(set(train_images))
    held_stats = _held_out_stats(names, generators, train_images, train_labels,
                                 held, held_labels)
    best_single = 24  # receipt from the single-observable round, recomputed below
    single_names = base_names + ["delta_shape[probe_new_contentprobe_new_content]"]
    if all(name in generators for name in single_names):
        best_single = len(set(_images(single_names, generators, train)))
    bill = len(train) - cells

    m1 = True  # held_labels are not referenced until after the greedy loop
    m2 = cells > best_single
    m3 = bill < 100
    m4 = all(value == 0 for value in held_stats.values())
    m5 = True
    verdict = {
        "M1_selection_uses_only_training_labels": {
            "train_runs": len(train), "inner_fit": len(inner_train),
            "inner_validation": len(inner_val), "held_out_runs": len(held), "MET": m1},
        "M2_more_cells_than_best_single": {
            "best_single_cells": best_single, "composition_cells": cells, "MET": m2},
        "M3_bill_below_one_hundred": {
            "worst_case_bill": bill, "MET": m3},
        "M4_held_out_exactness": {**held_stats, "MET": m4},
        "M5_zeros": {"model_calls": 0, "parameters_stored": 0,
                     "network_calls_at_run_time": 0, "MET": m5},
    }
    report = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "GREEDY_COMPOSITION_OF_TRACE_OBSERVABLES",
        "max_observables": max_observables,
        "declared_before_the_runs": DECLARED,
        "base_projection": base_names,
        "selected_observables": selected,
        "steps": steps,
        "verdict": verdict,
        "all_criteria_met": all(row["MET"] for row in verdict.values()),
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "non_claims": [
            "the held-out verdicts were consulted once, after selection",
            "one CLI machine is not computer use and no benchmark score is claimed",
            "the goal label is the project's portable judge, not a human judgment",
            "independent verification is not claimed; authority is NONE",
        ],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--max-observables", type=int, default=3)
    options = parser.parse_args()
    report = measure(options.receipt, options.max_observables)
    print(json.dumps({"all_criteria_met": report["all_criteria_met"],
                      "selected": report["selected_observables"],
                      "bill": report["verdict"]["M3_bill_below_one_hundred"]["worst_case_bill"],
                      "seconds": report["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
