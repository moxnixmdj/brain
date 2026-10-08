"""Total next-control-action normal form for R2.

This module does not mint semantic truth, policy adequacy, execution authority,
or goal acceptance. It converts every R2 outcome into exactly one structural
next control action so an unresolved open-world case is never an ambiguous
dead end.

The original task remains open until the existing independent goal-satisfaction
authority says it is closed.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_TOTAL_NEXT_CONTROL_ACTION_V1"


def _base(kind: str, result: Mapping[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    source = result if isinstance(result, Mapping) else {}
    return {
        "schema": SCHEMA,
        "kind": kind,
        "classification_complete": True,
        "source_status": source.get("status"),
        "source_fixed_point_status": source.get("r2_fixed_point_status"),
        "required_edge": (
            source.get("next_required_edge")
            or source.get("next_required_effect")
        ),
        "domain_goal_satisfaction_verified": (
            source.get("actual_goal_satisfaction_verified") is True
        ),
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _edge(result: Mapping[str, Any]) -> str:
    return str(
        result.get("next_required_edge")
        or result.get("next_required_effect")
        or ""
    ).strip()


def compile_next_action(result: Any) -> dict[str, Any]:
    """Return one and only one structural next action for any R2 outcome."""
    if not isinstance(result, Mapping):
        return _base(
            "STOP_FAIL_CLOSED",
            reason="R2_RESULT_NOT_OBJECT",
        )

    status = str(result.get("status") or "").strip()
    fixed_status = str(result.get("r2_fixed_point_status") or "").strip()

    # A task-level success is recognized only when the existing acceptance path
    # independently verified actual goal satisfaction. A plain pass bit is not
    # enough.
    if (
        result.get("pass") is True
        and result.get("actual_goal_satisfaction_verified") is True
    ):
        # This function runs *after* the verified domain action/result already
        # satisfied the goal. The next control action must therefore complete
        # the task, never replay an effectful action. Preserve the verified
        # realization only as a receipt for downstream consumers.
        receipt = (
            result.get("realization")
            if result.get("realization") is not None
            else result.get("action")
        )
        if receipt is None and isinstance(result.get("raw_result"), Mapping):
            receipt = result.get("raw_result")
        return _base(
            "COMPLETE_VERIFIED_GOAL",
            result,
            verified_result_available=receipt is not None,
            verified_result=deepcopy(receipt),
            execute_domain_action=False,
            requires_reverification=False,
        )

    if result.get("pass") is True:
        return _base(
            "ACQUIRE_GOAL_SATISFACTION_PROOF",
            result,
            reason="PASS_WITHOUT_INDEPENDENT_ACTUAL_GOAL_SATISFACTION",
            request=deepcopy(result.get("goal_satisfaction_binding")),
            requires_reverification=True,
        )

    if status == "FAIL_CLOSED" or fixed_status == "FAIL_CLOSED":
        return _base(
            "STOP_FAIL_CLOSED",
            result,
            reason=str(result.get("reason") or "R2_FAIL_CLOSED"),
            requires_reverification=False,
        )

    information = result.get("next_information_request")
    if isinstance(information, Mapping):
        return _base(
            "ACQUIRE_DECISION_RELEVANT_INFORMATION",
            result,
            request=deepcopy(dict(information)),
            requires_reverification=True,
        )

    observation = result.get("next_observation_request")
    if isinstance(observation, Mapping):
        return _base(
            "ACQUIRE_DECISION_RELEVANT_INFORMATION",
            result,
            request=deepcopy(dict(observation)),
            requires_reverification=True,
        )

    policy = result.get("next_policy_request")
    if isinstance(policy, Mapping):
        return _base(
            "ACQUIRE_OR_PROVE_POLICY_ADEQUACY",
            result,
            request=deepcopy(dict(policy)),
            requires_reverification=True,
        )

    edge = _edge(result)
    upper = edge.upper()
    if edge:
        if "GOAL_SATISFACTION" in upper or "ACCEPTANCE" in upper:
            kind = "ACQUIRE_GOAL_SATISFACTION_PROOF"
        elif "POLICY" in upper and ("ADEQUACY" in upper or "COVER" in upper):
            kind = "ACQUIRE_OR_PROVE_POLICY_ADEQUACY"
        elif (
            "EXECUTION_BINDING" in upper
            or "POLICY_TO_EXECUTION" in upper
            or "EXECUTION_REALIZATION" in upper
        ):
            kind = "ACQUIRE_POLICY_TO_EXECUTION_BINDING"
        elif "GOAL_TO_DECISION" in upper or "SEMANTIC" in upper:
            kind = "ACQUIRE_GOAL_SEMANTIC_BINDING"
        elif "CAPABILITY" in upper or "PRIMITIVE" in upper:
            kind = "ACQUIRE_VERIFIABLE_CAPABILITY"
        elif any(
            token in upper
            for token in ("SOURCE", "TRUTH", "FACT", "INFORMATION", "OBSERVATION")
        ):
            kind = "ACQUIRE_DECISION_RELEVANT_INFORMATION"
        else:
            kind = "RESOLVE_DECLARED_R2_EDGE"
        return _base(
            kind,
            result,
            request={"required_edge": edge},
            requires_reverification=True,
        )

    # An open result with no explicit next edge is not silently normalized into
    # success. The adequate controller action is to stop because proceeding
    # would require inventing an unproved semantic transition.
    return _base(
        "STOP_FAIL_CLOSED",
        result,
        reason="OPEN_R2_RESULT_WITHOUT_ACTIONABLE_NEXT_EDGE",
        requires_reverification=False,
    )
