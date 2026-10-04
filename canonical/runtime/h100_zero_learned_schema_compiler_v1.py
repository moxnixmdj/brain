"""Zero-learned observation-to-typed-numeric-schema compiler for H100.

This compiler is deliberately conservative. It accepts a bounded family of public
observation encodings (JSON rows, tool traces, JSONL, CSV, Markdown tables, and
simple numeric natural-language/key-value sentences) and returns exact numeric
rows for an already-declared input/target schema.

It does not infer semantic roles, solve the downstream mechanism, use a language
model, perform random search, or execute dynamic code. Unsupported or ambiguous
input fails closed.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_SCHEMA_COMPILER_V1"
_NUM = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_EQ_RE = re.compile(rf"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*({_NUM})")
_IS_RE = re.compile(rf"\b([A-Za-z_][A-Za-z0-9_]*)\s+is\s+({_NUM})\b", re.IGNORECASE)


class SchemaCompilerError(ValueError):
    pass


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise SchemaCompilerError("BOOLEAN_NOT_NUMERIC:" + label)
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaCompilerError("NON_NUMERIC:" + label) from exc
    if not math.isfinite(x):
        raise SchemaCompilerError("NONFINITE:" + label)
    return x


def _normalize_schema(inputs: Sequence[str], target: str) -> tuple[tuple[str, ...], str]:
    if isinstance(inputs, (str, bytes)) or not isinstance(inputs, Sequence):
        raise SchemaCompilerError("INPUT_SCHEMA_INVALID")
    names = tuple(str(x).strip() for x in inputs)
    target = str(target).strip()
    if not names or not target or any(not x for x in names):
        raise SchemaCompilerError("INPUT_SCHEMA_INVALID")
    if len(set(names)) != len(names) or target in names:
        raise SchemaCompilerError("INPUT_SCHEMA_INVALID")
    ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    if any(not ident.match(x) for x in names + (target,)):
        raise SchemaCompilerError("FIELD_NAME_INVALID")
    return names, target


def _row_from_mapping(row: Mapping[str, Any], inputs: tuple[str, ...], target: str) -> dict[str, float]:
    needed = inputs + (target,)
    if not all(name in row for name in needed):
        missing = [name for name in needed if name not in row]
        raise SchemaCompilerError("MISSING_FIELDS:" + ",".join(missing))
    return {name: _finite_number(row[name], name) for name in needed}


def _tool_row(row: Mapping[str, Any], inputs: tuple[str, ...], target: str) -> dict[str, float]:
    args = row.get("arguments")
    result = row.get("result")
    if not isinstance(args, Mapping) or not isinstance(result, Mapping):
        raise SchemaCompilerError("TOOL_TRACE_SHAPE_INVALID")
    merged = dict(args)
    for key, value in result.items():
        if key in merged and merged[key] != value:
            raise SchemaCompilerError("TOOL_TRACE_FIELD_CONFLICT:" + str(key))
        merged[key] = value
    return _row_from_mapping(merged, inputs, target)


def _parse_jsonlike(payload: Any, inputs: tuple[str, ...], target: str) -> list[dict[str, float]]:
    if isinstance(payload, Mapping):
        payload = [payload]
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        raise SchemaCompilerError("JSON_ROWS_INVALID")
    rows: list[dict[str, float]] = []
    for i, raw in enumerate(payload):
        if not isinstance(raw, Mapping):
            raise SchemaCompilerError(f"ROW_NOT_MAPPING:{i}")
        if "arguments" in raw or "result" in raw:
            rows.append(_tool_row(raw, inputs, target))
        else:
            rows.append(_row_from_mapping(raw, inputs, target))
    return rows


def _parse_jsonl(text: str, inputs: tuple[str, ...], target: str) -> list[dict[str, float]]:
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SchemaCompilerError(f"JSONL_INVALID:{i}") from exc
        if not isinstance(raw, Mapping):
            raise SchemaCompilerError(f"JSONL_ROW_NOT_OBJECT:{i}")
        rows.append(_tool_row(raw, inputs, target) if ("arguments" in raw or "result" in raw) else _row_from_mapping(raw, inputs, target))
    if not rows:
        raise SchemaCompilerError("JSONL_EMPTY")
    return rows


def _parse_csv(text: str, inputs: tuple[str, ...], target: str) -> list[dict[str, float]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise SchemaCompilerError("CSV_HEADER_MISSING")
    headers = [str(x).strip() for x in reader.fieldnames]
    needed = list(inputs) + [target]
    if any(name not in headers for name in needed):
        raise SchemaCompilerError("CSV_REQUIRED_FIELD_MISSING")
    rows = []
    for i, raw in enumerate(reader, 1):
        if raw is None:
            continue
        clean = {str(k).strip(): v for k, v in raw.items() if k is not None}
        try:
            rows.append(_row_from_mapping(clean, inputs, target))
        except SchemaCompilerError as exc:
            raise SchemaCompilerError(f"CSV_ROW_INVALID:{i}:{exc}") from exc
    if not rows:
        raise SchemaCompilerError("CSV_EMPTY")
    return rows


def _parse_markdown(text: str, inputs: tuple[str, ...], target: str) -> list[dict[str, float]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise SchemaCompilerError("MARKDOWN_TABLE_TOO_SHORT")

    def cells(line: str) -> list[str]:
        if not line.startswith("|") or not line.endswith("|"):
            raise SchemaCompilerError("MARKDOWN_ROW_SHAPE_INVALID")
        return [part.strip() for part in line[1:-1].split("|")]

    headers = cells(lines[0])
    separator = cells(lines[1])
    if len(separator) != len(headers) or not all(re.fullmatch(r":?-{3,}:?", part) for part in separator):
        raise SchemaCompilerError("MARKDOWN_SEPARATOR_INVALID")
    needed = list(inputs) + [target]
    if any(name not in headers for name in needed):
        raise SchemaCompilerError("MARKDOWN_REQUIRED_FIELD_MISSING")

    rows = []
    for i, line in enumerate(lines[2:], 1):
        values = cells(line)
        if len(values) != len(headers):
            raise SchemaCompilerError(f"MARKDOWN_WIDTH_INVALID:{i}")
        rows.append(_row_from_mapping(dict(zip(headers, values)), inputs, target))
    if not rows:
        raise SchemaCompilerError("MARKDOWN_EMPTY")
    return rows


def _parse_text_lines(payload: Any, inputs: tuple[str, ...], target: str) -> list[dict[str, float]]:
    lines = payload if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)) else str(payload).splitlines()
    needed = set(inputs + (target,))
    rows = []
    for i, raw in enumerate(lines, 1):
        if not isinstance(raw, str):
            raise SchemaCompilerError(f"TEXT_ROW_NOT_STRING:{i}")
        found: dict[str, str] = {}
        for name, value in _EQ_RE.findall(raw):
            if name in found and found[name] != value:
                raise SchemaCompilerError(f"TEXT_FIELD_DUPLICATE_CONFLICT:{i}:{name}")
            found[name] = value
        for name, value in _IS_RE.findall(raw):
            if name in found and found[name] != value:
                raise SchemaCompilerError(f"TEXT_FIELD_DUPLICATE_CONFLICT:{i}:{name}")
            found[name] = value
        if set(found) & needed != needed:
            missing = sorted(needed - set(found))
            raise SchemaCompilerError(f"TEXT_REQUIRED_FIELD_MISSING:{i}:" + ",".join(missing))
        rows.append(_row_from_mapping(found, inputs, target))
    if not rows:
        raise SchemaCompilerError("TEXT_EMPTY")
    return rows


def compile_observations(payload: Any, *, inputs: Sequence[str], target: str, format_hint: str | None = None) -> dict[str, Any]:
    names, target = _normalize_schema(inputs, target)
    hint = str(format_hint or "").strip().upper()

    if hint in {"JSON_ROWS", "TOOL_TRACE"}:
        rows = _parse_jsonlike(payload, names, target)
    elif hint == "JSONL_TOOL_TRACE":
        if not isinstance(payload, str):
            raise SchemaCompilerError("JSONL_REQUIRES_STRING")
        rows = _parse_jsonl(payload, names, target)
    elif hint == "CSV":
        if not isinstance(payload, str):
            raise SchemaCompilerError("CSV_REQUIRES_STRING")
        rows = _parse_csv(payload, names, target)
    elif hint == "MARKDOWN_TABLE":
        if not isinstance(payload, str):
            raise SchemaCompilerError("MARKDOWN_REQUIRES_STRING")
        rows = _parse_markdown(payload, names, target)
    elif hint in {"FREE_TEXT_KEY_VALUE", "FREE_TEXT_RELATIONAL"}:
        rows = _parse_text_lines(payload, names, target)
    else:
        raise SchemaCompilerError("UNSUPPORTED_OR_MISSING_FORMAT_HINT")

    return {
        "schema": SCHEMA,
        "status": "TYPED_NUMERIC_SCHEMA_COMPILED",
        "inputs": list(names),
        "target": target,
        "rows": rows,
        "row_count": len(rows),
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "dynamic_code_execution": False,
        "hard_nonclaim": "BOUNDED_FORMAT_COMPILATION_IS_NOT_OPEN_WORLD_NATURAL_LANGUAGE_UNDERSTANDING",
    }
