"""R2 totalized meta-action controller V1.

Turns every output of the verified R2 fixed-point controller into exactly one
proof-disciplined next meta-action. This closes the control-law totality problem
without claiming impossible open-world semantic or factual completeness.

The totalizer never authorizes execution. It only classifies what the already
verified R2 controller has proved is safe to do next.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import general_adequate_decision_fixed_point_v2 as fixed_point

SCHEMA = "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_TOTALIZED_V1"

RETURN_VERIFIED_RESULT = "RETURN_VERIFIED_RESULT"
ACQUIRE_MINIMUM_INFORMATION = "ACQUIRE_MINIMUM_POLICY_CHANGING_INFORMATION"
ACQUIRE_AUTHORITY_BINDING = "ACQUIRE_REQUIRED_AUTHORITY_BINDING"
REPAIR_ADEQUACY_COVER = "REPAIR_OR_EXPAND_VERIFIABLE_ADEQUACY_COVER"
ABSTAIN_FAIL_CLOSED = "ABSTAIN_FAIL_CLOSED"

META_ACTIONS = frozenset(
    {
        RETURN_VERIFIED_RESULT,
        ACQUIRE_MINIMUM_INFORMATION,
        ACQUIRE_AUTHORITY_BINDING,
        REPAIR_ADEQUACY_COVER,
        ABSTAIN_FAIL_CLOSED,
    }
)


def classify(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return exactly one sound next meta-action for an R2 controller result."""
    if not isinstance(result, Mapping):
        return {
            "meta_action": ABSTAIN_FAIL_CLOSED,
            "reason": "R2_RESULT_NOT_OBJECT",
            "sound_under_current_authenticated_evidence": True,
        }

    status = str(result.get("status") or "")
    fixed_status = str(result.get("r2_fixed_point_status") or "")
    edge = str(
        result.get("next_required_edge")
        or result.get("next_required_effect")
        or ""
    )

    if result.get("pass") is True:
        if result.get("actual_goal_satisfaction_verified") is True:
            return {
                "meta_action": RETURN_VERIFIED_RESULT,
                "reason": "ACTUAL_GOAL_SATISFACTION_INDEPENDENTLY_VERIFIED",
                "sound_under_current_authenticated_evidence": True,
            }
        return {
            "meta_action": ABSTAIN_FAIL_CLOSED,
            "reason": "PASS_WITHOUT_VERIFIED_ACTUAL_GOAL_SATISFACTION",
            "sound_under_current_authenticated_evidence": True,
        }

    if isinstance(result.get("next_information_request"), Mapping) or isinstance(
        result.get("next_observation_request"), Mapping
    ):
        return {
            "meta_action": ACQUIRE_MINIMUM_INFORMATION,
            "reason": "DECISION_RELEVANT_INFORMATION_EDGE_EXPOSED",
            "sound_under_current_authenticated_evidence": True,
        }

    binding_signal = "BINDING" in status.upper() or "BINDING" in edge.upper()
    if binding_signal:
        return {
            "meta_action": ACQUIRE_AUTHORITY_BINDING,
            "reason": "REQUIRED_AUTHORITY_BINDING_NOT_YET_AUTHENTICATED",
            "sound_under_current_authenticated_evidence": True,
        }

    if isinstance(result.get("next_policy_request"), Mapping) or fixed_status in {
        "OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
        "OPEN__R2_EDGE_RESOLVER_NO_PROGRESSIVE_CANDIDATE",
        "OPEN__R2_FIXED_POINT_STEP_BOUND_EXHAUSTED",
    }:
        return {
            "meta_action": REPAIR_ADEQUACY_COVER,
            "reason": "NO_CURRENTLY_CERTIFIED_ADEQUATE_POLICY_COVER",
            "sound_under_current_authenticated_evidence": True,
        }

    return {
        "meta_action": ABSTAIN_FAIL_CLOSED,
        "reason": "NO_SOUND_PROGRESS_EDGE_PROVED",
        "sound_under_current_authenticated_evidence": True,
    }


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    execution_provider: Callable[..., Mapping[str, Any]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    result = fixed_point.run(
        request,
        repo_root=repo_root,
        information_provider=information_provider,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
        execution_provider=execution_provider,
        **kwargs,
    )
    if not isinstance(result, Mapping):
        result = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "R2_FIXED_POINT_RESULT_NOT_OBJECT",
            "actual_goal_satisfaction_verified": False,
        }

    out = deepcopy(dict(result))
    decision = classify(out)
    out["r2_totalizer_schema"] = SCHEMA
    out["r2_meta_action"] = decision["meta_action"]
    out["r2_meta_action_reason"] = decision["reason"]
    out["r2_meta_action_totalized"] = out["r2_meta_action"] in META_ACTIONS
    out["r2_control_law_total_over_authenticated_outputs"] = True
    out["r2_meta_action_execution_authority"] = False
    out["r2_meta_action_semantic_truth_authority"] = False
    out["r2_meta_action_open_world_completion_claimed"] = False
    out.setdefault("terminal_authority", False)
    out.setdefault("terminal_credit_delta", 0)
    return out
