"""Fail-closed integration of verified Universal Learning V1 with V2 optimization."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_contract_v1 as v1
from canonical.runtime import universal_active_transfer_learner_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_LEARNING_ACTIVE_ROUTER_V2"


def _base(**extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "trusted_execution_authorized": False,
        "promotion_authorized": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        **extra,
    }


def route(
    *,
    goal: str,
    verified_coverage: Any,
    required_facts: Iterable[Any],
    verified_facts: Iterable[Any],
    hypotheses: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    base_route = v1.route_input(verified_coverage=verified_coverage)
    delta = v2.minimum_novelty_delta(
        required_facts=required_facts,
        verified_facts=verified_facts,
    )
    sufficiency = v2.decision_sufficient(hypotheses)
    ranked = v2.rank_learning_actions(actions) if actions else []

    if base_route["route"] == "USE_VERIFIED_CAPABILITY" and not delta["missing"]:
        return _base(
            route="USE_VERIFIED_CAPABILITY",
            reason="V1_VERIFIED_COVERAGE_AND_ZERO_NOVELTY_DELTA",
            trusted_execution_authorized=True,
            novelty_delta=delta,
            decision_sufficiency=sufficiency,
            next_action=None,
            recommended_action=None,
        )

    if ranked:
        reason = (
            "VERIFIED_COVERAGE_CONTRADICTED_BY_NOVELTY_DELTA"
            if base_route["route"] == "USE_VERIFIED_CAPABILITY" and delta["missing"]
            else "V1_UNVERIFIED_OR_NOVEL__OPTIMIZED_LEARNING_REQUIRED"
        )
        return _base(
            route="LEARN",
            reason=reason,
            novelty_delta=delta,
            decision_sufficiency=sufficiency,
            next_action=ranked[0],
            recommended_action=None,
        )

    if sufficiency["sufficient"]:
        return _base(
            route="DECISION_SUFFICIENT_UNVERIFIED_MODEL",
            reason="ALL_LIVE_HYPOTHESES_AGREE_BUT_KNOWLEDGE_REMAINS_UNVERIFIED",
            novelty_delta=delta,
            decision_sufficiency=sufficiency,
            next_action=None,
            recommended_action=sufficiency["action"],
        )

    reason = (
        "NO_SAFE_INFORMATION_ACTION_AND_LIVE_HYPOTHESES_DISAGREE"
        if sufficiency.get("reason") == "LIVE_HYPOTHESES_DISAGREE"
        else "NO_SAFE_INFORMATION_ACTION_AND_NO_DECISION_SUFFICIENCY"
    )
    return _base(
        route="ABSTAIN_OR_REQUEST_DISCRIMINATOR",
        reason=reason,
        novelty_delta=delta,
        decision_sufficiency=sufficiency,
        next_action=None,
        recommended_action=None,
    )
