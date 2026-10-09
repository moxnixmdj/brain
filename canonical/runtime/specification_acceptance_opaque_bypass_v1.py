"""Truth-repair kernel for the specification->acceptance residual.

This module proves only a dependency reduction.  It does not interpret raw
language, prove any policy adequate, or grant benchmark/terminal credit.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SPECIFICATION_ACCEPTANCE_OPAQUE_BYPASS_V1"

PREMISES = (
    "lossless_raw_obligations_preserved",
    "initial_overapprox_contains_all_authorized_interpretations",
    "semantic_narrowing_requires_authenticated_sound_evidence",
    "positive_acceptance_requires_scope_sound_adequacy_or_direct_acceptance",
    "unresolved_semantics_fail_closed",
)


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "PAYLOAD_MAPPING_REQUIRED",
            "terminal_authority": False,
        }

    missing = [key for key in PREMISES if payload.get(key) is not True]
    passed = not missing
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__EXPLICIT_R1_R2_MATERIALIZATION_NOT_SEPARATELY_NECESSARY"
            if passed
            else "FAIL_CLOSED__BYPASS_PREMISE_MISSING"
        ),
        "missing_premises": missing,
        "explicit_complete_semantic_hypothesis_enumeration_required": False if passed else None,
        "explicit_intermediate_consequence_model_materialization_required": False if passed else None,
        "remaining_load_bearing_residual": (
            "SOURCE_BOUND_SCOPE_SOUND_POLICY_ADEQUACY_OR_DIRECT_END_TO_END_ACCEPTANCE"
            if passed
            else None
        ),
        "semantic_interpretation_solved": False,
        "policy_adequacy_proved": False,
        "benchmark_acceptance_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
