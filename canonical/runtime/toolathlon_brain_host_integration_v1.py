"""Brain-owned host integration for Toolathlon decoupled MCP gateway V1.

Binds Toolathlon's frozen JSON-RPC gateway surface (tools/list + tools/call) to
the independently verified Brain-owned selection adapter. The cognition
substrate never receives tool identities, alternative routes, or costs and
cannot directly choose/call a tool.

This module deliberately does not own the benchmark container, evaluator, or
model transport. It is a narrow host-side control seam.
"""
from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable, Callable, Mapping

from canonical.runtime import toolathlon_brain_owned_selection_adapter_v1 as adapter

RpcCall = Callable[[Mapping[str, Any]], Awaitable[Mapping[str, Any]] | Mapping[str, Any]]
SubstrateCall = Callable[[str, Mapping[str, Any]], Awaitable[Mapping[str, Any]] | Mapping[str, Any]]

JSONRPC_VERSION = "2.0"


class ToolathlonBrainHostError(RuntimeError):
    pass


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _require_mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ToolathlonBrainHostError(code)
    return value


def _jsonrpc_request(request_id: int, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "id": request_id, "method": method}
    if params is not None:
        out["params"] = dict(params)
    return out


async def _rpc_checked(rpc: RpcCall, request: Mapping[str, Any]) -> Mapping[str, Any]:
    response = _require_mapping(await _maybe_await(rpc(request)), "GATEWAY_RESPONSE_NOT_OBJECT")
    if response.get("jsonrpc") != JSONRPC_VERSION:
        raise ToolathlonBrainHostError("GATEWAY_JSONRPC_VERSION_MISMATCH")
    if response.get("id") != request.get("id"):
        raise ToolathlonBrainHostError("GATEWAY_RESPONSE_ID_MISMATCH")
    if "error" in response:
        raise ToolathlonBrainHostError("GATEWAY_ERROR:" + json.dumps(response["error"], sort_keys=True))
    result = response.get("result")
    return _require_mapping(result, "GATEWAY_RESULT_NOT_OBJECT")


async def gateway_list_tools(rpc: RpcCall, request_id: int = 1) -> list[dict[str, Any]]:
    result = await _rpc_checked(rpc, _jsonrpc_request(request_id, "tools/list", {}))
    raw = result.get("tools")
    if not isinstance(raw, list) or not raw:
        raise ToolathlonBrainHostError("GATEWAY_TOOL_LIST_EMPTY_OR_INVALID")
    records: list[Mapping[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ToolathlonBrainHostError("GATEWAY_TOOL_RECORD_NOT_OBJECT")
        records.append(item)
    try:
        return adapter.normalize_gateway_tools(records)
    except Exception as exc:
        raise ToolathlonBrainHostError("GATEWAY_TOOL_NORMALIZATION_FAILED:" + type(exc).__name__) from exc


async def gateway_call_tool(
    rpc: RpcCall,
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    request_id: int,
) -> Mapping[str, Any]:
    if not tool_name:
        raise ToolathlonBrainHostError("SELECTED_TOOL_ID_MISSING")
    if not isinstance(arguments, Mapping):
        raise ToolathlonBrainHostError("SELECTED_TOOL_ARGUMENTS_NOT_OBJECT")
    return await _rpc_checked(
        rpc,
        _jsonrpc_request(
            request_id,
            "tools/call",
            {"name": tool_name, "arguments": dict(arguments)},
        ),
    )


async def _substrate_checked(
    substrate: SubstrateCall,
    kind: str,
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    # Payloads are constructed only by the verified adapter. The substrate
    # cannot inject a gateway request; returned values are parsed by phase.
    return _require_mapping(
        await _maybe_await(substrate(kind, payload)),
        "SUBSTRATE_RESPONSE_NOT_OBJECT:" + kind,
    )


async def resolve_brain_selected_route(
    *,
    rpc: RpcCall,
    substrate: SubstrateCall,
    task_context: str,
    public_state_summary: str = "",
    request_id_start: int = 1,
) -> dict[str, Any]:
    """Resolve exactly one Brain-selected Toolathlon route.

    Returns the selected tool id plus the current evidence state. No tool call
    happens here.
    """
    tools = await gateway_list_tools(rpc, request_id=request_id_start)

    subproblem_request = adapter.build_subproblem_request(
        task_context=task_context,
        public_state_summary=public_state_summary,
    )
    contract = await _substrate_checked(substrate, "SUBPROBLEM", subproblem_request)
    valid, errors = adapter.validate_subproblem_contract(contract, tools)
    if not valid:
        raise ToolathlonBrainHostError("SUBPROBLEM_CONTRACT_REJECTED:" + ",".join(errors))

    public: dict[str, Any] = {
        "tools": tools,
        "subproblem_contract": dict(contract),
        "task_context": str(task_context),
        "schema_judgment_receipts": [],
        "version_events": [],
    }

    required = contract.get("required_capabilities")
    if not isinstance(required, list) or not required:
        raise ToolathlonBrainHostError("NO_REQUIRED_CAPABILITIES")
    judgment_budget = max(1, len(tools) * len(required) + 1)

    for _ in range(judgment_budget):
        action = adapter.next_action(public)
        kind = action.get("action")

        if kind == "JUDGE_SCHEMA":
            substrate_payload = _require_mapping(
                action.get("substrate_payload"),
                "SCHEMA_JUDGMENT_PAYLOAD_MISSING",
            )
            judgment = await _substrate_checked(substrate, "SCHEMA_JUDGMENT", substrate_payload)
            if type(judgment.get("supported")) is not bool:
                raise ToolathlonBrainHostError("SCHEMA_JUDGMENT_SUPPORTED_NOT_BOOLEAN")
            receipt = adapter.bind_schema_judgment_receipt(
                tool_id=str(action["internal_tool_id"]),
                epoch=int(action["epoch"]),
                capability=str(action["capability"]),
                supported=judgment["supported"],
                request_hash=str(action["request_hash"]),
            )
            public["schema_judgment_receipts"].append(receipt)
            continue

        if kind == "SELECT":
            selected = str(action.get("tool_id") or "")
            if not selected:
                raise ToolathlonBrainHostError("BRAIN_SELECTED_EMPTY_TOOL_ID")
            if selected not in {str(t.get("tool_id") or "") for t in tools}:
                raise ToolathlonBrainHostError("BRAIN_SELECTED_TOOL_OUTSIDE_GATEWAY_SNAPSHOT")
            return {
                "selected_tool_id": selected,
                "tools": tools,
                "subproblem_contract": dict(contract),
                "schema_judgment_receipts": list(public["schema_judgment_receipts"]),
                "next_request_id": request_id_start + 1,
            }

        if kind == "ESCALATE":
            raise ToolathlonBrainHostError("BRAIN_SELECTION_ESCALATED:" + str(action.get("reason") or ""))

        raise ToolathlonBrainHostError("UNKNOWN_BRAIN_SELECTION_ACTION:" + str(kind))

    raise ToolathlonBrainHostError("SCHEMA_JUDGMENT_BUDGET_EXHAUSTED")


async def execute_one_brain_selected_step(
    *,
    rpc: RpcCall,
    substrate: SubstrateCall,
    task_context: str,
    public_state_summary: str = "",
    request_id_start: int = 1,
) -> dict[str, Any]:
    """Resolve one route, synthesize arguments only for it, then call gateway."""
    resolved = await resolve_brain_selected_route(
        rpc=rpc,
        substrate=substrate,
        task_context=task_context,
        public_state_summary=public_state_summary,
        request_id_start=request_id_start,
    )
    selected = resolved["selected_tool_id"]
    tool = next(t for t in resolved["tools"] if t["tool_id"] == selected)

    arg_request = adapter.build_selected_tool_argument_request(
        tool=tool,
        task_context=task_context,
        selected_capabilities=list(resolved["subproblem_contract"]["required_capabilities"]),
    )
    arg_response = await _substrate_checked(substrate, "ARGUMENTS", arg_request)
    arguments = arg_response.get("arguments")
    if not isinstance(arguments, Mapping):
        raise ToolathlonBrainHostError("SUBSTRATE_ARGUMENTS_NOT_OBJECT")

    result = await gateway_call_tool(
        rpc,
        tool_name=selected,
        arguments=arguments,
        request_id=int(resolved["next_request_id"]),
    )
    return {
        "selected_tool_id": selected,
        "arguments": dict(arguments),
        "gateway_result": dict(result),
        "schema_judgment_receipts": resolved["schema_judgment_receipts"],
        "tool_snapshot_size": len(resolved["tools"]),
        "terminal_credit": 0,
    }
