#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
PINNED_IFBENCH_COMMIT = "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"
PINNED_IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
OPUS55_IF_PERCENT = 65.73775


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--ifbench-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    brain_root = Path(__file__).resolve().parents[2]
    livebench_root = Path(args.livebench_root).resolve()
    ifbench_root = Path(args.ifbench_root).resolve()

    checker_path = livebench_root / "livebench/if_runner/ifbench/instructions.py"
    dataset_path = ifbench_root / "data/IFBench_test.jsonl"

    assert checker_path.exists(), checker_path
    assert dataset_path.exists(), dataset_path
    assert git_blob_sha(checker_path) == FROZEN_CHECKER_BLOB
    assert git_blob_sha(dataset_path) == PINNED_IFBENCH_BLOB

    sys.path.insert(0, str(brain_root))
    sys.path.insert(0, str(livebench_root))

    from canonical.runtime import livebench_if_single_checker_solver_v1 as solver
    from livebench.if_runner.ifbench import instructions_registry

    rows = [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]
    assert len(rows) == 300

    single = [row for row in rows if len(row["instruction_id_list"]) == 1]
    multi = [row for row in rows if len(row["instruction_id_list"]) == 2]
    assert len(single) == 256
    assert len(multi) == 44

    family = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0})
    failures = []
    passes = 0

    for row in single:
        iid = row["instruction_id_list"][0]
        family[iid]["total"] += 1

        try:
            out = solver.solve(row["prompt"])
            response = out.get("response") or ""
            if out.get("status") != "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS":
                ok = False
                reason = out.get("error") or out.get("status")
            else:
                instruction_cls = instructions_registry.INSTRUCTION_DICT[iid]
                instruction = instruction_cls(iid)
                kwargs = {
                    key: value
                    for key, value in row["kwargs"][0].items()
                    if value is not None
                }
                instruction.build_description(**kwargs)
                built = instruction.get_instruction_args()
                if built and "prompt" in built:
                    instruction.build_description(prompt=row["prompt"])
                ok = bool(response.strip()) and bool(instruction.check_following(response))
                reason = None if ok else "EXACT_FROZEN_CHECKER_FALSE"
        except Exception as exc:
            ok = False
            reason = f"{type(exc).__name__}:{exc}"

        if ok:
            passes += 1
            family[iid]["pass"] += 1
        else:
            family[iid]["fail"] += 1
            if len(failures) < 256:
                failures.append(
                    {
                        "key": row.get("key"),
                        "instruction_id": iid,
                        "reason": reason,
                    }
                )

    required_all300_passes = math.ceil(OPUS55_IF_PERCENT / 100.0 * len(rows))
    floor_percent = passes / len(rows) * 100.0

    result = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_SINGLE_CHECKER_PUBLIC_EXACT_AUDIT_V1",
        "status": "PUBLIC_EXACT_FROZEN_SCORER_AUDIT_COMPLETE",
        "bindings": {
            "livebench_commit": FROZEN_LIVEBENCH_COMMIT,
            "checker_blob": FROZEN_CHECKER_BLOB,
            "ifbench_commit": PINNED_IFBENCH_COMMIT,
            "ifbench_blob": PINNED_IFBENCH_BLOB,
            "solver_schema": solver.SCHEMA,
        },
        "population": {
            "rows": len(rows),
            "single_checker_rows": len(single),
            "two_checker_rows": len(multi),
        },
        "single_checker_exact": {
            "pass": passes,
            "fail": len(single) - passes,
            "accuracy_percent": passes / len(single) * 100.0,
        },
        "conservative_all_300_floor": {
            "assumption": "ALL_44_TWO_CHECKER_ROWS_SCORE_ZERO",
            "pass_count": passes,
            "percent": floor_percent,
            "opus55_percent": OPUS55_IF_PERCENT,
            "required_pass_count": required_all300_passes,
            "clears_opus55_without_any_two_checker_credit": passes >= required_all300_passes,
        },
        "by_family": dict(sorted(family.items())),
        "failures": failures,
        "hard_nonclaims": [
            "PUBLIC_PINNED_IFBENCH_ONLY",
            "NO_TERMINAL_CASE_CONTENT",
            "NO_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
        ],
    }

    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "single_pass": passes,
        "single_fail": len(single) - passes,
        "all300_floor_percent": floor_percent,
        "required_all300_passes": required_all300_passes,
        "clears_opus55_without_multichecker": passes >= required_all300_passes,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# workflow-trigger-v1
