"""Fail-closed promotion firewall for the frozen composition invariant claim.

This module grants no capability by itself. It only prevents partial runtime
mediation receipts from being mistaken for a proof of the frozen
COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES C1 boundary.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_ACCEPTANCE_BOUNDARY_FIREWALL_V1"
CLAIM = "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"
REQUIRED_RUNTIME_SCOPE = "DETERMINISTIC_CAPABILITY_GRAPH_DECLARED_CROSS_CAPABILITY_STATE"


def evaluate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(candidate, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "claim": CLAIM,
            "errors": ["CANDIDATE_MAPPING_REQUIRED"],
            "promotion_allowed": False,
            "acceptance_credit_delta": 0,
        }

    if candidate.get("planning_mode") != "DETERMINISTIC_CAPABILITY_GRAPH":
        errors.append("DETERMINISTIC_CAPABILITY_GRAPH_REQUIRED")

    binding = candidate.get("composition_state_capsule")
    if not isinstance(binding, Mapping):
        errors.append("COMPOSITION_STATE_CAPSULE_BINDING_REQUIRED")
        binding = {}

    if binding.get("status") != "PASS":
        errors.append("CAPSULE_RUNTIME_BINDING_PASS_REQUIRED")
    if binding.get("scope") != REQUIRED_RUNTIME_SCOPE:
        errors.append("CAPSULE_RUNTIME_SCOPE_MISMATCH")

    # These are deliberately strict. Missing is not false-ish success; it is open.
    required_true = {
        "declared_cross_capability_state_no_bypass":
            "DECLARED_STATE_NO_BYPASS_NOT_PROVED",
        "content_bound_action_result_provenance":
            "V2_CONTENT_BOUND_ACTION_RESULT_PROVENANCE_NOT_PROVED",
        "semantic_declaration_completeness":
            "SEMANTIC_DECLARATION_COMPLETENESS_NOT_PROVED",
        "external_evidence_channel_completeness":
            "EXTERNAL_EVIDENCE_CHANNEL_COMPLETENESS_NOT_PROVED",
        "broader_runtime_channel_totality":
            "BROADER_RUNTIME_CHANNEL_TOTALITY_NOT_PROVED",
        "rollback_scope_complete":
            "ROLLBACK_SCOPE_COMPLETENESS_NOT_PROVED",
    }
    for field, error in required_true.items():
        if binding.get(field) is not True:
            errors.append(error)

    capsule_schema = str(binding.get("capsule_schema") or "")
    if capsule_schema != "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V2":
        errors.append("STRICT_CAPSULE_V2_SCHEMA_REQUIRED")

    independent = candidate.get("independent_system_verification")
    if not isinstance(independent, Mapping):
        errors.append("INDEPENDENT_SYSTEM_VERIFICATION_REQUIRED")
        independent = {}
    if independent.get("status") != "PASS":
        errors.append("INDEPENDENT_SYSTEM_VERIFICATION_PASS_REQUIRED")
    if independent.get("c1_closed_world_mediation_totality") is not True:
        errors.append("C1_CLOSED_WORLD_MEDIATION_TOTALITY_NOT_INDEPENDENTLY_PROVED")
    if independent.get("subject_capsule_head_hash") != binding.get("head_hash"):
        errors.append("INDEPENDENT_VERIFICATION_CAPSULE_HEAD_MISMATCH")

    promotion_allowed = not errors
    return {
        "schema": SCHEMA,
        "status": "PASS__C1_PROMOTION_BOUNDARY_SATISFIED" if promotion_allowed else "FAIL_CLOSED",
        "claim": CLAIM,
        "runtime_scope": REQUIRED_RUNTIME_SCOPE,
        "promotion_allowed": promotion_allowed,
        "errors": sorted(errors),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "PASS_DOES_NOT_PROVE_C2_CRITICAL_INVARIANT_REGISTRY_TOTALITY",
            "PASS_DOES_NOT_PROVE_COMPOSITION_TERMINAL_SUCCESS_NONINFERIORITY",
            "PASS_DOES_NOT_CLOSE_OPEN_ISOLATED_COMPONENT_PROOFS",
        ],
    }
