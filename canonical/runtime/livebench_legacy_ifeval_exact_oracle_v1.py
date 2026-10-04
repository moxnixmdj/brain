#!/usr/bin/env python3
"""Exact local oracle for the pinned legacy LiveBench IFEval checkers.

The checker source is vendored byte-for-byte from:
LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091

No approximation is accepted: source blobs are verified before import and any
missing dependency or checker exception is reported fail-closed.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_IFEVAL_EXACT_ORACLE_V1"

_EXPECTED_BLOBS = {
    "instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "instructions_registry.py": "903ed738398648c7cfac61d5ffa478c22f1f0891",
}


def _vendor_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "vendor" / "instruction_following_eval"


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def verify_source_lock() -> dict[str, Any]:
    root = _vendor_dir()
    observed: dict[str, str] = {}
    for name, expected in _EXPECTED_BLOBS.items():
        data = (root / name).read_bytes()
        actual = _git_blob_sha(data)
        observed[name] = actual
        if actual != expected:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "error": "VENDORED_SOURCE_BLOB_MISMATCH",
                "file": name,
                "expected": expected,
                "actual": actual,
            }
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "source_blobs": observed,
    }


def _load_registry():
    lock = verify_source_lock()
    if lock["status"] != "PASS":
        raise RuntimeError(lock)

    vendor_parent = str(_vendor_dir().parent)
    if vendor_parent not in sys.path:
        sys.path.insert(0, vendor_parent)

    try:
        from instruction_following_eval import instructions_registry
    except Exception as exc:
        raise RuntimeError(
            "PINNED_LEGACY_IFEVAL_DEPENDENCY_OR_IMPORT_FAILURE:" + repr(exc)
        ) from exc
    return instructions_registry


def exact_check(
    instruction_id: str,
    kwargs: dict[str, Any] | None,
    response: str,
    *,
    prompt: str | None = None,
) -> dict[str, Any]:
    iid = str(instruction_id)
    value = str(response)
    if not value.strip():
        return {
            "schema": SCHEMA,
            "status": "PASS",
            "instruction_id": iid,
            "follows": False,
            "reason": "STRICT_EVALUATOR_REJECTS_EMPTY_RESPONSE",
        }

    try:
        registry = _load_registry()
        cls = registry.INSTRUCTION_DICT[iid]
        checker = cls(iid)
        checker.build_description(**dict(kwargs or {}))
        args = checker.get_instruction_args()
        if args and "prompt" in args:
            if prompt is None:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED",
                    "instruction_id": iid,
                    "error": "PROMPT_REQUIRED_BY_CHECKER",
                }
            checker.build_description(prompt=prompt)
        follows = bool(checker.check_following(value))
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "instruction_id": iid,
            "error": "EXACT_CHECKER_EXECUTION_FAILED",
            "detail": repr(exc),
        }

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "instruction_id": iid,
        "follows": follows,
        "source_lock": _EXPECTED_BLOBS,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
    }


def exact_check_all(
    instruction_id_list: list[str],
    kwargs_list: list[dict[str, Any]],
    response: str,
    *,
    prompt: str | None = None,
) -> dict[str, Any]:
    if len(instruction_id_list) != len(kwargs_list):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "INSTRUCTION_KWARGS_LENGTH_MISMATCH",
        }

    results = [
        exact_check(iid, kwargs, response, prompt=prompt)
        for iid, kwargs in zip(instruction_id_list, kwargs_list)
    ]
    if any(item["status"] != "PASS" for item in results):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "AT_LEAST_ONE_EXACT_CHECK_FAILED_TO_EXECUTE",
            "results": results,
        }

    follows = [bool(item["follows"]) for item in results]
    all_follow = all(follows)
    fraction = (sum(follows) / len(follows)) if follows else 0.0
    row_score = ((1.0 if all_follow else 0.0) + fraction) / 2.0
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "follow_instruction_list": follows,
        "follow_all_instructions": all_follow,
        "row_score": row_score,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return exact_check_all(
        [str(x) for x in args.get("instruction_id_list", [])],
        [dict(x) for x in args.get("kwargs", [])],
        str(args.get("response") or ""),
        prompt=args.get("prompt"),
    )
