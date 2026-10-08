"""R2 total adequate-next-move control law V1.

This module closes the *control-law* form of R2 without pretending that every
open-world task already has a final executable policy. It delegates semantic
truth, adequacy, execution, and acceptance to the existing verified fixed-point
controller, then converts every residual state into exactly one explicit next
move.

Fresh facts absent from authentic sources are never inferred.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime.general_adequate_decision_fixed_point_v2 import (
    run as run_fixed_point,
)

SCHEMA = "PROJECT_BRAIN_R2_TOTAL_ADEQUATE_NEXT_MOVE_V1"

RETURN_VERIFIED_ACTION = "RETURN_VERIFIED_ACTION"
ACQUIRE_MINIMUM_INFORMATION = "ACQUIRE_MINIMUM_POLICY_CHANGING_INFORMATION"
ACQUIRE_FRESH_REALITY = "ACQUIRE_FRESH_SOURCE_OR_EXTERNAL_REALITY"
ACQUIRE_POLICY_COVER_OBSERVATION = "ACQUIRE_SELECTED_POLICY_COVER_OBSERVATION"
SYNTHESIZE_POLICY_ADEQUACY = "SYNTHESIZE_OR_AUTHENTICATE_POLICY_ADEQUACY"
ACQUIRE_SEMANTIC_BINDING = "ACQUIRE_AUTHENTICATED_SEMANTIC_BINDING"
REALIZE_POLICY = "REALIZE_OR_AUTHENTICATE_SELECTED_POLICY_EXECUTION"
ACQUIRE_GOAL_ACCEPTANCE = "ACQUIRE_INDEPENDENT_GOAL_SATISFACTION_VERIFICATION"
EXPAND_VERIFIED_PRIMITIVE = "EXPAND_VERIFIED_POLICY_OR_PROOF_CAPABILITY"
REPAIR_DIRECT = "REPAIR_MATCHED_DIRECT_ADEQUACY_ROUTE"\nFAIL_CLOSED = "FAIL_CLOSED_INVALID_OR_UNSAFE_STATE"


def _base(kind: str, status: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "next_move_kind": kind,
        "total_next_move_control_law": True,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        "global_open_world_final_action_closure_claimed": False,
    }


def _last_information_attempt_failed(result: Mapping[str, Any]) -> bool:
    trace = result.get("information_trace")
    if not isinstance(trace, list):
        return False
    for row in reversed(trace):
        if not isinstance(row, Mapping):
            continue
        if "provider_returned_payload" in row:
            return row.get("provider_returned_payload") is not True
    return False


def classify_result(
    result: Mapping[str, Any],
    *,
    information_provider_supplied: bool = False,
    proposal_provider_supplied: bool = False,
    capability_expander_supplied: bool = False,
    execution_provider_supplied: bool = False,
) -> dict[str, Any]:
    """Convert an authenticated fixed-point residual into one explicit next move."""
    if not isinstance(result, Mapping):
        return {
            **_base(FAIL_CLOSED, "FAIL_CLOSED__FIXED_POINT_RESULT_NOT_OBJECT"),
            "pass": False,
            "goal_progress_guaranteed": False,
            "reason": "FIXED_POINT_RESULT_NOT_OBJECT",
        }

    status = str(result.get("status") or result.get("r2_fixed_point_status") or "")
    fixed_status = str(result.get("r2_fixed_point_status") or "")

    if result.get("pass") is True:
        if result.get("actual_goal_satisfaction_verified") is not True:
            return {
                **_base(
                    FAIL_CLOSED,
                    "FAIL_CLOSED__PASS_WITHOUT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
                ),
                "pass": False,
                "goal_progress_guaranteed": False,
                "reason": "PASS_WITHOUT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
            }
        action = result.get("realization")
        if action is None:
            action = result.get("action")
        return {
            **_base(RETURN_VERIFIED_ACTION, "PASS__VERIFIED_ADEQUATE_RESULT_AVAILABLE"),
            "pass": True,
            "goal_progress_guaranteed": True,
            "actual_goal_satisfaction_verified": True,
            "selected_policy_id": result.get("selected_policy_id"),
            "verified_result": deepcopy(action),
        }

    if status.startswith("FAIL_CLOSED") or fixed_status == "FAIL_CLOSED":
        return {
            **_base(FAIL_CLOSED, status or fixed_status or "FAIL_CLOSED"),
            "pass": False,
            "goal_progress_guaranteed": False,
            "reason": result.get("reason"),
        }

    next_information = result.get("next_information_request")
    if isinstance(next_information, Mapping):
        if information_provider_supplied and _last_information_attempt_failed(result):
            return {
                **_base(
                    ACQUIRE_FRESH_REALITY,
                    "OPEN__CURRENT_AUTHENTIC_INFORMATION_PROVIDER_COULD_NOT_SUPPLY_SELECTED_FACT",
                ),
                "pass": False,
                "goal_progress_guaranteed": False,
                "next_move_packet": deepcopy(dict(next_information)),
                "epistemic_boundary": (
                    "SELECTED_POLICY_CHANGING_FACT_NOT_OBTAINED_FROM_CURRENT_PROVIDER"
                ),
            }
        return {
            **_base(
                ACQUIRE_MINIMUM_INFORMATION,
                "OPEN__MINIMUM_POLICY_CHANGING_INFORMATION_REQUIRED",
            ),
            "pass": False,
            "goal_progress_guaranteed": False,
            "next_move_packet": deepcopy(dict(next_information)),
        }

    next_observation = result.get("next_observation_request")
    if isinstance(next_observation, Mapping):
        return {
            **_base(
                ACQUIRE_POLICY_COVER_OBSERVATION,
                "OPEN__SELECTED_POLICY_COVER_OBSERVATION_REQUIRED",
            ),
            "pass": False,
            "goal_progress_guaranteed": False,
            "next_move_packet": deepcopy(dict(next_observation)),
        }

    next_policy = result.get("next_policy_request")
    if isinstance(next_policy, Mapping):
        return {
            **_base(
                SYNTHESIZE_POLICY_ADEQUACY,
                "OPEN__VERIFIABLE_POLICY_ADEQUACY_REPAIR_REQUIRED",
            ),
            "pass": False,
            "goal_progress_guaranteed": False,
            "next_move_packet": deepcopy(dict(next_policy)),
        }

    edge = str(result.get("next_required_edge") or "")
    edge_upper = edge.upper()

    if "GOAL_SATISFACTION" in edge_upper or "ACTUAL_GOAL" in edge_upper:
        return {
            **_base(
                ACQUIRE_GOAL_ACCEPTANCE,
                "OPEN__INDEPENDENT_GOAL_SATISFACTION_VERIFICATION_REQUIRED",
            ),
            "pass": False,
            "goal_progress_guaranteed": False,
            "next_required_edge": edge,
        }

    if "EXECUTION" in edge_upper or "REALIZATION" in edge_upper:
        return {
            **_base(
                REALIZE_POLICY,
                "OPEN__SELECTED_POLICY_REALIZATION_OR_EXECUTION_EVIDENCE_REQUIRED",
            ),
            "pass": False,
            "goal_progress_guaranteed": False,
            "next_required_edge": edge,
            "execution_provider_was_supplied": bool(execution_provider_supplied),
        }

    if (
        "GOAL_TO_DECISION" in edge_upper
        or "SEMANTIC" in edge_upper
        or "DECISION_CONTEXT" in edge_upper
    ):
        return {
            **_base(
                ACQUIRE_SEMANTIC_BINDING,
                "OPEN__AUTHENTICATED_SEMANTIC_BINDING_REQUIRED",
            ),
            "pass": False,
            "goal_progress_guaranteed": False,
            "next_required_edge": edge,
        }

    return {
        **_base(
            EXPAND_VERIFIED_PRIMITIVE,
            "OPEN__VERIFIED_POLICY_OR_PROOF_CAPABILITY_EXPANSION_REQUIRED",
        ),
        "pass": False,
        "goal_progress_guaranteed": False,
        "next_required_edge": edge or None,
        "fixed_point_status": fixed_status or None,
        "proposal_provider_was_supplied": bool(proposal_provider_supplied),
        "capability_expander_was_supplied": bool(capability_expander_supplied),
        "epistemic_boundary": (
            "NO_EXISTING_VERIFIED_INTERNAL_MOVE_CAN_CLOSE_THE_CURRENT_R2_EDGE"
        ),
    }


def run(
    request: Mapping[str, Any],
    *,
    repo_root=None,
    information_provider=None,
    proposal_provider=None,
    capability_expander=None,
    execution_provider=None,
    max_fixed_point_steps=16,
    provider_max_candidates=4,
) -> dict[str, Any]:
    result = run_fixed_point(
        request,
        repo_root=repo_root,
        information_provider=information_provider,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
        execution_provider=execution_provider,
        max_fixed_point_steps=max_fixed_point_steps,
        provider_max_candidates=provider_max_candidates,
    )
    out = classify_result(
        result,
        information_provider_supplied=information_provider is not None,
        proposal_provider_supplied=proposal_provider is not None,
        capability_expander_supplied=capability_expander is not None,
        execution_provider_supplied=execution_provider is not None,
    )
    out["decision_result"] = (
        deepcopy(dict(result)) if isinstance(result, Mapping) else result
    )
    return out
