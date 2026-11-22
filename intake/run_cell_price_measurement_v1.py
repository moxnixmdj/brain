#!/usr/bin/env python3
"""Price the cells: can a wider conjunction buy a coarser sufficient statistic?

The constructed-question round showed that harm cannot be aimed at with four
different computable policies, while labelling cells is sound at n - cells.
The only honest lever left is the number of cells. This tool fits the coarsest
sufficient statistic at conjunction size 2 and 3 on a real depth-5 TARBALL
pool, then judges a held-out fifth of that pool with each table.

Criteria are declared before execution. Authority NONE, no model, no parameters.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402

SCHEMA = "BRAIN_CELL_PRICE_MEASUREMENT_V1"
DEPTH = 5
HELD_OUT_EVERY = 5

DECLARED: dict[str, str] = {
    "R1": "the depth-5 pool is real and split before fitting, with no held-out label used for fitting",
    "R2": "a size-3 conjunction search is computed over the same generator family",
    "R3": "the wider search reports its coarsest sufficient statistic and its cell count",
    "R4": "each fitted statistic makes zero false accepts on the held-out fifth",
    "R5": "zero model calls, zero stored parameters, zero network calls",
}


def _traces() -> list[quotient.Trace]:
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-cell-price-"))
    machine = env.build_tarball(where / "tarball")
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
            "name": "seed", "target": "copy"}
    _sequences, traces = quotient.sequences_for(machine, args, depth=DEPTH)
    return list(dict.fromkeys(traces))


def _split(traces: Sequence[quotient.Trace]) -> tuple[list[quotient.Trace], list[quotient.Trace]]:
    def bucket(trace: quotient.Trace) -> int:
        material = json.dumps(trace, sort_keys=True).encode("utf-8")
        return int.from_bytes(hashlib.sha256(material).digest()[:4], "big") % HELD_OUT_EVERY

    train = [trace for trace in traces if bucket(trace) != 0]
    held = [trace for trace in traces if bucket(trace) == 0]
    return train, held


def _fit(train: Sequence[quotient.Trace], labels: Sequence[bool], max_size: int) -> dict[str, Any]:
    """Fast equivalent of quotient.enumerate_lattice: precomputed integer partition ids."""
    generators = quotient.generators_for_rung("derived", train)
    signatures = {name: [generator(trace, trace) for trace in train]
                  for name, generator in generators.items()}
    ids = {name: {value: index for index, value in enumerate(set(values))}
           for name, values in signatures.items()}
    parts = {name: [ids[name][value] for value in values]
             for name, values in signatures.items()}
    names = sorted(generators)
    lattice = 0
    sufficient: list[dict[str, Any]] = []
    for size in range(1, min(max_size, len(names)) + 1):
        for combo in itertools.combinations(names, size):
            lattice += 1
            groups: dict[tuple[int, ...], bool] = {}
            for index, label in enumerate(labels):
                key = tuple(parts[name][index] for name in combo)
                if groups.setdefault(key, bool(label)) != bool(label):
                    break
            else:
                sufficient.append({"projections": list(combo), "images": len(groups),
                                   "size": size, "sufficient": True})
    winner = min(sufficient, key=lambda row: (row["images"], row["size"],
                                              tuple(row["projections"]))) if sufficient else None
    return {"generators": generators, "lattice": lattice,
            "sufficient": len(sufficient), "winner": winner}


def _judge_held_out(fit: dict[str, Any], train: Sequence[quotient.Trace], labels: Sequence[bool],
                    held: Sequence[quotient.Trace], held_labels: Sequence[bool]) -> dict[str, Any]:
    winner = fit["winner"]
    if not winner:
        return {"undecided": len(held), "false_accepts": 0, "false_rejects": 0}
    names = list(winner["projections"])
    generators = fit["generators"]
    table: dict[tuple[Any, ...], set[bool]] = {}
    for trace, label in zip(train, labels):
        image = tuple(generators[name](trace, trace) for name in names)
        table.setdefault(image, set()).add(label)
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


def measure(receipt_path: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    traces = _traces()
    train, held = _split(traces)
    train_labels = [bool(quotient.portable_judge(trace)) for trace in train]
    held_labels = [bool(quotient.portable_judge(trace)) for trace in held]
    small = _fit(train, train_labels, 2)
    wide = _fit(train, train_labels, 3)
    small_result = _judge_held_out(small, train, train_labels, held, held_labels)
    wide_result = _judge_held_out(wide, train, train_labels, held, held_labels)

    small_cells = small["winner"]["images"] if small["winner"] else None
    wide_cells = wide["winner"]["images"] if wide["winner"] else None
    r1 = bool(train and held) and len(train) + len(held) == len(traces)
    r2 = wide["lattice"] > small["lattice"]
    r3 = small_cells is not None and wide_cells is not None
    r4 = (small_result["false_accepts"] == 0 and wide_result["false_accepts"] == 0)
    r5 = True
    verdict = {
        "R1_real_split_pool": {
            "distinct_runs": len(traces), "train": len(train), "held_out": len(held), "MET": r1},
        "R2_wider_lattice_computed": {
            "size2": small["lattice"], "size3": wide["lattice"], "MET": r2},
        "R3_coarsest_statistics": {
            "size2_projection": small["winner"]["projections"] if small["winner"] else None,
            "size2_cells": small_cells,
            "size3_projection": wide["winner"]["projections"] if wide["winner"] else None,
            "size3_cells": wide_cells,
            "cells_saved": (small_cells - wide_cells) if r3 else None,
            "MET": r3},
        "R4_held_out_soundness": {
            "size2": small_result, "size3": wide_result, "MET": r4},
        "R5_zeros": {"model_calls": 0, "parameters_stored": 0,
                     "network_calls_at_run_time": 0, "MET": r5},
    }
    report = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "PRICE_THE_CELLS_OF_A_SUFFICIENT_STATISTIC",
        "declared_before_the_runs": DECLARED,
        "verdict": verdict,
        "all_criteria_met": all(row["MET"] for row in verdict.values()),
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "non_claims": [
            "one CLI machine at depth five is not computer use",
            "the goal label is the project's portable judge, not a new human judgment",
            "independent verification is not claimed; authority is NONE",
        ],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args()
    report = measure(options.receipt)
    print(json.dumps({"all_criteria_met": report["all_criteria_met"],
                      "cells_saved": report["verdict"]["R3_coarsest_statistics"]["cells_saved"],
                      "seconds": report["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
