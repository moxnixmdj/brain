"""Deterministic verifier for concrete capability-plan execution traces.

The executor is untrusted. This verifier recomputes the minimum-cost capability
plan from the trusted problem, recomputes the exact planned actions, and then uses
capability_execution_trace_capsule_v1 to prove that the supplied execution trace:

- executed exactly that plan,
- witnessed every capability expectation,
- satisfied every prerequisite from an earlier witness or initial fact,
- used only declared backward result edges,
- produced every target effect,
- compiled to a valid content-addressed composition capsule.

It does not execute any tool and grants no effect semantics beyond the supplied
capability problem. A universal solver must still authenticate the meaning of
the target/provided effects separately.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.capability_planner import plan_actions
from canonical.runtime.capability_execution_trace_capsule_v1 import verify_and_compile

SCHEMA = "PROJECT_BRAIN_BOUND_CAPABILITY_EXECUTION_VERIFIER_V1"


def verify(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(payload, Mapping) or set(payload) != {"problem"}:
            raise ValueError("PAYLOAD_MUST_CONTAIN_EXACTLY_PROBLEM")
        problem = payload.get("problem")
        if not isinstance(problem, Mapping):
            raise ValueError("PROBLEM_NOT_OBJECT")
        if not isinstance(proposal, Mapping) or set(proposal) != {"execution"}:
            raise ValueError("PROPOSAL_MUST_CONTAIN_EXACTLY_EXECUTION")
        execution = proposal.get("execution")
        if not isinstance(execution, Mapping):
            raise ValueError("EXECUTION_NOT_OBJECT")

        planned = plan_actions(problem)
        verdict = verify_and_compile(problem, planned, execution)
        ok = verdict.get("status") == "PASS"
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "VERIFIED" if ok else "FALSIFIED",
            "reason": None if ok else str(verdict.get("reason") or "TRACE_VERIFICATION_FAILED"),
            "verified_output": {
                "capsule_head_hash": verdict.get("capsule_head_hash"),
                "capsule_record_count": verdict.get("capsule_record_count"),
                "plan_capability_count": verdict.get("plan_capability_count"),
                "all_target_effects_have_witnesses": verdict.get("all_target_effects_have_witnesses"),
            } if ok else None,
            "detail": verdict,
            "execution_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "execution_authority": False,
            "terminal_authority": False,
        }
