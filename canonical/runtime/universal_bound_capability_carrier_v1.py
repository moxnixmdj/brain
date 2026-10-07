"""Verified carrier for deterministic Astra bound-capability subplans.

This carrier is intentionally narrow:
- input is one native capability_planner problem;
- plan_actions deterministically chooses the minimum-cost declared route;
- every non-finish action must be invoke_capability;
- Astra's bound-capability runtime may invoke only an existing
  VERIFIED_BOUND_CAPABILITY at zero incremental spend;
- every action expectation is checked immediately;
- the full execution trace is independently rederived and checked by
  BOUND_CAPABILITY_EXECUTION_V1 before a proposal is returned.

The carrier does NOT assign semantic meaning to the outer solver's effects.
Universal Solver effect-semantics authentication remains a separate mandatory gate.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.capability_planner import plan_actions
from canonical.runtime.capability_execution_trace_capsule_v1 import (
    _resolve_result_refs,
)
from canonical.runtime.bound_capability_execution_verifier_v1 import (
    verify as verify_bound_execution,
)
from canonical.runtime import astra_runtime

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_BOUND_CAPABILITY_CARRIER_V1"


def execute(problem: Mapping[str, Any]) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    executed_nonfinish = 0
    try:
        if not isinstance(problem, Mapping):
            raise ValueError("BOUND_PROBLEM_NOT_OBJECT")
        planned = plan_actions(problem)
        actions = planned.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ValueError("BOUND_PLAN_ACTIONS_INVALID")

        for cycle, raw_action in enumerate(actions):
            if not isinstance(raw_action, Mapping):
                raise ValueError("BOUND_PLAN_ACTION_NOT_OBJECT:" + str(cycle))
            resolved = _resolve_result_refs(raw_action, trace)
            typ = str(resolved.get("type") or "").strip()

            if cycle == len(actions) - 1:
                if typ != "finish":
                    raise ValueError("BOUND_PLAN_FINAL_ACTION_NOT_FINISH")
                args = resolved.get("args")
                if not isinstance(args, Mapping):
                    raise ValueError("BOUND_FINISH_ARGS_INVALID")
                summary = str(args.get("summary") or "").strip()
                if not summary:
                    raise ValueError("BOUND_FINISH_SUMMARY_EMPTY")
                trace.append({
                    "cycle": cycle,
                    "plan": resolved,
                    "result": {"summary": summary},
                })
                continue

            if typ != "invoke_capability":
                raise ValueError(
                    "BOUND_CARRIER_ACTION_TYPE_NOT_ADMITTED:" + typ
                )
            args = resolved.get("args")
            if not isinstance(args, Mapping):
                raise ValueError("BOUND_INVOKE_ARGS_INVALID:" + str(cycle))

            result = astra_runtime._invoke_bound_capability(dict(args))
            executed_nonfinish += 1
            if not isinstance(result, Mapping):
                raise ValueError("BOUND_ACTION_RESULT_NOT_OBJECT:" + str(cycle))
            if result.get("error"):
                raise ValueError(
                    "BOUND_ACTION_RESULT_ERROR:"
                    + str(cycle)
                    + ":"
                    + str(result.get("error"))
                )
            if not astra_runtime._verify_action_expectation(resolved, result):
                raise ValueError(
                    "BOUND_ACTION_EXPECTATION_NOT_WITNESSED:" + str(cycle)
                )
            trace.append({
                "cycle": cycle,
                "plan": resolved,
                "result": dict(result),
            })

        execution = {"trace": trace}
        verdict = verify_bound_execution(
            {"problem": problem},
            {"execution": execution},
        )
        if verdict.get("pass") is not True:
            raise ValueError(
                "BOUND_EXECUTION_INDEPENDENT_VERIFICATION_FAILED:"
                + str(verdict.get("reason") or verdict.get("status"))
            )
        return {
            "schema": SCHEMA,
            "status": "PASS__BOUND_SUBPLAN_EXECUTED_AND_INDEPENDENTLY_VERIFIED",
            "pass": True,
            "proposal": {"execution": execution},
            "execution": execution,
            "execution_verification": verdict,
            "effect_may_have_occurred": bool(executed_nonfinish),
            "executed_nonfinish_action_count": executed_nonfinish,
            "terminal_authority": False,
            "semantic_effect_authority": False,
            "incremental_spend_usd": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "partial_trace": trace,
            "effect_may_have_occurred": bool(executed_nonfinish),
            "executed_nonfinish_action_count": executed_nonfinish,
            "terminal_authority": False,
            "semantic_effect_authority": False,
        }
