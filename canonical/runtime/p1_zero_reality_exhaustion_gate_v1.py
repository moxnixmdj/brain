"""Fail-closed P1 zero-reality exhaustion and terminal-clearance gate.

This gate prevents independently verified prewave/synthetic evidence from being
mistaken for terminal-surface proof. It compiles the current P1 evidence into the
smallest truthful residual, but it grants no clearance, capability, family,
execution, or promotion authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_ZERO_REALITY_EXHAUSTION_GATE_V1"

P1_BINDING = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
P1_QUARANTINE = "canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"
P1_V4_RESIDUAL = "canonical/verification/P1_V4_SCOPE_SAFE_RESIDUAL_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
TYPED_V4 = "canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
INFO_SAFE_V2 = "canonical/verification/TRAJECTORY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

EXPECTED_SURFACES = {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
EXPECTED_RESIDUALS = {
    "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
    "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
}
EXPECTED_TYPED_V4_KINDS = {
    "AUTHORITY",
    "SCHEMA",
    "PROVENANCE",
    "INVARIANT",
    "STATE_TRANSITION",
    "TOOL_CONTRACT",
    "DEPENDENCY",
}
EXPECTED_TYPED_V4_PATTERNS = {"SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS"}


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _evaluate(
    binding: Mapping[str, Any],
    quarantine: Mapping[str, Any],
    residual: Mapping[str, Any],
    typed_v4: Mapping[str, Any],
    info_v2: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if binding.get("proof_mode") != "T0_T2_MULTIPLEXED_DETERMINISTIC_INTERVENTION_RESCUE_GATE":
        errors.append("P1_PROOF_MODE_DRIFT")
    surfaces = set(binding.get("direct_surface_bindings") or [])
    if surfaces != EXPECTED_SURFACES:
        errors.append("P1_DIRECT_SURFACE_SET_DRIFT")

    terminal = binding.get("terminal_acceptance") or {}
    if terminal.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_TERMINAL_SCORE_FIREWALL_MISSING")
    if terminal.get("parent_or_direct_surface_credit_only_for_declared_scope") is not True:
        errors.append("DECLARED_SCOPE_CREDIT_FIREWALL_MISSING")
    evidence_source = str(terminal.get("terminal_evidence_source") or "")
    if "FROZEN_T0_AND_T2_TERMINAL_OBSERVATIONS" not in evidence_source:
        errors.append("TERMINAL_EVIDENCE_SOURCE_DRIFT")
    proof_rule = str(terminal.get("proof_rule") or "")
    if "DIRECT_P1_INTERVENTION_RESCUE_INSTRUMENTATION_MUST_PASS" not in proof_rule:
        errors.append("DIRECT_INTERVENTION_RESCUE_RULE_MISSING")

    if "QUARANTIN" not in str(quarantine.get("status") or ""):
        errors.append("P1_QUARANTINE_NOT_ACTIVE")

    if not str(residual.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("P1_V4_RESIDUAL_NOT_INDEPENDENT_PASS")
    result = residual.get("result") or {}
    residual_ids = set(result.get("residual_obligations") or [])
    if residual_ids != EXPECTED_RESIDUALS:
        errors.append("P1_EXACT_RESIDUAL_SET_DRIFT")
    if result.get("can_clear_p1_scope_quarantine") is not False:
        errors.append("P1_V4_RESIDUAL_RECEIPT_UNEXPECTEDLY_CLEARABLE")

    if not str(typed_v4.get("status") or "").startswith("INDEPENDENT_PASS__"):
        errors.append("TYPED_V4_NOT_INDEPENDENT_PASS")
    tv = typed_v4.get("verified") or {}
    if set(tv.get("mechanism_classes") or []) != EXPECTED_TYPED_V4_KINDS:
        errors.append("TYPED_V4_MECHANISM_SET_DRIFT")
    if set(tv.get("causal_patterns") or []) != EXPECTED_TYPED_V4_PATTERNS:
        errors.append("TYPED_V4_PATTERN_SET_DRIFT")
    if int(tv.get("cross_product_case_count") or -1) != 168:
        errors.append("TYPED_V4_CASE_COUNT_DRIFT")

    if not str(info_v2.get("status") or "").startswith("INDEPENDENT_PASS__"):
        errors.append("INFO_SAFE_V2_NOT_INDEPENDENT_PASS")
    if int((info_v2.get("result") or {}).get("case_count") or -1) != 1024:
        errors.append("INFO_SAFE_V2_CASE_COUNT_DRIFT")
    limitations = set(info_v2.get("limitations") or [])
    if "CURRENT_GENERATOR_USES_BOUNDED_ADDITIVE_STATE_TRANSITIONS" not in limitations:
        errors.append("INFO_SAFE_V2_ADDITIVE_SCOPE_LIMITATION_MISSING")
    if "FULL_CROSS_DOMAIN_TRAJECTORY_SCOPE_EQUIVALENCE_AND_TERMINAL_POST_FREEZE_POPULATION_STILL_REQUIRED" not in limitations:
        errors.append("INFO_SAFE_V2_SCOPE_LIMITATION_MISSING")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SOURCE_DRIFT",
            "errors": sorted(set(errors)),
            "can_clear_p1_scope_quarantine": False,
            "zero_reality_fixed_point_reached": False,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    typed_has_scope = "SCOPE" in set(tv.get("mechanism_classes") or [])
    typed_has_heterogeneous_rescue = (
        tv.get("heterogeneous_post_intervention_terminal_rescue_verified") is True
    )
    info_v2_scope_complete = not {
        "CURRENT_GENERATOR_USES_BOUNDED_ADDITIVE_STATE_TRANSITIONS",
        "FULL_CROSS_DOMAIN_TRAJECTORY_SCOPE_EQUIVALENCE_AND_TERMINAL_POST_FREEZE_POPULATION_STILL_REQUIRED",
    } & limitations

    return {
        "schema": SCHEMA,
        "status": "PASS__P1_ZERO_REALITY_EVIDENCE_EXHAUSTED__TWO_TERMINAL_SCOPE_RESIDUALS_REMAIN",
        "errors": [],
        "can_clear_p1_scope_quarantine": False,
        "zero_reality_fixed_point_reached": True,
        "direct_surface_bindings": sorted(EXPECTED_SURFACES),
        "residual_obligations": sorted(EXPECTED_RESIDUALS),
        "existing_evidence": {
            "typed_v4": {
                "case_count": 168,
                "cross_domain": True,
                "patterns": sorted(EXPECTED_TYPED_V4_PATTERNS),
                "explicit_scope_failure_class": typed_has_scope,
                "heterogeneous_post_intervention_terminal_rescue": typed_has_heterogeneous_rescue,
                "disposition": "CANNOT_CLEAR_EITHER_CURRENT_RESIDUAL",
            },
            "information_safe_v2": {
                "case_count": 1024,
                "counterfactual_terminal_rescue": True,
                "scope_complete_for_typed_cross_domain_terminal_envelope": info_v2_scope_complete,
                "disposition": "RESCUE_MECHANISM_EVIDENCE_ONLY__NO_SCOPE_TRANSPORT",
            },
        },
        "forbidden_shortcuts": [
            "DO_NOT_TREAT_SYNTHETIC_PREWAVE_PASS_AS_TERMINAL_SURFACE_PASS",
            "DO_NOT_TRANSPORT_BOUNDED_ADDITIVE_RESCUE_TO_HETEROGENEOUS_TYPED_SCOPE_WITHOUT_EXACT_OR_SUPERSET_SCOPE_PROOF",
            "DO_NOT_TREAT_AUTHORITY_AS_SCOPE",
            "DO_NOT_TREAT_REPAIR_TARGET_IDENTITY_AS_INTERVENTION_RESCUE",
            "DO_NOT_USE_P1_V4_RESIDUAL_CAN_CLEAR_FIELD_AS_PROMOTION_AUTHORITY",
        ],
        "next_proof_cut": {
            "objective": "ATTEMPT_ONE_SCOPE_COMPLETE_STRONGER_PROOF_CARRIER_BEFORE_SPLITTING_BY_DIRECT_SURFACE",
            "must_jointly_verify": [
                "EXPLICIT_SCOPE_FAILURE_IS_A_FIRST_CLASS_MECHANISM",
                "HETEROGENEOUS_DELAYED_AND_INTERACTION_INTERVENTION_RESCUE",
                "SYMPTOM_ONLY_AND_INCOMPLETE_REPAIRS_DO_NOT_RESCUE",
                "CANDIDATE_RECEIVES_NO_HIDDEN_CAUSE_OR_RESCUE_GOLD",
                "SCOPE_RELATION_TO_ALL_THREE_DECLARED_P1_DIRECT_SURFACES_IS_EXACT_OR_SUPERSET",
            ],
            "fallback_if_joint_scope_relation_fails": "SPLIT_STRONGER_PROOF_BY_DECLARED_DIRECT_SURFACE__DO_NOT_REPLAY_FULL_TERMINAL",
            "new_reality_authorized": False,
        },
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate() -> dict[str, Any]:
    return _evaluate(
        _load(P1_BINDING),
        _load(P1_QUARANTINE),
        _load(P1_V4_RESIDUAL),
        _load(TYPED_V4),
        _load(INFO_SAFE_V2),
    )


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
