#!/usr/bin/env python3
"""Audit visible-only recovery of legacy IFEval combination:repeat_prompt.

This audit is deliberately scoped to the exact public Google IFEval corpus blob.
It reads no LiveBench terminal prompt, terminal kwargs, response, or question ID.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from canonical.runtime.livebench_hidden_parameter_prompt_recovery_v1 import (
    recover_legacy_repeat_prompt,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_REPEAT_PROMPT_PUBLIC_RECOVERY_AUDIT_V1"
PUBLIC_DATASET_BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"
TARGET = "combination:repeat_prompt"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def norm(value: str) -> str:
    return str(value or "").strip().lower()


def audit(path: Path) -> dict:
    raw = path.read_bytes()
    assert git_blob_sha(raw) == PUBLIC_DATASET_BLOB, "PUBLIC_DATASET_BLOB_MISMATCH"
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert len(rows) == 541, len(rows)

    checked = 0
    failures = []
    for row in rows:
        ids = row["instruction_id_list"]
        for index, iid in enumerate(ids):
            if iid != TARGET:
                continue
            checked += 1
            expected = row["kwargs"][index]["prompt_to_repeat"]
            recovered = recover_legacy_repeat_prompt(row["prompt"])["prompt_to_repeat"]
            if norm(recovered) != norm(expected):
                failures.append({
                    "public_key": row.get("key"),
                    "expected": expected,
                    "recovered": recovered,
                })

    assert checked == 41, checked
    status = "PASS" if not failures else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "public_source": {
            "repository": "google-research/google-research",
            "path": "instruction_following_eval/data/input_data.jsonl",
            "git_blob_sha": PUBLIC_DATASET_BLOB,
            "row_count": len(rows),
        },
        "target_instruction_id": TARGET,
        "target_public_instances": checked,
        "exact_case_insensitive_recoveries": checked - len(failures),
        "failures": failures,
        "deduction": (
            "THE_ONLY_NONRENDERED_LEGACY_REPEAT_PROMPT_ARGUMENT_IS_RECOVERABLE_"
            "FROM_VISIBLE_PROMPT_TEXT_ON_ALL_41_EXACT_PUBLIC_GOOGLE_IFEVAL_INSTANCES"
        ),
        "hard_nonclaims": [
            "PUBLIC_CLASSIC_IFEVAL_ONLY",
            "NO_FROZEN_TERMINAL_PROMPTS_READ",
            "NO_TERMINAL_DISTRIBUTION_IDENTITY_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ifeval-jsonl", required=True)
    ap.add_argument("--output")
    ns = ap.parse_args()
    result = audit(Path(ns.ifeval_jsonl))
    if ns.output:
        Path(ns.output).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
