"""Strict raw-source to typed-context compiler.

This module treats the supplied raw JSON bytes/text as the declared authoritative
fact source for a task. It does NOT decide whether the caller was authorized to
select that source; authority selection remains an upstream task/source-contract
obligation.

It eliminates a weaker trust pattern where a caller supplies both a typed object
and the expected digest for that same object. Instead, this compiler:
- hashes the exact raw source bytes,
- rejects duplicate JSON keys,
- accepts only the frozen typed-context schema,
- validates every field value by declared type,
- emits the normalized typed context and its deterministic content digest.

No field-name semantics are inferred.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA = "BRAIN_AUTHORITATIVE_TYPED_CONTEXT_COMPILER_V1"
MAX_SOURCE_BYTES = 1_000_000
_TYPES = {"BOOL", "INT", "STRING", "DECIMAL_STRING"}
_FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class TypedContextCompileError(ValueError):
    pass


def _pairs_no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise TypedContextCompileError("DUPLICATE_JSON_KEY:" + str(k))
        out[k] = v
    return out


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _type_ok(kind: str, value: Any) -> bool:
    if kind == "BOOL":
        return isinstance(value, bool)
    if kind == "INT":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "STRING":
        return isinstance(value, str)
    if kind == "DECIMAL_STRING":
        return isinstance(value, str) and _DECIMAL.fullmatch(value) is not None
    return False


def compile_typed_context(
    raw_source: str | bytes,
    *,
    source_id: str,
) -> dict[str, Any]:
    try:
        if not isinstance(source_id, str) or not source_id.strip():
            raise TypedContextCompileError("SOURCE_ID_MISSING")
        if isinstance(raw_source, str):
            raw = raw_source.encode("utf-8")
        elif isinstance(raw_source, bytes):
            raw = raw_source
        else:
            raise TypedContextCompileError("RAW_SOURCE_MUST_BE_TEXT_OR_BYTES")
        if not raw:
            raise TypedContextCompileError("RAW_SOURCE_EMPTY")
        if len(raw) > MAX_SOURCE_BYTES:
            raise TypedContextCompileError("RAW_SOURCE_TOO_LARGE")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TypedContextCompileError("RAW_SOURCE_NOT_UTF8") from exc

        try:
            document = json.loads(text, object_pairs_hook=_pairs_no_duplicates)
        except TypedContextCompileError:
            raise
        except Exception as exc:
            raise TypedContextCompileError("RAW_SOURCE_JSON_INVALID") from exc

        if not isinstance(document, Mapping):
            raise TypedContextCompileError("TYPED_CONTEXT_NOT_OBJECT")
        if set(document) != {"schema_id", "fields"}:
            raise TypedContextCompileError("TYPED_CONTEXT_TOP_LEVEL_KEYS_INVALID")

        schema_id = document.get("schema_id")
        fields = document.get("fields")
        if not isinstance(schema_id, str) or not schema_id.strip():
            raise TypedContextCompileError("SCHEMA_ID_INVALID")
        if not isinstance(fields, Mapping) or not fields:
            raise TypedContextCompileError("FIELDS_INVALID_OR_EMPTY")

        normalized_fields: dict[str, dict[str, Any]] = {}
        for name, row in fields.items():
            if not isinstance(name, str) or _FIELD.fullmatch(name) is None:
                raise TypedContextCompileError("FIELD_NAME_INVALID:" + str(name))
            if not isinstance(row, Mapping) or set(row) != {"type", "value"}:
                raise TypedContextCompileError("FIELD_ROW_INVALID:" + name)
            kind = row.get("type")
            value = row.get("value")
            if kind not in _TYPES:
                raise TypedContextCompileError("FIELD_TYPE_UNSUPPORTED:" + name)
            if not _type_ok(str(kind), value):
                raise TypedContextCompileError("FIELD_VALUE_TYPE_MISMATCH:" + name)
            normalized_fields[name] = {"type": kind, "value": value}

        context = {
            "schema_id": schema_id.strip(),
            "fields": normalized_fields,
        }
        return {
            "schema": SCHEMA,
            "status": "COMPILED",
            "source_id": source_id.strip(),
            "raw_source_sha256": sha256(raw).hexdigest(),
            "raw_source_byte_length": len(raw),
            "typed_context": context,
            "typed_context_sha256": sha256(_canon(context).encode("utf-8")).hexdigest(),
            "field_count": len(normalized_fields),
            "terminal_authority": False,
            "authority_boundary": (
                "THIS_COMPILER_PROVES_EXACT_INTERPRETATION_OF_THE_DECLARED_TYPED_JSON_SOURCE;"
                "WHETHER_SOURCE_ID_IS_AUTHORIZED_FOR_THE_TASK_MUST_BE_PROVED_UPSTREAM"
            ),
        }
    except TypedContextCompileError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "terminal_authority": False,
        }
