"""Fail-closed reduction from universal learning control to acceptance residual.

The structural learning theorem can remove "unseen environment requires a
separate special-case route" as a control-flow concern. It cannot by itself
establish that the learner's terminal success rate is noninferior to Opus.

This reducer therefore emits exactly one residual class when structural premises
hold: matched empirical learning effectiveness. It grants no acceptance credit.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_LEARNING_ACCEPTANCE_REDUCER_V1"
TARGET = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"


def reduce(
    *,
    contract_verification: Mapping[str, Any],
    evidence_bindings: Mapping[str, Any],
    empirical_noninferiority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    runner = contract_verification.get("independent_runner")
    verified = contract_verification.get("verified")
    if not isinstance(runner, Mapping) or runner.get("conclusion") != "success":
        errors.append("UNIVERSAL_LEARNING_INDEPENDENT_RUNNER_NOT_SUCCESS")
    if not isinstance(verified, Mapping):
        errors.append("UNIVERSAL_LEARNING_VERIFIED_BLOCK_MISSING")
        verified = {}

    required_structural = (
        "unknown_capture_total",
        "only_verified_coverage_uses_known_route",
        "learning_channels_complete",
        "candidate_requires_verification_before_trust",
        "promotion_requires_verified_state",
        "environment_change_invalidates_to_unknown",
        "finite_control_product_exhaustively_checked",
        "actual_component_bindings_exact",
    )
    for key in required_structural:
        if verified.get(key) is not True:
            errors.append("STRUCTURAL_FACT_FALSE:" + key)

    claims = evidence_bindings.get("claims")
    if not isinstance(claims, list):
        errors.append("EVIDENCE_BINDINGS_CLAIMS_NOT_LIST")
        claims = []
    states = {
        str(x.get("predicate_id")): x.get("state")
        for x in claims
        if isinstance(x, Mapping)
    }
    for predicate in (
        "TOOL_LEARNING_SECOND_TASK_TRANSFER",
        "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION",
    ):
        if states.get(predicate) != "PROVED":
            errors.append("EXISTING_LEARNING_ATOM_NOT_PROVED:" + predicate)

    empirical_pass = False
    if isinstance(empirical_noninferiority, Mapping):
        empirical_pass = (
            empirical_noninferiority.get("target_predicate") == TARGET
            and empirical_noninferiority.get("independent") is True
            and empirical_noninferiority.get("matched_distribution_frozen") is True
            and empirical_noninferiority.get("brain_lcb_ge_opus_ucb_minus_delta") is True
            and empirical_noninferiority.get("contamination_controls_pass") is True
        )

    structural_pass = not errors
    if not structural_pass:
        status = "FAIL_CLOSED"
    elif empirical_pass:
        status = "CANDIDATE_FULL_PREDICATE_DISCHARGE__SEPARATE_ACCEPTANCE_PROMOTION_REQUIRED"
    else:
        status = "STRUCTURAL_NOVELTY_SCOPE_CLOSED__EMPIRICAL_NONINFERIORITY_REMAINS_OPEN"

    return {
        "schema": SCHEMA,
        "status": status,
        "pass": structural_pass,
        "errors": errors,
        "target_predicate": TARGET,
        "structural_novelty_scope_closed_candidate": structural_pass,
        "separate_environment_enumeration_required": False if structural_pass else None,
        "remaining_residuals": (
            []
            if structural_pass and empirical_pass
            else ["MATCHED_EMPIRICAL_LEARNING_EFFECTIVENESS_NONINFERIORITY"]
            if structural_pass
            else ["STRUCTURAL_UNIVERSAL_LEARNING_PREMISES"]
        ),
        "empirical_noninferiority_pass": empirical_pass,
        "target_predicate_discharge_candidate": structural_pass and empirical_pass,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_CLAIM_THAT_EVERY_NOVEL_ENVIRONMENT_IS_SOLVABLE",
            "NO_FINITE_SAMPLE_TO_OPEN_WORLD_SUCCESS_INFERENCE",
            "NO_ACCEPTANCE_CREDIT_WITHOUT_SEPARATE_ACCEPTANCE_REDUCTION",
        ],
    }
