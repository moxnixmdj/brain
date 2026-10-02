"""Deterministic adapter from Brain response records to IFBench prompt/response JSONL.

This adapter deliberately does not read benchmark case content. It only validates and
normalizes already-produced prompt/response pairs into the exact schema consumed by
allenai/IFBench evaluation_lib.read_prompt_to_response_dict at pinned commit
1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d.

No external model, judge, API, or paid service is used.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping, Any

PINNED_IFBENCH_COMMIT = "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"


class AdapterError(ValueError):
    pass


def normalize_record(record: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(record, Mapping):
        raise AdapterError("record must be a mapping")
    if "prompt" not in record or "response" not in record:
        raise AdapterError("record requires prompt and response")
    prompt = record["prompt"]
    response = record["response"]
    if not isinstance(prompt, str) or not prompt.strip():
        raise AdapterError("prompt must be non-empty text")
    if not isinstance(response, str):
        raise AdapterError("response must be text")
    # Preserve prompt bytes exactly. Upstream evaluator additionally indexes stripped
    # variants, so changing whitespace here would create an unnecessary mutation.
    return {"prompt": prompt, "response": response}


def adapt_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for record in records:
        normalized = normalize_record(record)
        prompt = normalized["prompt"]
        if prompt in seen:
            raise AdapterError("duplicate prompt would overwrite upstream response map")
        seen.add(prompt)
        out.append(normalized)
    if not out:
        raise AdapterError("at least one record is required")
    return out


def write_jsonl(records: Iterable[Mapping[str, Any]], output_path: str | Path) -> None:
    normalized = adapt_records(records)
    path = Path(output_path)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for record in normalized:
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
