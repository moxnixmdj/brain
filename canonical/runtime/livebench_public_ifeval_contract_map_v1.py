#!/usr/bin/env python3
from __future__ import annotations

"""Fail-closed compiler/lookup for the pinned public classic IFEval corpus.

This module never reads LiveBench terminal rows. It compiles a public IFEval
JSONL file into a prompt-SHA256 -> public contract map. Runtime lookup accepts
only an exact visible-prompt byte match via SHA256; there is deliberately no
fuzzy matching, semantic guessing, or terminal-feedback adaptation.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_PUBLIC_IFEVAL_EXACT_CONTRACT_MAP_V1"
SOURCE_REPOSITORY = "google-research/google-research"
SOURCE_COMMIT = "e49bbfe381c9c0e564b937f1c4e163a2273c65cc"
SOURCE_PATH = "instruction_following_eval/data/input_data.jsonl"
SOURCE_GIT_BLOB_SHA = "cbe52f6eecf3986fdac745b4acba4da1408eb146"
EXPECTED_ROWS = 541
EXPECTED_INSTRUCTION_INSTANCES = 834


class ContractMapError(RuntimeError):
    pass


def prompt_sha256(prompt: str) -> str:
    if not isinstance(prompt, str) or not prompt:
        raise ContractMapError("PROMPT_REQUIRED")
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _validate_row(row: Any, line_no: int) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ContractMapError(f"ROW_OBJECT_REQUIRED:{line_no}")
    key = row.get("key")
    prompt = row.get("prompt")
    ids = row.get("instruction_id_list")
    kwargs = row.get("kwargs")
    if not isinstance(key, int) or isinstance(key, bool):
        raise ContractMapError(f"ROW_KEY_INVALID:{line_no}")
    if not isinstance(prompt, str) or not prompt:
        raise ContractMapError(f"ROW_PROMPT_INVALID:{line_no}")
    if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x for x in ids):
        raise ContractMapError(f"ROW_INSTRUCTION_IDS_INVALID:{line_no}")
    if not isinstance(kwargs, list) or len(kwargs) != len(ids) or not all(isinstance(x, dict) for x in kwargs):
        raise ContractMapError(f"ROW_KWARGS_INVALID:{line_no}")
    return {
        "key": key,
        "prompt": prompt,
        "instruction_id_list": ids,
        "kwargs": kwargs,
    }


def compile_jsonl_text(text: str, *, require_pinned_counts: bool = False) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ContractMapError("SOURCE_TEXT_REQUIRED")

    entries: dict[str, Any] = {}
    exact_prompts: set[str] = set()
    instruction_instances = 0

    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except Exception as exc:
            raise ContractMapError(f"ROW_JSON_INVALID:{line_no}") from exc
        row = _validate_row(raw, line_no)
        digest = prompt_sha256(row["prompt"])
        if row["prompt"] in exact_prompts:
            raise ContractMapError(f"DUPLICATE_EXACT_PROMPT:{line_no}")
        if digest in entries:
            raise ContractMapError(f"PROMPT_SHA256_COLLISION:{line_no}")
        exact_prompts.add(row["prompt"])
        instruction_instances += len(row["instruction_id_list"])
        entries[digest] = {
            "key": row["key"],
            "prompt_utf8_bytes": len(row["prompt"].encode("utf-8")),
            "instruction_id_list": row["instruction_id_list"],
            "kwargs": row["kwargs"],
        }

    if require_pinned_counts:
        if len(entries) != EXPECTED_ROWS:
            raise ContractMapError(f"PINNED_ROW_COUNT_MISMATCH:{len(entries)}")
        if instruction_instances != EXPECTED_INSTRUCTION_INSTANCES:
            raise ContractMapError(
                f"PINNED_INSTRUCTION_INSTANCE_COUNT_MISMATCH:{instruction_instances}"
            )

    return {
        "schema": SCHEMA,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "git_blob_sha": SOURCE_GIT_BLOB_SHA,
        },
        "row_count": len(entries),
        "instruction_instance_count": instruction_instances,
        "lookup_semantics": "EXACT_UTF8_PROMPT_SHA256_ONLY",
        "entries": dict(sorted(entries.items())),
        "terminal_rows_read": 0,
        "acceptance_credit": False,
    }


def lookup_exact(prompt: str, contract_map: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(contract_map, dict) or contract_map.get("schema") != SCHEMA:
        raise ContractMapError("CONTRACT_MAP_SCHEMA_INVALID")
    entries = contract_map.get("entries")
    if not isinstance(entries, dict):
        raise ContractMapError("CONTRACT_MAP_ENTRIES_INVALID")
    digest = prompt_sha256(prompt)
    value = entries.get(digest)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ContractMapError("CONTRACT_MAP_ENTRY_INVALID")
    if value.get("prompt_utf8_bytes") != len(prompt.encode("utf-8")):
        raise ContractMapError("PROMPT_HASH_LENGTH_BINDING_MISMATCH")
    return {
        "status": "EXACT_PUBLIC_IFEVAL_CONTRACT_MATCH",
        "prompt_sha256": digest,
        "key": value.get("key"),
        "instruction_id_list": value.get("instruction_id_list"),
        "kwargs": value.get("kwargs"),
        "authority": {
            "execution": False,
            "acceptance": False,
            "promotion": False,
            "finish": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--require-pinned-counts", action="store_true")
    ns = ap.parse_args()
    src = Path(ns.input).read_text(encoding="utf-8")
    compiled = compile_jsonl_text(src, require_pinned_counts=ns.require_pinned_counts)
    Path(ns.output).write_text(
        json.dumps(compiled, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "schema": compiled["schema"],
        "row_count": compiled["row_count"],
        "instruction_instance_count": compiled["instruction_instance_count"],
        "output": ns.output,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
