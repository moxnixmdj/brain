#!/usr/bin/env python3
"""Brain-owned Finance Agent v2 model-boundary adapter V1.

This adapter does not execute Finance tools and does not replace the Vals agent.
It consumes the exact tool definitions exposed to the model by the official
Vals model-library Agent, uses Project Brain's verified dynamic schema-selection
policy, and returns one selected tool call. The untouched Vals host remains
responsible for tool execution, loop continuation, the two-hour limit, and
SubmitFinalResult termination.

The cognition substrate is proposal-only: it may form the next semantic
subproblem, judge one anonymous schema, and synthesize arguments for the already
Brain-selected anonymous schema. It never sees route identities or alternatives
during selection and has no execution or terminal authority.
"""
from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable, Callable, Mapping, Sequence

from canonical.runtime import toolathlon_brain_owned_selection_adapter_v1 as selector

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_BRAIN_MODEL_BOUNDARY_V1"
MAX_SCHEMA_JUDGMENTS = 128

Substrate = Callable[[str, Mapping[str, Any]], Awaitable[Mapping[str, Any]] | Mapping[str, Any]]


class FinanceModelBoundaryError(RuntimeError):
    pass


async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FinanceModelBoundaryError(code)
    return value


def normalize_vals_tools(tool_definitions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Map Vals ToolDefinition JSON into the selector's neutral tool records."""
    rows: list[dict[str, Any]] = []
    for raw in tool_definitions:
        if not isinstance(raw, Mapping):
            raise FinanceModelBoundaryError("VALS_TOOL_DEFINITION_NOT_OBJECT")
        name = str(raw.get("name") or "").strip()
        body = raw.get("body")
        if not name or not isinstance(body, Mapping):
            raise FinanceModelBoundaryError("VALS_TOOL_DEFINITION_INVALID")

        description = str(body.get("description") or "")
        properties = body.get("properties")
        required = body.get("required")
        if not isinstance(properties, Mapping):
            raise FinanceModelBoundaryError("VALS_TOOL_PROPERTIES_INVALID:" + name)
        if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
            raise FinanceModelBoundaryError("VALS_TOOL_REQUIRED_INVALID:" + name)

        rows.append({
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": dict(properties),
                "required": list(required),
                "additionalProperties": False,
            },
            "available": True,
            "authorized": True,
            # The official Vals model boundary publishes no per-tool cost.
            # Equal cost preserves a deterministic opaque-id tie break without
            # inventing a preference not present in the official harness.
            "cost": 1.0,
            "epoch": 0,
        })
    try:
        return selector.normalize_gateway_tools(rows)
    except Exception as exc:
        raise FinanceModelBoundaryError(
            "VALS_TOOL_NORMALIZATION_FAILED:" + type(exc).__name__
        ) from exc


def serialize_task_context(history: Sequence[Mapping[str, Any]]) -> str:
    """Content-preserving deterministic conversation envelope for the substrate."""
    if not isinstance(history, Sequence) or isinstance(history, (str, bytes)):
        raise FinanceModelBoundaryError("HISTORY_NOT_SEQUENCE")
    cleaned: list[dict[str, Any]] = []
    for index, item in enumerate(history):
        if not isinstance(item, Mapping):
            raise FinanceModelBoundaryError("HISTORY_ITEM_NOT_OBJECT:" + str(index))
        cleaned.append(dict(item))
    return json.dumps(
        {"conversation": cleaned},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


async def choose_next_tool_call(
    *,
    history: Sequence[Mapping[str, Any]],
    tool_definitions: Sequence[Mapping[str, Any]],
    substrate: Substrate,
) -> dict[str, Any]:
    """Return one Brain-selected Vals tool call for the current official turn."""
    if not callable(substrate):
        raise FinanceModelBoundaryError("SUBSTRATE_NOT_CALLABLE")

    tools = normalize_vals_tools(tool_definitions)
    task_context = serialize_task_context(history)

    subproblem_payload = selector.build_subproblem_request(task_context=task_context)
    contract = _mapping(
        await _maybe_await(substrate("SUBPROBLEM", subproblem_payload)),
        "SUBPROBLEM_RESULT_NOT_OBJECT",
    )
    valid, errors = selector.validate_subproblem_contract(contract, tools)
    if not valid:
        raise FinanceModelBoundaryError(
            "SUBPROBLEM_CONTRACT_REJECTED:" + ",".join(errors)
        )

    public: dict[str, Any] = {
        "tools": tools,
        "subproblem_contract": dict(contract),
        "task_context": task_context,
        "schema_judgment_receipts": [],
        "version_events": [],
    }

    selected: str | None = None
    for _ in range(min(MAX_SCHEMA_JUDGMENTS, max(1, len(tools) * 16))):
        action = selector.next_action(public)
        kind = action.get("action")

        if kind == "JUDGE_SCHEMA":
            payload = _mapping(
                action.get("substrate_payload"),
                "SCHEMA_JUDGMENT_PAYLOAD_MISSING",
            )
            judgment = _mapping(
                await _maybe_await(substrate("SCHEMA_JUDGMENT", payload)),
                "SCHEMA_JUDGMENT_RESULT_NOT_OBJECT",
            )
            if not isinstance(judgment.get("supported"), bool):
                raise FinanceModelBoundaryError(
                    "SCHEMA_JUDGMENT_SUPPORTED_NOT_BOOLEAN"
                )
            public["schema_judgment_receipts"].append(
                selector.bind_schema_judgment_receipt(
                    tool_id=str(action["internal_tool_id"]),
                    epoch=int(action["epoch"]),
                    capability=str(action["capability"]),
                    supported=judgment["supported"],
                    request_hash=str(action["request_hash"]),
                )
            )
            continue

        if kind == "SELECT":
            selected = str(action.get("tool_id") or "")
            break

        if kind == "ESCALATE":
            raise FinanceModelBoundaryError(
                "BRAIN_SELECTION_ESCALATED:" + str(action.get("reason") or "")
            )
        raise FinanceModelBoundaryError(
            "UNKNOWN_BRAIN_SELECTION_ACTION:" + str(kind)
        )

    if not selected:
        raise FinanceModelBoundaryError("SCHEMA_JUDGMENT_BUDGET_EXHAUSTED")

    tool = next((x for x in tools if x["tool_id"] == selected), None)
    if tool is None:
        raise FinanceModelBoundaryError("SELECTED_TOOL_OUTSIDE_SNAPSHOT")

    required_caps = [
        str(x).strip()
        for x in contract.get("required_capabilities", [])
        if isinstance(x, str) and x.strip()
    ]
    arg_payload = selector.build_selected_tool_argument_request(
        tool=tool,
        task_context=task_context,
        selected_capabilities=required_caps,
    )
    generated = _mapping(
        await _maybe_await(substrate("ARGUMENTS", arg_payload)),
        "ARGUMENT_RESULT_NOT_OBJECT",
    )
    arguments = generated.get("arguments")
    if not isinstance(arguments, Mapping):
        raise FinanceModelBoundaryError("ARGUMENTS_NOT_OBJECT")

    # Identity is Brain-selected. Any route-like fields supplied alongside the
    # arguments are ignored; the substrate cannot switch tools here.
    return {
        "schema": SCHEMA,
        "status": "BRAIN_SELECTED_OFFICIAL_VALS_TOOL_CALL",
        "tool_name": selected,
        "arguments": dict(arguments),
        "brain_selection_authority": True,
        "substrate_route_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
    }
