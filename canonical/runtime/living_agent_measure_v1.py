#!/usr/bin/env python3
"""Measure the living core: learn each family from one demonstration, then
score exact behaviour on held-out instances from an independent stream.

This is a measurement, not a verification receipt and not a capability claim.
The authority is ``tests/test_living_agent_v1.py``; this script exists so a
human can watch the same numbers appear in a few seconds.

    python3 -m canonical.runtime.living_agent_measure_v1
    python3 -m canonical.runtime.living_agent_measure_v1 --json
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.runtime import living_agent_benchmark_v1 as benchmark
from canonical.runtime.living_core_v1 import apply_program, induce, program_to_json

SCHEMA = "PROJECT_BRAIN_LIVING_AGENT_MEASUREMENT_V1"


def measure(
    *,
    seed: int = 7,
    holdout_seed: int = 99,
    cases: int = 20,
    max_probes: int = 24,
    validation_cases: int = 6,
) -> dict[str, Any]:
    rows = []
    for name in benchmark.FAMILIES:
        oracle = benchmark.guarded_oracle(name)
        demo = benchmark.covering_instance(name, random.Random(seed))
        expected = oracle(demo)
        started = time.perf_counter()
        result = induce(
            oracle,
            [(demo, expected)],
            seed=seed,
            max_probes=max_probes,
            validation_cases=validation_cases,
        )
        seconds = time.perf_counter() - started
        passed = 0
        failures = []
        holdout = random.Random(holdout_seed)
        for _ in range(cases):
            table = benchmark.generate_instance(name, holdout)
            want = oracle(table)
            if result.success and result.program is not None:
                try:
                    got = apply_program(result.program, table)
                except Exception:  # a crash on unseen input is a failure, never a skip
                    got = None
                if got is not None and got.columns == want.columns and got.rows == want.rows:
                    passed += 1
                    continue
            failures.append({"input": table.to_csv(), "expected": want.to_csv()})
        rows.append(
            {
                "family": name,
                "success": bool(result.success),
                "failure_reason": result.failure_reason,
                "heldout_passed": passed,
                "heldout_cases": cases,
                "probes": result.probes,
                "validation_cases": result.validation_cases,
                "seconds": round(seconds, 4),
                "program": program_to_json(result.program) if result.program else None,
                "first_failure": failures[0] if failures else None,
            }
        )
    seconds = [row["seconds"] for row in rows]
    total_passed = sum(row["heldout_passed"] for row in rows)
    total_cases = sum(row["heldout_cases"] for row in rows)
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "kind": "MEASUREMENT_NOT_RECEIPT",
        "seed": seed,
        "holdout_seed": holdout_seed,
        "families": rows,
        "totals": {
            "families": len(rows),
            "solved": sum(1 for row in rows if row["success"]),
            "heldout_passed": total_passed,
            "heldout_cases": total_cases,
            "median_seconds": round(statistics.median(seconds), 4),
            "max_seconds": round(max(seconds), 4),
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--holdout-seed", type=int, default=99)
    parser.add_argument("--cases", type=int, default=20)
    parser.add_argument("--max-probes", type=int, default=24)
    parser.add_argument("--validation-cases", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = measure(
        seed=args.seed,
        holdout_seed=args.holdout_seed,
        cases=args.cases,
        max_probes=args.max_probes,
        validation_cases=args.validation_cases,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    for row in report["families"]:
        print(
            f"{row['family']:14s} solved={str(row['success']):5s} "
            f"heldout={row['heldout_passed']}/{row['heldout_cases']} "
            f"probes={row['probes']:2d} t={row['seconds']:.3f}s"
        )
    totals = report["totals"]
    print(
        f"TOTAL {totals['heldout_passed']}/{totals['heldout_cases']} "
        f"families={totals['solved']}/{totals['families']} "
        f"median_t={totals['median_seconds']:.3f}s "
        f"model_dependencies={totals['model_dependency_count']} "
        f"spend=${totals['incremental_spend_usd']}"
    )
    return 0 if totals["solved"] == totals["families"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
