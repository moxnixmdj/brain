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
    observation_plan,
    rank_source_records,
    search_queries,
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

    if not fetches:
        payloads = [_payload(x) for x in searches]
        calls = observation_plan(prompt, payloads, max_calls=max_parallel_calls)
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
        "reason": "NO_GROUNDED_TYPED_MUTATION_COMPILER_MATCHED_CURRENT_OBSERVATIONS",
    }
