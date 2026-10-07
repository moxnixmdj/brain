from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import dominance_binding_v2 as bind
from canonical.runtime import dominance_semantic_binding_v4 as sem
from canonical.runtime.dominance_sufficiency_v4 import (
    compile_dominance_sufficiency_v4,
)
from canonical.runtime import universal_learning_decision_router_v3 as base_v3

SCHEMA = "PROJECT_BRAIN_DOMINANCE_FIRST_LEARNING_ROUTER_V4"


def route(
    *,
    goal: str,
    verified_coverage: Any,
    required_facts,
    verified_facts,
    transfer_mappings: Sequence[Mapping[str, Any]],
    hypotheses: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
    dominance_certificate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    common = {
        "schema": SCHEMA,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authorized": False,
        "trusted_execution_authorized": False,
    }

    dominance = None
    if dominance_certificate is not None:
        try:
            current_rows = sem.live_worlds(list(hypotheses))
            current_world_sha = sem.live_world_digest(current_rows)
        except (sem.SemanticBindingV4Error, bind.BindingError) as exc:
            return {
                **common,
                "route": "FAIL_CLOSED__CURRENT_WORLD_DEFINITIONS_UNBOUND",
                "recommended_action": None,
                "next_action": None,
                "errors": [str(exc)],
            }

        dominance = compile_dominance_sufficiency_v4(
            dominance_certificate
        )
        if dominance.get("status") == "FAIL_CLOSED":
            return {
                **common,
                "route": "FAIL_CLOSED__DOMINANCE_CERTIFICATE_INVALID",
                "recommended_action": None,
                "next_action": None,
                "dominance": dominance,
            }

        if dominance.get("live_world_set_sha256") != current_world_sha:
            return {
                **common,
                "route": "FAIL_CLOSED__DOMINANCE_WORLD_SET_MISMATCH",
                "recommended_action": None,
                "next_action": None,
                "dominance": dominance,
                "current_live_world_set_sha256": current_world_sha,
            }

        if dominance.get("status") == "PASS__CONTENT_BOUND_DOMINANCE_SUFFICIENT":
            return {
                **common,
                "route": "DOMINANCE_SUFFICIENT_CERTIFICATE_V4",
                "recommended_action": dominance.get(
                    "selected_configuration"
                ),
                "recommended_action_sha256": dominance.get(
                    "selected_configuration_sha256"
                ),
                "next_action": None,
                "dominance": dominance,
                "current_live_world_set_sha256": current_world_sha,
                "certificate_only": True,
                "reason": (
                    "THE_EXACT_CONTENT_BOUND_CURRENT_WORLD_SET_HAS_ONE_"
                    "CONTENT_BOUND_BRAIN_OWNED_CONFIGURATION_CERTIFIED_"
                    "NONINFERIOR_IN_EVERY_LIVE_WORLD__NO_WORLD_"
                    "DISAMBIGUATION_REQUIRED__EXECUTION_AUTHORITY_SEPARATE"
                ),
            }

    fallback = base_v3.route(
        goal=goal,
        verified_coverage=verified_coverage,
        required_facts=required_facts,
        verified_facts=verified_facts,
        transfer_mappings=transfer_mappings,
        hypotheses=hypotheses,
        actions=actions,
    )
    return {
        **common,
        "route": fallback.get("route"),
        "recommended_action": fallback.get("recommended_action"),
        "next_action": fallback.get("next_action"),
        "fallback_v3": fallback,
        "dominance": dominance,
        "reason": fallback.get("reason"),
    }
