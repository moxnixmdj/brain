"""V3 router: verified V2 safety plus structural transfer and exact discriminators."""
from __future__ import annotations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import universal_learning_active_router_v2 as v2
from canonical.runtime import universal_recursive_learning_engine_v3 as v3

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_ACTIVE_ROUTER_V3"


def _base(**extra: Any) -> dict[str, Any]:
    return {
        "schema":SCHEMA,
        "trusted_execution_authorized":False,
        "promotion_authorized":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        **extra,
    }


def route(
    *,
    goal: str,
    verified_coverage: Any,
    target_requirements: Iterable[Any],
    verified_facts: Iterable[Any],
    structural_mappings: Sequence[Mapping[str, Any]],
    hypotheses: Sequence[Mapping[str, Any]],
    probes: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    requirements={str(x).strip() for x in target_requirements if str(x).strip()}
    verified={str(x).strip() for x in verified_facts if str(x).strip()}

    base=v2.route(
        goal=goal,
        verified_coverage=verified_coverage,
        required_facts=requirements,
        verified_facts=verified,
        hypotheses=hypotheses,
        actions=actions,
    )
    if base["route"]=="USE_VERIFIED_CAPABILITY":
        return _base(
            route="USE_VERIFIED_CAPABILITY",
            reason="V2_VERIFIED_ROUTE_PRESERVED",
            trusted_execution_authorized=True,
            next_action=None,
            recommended_action=None,
            structural_transfer=None,
            discriminator=None,
        )

    raw_missing=requirements-verified
    transfer=v3.structural_transfer_plan(
        target_requirements=raw_missing,
        mappings=structural_mappings,
    )
    residual=set(transfer["missing"])

    discriminator=v3.minimum_action_discriminator(
        hypotheses=hypotheses,
        probes=probes,
    )

    if transfer["covered"] and not residual:
        return _base(
            route="LEARN_WITH_STRUCTURAL_TRANSFER",
            reason="VERIFIED_STRUCTURAL_MAPPING_REDUCES_NOVELTY_TO_TARGET_VERIFICATION",
            structural_transfer=transfer,
            discriminator=discriminator,
            next_action=None,
            recommended_action=None,
            next_requirement="VERIFY_TRANSFERRED_SOLUTION_IN_TARGET_DOMAIN",
        )

    if discriminator["route"]=="PROBE":
        return _base(
            route="LEARN_WITH_MINIMUM_DISCRIMINATOR",
            reason="ACTION_RELEVANT_HYPOTHESES_DISAGREE_AND_EXACT_SAFE_DISCRIMINATOR_EXISTS",
            structural_transfer=transfer,
            discriminator=discriminator,
            probe_ids=discriminator["probe_ids"],
            next_action=None,
            recommended_action=None,
            remaining_requirements=sorted(residual),
        )

    if discriminator["route"]=="DECISION_SUFFICIENT":
        return _base(
            route="DECISION_SUFFICIENT_UNVERIFIED_MODEL",
            reason="ALL_LIVE_HYPOTHESES_IMPLY_SAME_ACTION",
            structural_transfer=transfer,
            discriminator=discriminator,
            next_action=None,
            recommended_action=base.get("recommended_action"),
            remaining_requirements=sorted(residual),
        )

    if base["route"]=="LEARN" and base.get("next_action") is not None:
        return _base(
            route="LEARN_GENERAL_INFORMATION",
            reason="NO_CURRENT_EXACT_MODEL_DISCRIMINATOR__V2_INFORMATION_ACTION_REMAINS_AVAILABLE",
            structural_transfer=transfer,
            discriminator=discriminator,
            next_action=base["next_action"],
            recommended_action=None,
            remaining_requirements=sorted(residual),
        )

    return _base(
        route="ABSTAIN_OR_REQUEST_DISCRIMINATOR",
        reason="NO_SAFE_DISCRIMINATOR_OR_GENERAL_INFORMATION_ACTION_RESOLVES_ACTION_RELEVANT_UNCERTAINTY",
        structural_transfer=transfer,
        discriminator=discriminator,
        next_action=None,
        recommended_action=None,
        remaining_requirements=sorted(residual),
    )
