from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.dominance_sufficiency_v1 import compile_dominance_sufficiency
from canonical.runtime import universal_learning_decision_router_v3 as v3

SCHEMA = "PROJECT_BRAIN_DOMINANCE_FIRST_LEARNING_ROUTER_V1"


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
    }

    if dominance_certificate is not None:
        dominance = compile_dominance_sufficiency(dominance_certificate)
        status = str(dominance.get("status") or "")
        if status == "FAIL_CLOSED":
            return {
                **common,
                "route": "FAIL_CLOSED__DOMINANCE_CERTIFICATE_INVALID",
                "trusted_execution_authorized": False,
                "recommended_action": None,
                "next_action": None,
                "dominance": dominance,
            }
        if status.startswith("PASS__DOMINANCE_SUFFICIENT"):
            return {
                **common,
                "route": "DOMINANCE_SUFFICIENT",
                "trusted_execution_authorized": True,
                "recommended_action": dominance["selected_configuration"],
                "next_action": None,
                "dominance": dominance,
                "reason": (
                    "SCOPE_COMPLETE_ROBUST_NONINFERIOR_BRAIN_OWNED_CONFIGURATION_"
                    "EXISTS__HYPOTHESIS_DISAMBIGUATION_NOT_REQUIRED"
                ),
            }

    fallback = v3.route(
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
        "trusted_execution_authorized": fallback.get("trusted_execution_authorized", False),
        "recommended_action": fallback.get("recommended_action"),
        "next_action": fallback.get("next_action"),
        "fallback_v3": fallback,
        "dominance": (
            compile_dominance_sufficiency(dominance_certificate)
            if dominance_certificate is not None
            else None
        ),
        "reason": fallback.get("reason"),
    }
