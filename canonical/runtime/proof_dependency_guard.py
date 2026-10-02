"""Dependency-scoped proof invalidation for Project Brain.

A proof receipt is invalidated only when one of its explicitly frozen transitive
behavior-relevant dependencies changes, disappears, or was never bound. Changes
outside that dependency closure do not erase the proof.

This module never grants capability credit. It only decides whether an existing
receipt remains eligible to be considered by higher-level reducers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_PROOF_DEPENDENCY_GUARD_V1"


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": sorted(set(errors)),
        "valid_proof_ids": [],
        "invalidated_proofs": [],
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _fail(["INPUT_NOT_OBJECT"])

    current = data.get("current_blobs")
    receipts = data.get("receipts")
    changed_raw = data.get("changed_paths", [])
    if not isinstance(current, dict):
        return _fail(["CURRENT_BLOBS_NOT_OBJECT"])
    if not isinstance(receipts, list):
        return _fail(["RECEIPTS_NOT_LIST"])
    if not isinstance(changed_raw, list) or any(not isinstance(x, str) or not x for x in changed_raw):
        return _fail(["CHANGED_PATHS_INVALID"])

    current_blobs: dict[str, str] = {}
    errors: list[str] = []
    for path, sha in current.items():
        if not isinstance(path, str) or not path or not isinstance(sha, str) or not sha:
            errors.append("CURRENT_BLOB_ENTRY_INVALID")
            continue
        current_blobs[path] = sha
    if errors:
        return _fail(errors)

    changed = set(changed_raw)
    seen: set[str] = set()
    valid: list[str] = []
    invalidated: list[dict[str, Any]] = []
    unaffected_changes: dict[str, list[str]] = {}

    for i, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            errors.append(f"RECEIPT_{i}_NOT_OBJECT")
            continue
        pid = receipt.get("proof_id")
        if not isinstance(pid, str) or not pid:
            errors.append(f"RECEIPT_{i}_PROOF_ID_INVALID")
            continue
        if pid in seen:
            errors.append("DUPLICATE_PROOF_ID:" + pid)
            continue
        seen.add(pid)

        deps = receipt.get("bound_dependencies")
        closure = receipt.get("transitive_dependency_closure_frozen")
        if closure is not True:
            invalidated.append({
                "proof_id": pid,
                "reason": "DEPENDENCY_CLOSURE_NOT_FROZEN",
                "changed_dependency_paths": [],
                "missing_dependency_paths": [],
            })
            continue
        if not isinstance(deps, dict) or not deps:
            invalidated.append({
                "proof_id": pid,
                "reason": "BOUND_DEPENDENCIES_INVALID",
                "changed_dependency_paths": [],
                "missing_dependency_paths": [],
            })
            continue

        bad_entries = [
            path for path, sha in deps.items()
            if not isinstance(path, str) or not path or not isinstance(sha, str) or not sha
        ]
        if bad_entries:
            invalidated.append({
                "proof_id": pid,
                "reason": "BOUND_DEPENDENCY_ENTRY_INVALID",
                "changed_dependency_paths": [],
                "missing_dependency_paths": sorted(str(x) for x in bad_entries),
            })
            continue

        dep_paths = set(deps)
        missing = sorted(path for path in dep_paths if path not in current_blobs)
        changed_deps = sorted(
            path for path in dep_paths
            if path in current_blobs and current_blobs[path] != deps[path]
        )

        if missing or changed_deps:
            invalidated.append({
                "proof_id": pid,
                "reason": "BOUND_DEPENDENCY_CHANGED_OR_MISSING",
                "changed_dependency_paths": changed_deps,
                "missing_dependency_paths": missing,
            })
            continue

        valid.append(pid)
        unaffected_changes[pid] = sorted(changed - dep_paths)

    if errors:
        return _fail(errors)

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "pass": True,
        "execution_authority": False,
        "promotion_authority": False,
        "valid_proof_ids": sorted(valid),
        "invalidated_proofs": sorted(invalidated, key=lambda x: x["proof_id"]),
        "unaffected_changed_paths_by_valid_proof": {
            k: unaffected_changes[k] for k in sorted(unaffected_changes)
        },
        "rule": (
            "INVALIDATE_ONLY_ON_FROZEN_TRANSITIVE_BEHAVIOR_RELEVANT_DEPENDENCY_CHANGE__"
            "UNRELATED_REPOSITORY_CHANGES_DO_NOT_ERASE_PROOF__UNKNOWN_FAILS_CLOSED"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    args = ap.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    out = evaluate(data)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
