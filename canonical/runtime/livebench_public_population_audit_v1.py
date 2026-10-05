#!/usr/bin/env python3
from __future__ import annotations

"""Public-population soundness/coverage audit for the LiveBench Root1 successor.

This reads only the pinned public IFBench test population. It never reads frozen
terminal LiveBench cases. Every solver emission is post-validated by the exact
pinned LiveBench IFBench evaluator. Any emitted witness that fails even one
registered checker is a hard soundness failure.
"""

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from livebench.if_runner.ifbench import evaluation_lib
from canonical.runtime.livebench_public_constraint_solver_v1 import solve

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_POPULATION_AUDIT_V1"


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    emitted = 0
    full_pass = 0
    blocked = 0
    unsafe = []
    passed_instruction_occurrences = 0
    total_instruction_occurrences = 0
    full_pass_by_instruction = Counter()
    emitted_by_instruction = Counter()
    blocked_by_instruction = Counter()

    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        total_instruction_occurrences += len(ids)
        out = solve(str(row.get("prompt") or ""))
        if out.get("status") != "WITNESS_CONSTRUCTED":
            blocked += 1
            blocked_by_instruction.update(ids)
            continue

        emitted += 1
        emitted_by_instruction.update(ids)
        inp = evaluation_lib.InputExample(
            key=int(row.get("key") or 0),
            instruction_id_list=ids,
            prompt=str(row.get("prompt") or ""),
            kwargs=copy.deepcopy(list(row.get("kwargs") or [])),
        )
        scored = evaluation_lib.test_instruction_following_strict(
            inp, str(out.get("response") or "")
        )
        passed_instruction_occurrences += sum(scored.follow_instruction_list)
        if scored.follow_all_instructions:
            full_pass += 1
            full_pass_by_instruction.update(ids)
        else:
            unsafe.append({
                "key": str(row.get("key")),
                "instruction_ids": ids,
                "follow_instruction_list": scored.follow_instruction_list,
                "route": out.get("route"),
                "response": out.get("response"),
            })

    return {
        "schema": SCHEMA,
        "public_rows": len(rows),
        "public_instruction_occurrences": total_instruction_occurrences,
        "solver_emitted_rows": emitted,
        "solver_blocked_rows": blocked,
        "exact_checker_full_pass_rows": full_pass,
        "exact_checker_full_pass_percent": round(100.0 * full_pass / len(rows), 6) if rows else 0.0,
        "passed_instruction_occurrences": passed_instruction_occurrences,
        "instruction_level_pass_percent": round(
            100.0 * passed_instruction_occurrences / total_instruction_occurrences, 6
        ) if total_instruction_occurrences else 0.0,
        "unsafe_emission_count": len(unsafe),
        "unsafe_emissions": unsafe,
        "emitted_by_instruction": dict(sorted(emitted_by_instruction.items())),
        "full_pass_by_instruction": dict(sorted(full_pass_by_instruction.items())),
        "blocked_by_instruction": dict(sorted(blocked_by_instruction.items())),
        "terminal_cases_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    rows = [
        json.loads(line)
        for line in Path(ns.data).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = audit(rows)
    Path(ns.output).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    if report["public_rows"] != 300:
        raise SystemExit("PINNED_PUBLIC_POPULATION_ROW_COUNT_MISMATCH")
    if report["unsafe_emission_count"]:
        raise SystemExit(
            f"UNSOUND_SOLVER_EMISSIONS:{report['unsafe_emission_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
