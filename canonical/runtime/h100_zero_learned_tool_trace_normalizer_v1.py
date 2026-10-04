"""Zero-learned structural tool-trace normalizer for H100.

This module normalizes a bounded, pre-exposed family of tool-trace shapes into a
declared typed numeric schema. It uses only explicit structure, declared field
names, call IDs, attempt IDs, and event types. Unknown wrappers, incomplete calls,
conflicting successful results, and nonnumeric declared fields fail closed.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_TOOL_TRACE_NORMALIZER_V1"


class ToolTraceError(ValueError):
    pass


class _Abstain(Exception):
    def __init__(self, status: str):
        super().__init__(status)
        self.status = status


def _schema(inputs: Sequence[str], target: str) -> tuple[tuple[str, ...], str]:
    if not isinstance(inputs, Sequence) or isinstance(inputs, (str, bytes)):
        raise ToolTraceError("INPUT_SCHEMA_INVALID")
    names = tuple(str(x).strip() for x in inputs)
    target = str(target).strip()
    if not names or not target or any(not x for x in names):
        raise ToolTraceError("INPUT_SCHEMA_INVALID")
    if len(set(names)) != len(names) or target in names:
        raise ToolTraceError("INPUT_SCHEMA_INVALID")
    return names, target


def _finite(value: Any) -> float:
    if isinstance(value, bool):
        raise _Abstain("ABSTAIN_TRACE_NONNUMERIC")
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise _Abstain("ABSTAIN_TRACE_NONNUMERIC")
    if not math.isfinite(out):
        raise _Abstain("ABSTAIN_TRACE_NONNUMERIC")
    return out


def _declared(mapping: Mapping[str, Any], fields: Sequence[str]) -> dict[str, float]:
    if not isinstance(mapping, Mapping):
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
    if any(name not in mapping for name in fields):
        raise _Abstain("ABSTAIN_TRACE_INCOMPLETE")
    return {name: _finite(mapping[name]) for name in fields}


def _unwrap(mapping: Any, nested_key: str | None = None) -> Mapping[str, Any]:
    if not isinstance(mapping, Mapping):
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
    if nested_key is not None and nested_key in mapping:
        nested = mapping[nested_key]
        if not isinstance(nested, Mapping):
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        return nested
    return mapping


def _name_value(items: Any) -> dict[str, Any]:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or not items:
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
    out: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or "value" not in item:
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        key = name.strip()
        if key in out and out[key] != item["value"]:
            raise _Abstain("ABSTAIN_TRACE_CONFLICT")
        out[key] = item["value"]
    return out


def _json_row(row: Mapping[str, Any], inputs: tuple[str, ...], target: str) -> dict[str, float]:
    if not isinstance(row, Mapping):
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")

    keys = set(row)
    if {"request", "response"} <= keys:
        left = _unwrap(row["request"], "payload")
        right = _unwrap(row["response"], "data")
    elif {"params", "output"} <= keys:
        left = _unwrap(row["params"])
        right = _unwrap(row["output"])
    elif {"inputs", "outputs"} <= keys:
        left = _name_value(row["inputs"])
        right = _name_value(row["outputs"])
    else:
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")

    a = _declared(left, inputs)
    b = _declared(right, (target,))
    return {**a, **b}


def _compile_json_rows(payload: Any, inputs: tuple[str, ...], target: str) -> list[dict[str, float]]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
    return [_json_row(row, inputs, target) for row in payload]


def _event_data(row: Mapping[str, Any]) -> Mapping[str, Any]:
    data = row.get("data")
    if not isinstance(data, Mapping):
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
    return data


def _compile_event_stream(payload: Any, inputs: tuple[str, ...], target: str) -> list[dict[str, float]]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
        raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")

    order: list[str] = []
    calls: dict[str, dict[int, dict[str, Any]]] = {}

    for row in payload:
        if not isinstance(row, Mapping):
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        call_id = row.get("call_id")
        event = row.get("event")
        attempt = row.get("attempt", 1)
        if not isinstance(call_id, str) or not call_id.strip():
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        call_id = call_id.strip()
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        if event not in {"request", "response", "error"}:
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        data = _event_data(row)

        if call_id not in calls:
            calls[call_id] = {}
            order.append(call_id)
        state = calls[call_id].setdefault(
            attempt, {"requests": [], "responses": [], "errors": []}
        )
        state[event + "s"].append(data)

    rows: list[dict[str, float]] = []
    for call_id in order:
        attempts = calls[call_id]
        successful: list[tuple[int, dict[str, float], dict[str, float]]] = []
        failed_inputs: list[dict[str, float]] = []

        for attempt in sorted(attempts):
            state = attempts[attempt]
            requests = state["requests"]
            responses = state["responses"]
            errors = state["errors"]

            if len(requests) > 1:
                # Duplicate requests are accepted only if their declared fields agree.
                parsed_requests = [_declared(x, inputs) for x in requests]
                first = parsed_requests[0]
                if any(x != first for x in parsed_requests[1:]):
                    raise _Abstain("ABSTAIN_TRACE_CONFLICT")
                request = first
            elif len(requests) == 1:
                request = _declared(requests[0], inputs)
            else:
                request = None

            if responses:
                if request is None:
                    raise _Abstain("ABSTAIN_TRACE_INCOMPLETE")
                parsed_responses = [_declared(x, (target,)) for x in responses]
                first_response = parsed_responses[0]
                if any(x != first_response for x in parsed_responses[1:]):
                    raise _Abstain("ABSTAIN_TRACE_CONFLICT")
                if errors:
                    raise _Abstain("ABSTAIN_TRACE_CONFLICT")
                successful.append((attempt, request, first_response))
            elif errors:
                if request is None:
                    raise _Abstain("ABSTAIN_TRACE_INCOMPLETE")
                failed_inputs.append(request)
            elif request is not None:
                raise _Abstain("ABSTAIN_TRACE_INCOMPLETE")

        if not successful:
            raise _Abstain("ABSTAIN_TRACE_INCOMPLETE")

        # More than one successful attempt for a call must agree exactly.
        _, chosen_inputs, chosen_output = successful[-1]
        for _, earlier_inputs, earlier_output in successful[:-1]:
            if earlier_inputs != chosen_inputs or earlier_output != chosen_output:
                raise _Abstain("ABSTAIN_TRACE_CONFLICT")

        # A retry after an error may be used only when declared inputs are unchanged.
        if any(failed != chosen_inputs for failed in failed_inputs):
            raise _Abstain("ABSTAIN_TRACE_CONFLICT")

        rows.append({**chosen_inputs, **chosen_output})

    return rows


def _result(status: str, rows: list[dict[str, float]], inputs: tuple[str, ...], target: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "inputs": list(inputs),
        "target": target,
        "rows": rows,
        "row_count": len(rows),
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "dynamic_code_execution": False,
        "hard_nonclaim": "FINITE_STRUCTURAL_TRACE_NORMALIZATION_IS_NOT_OPEN_WORLD_TOOL_SEMANTICS",
    }


def normalize_tool_trace(
    payload: Any,
    *,
    inputs: Sequence[str],
    target: str,
    format_hint: str,
) -> dict[str, Any]:
    names, target_n = _schema(inputs, target)
    hint = str(format_hint or "").strip().upper()
    try:
        if hint == "JSON_ROWS":
            rows = _compile_json_rows(payload, names, target_n)
        elif hint == "EVENT_STREAM":
            rows = _compile_event_stream(payload, names, target_n)
        else:
            raise _Abstain("ABSTAIN_TRACE_STRUCTURE_UNKNOWN")
        return _result("TYPED_NUMERIC_SCHEMA_COMPILED", rows, names, target_n)
    except _Abstain as exc:
        return _result(exc.status, [], names, target_n)
