"""Bounded authoritative task-source enumeration and parse-coverage gate.

For task packages that explicitly declare the complete mounted source set (for
example, a task record with task brief, scenario/week overviews, shared_files,
and week_files), this gate deletes keyword-search source-discovery false negatives.

It proves structural source-set completeness relative to the declared task record:
- every declared source identity is enumerated exactly once;
- every enumerated source must be materialized with exact bytes;
- every source must carry a parser disposition;
- an unparsed or unsupported source blocks execution instead of silently becoming optional.

It does NOT prove the declared task record itself contains every authority source
in the universe, nor that a parser interpreted source semantics correctly.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_BOUNDED_TASK_SOURCE_SET_GATE_V1"

_SINGLE_PATH_FIELDS = (
    "task_md_path",
    "scenario_overview_path",
    "week_overview_path",
)
_LIST_PATH_FIELDS = ("shared_files", "week_files")


def _path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + "_INVALID")
    p = value.strip().replace("\\", "/")
    if p.startswith("/") or p.startswith("../") or "/../" in p or "\x00" in p:
        raise ValueError(label + "_NONCANONICAL")
    return p


def compile_required_source_set(task_record: Any) -> dict[str, Any]:
    try:
        if not isinstance(task_record, Mapping):
            raise ValueError("TASK_RECORD_NOT_OBJECT")
        task_id = str(task_record.get("task_id") or "").strip()
        if not task_id:
            raise ValueError("TASK_ID_MISSING")

        paths: list[dict[str, str]] = []
        for field in _SINGLE_PATH_FIELDS:
            value = task_record.get(field)
            if value is None:
                continue
            paths.append({"path": _path(value, field), "origin": field})

        for field in _LIST_PATH_FIELDS:
            raw = task_record.get(field)
            if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
                raise ValueError(field + "_INVALID")
            for i, value in enumerate(raw):
                paths.append({"path": _path(value, f"{field}:{i}"), "origin": field})

        if not paths:
            raise ValueError("DECLARED_SOURCE_SET_EMPTY")

        seen: set[str] = set()
        duplicates: list[str] = []
        unique: list[dict[str, str]] = []
        for row in paths:
            p = row["path"]
            if p in seen:
                duplicates.append(p)
                continue
            seen.add(p)
            unique.append(row)
        if duplicates:
            raise ValueError("DECLARED_SOURCE_DUPLICATE:" + ",".join(sorted(set(duplicates))))

        unique.sort(key=lambda x: (x["path"], x["origin"]))
        manifest_payload = "\n".join(row["path"] + "\t" + row["origin"] for row in unique)
        return {
            "schema": SCHEMA,
            "status": "COMPILED_BOUNDED_SOURCE_SET",
            "pass": True,
            "task_id": task_id,
            "source_count": len(unique),
            "sources": unique,
            "source_set_sha256": sha256(manifest_payload.encode("utf-8")).hexdigest(),
            "bounded_enumeration": True,
            "open_world_completeness_claim": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }


def verify_source_coverage(
    task_record: Any,
    *,
    materialized_sources: Mapping[str, bytes | str],
    parse_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    compiled = compile_required_source_set(task_record)
    if compiled.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["SOURCE_SET_COMPILE_FAILED", *(compiled.get("errors") or [])],
            "terminal_authority": False,
        }
    if not isinstance(materialized_sources, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "errors": ["MATERIALIZED_SOURCES_INVALID"], "terminal_authority": False}
    if not isinstance(parse_receipts, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "errors": ["PARSE_RECEIPTS_INVALID"], "terminal_authority": False}

    required = {row["path"] for row in compiled["sources"]}
    supplied = set(materialized_sources)
    receipt_paths = set(parse_receipts)
    errors: list[str] = []

    for missing in sorted(required - supplied):
        errors.append("DECLARED_SOURCE_NOT_MATERIALIZED:" + missing)
    for undeclared in sorted(supplied - required):
        errors.append("UNDECLARED_SOURCE_PAYLOAD:" + undeclared)
    for missing in sorted(required - receipt_paths):
        errors.append("DECLARED_SOURCE_PARSE_RECEIPT_MISSING:" + missing)
    for undeclared in sorted(receipt_paths - required):
        errors.append("UNDECLARED_SOURCE_PARSE_RECEIPT:" + undeclared)

    rows: list[dict[str, Any]] = []
    for path in sorted(required & supplied & receipt_paths):
        payload = materialized_sources[path]
        if isinstance(payload, str):
            data = payload.encode("utf-8")
        elif isinstance(payload, bytes):
            data = payload
        else:
            errors.append("SOURCE_PAYLOAD_INVALID:" + path)
            continue
        digest = sha256(data).hexdigest()
        receipt = parse_receipts[path]
        if not isinstance(receipt, Mapping):
            errors.append("PARSE_RECEIPT_NOT_OBJECT:" + path)
            continue
        if receipt.get("source_sha256") != digest:
            errors.append("PARSE_RECEIPT_SOURCE_HASH_MISMATCH:" + path)
        status = receipt.get("status")
        if status != "PARSED":
            errors.append("DECLARED_SOURCE_NOT_PARSED:" + path + ":" + str(status))
        parser_id = receipt.get("parser_id")
        parser_receipt = receipt.get("parser_receipt_id")
        if not isinstance(parser_id, str) or not parser_id.strip():
            errors.append("PARSER_ID_MISSING:" + path)
        if not isinstance(parser_receipt, str) or not parser_receipt.strip():
            errors.append("PARSER_RECEIPT_ID_MISSING:" + path)
        rows.append({
            "path": path,
            "source_sha256": digest,
            "byte_length": len(data),
            "parse_status": status,
            "parser_id": parser_id,
            "parser_receipt_id": parser_receipt,
        })

    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_DECLARED_BOUNDED_TASK_SOURCES_MATERIALIZED_AND_PARSE_RECEIPTED" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "task_id": compiled["task_id"],
        "source_set_sha256": compiled["source_set_sha256"],
        "source_count": compiled["source_count"],
        "source_rows": rows,
        "bounded_source_discovery_false_negative_closed": not errors,
        "parser_semantic_correctness_self_verified": False,
        "declared_manifest_universe_completeness_self_verified": False,
        "execution_should_block_on_unparsed_declared_source": True,
        "terminal_authority": False,
    }
