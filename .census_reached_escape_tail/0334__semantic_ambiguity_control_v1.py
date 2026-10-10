"""Decision-relevant semantic ambiguity control V1.

This module does not try to infer missing meaning from nowhere. It consumes a
declared complete finite hypothesis set and the existing exact semantic
information frontier. It distinguishes three cases:

1. surviving interpretations are terminally equivalent -> no clarification;
2. a declared observation can separate terminally distinct interpretations ->
   acquire the minimum such discriminator;
3. terminally distinct interpretations are not separable by the declared
   complete observation set -> the problem is underdetermined within that model.

For USER_INTENT ambiguity, case (3) routes to minimum user clarification.
For non-user-owned ambiguity, it routes to fail-closed abstention/stronger
information instead of guessing.

No semantic-truth, execution, acceptance, promotion, or terminal authority is
granted by this control layer.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime.semantic_information_frontier_v1 import solve as solve_frontier

SCHEMA = "PROJECT_BRAIN_SEMANTIC_AMBIGUITY_CONTROL_V1"

OWNERS = {"USER_INTENT", "EXTERNAL_WORLD", "SYSTEM_MODEL"}


def _base(status: str, *, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "ask_user_required": False,
        "clarification_required": False,
        "additional_information_required": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def decide(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _base(
            "FAIL_CLOSED__AMBIGUITY_PROBLEM_REQUIRED",
            passed=False,
            reason="PROBLEM_NOT_OBJECT",
        )

    owner = str(problem.get("ambiguity_owner") or "").strip().upper()
    if owner not in OWNERS:
        return _base(
            "FAIL_CLOSED__AMBIGUITY_OWNER_REQUIRED",
            passed=False,
            reason="AMBIGUITY_OWNER_INVALID",
        )

    frontier_problem = {
        "hypothesis_set_complete": problem.get("hypothesis_set_complete"),
        "worlds": deepcopy(problem.get("worlds")),
        "observations": deepcopy(problem.get("observations")),
    }
    frontier = solve_frontier(frontier_problem)

    if frontier.get("pass") is True:
        first = frontier.get("first_observation_id")
        eq_count = frontier.get("terminal_equivalence_class_count")
        if first is None and eq_count == 1:
            return _base(
                "PASS__AMBIGUITY_TERMINALLY_IRRELEVANT",
                passed=True,
                action="CONTINUE_WITHOUT_DISAMBIGUATION",
                reason=(
                    "ALL_DECLARED_COMPLETE_SURVIVING_INTERPRETATIONS_HAVE_"
                    "THE_SAME_TERMINAL_SIGNATURE"
                ),
                ambiguity_owner=owner,
                semantic_frontier=frontier,
                terminally_equivalent=True,
                does_not_require_full_interpretation_identity=True,
            )

        return _base(
            "OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED",
            passed=False,
            action="ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR",
            reason=(
                "TERMINALLY_DISTINCT_INTERPRETATIONS_REMAIN_AND_A_DECLARED_"
                "SEPARATING_OBSERVATION_EXISTS"
            ),
            ambiguity_owner=owner,
            additional_information_required=True,
            next_observation_id=first,
            minimum_worst_case_cost_units=frontier.get(
                "minimum_worst_case_cost_units"
            ),
            semantic_frontier=frontier,
        )

    status = str(frontier.get("status") or "")
    reason = str(frontier.get("reason") or "")
    if status == (
        "FAIL_CLOSED__TERMINALLY_DISTINCT_WORLDS_NOT_SEPARABLE_BY_DECLARED_OBSERVATIONS"
    ):
        if owner == "USER_INTENT":
            return _base(
                "OPEN__MINIMUM_USER_CLARIFICATION_REQUIRED__SEMANTIC_UNDERDETERMINATION",
                passed=False,
                action="ASK_USER_MINIMUM_CLARIFICATION",
                reason=(
                    "COMPLETE_DECLARED_INTERPRETATION_SET_CONTAINS_"
                    "OBSERVATIONALLY_INSEPARABLE_WORLDS_REQUIRING_DIFFERENT_ACTIONS"
                ),
                ambiguity_owner=owner,
                ask_user_required=True,
                clarification_required=True,
                additional_information_required=True,
                unresolved_pairs=deepcopy(frontier.get("unresolved_pairs", [])),
                semantic_frontier=frontier,
            )

        return _base(
            "OPEN__DECISIVE_INFORMATION_UNOBSERVABLE_WITHIN_DECLARED_MODEL",
            passed=False,
            action="ABSTAIN_OR_ACQUIRE_STRONGER_AUTHENTIC_INFORMATION",
            reason=(
                "TERMINALLY_DISTINCT_WORLDS_ARE_NOT_SEPARABLE_BY_THE_DECLARED_"
                "COMPLETE_OBSERVATION_SET"
            ),
            ambiguity_owner=owner,
            additional_information_required=True,
            unresolved_pairs=deepcopy(frontier.get("unresolved_pairs", [])),
            semantic_frontier=frontier,
        )

    return _base(
        "FAIL_CLOSED__AMBIGUITY_MODEL_INSUFFICIENT",
        passed=False,
        reason=reason or status or "SEMANTIC_INFORMATION_FRONTIER_FAILED",
        ambiguity_owner=owner,
        semantic_frontier=frontier,
    )
