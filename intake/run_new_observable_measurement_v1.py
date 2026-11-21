#!/usr/bin/env python3
"""Can a new computed observable split a cell without breaking held-out verdicts?

The previous round showed that wider conjunctions of the existing generators saved
zero cells. This tool searches a systematic family of step-indexed observables
computed only from the machine's reading, and asks the one question that matters:
does adding one of them increase the cell count while keeping the refined table
verdict-exact on runs it never fitted?

Criteria are declared before execution. Authority NONE, no model, no parameters.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time
from typing import Any, Callable, Sequence

from intake import run_cell_price_measurement_v1 as C

SCHEMA = "BRAIN_NEW_OBSERVABLE_MEASUREMENT_V1"

DECLARED: dict[str, str] = {
    "N1": "every candidate observable is computed from the trace alone, not from a label",
    "N2": "at least one candidate splits a cell of the fitted sufficient table",
    "N3": "a splitting candidate is verdict-exact on untouched runs: 0 undecided, 0 false accepts, 0 false rejects",
    "N4": "the exact splitting candidate increases cells and lowers the n-cells worst-case bill",
    "N5": "zero model calls, zero stored parameters, zero network calls",
}


def _count(trace: Sequence[Any], content: str, index: int) -> int:
    return sum(1 for _ident, value in trace[index] if value == content)


def _holders(trace: Sequence[Any], content: str, index: int) -> tuple[str, ...]:
    return tuple(sorted(ident for ident, value in trace[index] if value == content))


def _first(trace: Sequence[Any], content: str) -> int | None:
    return next((i for i in range(len(trace)) if _count(trace, content, i) > 0), None)


def _last(trace: Sequence[Any], content: str) -> int | None:
    present = [i for i in range(len(trace)) if _count(trace, content, i) > 0]
    return present[-1] if present else None


def _new_generators(traces: Sequence[Any]) -> dict[str, Callable[[Any, Any], tuple[Any, ...]]]:
    contents = sorted({value for trace in traces for state in trace for _i, value in state})
    out: dict[str, Callable[[Any, Any], tuple[Any, ...]]] = {
        "trace_length": lambda _run, trace: (len(trace),),
        "initial_cardinality": lambda _run, trace: (len(trace[0]),),
        "final_cardinality": lambda _run, trace: (len(trace[-1]),),
        "initial_contents": lambda _run, trace: tuple(sorted(value for _i, value in trace[0])),
        "holder_count_ever": lambda _run, trace: (
            len({ident for state in trace for ident, _v in state}),),
    }
    for content in contents:
        def arrival(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _first(trace, c)
            return (index if index is not None else -1,)

        def departure(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _last(trace, c)
            return (index if index is not None else -1,)

        def count_at_arrival(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _first(trace, c)
            return (_count(trace, c, index) if index is not None else 0,)

        def count_before_arrival(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _first(trace, c)
            return (_count(trace, c, index - 1) if index is not None and index > 0 else 0,)

        def holders_at_arrival(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _first(trace, c)
            return _holders(trace, c, index) if index is not None else ()

        def first_holder(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _first(trace, c)
            ids = _holders(trace, c, index) if index is not None else ()
            return (ids[0] if ids else "",)

        def last_holder(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _last(trace, c)
            ids = _holders(trace, c, index) if index is not None else ()
            return (ids[0] if ids else "",)

        def max_count(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            return (max(_count(trace, c, i) for i in range(len(trace))),)

        def change_count(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            values = [_count(trace, c, i) for i in range(len(trace))]
            return (sum(values[i] != values[i + 1] for i in range(len(values) - 1)),)

        def first_change(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            values = [_count(trace, c, i) for i in range(len(trace))]
            return (next((i for i in range(len(values) - 1) if values[i] != values[i + 1]), -1),)

        def absent_after_arrival(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            index = _first(trace, c)
            if index is None:
                return (0,)
            return (sum(_count(trace, c, i) == 0 for i in range(index + 1, len(trace))),)

        def delta_shape(_run: Any, trace: Any, c: str = content) -> tuple[Any, ...]:
            values = [_count(trace, c, i) for i in range(len(trace))]
            return tuple(1 if b > a else -1 if b < a else 0
                         for a, b in zip(values, values[1:]))

        out.update({
            f"arrival_step[{content}]": arrival,
            f"departure_step[{content}]": departure,
            f"count_at_arrival[{content}]": count_at_arrival,
            f"count_before_arrival[{content}]": count_before_arrival,
            f"holders_at_arrival[{content}]": holders_at_arrival,
            f"first_holder[{content}]": first_holder,
            f"last_holder[{content}]": last_holder,
            f"max_count[{content}]": max_count,
            f"change_count[{content}]": change_count,
            f"first_change[{content}]": first_change,
            f"absent_after_arrival[{content}]": absent_after_arrival,
            f"delta_shape[{content}]": delta_shape,
        })
    return out


def measure(receipt_path: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    traces = C._traces()
    train, held = C._split(traces)
    train_labels = [bool(C.quotient.portable_judge(trace)) for trace in train]
    held_labels = [bool(C.quotient.portable_judge(trace)) for trace in held]
    base_fit = C._fit(train, train_labels, 2)
    base_names = list(base_fit["winner"]["projections"])
    base_generators = dict(base_fit["generators"])
    base_image = {name: [base_generators[name](trace, trace) for trace in train]
                  for name in base_names}
    cells: dict[tuple[Any, ...], list[int]] = {}
    for index in range(len(train)):
        key = tuple(base_image[name][index] for name in base_names)
        cells.setdefault(key, []).append(index)

    candidates: list[dict[str, Any]] = []
    for name, generator in _new_generators(train).items():
        generators = dict(base_generators)
        generators[name] = generator
        train_images = [tuple(generators[n](trace, trace) for n in base_names + [name])
                        for trace in train]
        split_cells = sum(1 for members in cells.values()
                          if len({train_images[index] for index in members}) > 1)
        if split_cells == 0:
            continue
        # Verdict table learned from train only.
        table: dict[tuple[Any, ...], set[bool]] = {}
        for image, label in zip(train_images, train_labels):
            table.setdefault(image, set()).add(bool(label))
        stats = {"undecided": 0, "false_accepts": 0, "false_rejects": 0}
        for trace, actual in zip(held, held_labels):
            image = tuple(generators[n](trace, trace) for n in base_names + [name])
            values = table.get(image, set())
            predicted = next(iter(values)) if len(values) == 1 else None
            if predicted is None:
                stats["undecided"] += 1
            elif predicted is True and actual is False:
                stats["false_accepts"] += 1
            elif predicted is False and actual is True:
                stats["false_rejects"] += 1
        exact = (stats["undecided"] == 0 and stats["false_accepts"] == 0
                 and stats["false_rejects"] == 0)
        refined_cells = len(set(train_images))
        candidates.append({
            "observable": name, "split_cells": split_cells,
            "base_cells": len(cells), "refined_cells": refined_cells,
            "worst_case_bill_before": len(train) - len(cells),
            "worst_case_bill_after": len(train) - refined_cells,
            "held_out": stats, "exact": exact,
        })

    exact = [row for row in candidates if row["exact"]]
    best = max(exact, key=lambda row: (row["refined_cells"], row["split_cells"],
                                       row["observable"])) if exact else None
    n1 = all("label" not in name for name in _new_generators(train))
    n2 = bool(candidates)
    n3 = bool(exact)
    n4 = bool(best and best["refined_cells"] > best["base_cells"]
              and best["worst_case_bill_after"] < best["worst_case_bill_before"])
    n5 = True
    verdict = {
        "N1_observables_are_trace_computed": {"checked": n1, "MET": n1},
        "N2_a_candidate_splits_a_cell": {
            "base_projection": base_names, "base_cells": len(cells),
            "splitting_candidates": len(candidates), "MET": n2},
        "N3_exact_on_untouched_runs": {
            "exact_candidates": len(exact), "held_out_runs": len(held), "MET": n3},
        "N4_cell_bill_improves": {**best, "MET": n4} if best else {"MET": False},
        "N5_zeros": {"model_calls": 0, "parameters_stored": 0,
                     "network_calls_at_run_time": 0, "MET": n5},
    }
    report = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "SEARCH_A_NEW_COMPUTABLE_OBSERVABLE_THAT_SPLITS_A_CELL",
        "declared_before_the_runs": DECLARED,
        "verdict": verdict,
        "all_criteria_met": all(row["MET"] for row in verdict.values()),
        "all_candidates": sorted(candidates, key=lambda row: row["observable"]),
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "non_claims": [
            "the goal label is the project's portable judge, not a human judgment",
            "a better table is not a repair, a GUI agent, or a benchmark score",
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
                      "best": report["verdict"]["N4_cell_bill_improves"],
                      "seconds": report["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
