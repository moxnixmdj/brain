"""Provenance-bound cross-tool dataflow V2 for capability-first computer use.

V2 extends the explicit prior-step scalar bridge with source-qualified and
"found earlier" references. It never guesses among distinct values, never
moves sensitive credentials, and never reads benchmark/evaluator sources.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_RECEIPT_DATAFLOW_V2"
SENSITIVE = {
    "password", "passwd", "secret", "token", "api key", "apikey",
    "authorization", "cookie", "private key", "access key", "session id",
}
MAX_DEPTH = 10
MAX_SCALAR_CHARS = 20000

_PREVIOUS = re.compile(
    r"\bthe\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+"
    r"from\s+(?:the\s+)?(?:previous|prior|earlier)\s+"
    r"(?:step|result|receipt)\b",
    re.I,
)
_FOUND = re.compile(
    r"\bthe\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+"
    r"(?:you\s+)?(?:found|observed|retrieved|identified|read)\s+earlier\b",
    re.I,
)
_SOURCE = re.compile(
    r"\bthe\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+from\s+"
    r"(Mailhub|TeamChat|CloudCRM|VaultBank|BudgetWise|Calendar|browser|the browser)\b",
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

def _walk(value: Any, *, path: tuple[str, ...] = (), depth: int = 0):
    if depth > MAX_DEPTH:
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
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

def _source_labels(source_name: str, source: Mapping[str, Any]) -> set[str]:
    labels = {_norm(source_name)}
    for key in ("app", "type", "operation"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            labels.add(_norm(value))
    if source_name == "browser_result":
        labels.update({"browser", "the browser"})
    return labels

def resolve_named_scalar(
    prior_rows: Sequence[Mapping[str, Any]],
    field_name: str,
    *,
    source_hint: str | None = None,
) -> dict[str, Any]:
    if not isinstance(field_name, str) or not field_name.strip():
        raise DataflowError("FIELD_NAME_REQUIRED")
    wanted = _norm(field_name)
    if not wanted:
        raise DataflowError("FIELD_NAME_INVALID")
    if _sensitive(wanted):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED__SENSITIVE_FIELD", "field": wanted, "pass": False}

    hint = _norm(source_hint) if isinstance(source_hint, str) and source_hint.strip() else None
    matches: list[dict[str, Any]] = []
    for row_index, row in enumerate(prior_rows):
        if not isinstance(row, Mapping):
            continue
        for source_name, source in _structured_sources(row):
            labels = _source_labels(source_name, source)
            if hint is not None and hint not in labels:
                continue
            for path, value in _walk(source):
                if not path or _norm(path[-1]) != wanted or _sensitive(path[-1]):
                    continue
                if isinstance(value, str) and len(value) > MAX_SCALAR_CHARS:
                    continue
                if value is None or isinstance(value, (bool, int, float, str)):
                    matches.append({
                        "row_index": row_index,
                        "source": source_name,
                        "source_labels": sorted(labels),
                        "path": list(path),
                        "value": value,
                    })

    distinct: dict[str, Any] = {}
    for row in matches:
        distinct[json.dumps(row["value"], sort_keys=True, ensure_ascii=False)] = row["value"]

    base = {"schema": SCHEMA, "field": wanted, "source_hint": hint}
    if not matches:
        return {**base, "status": "OPEN__FIELD_NOT_FOUND", "pass": False, "matches": []}
    if len(distinct) != 1:
        return {
            **base, "status": "OPEN__FIELD_AMBIGUOUS", "pass": False,
            "candidate_count": len(distinct), "matches": matches,
        }
    value = next(iter(distinct.values()))
    return {
        **base,
        "status": "PASS__UNIQUE_PRIOR_RECEIPT_SCALAR",
        "pass": True,
        "value": value,
        "provenance": [
            {
                "row_index": row["row_index"],
                "source": row["source"],
                "source_labels": row["source_labels"],
                "path": row["path"],
            }
            for row in matches
        ],
    }

def _references(text: str):
    found: list[tuple[int, int, str, str | None, str]] = []
    for kind, pattern in (("previous", _PREVIOUS), ("found", _FOUND), ("source", _SOURCE)):
        for match in pattern.finditer(text):
            source_hint = match.group(2) if kind == "source" else None
            found.append((match.start(), match.end(), match.group(1).strip(), source_hint, kind))
    found.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    out = []
    cursor = -1
    for item in found:
        if item[0] < cursor:
            continue
        out.append(item)
        cursor = item[1]
    return out

def materialize_explicit_references(
    text: str,
    prior_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise DataflowError("TEXT_REQUIRED")
    refs = _references(text)
    if not refs:
        return {"schema": SCHEMA, "status": "NO_EXPLICIT_REFERENCE", "pass": True, "text": text, "bindings": []}

    chunks: list[str] = []
    bindings: list[dict[str, Any]] = []
    cursor = 0
    for start, end, field, source_hint, kind in refs:
        resolved = resolve_named_scalar(prior_rows, field, source_hint=source_hint)
        if resolved.get("pass") is not True:
            return {
                "schema": SCHEMA, "status": "OPEN__REFERENCE_UNRESOLVED", "pass": False,
                "field": _norm(field), "reference_kind": kind,
                "resolution": resolved, "text": text, "bindings": bindings,
            }
        value = resolved.get("value")
        chunks.append(text[cursor:start])
        chunks.append(json.dumps(str(value), ensure_ascii=False))
        cursor = end
        bindings.append({
            "field": resolved["field"], "source_hint": resolved.get("source_hint"),
            "reference_kind": kind, "value": value, "provenance": resolved["provenance"],
        })
    chunks.append(text[cursor:])
    return {
        "schema": SCHEMA, "status": "PASS__EXPLICIT_REFERENCES_MATERIALIZED", "pass": True,
        "text": "".join(chunks), "bindings": bindings,
    }
