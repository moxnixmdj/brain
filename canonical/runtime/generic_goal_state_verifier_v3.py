"""Generic goal-state verifier V3 with complete execution-trace constraints.

V3 preserves V2 post-state verification and adds a second evidence surface for
forbidden actions: the complete executed-mutation trace.

- Existing strong state proofs remain authoritative.
- A conflicting executed mutation always fails a forbidden constraint.
- Previously unsupported forbidden action classes may pass only when the trace
  is complete and contains no potentially conflicting executed mutation.
- Incomplete traces never relax V2 fail-closed behavior.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.generic_goal_constraint_guard_v1 import verify_forbidden_execution_trace
from canonical.runtime.generic_goal_state_verifier_v2 import verify_goal_state as verify_goal_state_v2
from canonical.runtime.generic_goal_tool_effect_planner_v1 import compile_goal_contract

SCHEMA = "PROJECT_BRAIN_GENERIC_GOAL_STATE_VERIFIER_V3"


def verify_goal_state(
    *,
    goal: str,
    context_observations: Sequence[Any],
    verification_observations: Sequence[Any],
    execution_trace: Sequence[Mapping[str, Any]] = (),
    execution_trace_complete: bool = False,
) -> dict[str, Any]:
    base = verify_goal_state_v2(
        goal=goal,
        context_observations=context_observations,
        verification_observations=verification_observations,
    )
    contract = compile_goal_contract(goal)
    forbidden = [x for x in (contract.get("intents") or []) if bool(x.get("forbidden"))]
    if not forbidden:
        return {**base, "schema": SCHEMA}

    trace = verify_forbidden_execution_trace(
        contract=contract,
        execution_trace=execution_trace,
        trace_complete=execution_trace_complete,
    )
    trace_by_id = {
        str(x.get("intent_id") or ""): x
        for x in (trace.get("constraint_results") or [])
    }

    merged: list[dict[str, Any]] = []
    for row0 in base.get("constraint_results") or []:
        row = dict(row0)
        tid = str(row.get("intent_id") or "")
        traced = trace_by_id.get(tid)

        if (
            execution_trace_complete
            and isinstance(traced, Mapping)
            and traced.get("verified") is False
            and traced.get("reason") == "CONFLICTING_MUTATION_EXECUTED"
        ):
            row.update(dict(traced))
            merged.append(row)
            continue

        reason = str(row.get("reason") or "")
        if (
            row.get("verified") is not True
            and reason.startswith("FORBIDDEN_ACTION_VERIFICATION_UNSUPPORTED:")
            and isinstance(traced, Mapping)
            and traced.get("verified") is True
        ):
            row.update(dict(traced))
            row["verification_basis"] = "COMPLETE_EXECUTION_TRACE_NONEXECUTION"

        merged.append(row)

    positive_ok = all(x.get("verified") is True for x in (base.get("intent_results") or []))
    constraints_ok = all(x.get("verified") is True for x in merged)
    ok = positive_ok and constraints_ok

    return {
        **base,
        "schema": SCHEMA,
        "pass": ok,
        "status": "VERIFIED" if ok else "UNRESOLVED",
        "reason": None if ok else "ONE_OR_MORE_GOAL_OR_CONSTRAINT_PREDICATES_UNVERIFIED",
        "constraint_results": merged,
        "execution_trace_complete": execution_trace_complete,
        "execution_trace_mutation_count": len(execution_trace),
    }
