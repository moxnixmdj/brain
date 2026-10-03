#!/usr/bin/env python3
"""Root2 inference adapter for the already-verified Terminal-Bench-Science Brain route.

This module does not read benchmark cases at import/preflight time. It only bridges
an owner/public harness request carrying an already-instantiated Harbor environment
into the content-addressed Brain-owned science controller. The controller retains
command admissibility, verification, requirement-state, and finish authority.
"""
from __future__ import annotations

import asyncio
from typing import Any, Mapping

from canonical.runtime.harbor_science_agent_v1 import run_science_goal

SCHEMA = "PROJECT_BRAIN_ROOT2_TB_SCIENCE_INFERENCE_ADAPTER_V1"
BENCHMARK_ID = "TERMINAL_BENCH_SCIENCE_0_1"
MAX_CYCLES = 8


class TBScienceAdapterBlocked(RuntimeError):
    pass


def _nonempty(value: Any, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise TBScienceAdapterBlocked(code)
    return text


def _task_goal(payload: Any) -> tuple[str, int]:
    if not isinstance(payload, Mapping):
        raise TBScienceAdapterBlocked("TASK_PAYLOAD_MAPPING_REQUIRED")
    keys = [k for k in ("instruction", "goal") if str(payload.get(k) or "").strip()]
    if len(keys) != 1:
        raise TBScienceAdapterBlocked("EXACTLY_ONE_TASK_GOAL_FIELD_REQUIRED")
    goal = _nonempty(payload[keys[0]], "TASK_GOAL_REQUIRED")
    raw_cycles = payload.get("max_cycles", MAX_CYCLES)
    if not isinstance(raw_cycles, int) or isinstance(raw_cycles, bool):
        raise TBScienceAdapterBlocked("MAX_CYCLES_INTEGER_REQUIRED")
    if not 1 <= raw_cycles <= MAX_CYCLES:
        raise TBScienceAdapterBlocked("MAX_CYCLES_OUT_OF_RANGE")
    return goal, raw_cycles


def _environment(request: Mapping[str, Any]) -> Any:
    env = request.get("environment")
    if env is None or not callable(getattr(env, "exec", None)):
        raise TBScienceAdapterBlocked("LIVE_HARBOR_ENVIRONMENT_REQUIRED")
    return env


def _validate_tools(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise TBScienceAdapterBlocked("ALLOWED_TOOLS_LIST_REQUIRED")
    tools = [str(x).strip() for x in value]
    if any(not x for x in tools):
        raise TBScienceAdapterBlocked("ALLOWED_TOOL_INVALID")
    allowed = {"environment_exec", "finish"}
    if not set(tools).issubset(allowed):
        raise TBScienceAdapterBlocked("UNSUPPORTED_TOOL_DECLARATION")
    if "environment_exec" not in tools:
        raise TBScienceAdapterBlocked("ENVIRONMENT_EXEC_REQUIRED")
    return tools


def _run(coro: Any) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        result = asyncio.run(coro)
        if not isinstance(result, dict):
            raise TBScienceAdapterBlocked("CONTROLLER_RESULT_OBJECT_REQUIRED")
        return result
    raise TBScienceAdapterBlocked("SYNC_ENTRYPOINT_REQUIRES_NO_RUNNING_EVENT_LOOP")


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise TBScienceAdapterBlocked("REQUEST_MAPPING_REQUIRED")
    if _nonempty(request.get("benchmark_id"), "BENCHMARK_ID_REQUIRED") != BENCHMARK_ID:
        raise TBScienceAdapterBlocked("BENCHMARK_ID_MISMATCH")

    task_id = _nonempty(request.get("task_id"), "TASK_ID_REQUIRED")
    brain_commit = _nonempty(request.get("brain_commit"), "BRAIN_COMMIT_REQUIRED")
    configuration_hash = _nonempty(request.get("configuration_hash"), "CONFIGURATION_HASH_REQUIRED")
    tool_policy_hash = _nonempty(request.get("tool_policy_hash"), "TOOL_POLICY_HASH_REQUIRED")
    tools = _validate_tools(request.get("allowed_tools"))
    goal, max_cycles = _task_goal(request.get("task_payload"))
    env = _environment(request)

    output_contract = request.get("output_contract")
    if not isinstance(output_contract, Mapping):
        raise TBScienceAdapterBlocked("OUTPUT_CONTRACT_MAPPING_REQUIRED")

    result = _run(run_science_goal(goal, env, max_cycles=max_cycles))
    status = str(result.get("status") or "")
    if status not in {"FINISHED", "BLOCKED_MAX_CYCLES_NO_BRAIN_AUTHORIZED_FINISH"}:
        raise TBScienceAdapterBlocked("UNEXPECTED_CONTROLLER_STATUS:" + status)

    return {
        "schema": SCHEMA,
        "task_id": task_id,
        "status": status,
        "answer": str(result.get("summary") or ""),
        "artifacts": [],
        "tool_trace": list(result.get("trace") or []),
        "provenance": {
            "brain_commit": brain_commit,
            "configuration_hash": configuration_hash,
            "tool_policy_hash": tool_policy_hash,
            "benchmark_id": BENCHMARK_ID,
            "controller": "canonical/runtime/harbor_science_agent_v1.py",
            "controller_mode": result.get("controller_mode"),
            "model_dependency_count": 1,
            "model_role": "GENERAL_COGNITION_SUBSTRATE",
            "model_has_terminal_authority": False,
            "allowed_tools": tools,
        },
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
