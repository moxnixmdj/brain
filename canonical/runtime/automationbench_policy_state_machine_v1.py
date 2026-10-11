"""Deterministic AutomationBench policy state machine V1.

This is the owned execution spine that composes:
  prompt -> api_search -> safe GET observations -> source screening ->
  typed grounded mutation -> verification/replan signal.

It intentionally has no external model cognition and consumes no hidden benchmark
assertions. Unsupported mutation semantics fail closed as NEEDS_POLICY_EXTENSION.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from canonical.runtime.automationbench_mutation_compiler_v1 import (
    compile_asana_add_to_section,
    compile_asana_create_task,
    compile_salesforce_mark_won,
    validate_nonnegative_action,
)
from canonical.runtime.automationbench_owned_policy_kernel_v1 import (
    rank_source_records,
)
from canonical.runtime.automationbench_multihop_observation_v1 import (
    call_fingerprint,
    discovery_search_queries,
    observation_expansion_plan,
)

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


def _called_read_fingerprints(history: Sequence[Mapping[str, Any]]) -> set[str]:
    out: set[str] = set()
    for item in history:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("kind") or "") != "tool_call":
            continue
        if str(item.get("name") or item.get("tool") or "") != "api_fetch":
            continue
        arguments = item.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                continue
        if not isinstance(arguments, Mapping):
            continue
        if str(arguments.get("method") or "").upper() != "GET":
            continue
        out.add(call_fingerprint("api_fetch", arguments))
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
            for q in discovery_search_queries(prompt, max_queries=max_parallel_calls)
        ]
        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS" if calls else "NEEDS_POLICY_EXTENSION",
            "phase": "DISCOVER_ENDPOINTS",
            "calls": calls,
        }

    search_payloads = [_payload(x) for x in searches]
    called_reads = _called_read_fingerprints(history)

    if not fetches:
        calls = observation_expansion_plan(
            prompt,
            search_payloads,
            already_called=called_reads,
            max_calls=max_parallel_calls,
        )
        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS" if calls else "NEEDS_POLICY_EXTENSION",
            "phase": "OBSERVE_STATE",
            "calls": [{"tool":x["tool"],"arguments":x["arguments"]} for x in calls],
        }

    observations = [_payload(x) for x in fetches]

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

    # No grounded write matched yet. Expand the read graph using IDs and
    # metadata learned from prior observations before declaring a policy gap.
    continuation_calls = observation_expansion_plan(
        prompt,
        search_payloads,
        observations=observations,
        already_called=called_reads,
        max_calls=max_parallel_calls,
    )
    if continuation_calls:
        return {
            "schema": SCHEMA,
            "status": "CALL_TOOLS",
            "phase": "CONTINUE_OBSERVATION",
            "calls": [
                {"tool": item["tool"], "arguments": item["arguments"]}
                for item in continuation_calls
            ],
        }

    return {
        "schema": SCHEMA,
        "status": "NEEDS_POLICY_EXTENSION",
        "phase": "MUTATION_OR_VERIFICATION",
        "calls": [],
        "reason": "NO_GROUNDED_TYPED_MUTATION_COMPILER_MATCHED_CURRENT_OBSERVATIONS",
    }
