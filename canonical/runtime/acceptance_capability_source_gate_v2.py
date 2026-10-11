"""Fail-closed source gate for Opus 5.5 acceptance execution.

Canonical ownership forbids another model from supplying producer cognition
for any Brain-credited acceptance result. Model locality, openness, hosting,
wrapping, or content addressing does not change attribution.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_CAPABILITY_SOURCE_GATE_V2"
ALLOWED_MODEL_ROLES = {"NONE"}

def evaluate(route: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if route.get("benchmark_harness_zero_cost") is not True:
        errors.append("HARNESS_ZERO_COST_NOT_PROVEN")
    if route.get("scorer_frozen") is not True:
        errors.append("SCORER_NOT_FROZEN")
    if route.get("brain_candidate_bound") is not True:
        errors.append("BRAIN_CANDIDATE_NOT_BOUND")
    if route.get("brain_owned_operative_configuration") is not True:
        errors.append("BRAIN_OWNED_OPERATIVE_CONFIGURATION_NOT_PROVEN")
    if route.get("configuration_materially_constrains_execution") is not True:
        errors.append("CONFIGURATION_MATERIAL_CONTROL_NOT_PROVEN")
    if route.get("capability_package_contains_configuration") is not True:
        errors.append("CAPABILITY_PACKAGE_CONFIGURATION_MISSING")
    if route.get("promotion_evaluates_brain_configured_system") is not True:
        errors.append("PROMOTION_NOT_BOUND_TO_BRAIN_CONFIGURED_SYSTEM")
    if route.get("external_hidden_target_capability_provider") is not False:
        errors.append("HIDDEN_TARGET_CAPABILITY_PROVIDER_NOT_ZERO")
    if route.get("ownership_claim_relies_on_model_standalone_superiority") is not False:
        errors.append("MODEL_STANDALONE_SUPERIORITY_USED_AS_OWNERSHIP")
    if route.get("future_use_requires_capability_rediscovery") is not False:
        errors.append("CAPABILITY_REDISCOVERY_REQUIRED")
    if route.get("incremental_spend_usd") != 0:
        errors.append("INCREMENTAL_SPEND_NOT_ZERO")

    model_role = route.get("model_role")
    model_count = route.get("model_dependency_count")
    if model_role not in ALLOWED_MODEL_ROLES:
        errors.append("MODEL_ROLE_UNCLASSIFIED")
    if type(model_count) is not int:
        errors.append("MODEL_DEPENDENCY_COUNT_INVALID")
    elif model_count != 0:
        errors.append("EXTERNAL_MODEL_COGNITION_DEPENDENCY_FORBIDDEN")
    if model_role != "NONE":
        errors.append("MODEL_PRODUCER_ROLE_FORBIDDEN")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": "ADMISSIBLE_FOR_CLEAN_ACCEPTANCE_EXECUTION" if ok else "BLOCKED_BEFORE_CASE_SPEND",
        "pass": ok,
        "errors": sorted(set(errors)),
        "clean_case_execution_authority": ok,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": (
            "ZERO_EXTERNAL_MODEL_COGNITION_REQUIRED_IN_BRAIN_CREDITED_PRODUCER_PATH__"
            "MODEL_ROLE_MUST_BE_NONE__MODEL_DEPENDENCY_COUNT_MUST_BE_ZERO__"
            "UNKNOWN_OR_MODEL_ASSISTED_PROVENANCE_FAILS_CLOSED"
        ),
    }
