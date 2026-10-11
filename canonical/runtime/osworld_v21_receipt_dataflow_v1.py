"""Provenance-bound scalar dataflow across verified OSWorld workflow clauses.

Only explicit references such as "the email from the previous step" are
materialized. Values must be uniquely supported by prior structured receipts.
Ambiguous, missing, sensitive, or non-scalar bindings fail closed.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_RECEIPT_DATAFLOW_V1"
SENSITIVE = {
    "password", "passwd", "secret", "token", "api key", "apikey",
    "authorization", "cookie", "private key", "access key",
}
MAX_DEPTH = 10
MAX_SCALAR_CHARS = 20000

_REFERENCE = re.compile(
    r"\bthe\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+"
    r"from\s+(?:the\s+)?(?:previous|prior|earlier)\s+"
    r"(?:step|result|receipt)\b",
    re.I,
)


class DataflowError(ValueError):
    pass


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _sensitive(name: str) -> bool:
    n = _norm(name)
    return any(n == item or item in n for item in SENSITIVE)


def _walk(
    value: Any,
    *,
    path: tuple[str, ...] = (),
    depth: int = 0,
):
    if depth > MAX_DEPTH:
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            yield from _walk(item, path=path + (key,), depth=depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for i, item in enumerate(value):
            yield from _walk(item, path=path + (str(i),), depth=depth + 1)
        return
    if value is None or isinstance(value, (bool, int, float, str)):
        yield path, value


def _structured_sources(row: Mapping[str, Any]):
    for key in ("web_app_result", "browser_result", "app_result"):
        value = row.get(key)
        if isinstance(value, Mapping):
            yield key, value

    guest = row.get("guest_result")
    if isinstance(guest, Mapping):
        output = guest.get("output")
        if isinstance(output, str):
            stripped = output.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                except Exception:
                    parsed = None
                if isinstance(parsed, (Mapping, list)):
                    yield "guest_result.output_json", parsed


def resolve_named_scalar(
    prior_rows: Sequence[Mapping[str, Any]],
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(field_name, str) or not field_name.strip():
        raise DataflowError("FIELD_NAME_REQUIRED")
    wanted = _norm(field_name)
    if not wanted:
        raise DataflowError("FIELD_NAME_INVALID")
    if _sensitive(wanted):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SENSITIVE_FIELD",
            "field": wanted,
            "pass": False,
        }

    matches: list[dict[str, Any]] = []
    for row_index, row in enumerate(prior_rows):
        if not isinstance(row, Mapping):
            continue
        for source_name, source in _structured_sources(row):
            for path, value in _walk(source):
                if not path:
                    continue
                key = path[-1]
                if _norm(key) != wanted:
                    continue
                if _sensitive(key):
                    continue
                if isinstance(value, str) and len(value) > MAX_SCALAR_CHARS:
                    continue
                if value is None or isinstance(value, (bool, int, float, str)):
                    matches.append({
                        "row_index": row_index,
                        "source": source_name,
                        "path": list(path),
                        "value": value,
                    })

    distinct: dict[str, Any] = {}
    for row in matches:
        key = json.dumps(row["value"], sort_keys=True, ensure_ascii=False)
        distinct[key] = row["value"]

    if not matches:
        return {
            "schema": SCHEMA,
            "status": "OPEN__FIELD_NOT_FOUND",
            "field": wanted,
            "pass": False,
            "matches": [],
        }
    if len(distinct) != 1:
        return {
            "schema": SCHEMA,
            "status": "OPEN__FIELD_AMBIGUOUS",
            "field": wanted,
            "pass": False,
            "candidate_count": len(distinct),
            "matches": matches,
        }

    value = next(iter(distinct.values()))
    return {
        "schema": SCHEMA,
        "status": "PASS__UNIQUE_PRIOR_RECEIPT_SCALAR",
        "field": wanted,
        "pass": True,
        "value": value,
        "provenance": [
            {
                "row_index": row["row_index"],
                "source": row["source"],
                "path": row["path"],
            }
            for row in matches
        ],
    }


def materialize_explicit_references(
    text: str,
    prior_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise DataflowError("TEXT_REQUIRED")
    matches = list(_REFERENCE.finditer(text))
    if not matches:
        return {
            "schema": SCHEMA,
            "status": "NO_EXPLICIT_REFERENCE",
            "pass": True,
            "text": text,
            "bindings": [],
        }

    chunks: list[str] = []
    bindings: list[dict[str, Any]] = []
    cursor = 0
    for match in matches:
        field = match.group(1).strip()
        resolved = resolve_named_scalar(prior_rows, field)
        if resolved.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "OPEN__REFERENCE_UNRESOLVED",
                "pass": False,
                "field": _norm(field),
                "resolution": resolved,
                "text": text,
                "bindings": bindings,
            }
        value = resolved.get("value")
        replacement = json.dumps(str(value), ensure_ascii=False)
        chunks.append(text[cursor:match.start()])
        chunks.append(replacement)
        cursor = match.end()
        bindings.append({
            "field": resolved["field"],
            "value": value,
            "provenance": resolved["provenance"],
        })
    chunks.append(text[cursor:])
    return {
        "schema": SCHEMA,
        "status": "PASS__EXPLICIT_REFERENCES_MATERIALIZED",
        "pass": True,
        "text": "".join(chunks),
        "bindings": bindings,
    }
