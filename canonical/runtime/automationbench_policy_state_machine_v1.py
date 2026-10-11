"""Deterministic AutomationBench policy state machine V1.

This is the owned execution spine that composes:
  prompt -> api_search -> safe GET observations -> source screening ->
  typed grounded mutation -> verification/replan signal.

It intentionally has no external model cognition and consumes no hidden benchmark
assertions. Unsupported mutation semantics fail closed as NEEDS_POLICY_EXTENSION.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.automationbench_mutation_compiler_v1 import (
    compile_asana_add_to_section,
    compile_asana_create_task,
    compile_salesforce_mark_won,
    validate_nonnegative_action,
)
from canonical.runtime.automationbench_owned_policy_kernel_v1 import (
    observation_plan,
    rank_source_records,
    search_queries,
)
from canonical.runtime.generic_goal_tool_effect_planner_v1 import (
    endpoint_rows_from_search_payloads,
    plan_goal_over_tool_schemas,
)
from canonical.runtime.generic_tool_argument_binder_v1 import bind_endpoint_call
from canonical.runtime.generic_goal_state_verifier_v1 import verify_goal_state

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_POLICY_STATE_MACHINE_V1"


def _tool_events(history: Sequence[Mapping[str, Any]], name: str) -> list[Mapping[str, Any]]:
    return [
        x for x in history
        if str(x.get("kind") or x.get("type") or "") == "tool_result"
        and str(x.get("name") or x.get("tool") or "") == name
    ]


def _payload(event: Mapping[str, Any]) -> Any:
    value = event.get("content", event.get("result"))
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return value


def _flatten_records(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            d = dict(x)
            if any(str(k).lower() in {"id","gid","name","subject","title","body","body_plain","text"} for k in d):
                out.append(d)
            for v in d.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(value)
    return out


def _semantic_done(history: Sequence[Mapping[str, Any]], semantic: str) -> bool:
    for x in history:
        if not isinstance(x, Mapping):
            continue
        if x.get("semantic") == semantic:
            return True
        metadata = x.get("metadata")
        if isinstance(metadata, Mapping) and metadata.get("project_brain/automationbench_semantic") == semantic:
            return True
    return False


def _plan_token(plan: Sequence[Any]) -> str:
    raw = json.dumps(list(plan), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def _tool_results_after_semantic(
    history: Sequence[Mapping[str, Any]],
    semantic: str,
) -> list[Any]:
    seen = False
    out: list[Any] = []
    for row in history:
        if not isinstance(row, Mapping):
            continue
        metadata = row.get("metadata")
        if (
            isinstance(metadata, Mapping)
            and metadata.get("project_brain/automationbench_semantic") == semantic
        ):
            seen = True
            continue
        if (
            seen
            and str(row.get("kind") or row.get("type") or "") == "tool_result"
            and str(row.get("name") or row.get("tool") or "") == "api_fetch"
        ):
            out.append(_payload(row))
    return out


def _assistant_receipts(
    history: Sequence[Mapping[str, Any]],
    metadata_key: str,
) -> list[Any]:
    out: list[Any] = []
    for row in history:
        if not isinstance(row, Mapping):
            continue
        metadata = row.get("metadata")
        if not isinstance(metadata, Mapping):
            continue
        value = metadata.get(metadata_key)
        if isinstance(value, list):
            out.extend(value)
        elif value is not None:
            out.append(value)
    return out


def _pre_generic_action_observations(
    history: Sequence[Mapping[str, Any]],
) -> list[Any]:
    out: list[Any] = []
    for row in history:
        if not isinstance(row, Mapping):
            continue
        metadata = row.get("metadata")
        if isinstance(metadata, Mapping):
            semantic = str(metadata.get("project_brain/automationbench_semantic") or "")
            if semantic.startswith("GENERIC_TOOL_EFFECT::"):
                break
        if (
            str(row.get("kind") or row.get("type") or "") == "tool_result"
            and str(row.get("name") or row.get("tool") or "") == "api_fetch"
        ):
            out.append(_payload(row))
    return out


def next_policy_action(
    *,
    prompt: str,
    history: Sequence[Mapping[str, Any]],
    max_parallel_calls: int = 6,
) -> dict[str, Any]:
    """Return the next deterministic policy action bundle."""
    searches = _tool_events(history, "api_search")
    fetches = _tool_events(history, "api_fetch")

    if not searches:
        calls = [
            {"tool":"api_search","arguments":{"query":q,"top_k":5}}
            for q in search_queries(prompt, max_queries=max_parallel_calls)
        ]
        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS" if calls else "NEEDS_POLICY_EXTENSION",
            "phase": "DISCOVER_ENDPOINTS",
            "calls": calls,
        }

    search_payloads = [_payload(x) for x in searches]
    endpoint_rows = endpoint_rows_from_search_payloads(search_payloads)
    generic_plan = plan_goal_over_tool_schemas(prompt, endpoint_rows)

    if generic_plan.get("status") == "NO_POSITIVE_ACTION_REQUIRED":
        return {
            "schema": SCHEMA,
            "status": "DONE_VERIFIED",
            "phase": "NO_ACTION_REQUIRED",
            "calls": [],
            "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
            "verification": "NO_POSITIVE_ACTION_TARGETS",
        }

    if not fetches:
        selected_ids = set(generic_plan.get("observation_endpoint_ids") or [])
        selected_rows = [
            row for row in endpoint_rows
            if str(row.get("id") or row.get("name") or "") in selected_ids
        ]
        calls = observation_plan(
            prompt,
            [{"results": selected_rows}] if selected_rows else search_payloads,
            max_calls=max_parallel_calls,
        )
        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS" if calls else "NEEDS_POLICY_EXTENSION",
            "phase": "OBSERVE_STATE",
            "planner_mode": (
                "GENERIC_GOAL_TOOL_EFFECT_PLANNER"
                if selected_rows
                else "LEGACY_OBSERVATION_FALLBACK_ZERO_CREDIT"
            ),
            "generic_plan_status": generic_plan.get("status"),
            "generic_plan": generic_plan.get("plan") or [],
            "calls": [{"tool":x["tool"],"arguments":x["arguments"]} for x in calls],
        }

    observations = [_payload(x) for x in fetches]

    # Primary mutation route: generic planner chooses the endpoint and the generic
    # schema binder grounds its concrete arguments from goal + observed state.
    endpoint_by_id = {
        str(row.get("id") or row.get("name") or ""): row
        for row in endpoint_rows
    }
    generic_bind_failures: list[str] = []
    generic_mutation_steps = [
        step for step in (generic_plan.get("steps") or [])
        if step.get("role") == "mutation"
    ]
    generic_progress = any(
        _semantic_done(
            history,
            "GENERIC_TOOL_EFFECT::" + str(step.get("capability_id") or ""),
        )
        for step in generic_mutation_steps
        if step.get("capability_id")
    )
    for step in generic_mutation_steps:
        if step.get("role") != "mutation":
            continue
        capability_id = str(step.get("capability_id") or "")
        semantic = "GENERIC_TOOL_EFFECT::" + capability_id
        if not capability_id or _semantic_done(history, semantic):
            continue
        endpoint_id = str(step.get("endpoint_id") or "")
        endpoint = endpoint_by_id.get(endpoint_id)
        if endpoint is None:
            generic_bind_failures.append(capability_id + ":ENDPOINT_MISSING")
            break
        bound = bind_endpoint_call(
            goal=prompt,
            endpoint=endpoint,
            observations=observations,
        )
        if bound.get("pass") is True:
            return {
                "schema": SCHEMA,
                "status": "CALL_TOOLS",
                "phase": "MUTATE",
                "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
                "binder_mode": "GENERIC_SCHEMA_DRIVEN_ARGUMENT_BINDER",
                "semantic": semantic,
                "generic_capability_id": capability_id,
                "generic_endpoint_id": endpoint_id,
                "generic_execution_receipt": {
                    "action_class": str(step.get("action_class") or ""),
                    "capability_id": capability_id,
                    "endpoint_id": endpoint_id,
                    "bindings": dict(bound.get("bindings") or {}),
                    "arguments": dict(bound.get("arguments") or {}),
                },
                "calls": [{"tool":"api_fetch","arguments":bound["arguments"]}],
            }
        generic_bind_failures.append(
            capability_id + ":" + str(bound.get("reason") or bound.get("status"))
        )
        # Plan order is causal. Do not skip an ungrounded earlier mutation.
        break

    all_generic_mutations_done = bool(generic_mutation_steps) and all(
        _semantic_done(
            history,
            "GENERIC_TOOL_EFFECT::" + str(step.get("capability_id") or ""),
        )
        for step in generic_mutation_steps
        if step.get("capability_id")
    )

    if not generic_mutation_steps and generic_plan.get("pass") is True:
        verification = verify_goal_state(
            goal=prompt,
            context_observations=observations,
            verification_observations=observations,
        )
        if verification.get("pass") is True:
            return {
                "schema": SCHEMA,
                "status": "DONE_VERIFIED",
                "phase": "COMPLETE",
                "calls": [],
                "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
                "verification": verification,
            }

    if all_generic_mutations_done:
        verify_semantic = "GENERIC_VERIFY::" + _plan_token(generic_plan.get("plan") or [])
        if not _semantic_done(history, verify_semantic):
            selected_ids = set(generic_plan.get("observation_endpoint_ids") or [])
            verification_calls: list[dict[str, Any]] = []
            verification_receipts: list[dict[str, Any]] = []
            seen_calls: set[str] = set()
            for endpoint_id in selected_ids:
                endpoint = endpoint_by_id.get(endpoint_id)
                if endpoint is None:
                    continue
                bound = bind_endpoint_call(
                    goal=prompt,
                    endpoint=endpoint,
                    observations=observations,
                )
                if bound.get("pass") is not True:
                    continue
                args = bound.get("arguments") or {}
                if str(args.get("method") or "").upper() != "GET":
                    continue
                signature = json.dumps(args, sort_keys=True)
                if signature in seen_calls:
                    continue
                seen_calls.add(signature)
                verification_calls.append({"tool":"api_fetch","arguments":args})
                verification_receipts.append({
                    "endpoint_id": endpoint_id,
                    "method": "GET",
                    "bindings": dict(bound.get("bindings") or {}),
                    "arguments": dict(args),
                })
                if len(verification_calls) >= max_parallel_calls:
                    break
            if verification_calls:
                return {
                    "schema": SCHEMA,
                    "status": "CALL_TOOLS",
                    "phase": "VERIFY_STATE",
                    "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
                    "semantic": verify_semantic,
                    "generic_verification_receipts": verification_receipts,
                    "calls": verification_calls,
                }
            return {
                "schema": SCHEMA,
                "status": "NEEDS_POLICY_EXTENSION",
                "phase": "VERIFY_STATE",
                "calls": [],
                "reason": "NO_GROUNDED_INDEPENDENT_VERIFICATION_READ",
                "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
            }

        verification_observations = _tool_results_after_semantic(
            history,
            verify_semantic,
        )
        execution_receipts = _assistant_receipts(
            history,
            "project_brain/generic_execution_receipt",
        )
        verification_receipts = _assistant_receipts(
            history,
            "project_brain/generic_verification_receipts",
        )
        verification = verify_goal_state(
            goal=prompt,
            context_observations=_pre_generic_action_observations(history),
            verification_observations=verification_observations,
            execution_receipts=execution_receipts,
            verification_receipts=verification_receipts,
        )
        if verification.get("pass") is True:
            return {
                "schema": SCHEMA,
                "status": "DONE_VERIFIED",
                "phase": "COMPLETE",
                "calls": [],
                "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
                "verification": verification,
            }
        return {
            "schema": SCHEMA,
            "status": "NEEDS_POLICY_EXTENSION",
            "phase": "VERIFY_STATE",
            "calls": [],
            "reason": "GENERIC_POST_ACTION_STATE_UNVERIFIED",
            "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
            "verification": verification,
        }

    if generic_progress:
        return {
            "schema": SCHEMA,
            "status": "NEEDS_POLICY_EXTENSION",
            "phase": "MUTATION_OR_VERIFICATION",
            "calls": [],
            "reason": "GENERIC_TRAJECTORY_STARTED_BUT_NEXT_GENERIC_STEP_COULD_NOT_BE_GROUNDED",
            "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER",
            "generic_bind_failures": generic_bind_failures,
        }

    # Transitional typed binders below are argument-binding scaffolding only.
    # Generic route choice lives in generic_goal_tool_effect_planner_v1.
    # These binders carry zero capability/ownership credit.

    # Typed compiler 1: Salesforce mark-won.
    action = compile_salesforce_mark_won(prompt, observations)
    if action is not None and validate_nonnegative_action(prompt, action):
        if not _semantic_done(history, str(action.get("semantic") or "")):
            return {
                "schema": SCHEMA,
                "status": "CALL_TOOLS",
                "phase": "MUTATE",
                "semantic": action["semantic"],
                "calls": [{"tool":action["tool"],"arguments":action["arguments"]}],
            }

    # Continue a created Asana task into the explicitly requested section.
    if _semantic_done(history, "ASANA_TASK_CREATE") and not _semantic_done(
        history, "ASANA_TASK_ADD_TO_SECTION"
    ):
        action = compile_asana_add_to_section(prompt, observations)
        if action is not None and validate_nonnegative_action(prompt, action):
            return {
                "schema": SCHEMA,
                "status": "CALL_TOOLS",
                "phase": "MUTATE",
                "semantic": action["semantic"],
                "calls": [{"tool": action["tool"], "arguments": action["arguments"]}],
            }

    # Typed compiler 2: create an Asana task from the best eligible source record.
    all_records: list[dict[str, Any]] = []
    for obs in observations:
        all_records.extend(_flatten_records(obs))
    ranked = rank_source_records(prompt, all_records, record_role="action_candidate")
    for record in ranked:
        action = compile_asana_create_task(prompt, record)
        if action is not None and validate_nonnegative_action(prompt, action):
            if not _semantic_done(history, str(action.get("semantic") or "")):
                return {
                    "schema": SCHEMA,
                    "status": "CALL_TOOLS",
                    "phase": "MUTATE",
                    "semantic": action["semantic"],
                    "calls": [{"tool":action["tool"],"arguments":action["arguments"]}],
                }

    return {
        "schema": SCHEMA,
        "status": "NEEDS_POLICY_EXTENSION",
        "phase": "MUTATION_OR_VERIFICATION",
        "calls": [],
        "reason": "NO_GROUNDED_GENERIC_EXECUTOR_OR_TRANSITIONAL_BINDER_MATCHED_CURRENT_OBSERVATIONS",
        "planner_mode": "GENERIC_GOAL_TOOL_EFFECT_PLANNER_WITH_ZERO_CREDIT_BINDER_FALLBACK",
        "generic_plan_status": generic_plan.get("status"),
        "generic_plan": generic_plan.get("plan") or [],
        "generic_mutation_endpoint_ids": generic_plan.get("mutation_endpoint_ids") or [],
        "generic_bind_failures": generic_bind_failures,
    }
