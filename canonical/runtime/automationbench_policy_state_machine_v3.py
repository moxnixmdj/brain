"""AutomationBench transport state machine V3 over Brain's generic workflow core.

This module is intentionally benchmark-thin. It provides only the benchmark's
api_search/api_fetch transport loop. Goal interpretation, tool-effect planning,
argument grounding, causal sequencing, and post-state verification are generic
Brain capabilities.

No application-specific mutation compiler is reachable from this state machine.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.generic_tool_schema_discovery_v1 import discovery_queries
from canonical.runtime.generic_goal_tool_effect_planner_v2 import (
    endpoint_rows_from_search_payloads,
    plan_goal_over_tool_schemas,
)
from canonical.runtime.generic_goal_constraint_guard_v1 import mutation_step_guard
from canonical.runtime.generic_tool_argument_binder_v1 import bind_endpoint_call
from canonical.runtime.generic_goal_state_verifier_v3 import verify_goal_state
from canonical.runtime.generic_goal_tool_effect_planner_v1 import compile_goal_contract

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_POLICY_STATE_MACHINE_V3"


def _tool_events(
    history: Sequence[Mapping[str, Any]],
    name: str,
) -> list[Mapping[str, Any]]:
    return [
        row for row in history
        if str(row.get("kind") or row.get("type") or "") == "tool_result"
        and str(row.get("name") or row.get("tool") or "") == name
    ]


def _payload(event: Mapping[str, Any]) -> Any:
    value = event.get("content", event.get("result"))
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return value


def _is_error_payload(value: Any) -> bool:
    if isinstance(value, Mapping):
        if "error" in value and value.get("error") not in (None, "", False, {}):
            return True
        status = str(value.get("status") or "").lower()
        if status.startswith("error") or status.startswith("fail"):
            return True
    text = str(value or "").lower()
    return (
        '"error"' in text
        or "tool execution failed" in text
        or "invalid request" in text
    )


def _semantic_results(
    history: Sequence[Mapping[str, Any]],
    semantic: str,
) -> list[Any] | None:
    active = False
    results: list[Any] = []
    for row in history:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("kind") or "") == "assistant_state":
            metadata = row.get("metadata")
            current = (
                metadata.get("project_brain/automationbench_semantic")
                if isinstance(metadata, Mapping)
                else None
            )
            if active and current != semantic:
                break
            if current == semantic:
                active = True
            continue
        if (
            active
            and str(row.get("kind") or row.get("type") or "") == "tool_result"
            and str(row.get("name") or row.get("tool") or "") == "api_fetch"
        ):
            results.append(_payload(row))
    return results if active else None


def _semantic_state(
    history: Sequence[Mapping[str, Any]],
    semantic: str,
) -> str:
    results = _semantic_results(history, semantic)
    if results is None:
        return "MISSING"
    if not results:
        return "PENDING"
    if any(_is_error_payload(x) for x in results):
        return "ERROR"
    return "SUCCESS"


def _all_fetch_results(
    history: Sequence[Mapping[str, Any]],
) -> list[Any]:
    return [_payload(row) for row in _tool_events(history, "api_fetch")]


def _fetch_results_before_semantic(
    history: Sequence[Mapping[str, Any]],
    semantic: str,
) -> list[Any]:
    out: list[Any] = []
    for row in history:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("kind") or "") == "assistant_state":
            metadata = row.get("metadata")
            current = (
                metadata.get("project_brain/automationbench_semantic")
                if isinstance(metadata, Mapping)
                else None
            )
            if current == semantic:
                break
        if (
            str(row.get("kind") or row.get("type") or "") == "tool_result"
            and str(row.get("name") or row.get("tool") or "") == "api_fetch"
        ):
            out.append(_payload(row))
    return out


def _plan_token(plan: Sequence[Any], contract: Any = None) -> str:
    raw = json.dumps(
        {"plan": list(plan), "contract": contract},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def _bound_get_calls(
    *,
    goal: str,
    endpoint_ids: Sequence[str],
    endpoint_by_id: Mapping[str, Mapping[str, Any]],
    observations: Sequence[Any],
    max_calls: int,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    seen: set[str] = set()
    for endpoint_id in endpoint_ids:
        endpoint = endpoint_by_id.get(str(endpoint_id))
        if endpoint is None:
            continue
        bound = bind_endpoint_call(
            goal=goal,
            endpoint=endpoint,
            observations=observations,
        )
        if bound.get("pass") is not True:
            continue
        args = dict(bound.get("arguments") or {})
        if str(args.get("method") or "").upper() != "GET":
            continue
        sig = json.dumps(args, sort_keys=True, default=str)
        if sig in seen:
            continue
        seen.add(sig)
        calls.append({"tool": "api_fetch", "arguments": args})
        if len(calls) >= max_calls:
            break
    return calls


def _executed_mutation_trace(
    plan: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in plan.get("steps") or []:
        if str(step.get("role") or "") != "mutation":
            continue
        capability_id = str(step.get("capability_id") or "")
        if not capability_id:
            continue
        semantic = "GENERIC_TOOL_EFFECT::" + capability_id
        if _semantic_state(history, semantic) != "SUCCESS":
            continue
        out.append({
            "intent_id": str(step.get("intent_id") or ""),
            "action_class": str(step.get("action_class") or ""),
            "endpoint_id": str(step.get("endpoint_id") or ""),
            "capability_id": capability_id,
        })
    return out


def next_policy_action(
    *,
    prompt: str,
    history: Sequence[Mapping[str, Any]],
    max_parallel_calls: int = 6,
) -> dict[str, Any]:
    contract = compile_goal_contract(prompt)
    if contract.get("status") == "NO_POSITIVE_ACTION_REQUIRED":
        construction_proof = verify_goal_state(
            goal=prompt,
            context_observations=[],
            verification_observations=[],
            execution_trace=[],
            execution_trace_complete=True,
        )
        if construction_proof.get("pass") is True:
            return {
                "schema": SCHEMA,
                "status": "DONE_VERIFIED",
                "phase": "COMPLETE",
                "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                "calls": [],
                "verification": construction_proof,
                "completion_basis": "COMPLETE_EMPTY_MUTATION_TRACE",
            }

    searches = _tool_events(history, "api_search")
    if not searches:
        calls = [
            {"tool": "api_search", "arguments": {"query": q, "top_k": 5}}
            for q in discovery_queries(prompt, max_queries=max_parallel_calls)
        ]
        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS" if calls else "NEEDS_POLICY_EXTENSION",
            "phase": "DISCOVER_ENDPOINTS",
            "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
            "calls": calls,
        }

    search_payloads = [_payload(row) for row in searches]
    endpoint_rows = endpoint_rows_from_search_payloads(search_payloads)
    endpoint_by_id = {
        str(row.get("id") or row.get("name") or ""): row
        for row in endpoint_rows
    }
    plan = plan_goal_over_tool_schemas(prompt, endpoint_rows)
    contract = plan.get("contract") or contract
    observations = _all_fetch_results(history)

    if plan.get("status") == "NO_POSITIVE_ACTION_REQUIRED":
        verification_ids = list(plan.get("verification_endpoint_ids") or [])
        if not verification_ids:
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "VERIFY_CONSTRAINTS",
                "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                "calls": [],
                "reason": "NO_INDEPENDENT_CONSTRAINT_VERIFICATION_READ",
            }
        semantic = "GENERIC_CONSTRAINT_VERIFY::" + _plan_token(
            [],
            plan.get("contract"),
        )
        state = _semantic_state(history, semantic)
        if state == "MISSING":
            calls = _bound_get_calls(
                goal=prompt,
                endpoint_ids=verification_ids,
                endpoint_by_id=endpoint_by_id,
                observations=observations,
                max_calls=max_parallel_calls,
            )
            if not calls:
                return {
                    "schema": SCHEMA,
                    "status": "NEEDS_POLICY_EXTENSION",
                    "phase": "VERIFY_CONSTRAINTS",
                    "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                    "calls": [],
                    "reason": "CONSTRAINT_VERIFICATION_READ_UNGROUNDABLE",
                }
            return {
                "schema": SCHEMA,
                "status": "CALL_TOOLS",
                "phase": "VERIFY_CONSTRAINTS",
                "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                "semantic": semantic,
                "calls": calls,
            }
        if state == "ERROR":
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "VERIFY_CONSTRAINTS",
                "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                "calls": [],
                "reason": "CONSTRAINT_VERIFICATION_TOOL_ERROR",
            }
        if state == "PENDING":
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "VERIFY_CONSTRAINTS",
                "calls": [],
                "reason": "CONSTRAINT_VERIFICATION_RESULT_PENDING",
            }
        verification_observations = _semantic_results(history, semantic) or []
        verification = verify_goal_state(
            goal=prompt,
            context_observations=verification_observations,
            verification_observations=verification_observations,
            execution_trace=[],
            execution_trace_complete=True,
        )
        return {
            "schema": SCHEMA,
            "status": "DONE_VERIFIED" if verification.get("pass") else "NEEDS_POLICY_EXTENSION",
            "phase": "COMPLETE" if verification.get("pass") else "VERIFY_CONSTRAINTS",
            "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
            "calls": [],
            "verification": verification,
            **({} if verification.get("pass") else {
                "reason": "GENERIC_CONSTRAINT_STATE_UNVERIFIED"
            }),
        }

    if plan.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "NEEDS_POLICY_EXTENSION",
            "phase": "PLAN",
            "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
            "calls": [],
            "reason": str(plan.get("reason") or plan.get("status") or "GENERIC_PLAN_UNRESOLVED"),
            "generic_plan": plan.get("plan") or [],
        }

    # Execute exactly one causal plan step per turn. A step advances only after
    # its concrete tool result is present and error-free.
    for step in plan.get("steps") or []:
        capability_id = str(step.get("capability_id") or "")
        if not capability_id:
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "PLAN",
                "calls": [],
                "reason": "GENERIC_PLAN_STEP_MISSING_CAPABILITY_ID",
            }
        semantic = "GENERIC_TOOL_EFFECT::" + capability_id
        state = _semantic_state(history, semantic)
        if state == "SUCCESS":
            continue
        if state == "ERROR":
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "REPLAN",
                "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                "calls": [],
                "reason": "GENERIC_PLAN_STEP_TOOL_ERROR",
                "failed_capability_id": capability_id,
                "failed_endpoint_id": step.get("endpoint_id"),
            }
        if state == "PENDING":
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "EXECUTE",
                "calls": [],
                "reason": "GENERIC_PLAN_STEP_RESULT_PENDING",
                "pending_capability_id": capability_id,
            }

        role = str(step.get("role") or "")
        if role == "mutation":
            guard = mutation_step_guard(step=step, contract=contract)
            if guard.get("pass") is not True:
                return {
                    "schema": SCHEMA,
                    "status": "NEEDS_POLICY_EXTENSION",
                    "phase": "CONSTRAINT_GUARD",
                    "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                    "calls": [],
                    "reason": str(guard.get("reason") or guard.get("status") or "FORBIDDEN_ACTION_CONFLICT"),
                    "constraint_guard": guard,
                    "blocked_capability_id": capability_id,
                }

        endpoint_id = str(step.get("endpoint_id") or "")
        endpoint = endpoint_by_id.get(endpoint_id)
        if endpoint is None:
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "EXECUTE",
                "calls": [],
                "reason": "GENERIC_PLAN_ENDPOINT_MISSING",
                "endpoint_id": endpoint_id,
            }

        bound = bind_endpoint_call(
            goal=prompt,
            endpoint=endpoint,
            observations=observations,
        )
        if bound.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "REPLAN",
                "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                "calls": [],
                "reason": "GENERIC_PLAN_STEP_BINDING_FAILED",
                "capability_id": capability_id,
                "endpoint_id": endpoint_id,
                "binding": bound,
            }

        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS",
            "phase": "OBSERVE_STATE" if role == "observation" else "MUTATE",
            "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
            "binder_mode": "GENERIC_SCHEMA_DRIVEN_ARGUMENT_BINDER",
            "semantic": semantic,
            "generic_capability_id": capability_id,
            "generic_endpoint_id": endpoint_id,
            "calls": [{
                "tool": "api_fetch",
                "arguments": dict(bound["arguments"]),
            }],
        }

    # All causal plan steps succeeded. Read state independently before credit.
    mutation_steps = [
        step for step in (plan.get("steps") or [])
        if step.get("role") == "mutation"
    ]
    if not mutation_steps:
        execution_trace = _executed_mutation_trace(plan, history)
        verification = verify_goal_state(
            goal=prompt,
            context_observations=observations,
            verification_observations=observations,
            execution_trace=execution_trace,
            execution_trace_complete=True,
        )
        return {
            "schema": SCHEMA,
            "status": "DONE_VERIFIED" if verification.get("pass") else "NEEDS_POLICY_EXTENSION",
            "phase": "COMPLETE" if verification.get("pass") else "VERIFY_STATE",
            "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
            "calls": [],
            "verification": verification,
            **({} if verification.get("pass") else {
                "reason": "GENERIC_OBSERVATION_GOAL_UNVERIFIED"
            }),
        }

    verify_semantic = "GENERIC_VERIFY::" + _plan_token(
        plan.get("plan") or [],
        plan.get("contract"),
    )
    verify_state = _semantic_state(history, verify_semantic)
    if verify_state == "MISSING":
        calls = _bound_get_calls(
            goal=prompt,
            endpoint_ids=list(plan.get("verification_endpoint_ids") or []),
            endpoint_by_id=endpoint_by_id,
            observations=observations,
            max_calls=max_parallel_calls,
        )
        if not calls:
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "VERIFY_STATE",
                "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
                "calls": [],
                "reason": "NO_GROUNDED_INDEPENDENT_VERIFICATION_READ",
            }
        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS",
            "phase": "VERIFY_STATE",
            "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
            "semantic": verify_semantic,
            "calls": calls,
        }
    if verify_state == "ERROR":
        return {
            "schema": SCHEMA,
            "status": "NEEDS_POLICY_EXTENSION",
            "phase": "VERIFY_STATE",
            "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
            "calls": [],
            "reason": "GENERIC_VERIFICATION_TOOL_ERROR",
        }
    if verify_state == "PENDING":
        return {
            "schema": SCHEMA,
            "status": "NEEDS_POLICY_EXTENSION",
            "phase": "VERIFY_STATE",
            "calls": [],
            "reason": "GENERIC_VERIFICATION_RESULT_PENDING",
        }

    context_observations = _fetch_results_before_semantic(
        history,
        verify_semantic,
    )
    verification_observations = _semantic_results(
        history,
        verify_semantic,
    ) or []
    execution_trace = _executed_mutation_trace(plan, history)
    verification = verify_goal_state(
        goal=prompt,
        context_observations=context_observations,
        verification_observations=verification_observations,
        execution_trace=execution_trace,
        execution_trace_complete=True,
    )
    return {
        "schema": SCHEMA,
        "status": "DONE_VERIFIED" if verification.get("pass") else "NEEDS_POLICY_EXTENSION",
        "phase": "COMPLETE" if verification.get("pass") else "VERIFY_STATE",
        "planner_mode": "GENERIC_FIELD_LEVEL_WORKFLOW_V3",
        "calls": [],
        "verification": verification,
        **({} if verification.get("pass") else {
            "reason": "GENERIC_POST_ACTION_STATE_UNVERIFIED"
        }),
    }
