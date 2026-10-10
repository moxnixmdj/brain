"""Brain-owned Toolathlon tool discovery/selection adapter V1.

The external model, if any, is a *general cognition substrate*. It never receives
the full tool catalog and never ranks or chooses routes. Brain owns the target
capability: catalog ingestion, filtering, evidence epochs, deterministic route
order, selection, escalation, and transfer.

This module is intentionally benchmark-agnostic at the wire boundary. A later
Toolathlon host integration maps gateway tools/list records into this adapter and
maps SELECT back to the gateway call surface.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

CMP = {"eq", "neq", "in", "not_in", "lt", "le", "gt", "ge", "contains", "exists"}
FORBIDDEN_SUBSTRATE_KEYS = {
    "tool_id", "tool_name", "candidate_tools", "tools", "catalog", "cost",
    "ranked_tools", "selected_tool", "route",
}


def _get(obj: Mapping[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in str(path).split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _pred(expr: Any, tool: Mapping[str, Any]) -> bool:
    if expr in (None, {}, []):
        return True
    if not isinstance(expr, Mapping):
        return False
    op = str(expr.get("op") or "")
    if op == "and":
        xs = expr.get("args")
        return isinstance(xs, list) and all(_pred(x, tool) for x in xs)
    if op == "or":
        xs = expr.get("args")
        return isinstance(xs, list) and bool(xs) and any(_pred(x, tool) for x in xs)
    if op == "not":
        return not _pred(expr.get("arg"), tool)
    if op not in CMP:
        return False
    value = _get(tool, str(expr.get("path") or ""))
    target = expr.get("value")
    if op == "exists":
        return (value is not None) is bool(target)
    if op == "eq":
        return value == target
    if op == "neq":
        return value != target
    if op == "in":
        return isinstance(target, list) and value in target
    if op == "not_in":
        return isinstance(target, list) and value not in target
    if op == "contains":
        return isinstance(value, (str, list, tuple, set)) and target in value
    if isinstance(value, bool) or isinstance(target, bool):
        return False
    if not isinstance(value, (int, float)) or not isinstance(target, (int, float)):
        return False
    if op == "lt":
        return value < target
    if op == "le":
        return value <= target
    if op == "gt":
        return value > target
    if op == "ge":
        return value >= target
    return False


def normalize_gateway_tools(records: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalize task-local gateway tools/list records into Brain policy records."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in records:
        tid = str(raw.get("name") or raw.get("tool_id") or "")
        if not tid or tid in seen:
            raise ValueError("INVALID_OR_DUPLICATE_TOOL_ID")
        seen.add(tid)
        out.append({
            "tool_id": tid,
            "description": str(raw.get("description") or ""),
            "input_schema": raw.get("inputSchema") or raw.get("input_schema") or {},
            "available": raw.get("available", True) is True,
            "authorized": raw.get("authorized", True) is True,
            "cost": float(raw.get("cost", 1.0)),
            "epoch": int(raw.get("epoch", 0)),
            "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {},
        })
    return out


def _epochs(public: Mapping[str, Any]) -> dict[str, int]:
    out = {
        str(t.get("tool_id")): int(t.get("epoch", 0))
        for t in public.get("tools", [])
        if isinstance(t, Mapping) and str(t.get("tool_id") or "")
    }
    for ev in public.get("version_events", []):
        if not isinstance(ev, Mapping) or ev.get("kind") != "TOOL_VERSION_CHANGED":
            continue
        tid = str(ev.get("tool_id") or "")
        if tid in out:
            out[tid] = int(ev.get("new_epoch", out[tid] + 1))
    return out


def _evidence(public: Mapping[str, Any]) -> dict[tuple[str, str], bool]:
    epochs = _epochs(public)
    out: dict[tuple[str, str], bool] = {}
    for rec in public.get("schema_judgment_receipts", []):
        if not isinstance(rec, Mapping) or rec.get("kind") != "ISOLATED_SCHEMA_CAPABILITY_JUDGMENT":
            continue
        tid = str(rec.get("tool_id") or "")
        cap = str(rec.get("capability") or "")
        if tid in epochs and int(rec.get("epoch", -1)) == epochs[tid]:
            out[(tid, cap)] = rec.get("supported") is True
    return out


def _contains_forbidden_key(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if str(key) in FORBIDDEN_SUBSTRATE_KEYS:
                return True
            if _contains_forbidden_key(value):
                return True
    elif isinstance(obj, list):
        return any(_contains_forbidden_key(x) for x in obj)
    return False


def build_subproblem_request(*, task_context: str, public_state_summary: str = "") -> dict[str, Any]:
    """Tool-agnostic request for the general cognition substrate.

    The catalog is deliberately not an argument to this function. This is the
    structural noninterference boundary: subproblem formation cannot depend on
    tool identities, alternatives, costs, schemas, or ranking state.
    """
    return {
        "task_context": str(task_context),
        "public_state_summary": str(public_state_summary),
        "response_schema": {
            "goal": "short string",
            "required_capabilities": ["capability strings"],
            "constraint": "optional deterministic predicate or null",
        },
    }


def validate_subproblem_contract(contract: Mapping[str, Any], tools: list[Mapping[str, Any]]) -> tuple[bool, list[str]]:
    del tools  # identities are intentionally irrelevant to contract validation
    errors: list[str] = []
    if _contains_forbidden_key(contract):
        errors.append("SUBSTRATE_CONTRACT_CONTAINS_FORBIDDEN_ROUTE_KEY")
    required = contract.get("required_capabilities")
    if not isinstance(required, list) or not required or not all(isinstance(x, str) and x.strip() for x in required):
        errors.append("REQUIRED_CAPABILITIES_MISSING_OR_INVALID")
    return (not errors, sorted(set(errors)))


def build_schema_judgment_request(
    *,
    tool: Mapping[str, Any],
    capability: str,
    task_context: str,
) -> dict[str, Any]:
    """Payload allowed to reach the general cognition substrate.

    Deliberately excludes tool identity, cost, alternatives, availability,
    authorization, and any ranking state.
    """
    payload = {
        "task_context": str(task_context),
        "required_capability": str(capability),
        "anonymous_tool": {
            "description": str(tool.get("description") or ""),
            "input_schema": tool.get("input_schema") or {},
        },
        "response_schema": {
            "supported": "boolean",
            "reason": "short string",
        },
    }
    return payload


def schema_judgment_request_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def bind_schema_judgment_receipt(
    *,
    tool_id: str,
    epoch: int,
    capability: str,
    supported: bool,
    request_hash: str,
) -> dict[str, Any]:
    """Brain binds an anonymous substrate judgment back to an internal tool ID."""
    return {
        "kind": "ISOLATED_SCHEMA_CAPABILITY_JUDGMENT",
        "tool_id": str(tool_id),
        "epoch": int(epoch),
        "capability": str(capability),
        "supported": supported is True,
        "request_hash": str(request_hash),
    }


def build_selected_tool_argument_request(
    *,
    tool: Mapping[str, Any],
    task_context: str,
    selected_capabilities: list[str],
) -> dict[str, Any]:
    """Argument synthesis happens only after Brain has selected one route."""
    return {
        "task_context": str(task_context),
        "selected_capabilities": [str(x) for x in selected_capabilities],
        "anonymous_selected_tool": {
            "description": str(tool.get("description") or ""),
            "input_schema": tool.get("input_schema") or {},
        },
        "response_schema": {"arguments": "object"},
    }


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    tools = [t for t in public.get("tools", []) if isinstance(t, Mapping)]
    contract = public.get("subproblem_contract")
    if not isinstance(contract, Mapping):
        return {"action": "ESCALATE", "reason": "SUBPROBLEM_CONTRACT_MISSING"}

    valid, errors = validate_subproblem_contract(contract, tools)
    if not valid:
        return {"action": "ESCALATE", "reason": "SUBSTRATE_BOUNDARY_VIOLATION", "errors": errors}

    required = sorted({str(x).strip() for x in contract.get("required_capabilities", []) if str(x).strip()})
    if not required:
        return {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"}

    evidence = _evidence(public)
    epochs = _epochs(public)
    admissible = [
        t for t in tools
        if str(t.get("tool_id") or "")
        and t.get("available") is True
        and t.get("authorized") is True
        and _pred(contract.get("constraint"), t)
    ]
    admissible.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))

    for tool in admissible:
        tid = str(tool.get("tool_id") or "")
        impossible = False
        unknown: list[str] = []
        for cap in required:
            value = evidence.get((tid, cap))
            if value is False:
                impossible = True
                break
            if value is None:
                unknown.append(cap)
        if impossible:
            continue
        if unknown:
            payload = build_schema_judgment_request(
                tool=tool,
                capability=unknown[0],
                task_context=str(public.get("task_context") or ""),
            )
            return {
                "action": "JUDGE_SCHEMA",
                "internal_tool_id": tid,
                "epoch": epochs[tid],
                "capability": unknown[0],
                "substrate_payload": payload,
                "request_hash": schema_judgment_request_hash(payload),
            }
        return {"action": "SELECT", "tool_id": tid}

    return {"action": "ESCALATE", "reason": "NO_EVIDENCE_SUPPORTED_ADMISSIBLE_TOOL"}


def source_gate_v2_candidate_route(*, general_substrate_test_pass: bool, benchmark_harness_zero_cost: bool) -> dict[str, Any]:
    """Candidate projection only. It does not claim the external facts are proved."""
    return {
        "benchmark_harness_zero_cost": benchmark_harness_zero_cost is True,
        "scorer_frozen": True,
        "brain_candidate_bound": True,
        "brain_owned_operative_configuration": True,
        "configuration_materially_constrains_execution": True,
        "capability_package_contains_configuration": True,
        "promotion_evaluates_brain_configured_system": True,
        "external_hidden_target_capability_provider": False,
        "ownership_claim_relies_on_model_standalone_superiority": False,
        "future_use_requires_capability_rediscovery": False,
        "model_role": "GENERAL_COGNITION_SUBSTRATE",
        "model_dependency_count": 1,
        "model_dependencies_declared": True,
        "general_substrate_test_pass": general_substrate_test_pass is True,
        "incremental_spend_usd": 0,
    }
