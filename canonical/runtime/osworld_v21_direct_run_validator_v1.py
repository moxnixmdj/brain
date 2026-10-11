"""Fail-closed validator for the direct matched OSWorld v2.1 Brain route."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_DIRECT_RUN_VALIDATOR_V1"
TASK_COUNT = 108
RUN_COUNT = 5
THRESHOLD = 0.818
TASK_REVISION = "0a1aadad95aa79b00b3783e717d865089ab06e26"
MANIFEST_SHA256 = "c54d428329be5ca72742a6becd49ee83cf739df5dea429bba182e1f3f21badfb"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_task_tree(task_dir: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(task_dir)
    mp = Path(manifest_path)
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "phase": "TASK_IDENTITY_PREFLIGHT",
        "pass": False,
        "expected_task_count": TASK_COUNT,
        "expected_revision": TASK_REVISION,
        "expected_manifest_sha256": MANIFEST_SHA256,
    }
    if not root.is_dir() or not mp.is_file():
        return {**out, "status": "FAIL_CLOSED", "reason": "TASK_TREE_OR_MANIFEST_MISSING"}

    manifest_sha = _sha256(mp)
    out["observed_manifest_sha256"] = manifest_sha
    if manifest_sha != MANIFEST_SHA256:
        return {**out, "status": "FAIL_CLOSED", "reason": "OFFICIAL_MANIFEST_SHA256_MISMATCH"}

    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    except Exception as exc:
        return {**out, "status": "FAIL_CLOSED", "reason": f"MANIFEST_PARSE_ERROR:{type(exc).__name__}"}

    if manifest.get("source_revision") != TASK_REVISION:
        return {**out, "status": "FAIL_CLOSED", "reason": "TASK_SOURCE_REVISION_MISMATCH"}
    if manifest.get("task_count") != TASK_COUNT:
        return {**out, "status": "FAIL_CLOSED", "reason": "TASK_COUNT_MISMATCH"}

    files = manifest.get("files")
    if not isinstance(files, Mapping):
        return {**out, "status": "FAIL_CLOSED", "reason": "MANIFEST_FILES_INVALID"}

    expected_names = [f"task_{i:03d}.py" for i in range(1, TASK_COUNT + 1)]
    if sorted(files) != expected_names:
        return {**out, "status": "FAIL_CLOSED", "reason": "MANIFEST_TASK_UNIVERSE_MISMATCH"}

    mismatches: list[dict[str, str]] = []
    for name in expected_names:
        meta = files[name]
        p = root / name
        if not p.is_file():
            mismatches.append({"file": name, "reason": "MISSING"})
            continue
        size = p.stat().st_size
        digest = _sha256(p)
        if size != int(meta.get("size", -1)) or digest != str(meta.get("sha256", "")):
            mismatches.append({"file": name, "reason": "SIZE_OR_SHA256_MISMATCH"})

    if mismatches:
        return {
            **out,
            "status": "FAIL_CLOSED",
            "reason": "TASK_BYTE_IDENTITY_MISMATCH",
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }

    return {
        **out,
        "pass": True,
        "status": "PASS__ALL_108_OFFICIAL_TASK_BYTES_MATCH",
        "verified_task_count": TASK_COUNT,
        "task_tree_identity_bound": True,
    }


def _score_value(item: Any) -> float:
    if isinstance(item, Mapping):
        item = item.get("score")
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise ValueError("score must be numeric")
    value = float(item)
    if not 0.0 <= value <= 1.0:
        raise ValueError("score outside [0,1]")
    return value


def validate_scored_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "phase": "SCORED_RECEIPT",
        "pass": False,
        "threshold": THRESHOLD,
        "required_runs": RUN_COUNT,
        "required_tasks_per_run": TASK_COUNT,
    }
    required_true = (
        "protocol_comparable",
        "subject_frozen_before_run_1",
        "official_evaluator_unmodified",
        "official_task_identity_preflight_passed",
        "reference_corpus_used_as_execution_input",
    )
    for field in required_true[:-1]:
        if receipt.get(field) is not True:
            return {**base, "status": "FAIL_CLOSED", "reason": f"REQUIRED_TRUE_MISSING:{field}"}
    if receipt.get(required_true[-1]) is not False:
        return {**base, "status": "FAIL_CLOSED", "reason": "REFERENCE_CORPUS_EXECUTION_CONTAMINATION"}
    if receipt.get("outcome_driven_subject_changes_between_runs") is not False:
        return {**base, "status": "FAIL_CLOSED", "reason": "SUBJECT_NOT_FROZEN_ACROSS_RUNS"}
    deviations = receipt.get("protocol_deviations", [])
    if not isinstance(deviations, list) or deviations:
        return {**base, "status": "FAIL_CLOSED", "reason": "PROTOCOL_DEVIATION_PRESENT"}

    runs = receipt.get("runs")
    if not isinstance(runs, list) or len(runs) != RUN_COUNT:
        return {**base, "status": "FAIL_CLOSED", "reason": "RUN_COUNT_MISMATCH"}

    run_means: list[float] = []
    try:
        for index, run in enumerate(runs, start=1):
            if not isinstance(run, Mapping):
                raise ValueError(f"run_{index}_not_object")
            scores = run.get("scores")
            if not isinstance(scores, list) or len(scores) != TASK_COUNT:
                raise ValueError(f"run_{index}_task_count_mismatch")
            values = [_score_value(x) for x in scores]
            run_means.append(fmean(values))
    except ValueError as exc:
        return {**base, "status": "FAIL_CLOSED", "reason": str(exc)}

    aggregate = fmean(run_means)
    passed = aggregate >= THRESHOLD
    return {
        **base,
        "pass": passed,
        "status": "PASS__OSWORLD_V21_PARTIAL_GE_81_8" if passed else "FAIL__OSWORLD_V21_PARTIAL_LT_81_8",
        "run_means": run_means,
        "aggregate_partial_mean": aggregate,
        "aggregate_partial_percent": aggregate * 100.0,
        "promotion_authority": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--task-dir", required=True)
    p.add_argument("--manifest", required=True)
    s = sub.add_parser("score")
    s.add_argument("--receipt", required=True)
    args = parser.parse_args()

    if args.cmd == "preflight":
        result = verify_task_tree(args.task_dir, args.manifest)
    else:
        result = validate_scored_receipt(json.loads(Path(args.receipt).read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
