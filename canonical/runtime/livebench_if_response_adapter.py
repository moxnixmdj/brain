"""Deterministic fail-closed adapter from Brain terminal responses to LiveBench answer JSONL.

This adapter is intentionally case-agnostic. It never reads benchmark prompts, verifier
outputs, or terminal labels. It only normalizes already-produced Brain responses into the
pinned LiveBench answer schema consumed by the evaluation pipeline.

Frozen upstream integration evidence:
- LiveBench commit 8f8e5c381a16e3f24257776edd53471fe86f8091
- livebench/gen_api_answer.py blob a9186172abfa62ef087a16dfec0cb57013ff84b5
- expected fields used by common/process-results: question_id, choices[0].turns[0]
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Any


SCHEMA = "BRAIN_LIVEBENCH_RESPONSE_ADAPTER_V1"
UPSTREAM_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM_GEN_API_ANSWER_BLOB = "a9186172abfa62ef087a16dfec0cb57013ff84b5"
MODEL_ID = "project-brain-frozen-route"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        **extra,
    }


def _stable_answer_id(question_id: str, response: str) -> str:
    raw = (question_id + "\0" + response).encode("utf-8")
    return "brain-" + hashlib.sha256(raw).hexdigest()[:24]


def adapt_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        rows = list(records)
    except Exception:
        return _fail("RECORDS_NOT_ITERABLE")

    if not rows:
        return _fail("RECORDS_EMPTY")

    seen: set[str] = set()
    answers: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return _fail("RECORD_NOT_MAPPING", record_index=idx)

        unexpected = set(row) - {"question_id", "response"}
        missing = {"question_id", "response"} - set(row)
        if missing:
            return _fail("REQUIRED_FIELD_MISSING", record_index=idx, fields=sorted(missing))
        if unexpected:
            return _fail("UNDECLARED_FIELD_PRESENT", record_index=idx, fields=sorted(unexpected))

        qid = row["question_id"]
        response = row["response"]

        if isinstance(qid, bool) or not isinstance(qid, (str, int)):
            return _fail("QUESTION_ID_INVALID", record_index=idx)
        qid_s = str(qid)
        if not qid_s:
            return _fail("QUESTION_ID_EMPTY", record_index=idx)
        if qid_s in seen:
            return _fail("QUESTION_ID_DUPLICATE", record_index=idx, question_id=qid_s)
        seen.add(qid_s)

        if not isinstance(response, str):
            return _fail("RESPONSE_NOT_STRING", record_index=idx, question_id=qid_s)

        answers.append(
            {
                "question_id": qid if isinstance(qid, int) else qid_s,
                "answer_id": _stable_answer_id(qid_s, response),
                "model_id": MODEL_ID,
                "choices": [{"index": 0, "turns": [response]}],
            }
        )

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "answers": answers,
        "count": len(answers),
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_gen_api_answer_blob": UPSTREAM_GEN_API_ANSWER_BLOB,
        "case_content_read": False,
        "verifier_output_read": False,
        "terminal_authority": False,
    }


def write_jsonl(records: Iterable[Mapping[str, Any]], output_path: str | Path) -> dict[str, Any]:
    out = adapt_records(records)
    if out["status"] != "PASS":
        return out

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw = "".join(
            json.dumps(answer, sort_keys=True, separators=(",", ":")) + "\n"
            for answer in out["answers"]
        )
        path.write_text(raw, encoding="utf-8")
    except Exception as exc:
        path.unlink(missing_ok=True)
        return _fail("OUTPUT_WRITE_FAILED", error=type(exc).__name__)

    # Round-trip the exact bytes we wrote. No permissive parsing or silent row loss.
    try:
        parsed = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except Exception as exc:
        path.unlink(missing_ok=True)
        return _fail("OUTPUT_ROUNDTRIP_INVALID", error=type(exc).__name__)

    if parsed != out["answers"]:
        path.unlink(missing_ok=True)
        return _fail("OUTPUT_ROUNDTRIP_MISMATCH")

    return {
        **out,
        "output_path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
