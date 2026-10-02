"""Derive terminal-wave execution authority from current immutable evidence.

No writable authority flag is trusted as an input.  Authority is a deterministic
consequence of:
- the canonical noncircular four-portfolio prequalification reducer,
- the current 12/12 content-addressed route executor state,
- the current frozen V2 execution graph,
- an independent public-runner receipt for the exact atomic launcher bytes.

This module never constructs a beacon and never executes terminal cases.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.atomic_route_specific_terminal_launch_v1 import (
    build_prelaunch_commitment,
)
from canonical.runtime.terminal_prequalification_reducer import evaluate as evaluate_prequalification

SCHEMA = "PROJECT_BRAIN_ATOMIC_TERMINAL_EXECUTION_AUTHORITY_DERIVER_V1"
LAUNCH_RECEIPT = Path(
    "canonical/verification/ATOMIC_ROUTE_SPECIFIC_TERMINAL_LAUNCH_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
)
LAUNCHER = "canonical/runtime/atomic_route_specific_terminal_launch_v1.py"
LAUNCHER_TESTS = "canonical/tests/test_atomic_route_specific_terminal_launch_v1.py"
PLAN = "canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load(root: Path, rel: Path | str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(rel))
    return value


def validate_launcher_receipt(root: Path = Path(".")) -> dict[str, Any]:
    errors: list[str] = []
    try:
        receipt = _load(root, LAUNCH_RECEIPT)
    except Exception as exc:
        return {
            "pass": False,
            "errors": ["LAUNCH_RECEIPT_READ:" + type(exc).__name__],
        }

    if not str(receipt.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("LAUNCH_RECEIPT_NOT_INDEPENDENT_PASS")
    public = receipt.get("public_verifier")
    if not isinstance(public, Mapping) or public.get("conclusion") != "success":
        errors.append("LAUNCH_PUBLIC_WORKFLOW_NOT_SUCCESS")
    if receipt.get("terminal_results_observed") != 0:
        errors.append("LAUNCH_RECEIPT_TERMINAL_RESULTS_NONZERO")
    if receipt.get("fresh_terminal_evidence_consumed") != 0:
        errors.append("LAUNCH_RECEIPT_FRESH_EVIDENCE_NONZERO")

    exact = receipt.get("exact_brain_blobs")
    if not isinstance(exact, Mapping):
        errors.append("LAUNCH_RECEIPT_EXACT_BLOBS_MISSING")
        exact = {}

    for rel in (LAUNCHER, LAUNCHER_TESTS, PLAN):
        expected = exact.get(rel)
        path = root / rel
        if not isinstance(expected, str) or not expected:
            errors.append("LAUNCH_RECEIPT_BLOB_PIN_MISSING:" + rel)
        elif not path.is_file():
            errors.append("LAUNCH_RECEIPT_FILE_MISSING:" + rel)
        elif _git_blob_sha(path) != expected:
            errors.append("LAUNCH_RECEIPT_BLOB_DRIFT:" + rel)

    return {
        "pass": not errors,
        "errors": sorted(set(errors)),
        "receipt": str(LAUNCH_RECEIPT),
        "public_verifier": public if isinstance(public, Mapping) else None,
    }


def evaluate(root: Path = Path(".")) -> dict[str, Any]:
    errors: list[str] = []

    try:
        prequal = evaluate_prequalification(root)
    except Exception as exc:
        prequal = {"pass": False, "failed_predicates": ["EXCEPTION:" + type(exc).__name__]}
    if prequal.get("pass") is not True or prequal.get("execution_authority") is not True:
        errors.append("NONCIRCULAR_PREQUALIFICATION_NOT_PASS")

    try:
        launch = build_prelaunch_commitment(root)
    except Exception as exc:
        launch = {"pass": False, "errors": ["EXCEPTION:" + type(exc).__name__]}
    if launch.get("pass") is not True:
        errors.append("ATOMIC_PRELAUNCH_COMMITMENT_NOT_PASS")
    if launch.get("executor_state", {}).get("derived_bound_executor_count") != 12:
        errors.append("DERIVED_EXECUTOR_COUNT_NOT_12")
    if launch.get("terminal_case_generation_performed") is not False:
        errors.append("PRELAUNCH_GENERATED_TERMINAL_CASES")

    receipt = validate_launcher_receipt(root)
    if receipt.get("pass") is not True:
        errors.append("ATOMIC_LAUNCHER_INDEPENDENT_RECEIPT_NOT_CURRENT")

    errors = sorted(set(errors))
    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "AUTHORIZED__ATOMIC_V2_ROUTE_SPECIFIC_T0_T1_T2_T3_TERMINAL_WAVE__ZERO_TERMINAL_RESULTS"
            if passed
            else "FAIL_CLOSED"
        ),
        "pass": passed,
        "execution_authority": passed,
        "authorization": (
            "ATOMIC_V2_ROUTE_SPECIFIC_T0_T1_T2_T3_TERMINAL_WAVE" if passed else "NONE"
        ),
        "candidate_package_commitment": (
            launch.get("candidate_package_commitment") if passed else None
        ),
        "derived_bound_executor_count": launch.get("executor_state", {}).get(
            "derived_bound_executor_count"
        ),
        "noncircular_prequalification": prequal,
        "atomic_prelaunch": {
            "pass": launch.get("pass") is True,
            "errors": launch.get("errors", []),
            "terminal_case_generation_performed": launch.get(
                "terminal_case_generation_performed"
            ),
        },
        "atomic_launcher_receipt": receipt,
        "failed_predicates": errors,
        "post_freeze_beacon_constructed": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "promotion_authority": False,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", nargs="?", type=Path, default=Path("."))
    args = ap.parse_args()
    out = evaluate(args.repo_root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
