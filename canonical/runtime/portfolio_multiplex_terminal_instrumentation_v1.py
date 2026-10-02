"""Fail-closed adapters for the seven portfolio-multiplexed terminal routes.

These adapters DO NOT create standalone terminal populations. They bind direct
instrumentation receipts emitted inside the frozen T0/T1/T2/T3 parent terminal
observations. This preserves the canonical rule that multiplexed behaviors earn
evidence only when they are load-bearing inside the parent portfolio.

The five self-contained direct routes remain implemented in
canonical.runtime.direct_route_terminal_executors_v1.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PORTFOLIO_MULTIPLEX_TERMINAL_INSTRUMENTATION_V1"

M0 = "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
NATIVE = "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001"
STRUCTURED = "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
P2 = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3 = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
CAD = "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"

BINDINGS: dict[str, dict[str, Any]] = {
    M0: {
        "portfolios": ("T0", "T1", "T2", "T3"),
        "binding": "canonical/governance/M0_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json",
        "binding_blob": "d34a284f7c1f99fd93d420f3a5aba93851b29ef6",
    },
    NATIVE: {
        "portfolios": ("T1",),
        "binding": "canonical/governance/NATIVE_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json",
        "binding_blob": "977e18ce2c19f7bb8a429a8f1c99407ff3000e92",
    },
    STRUCTURED: {
        "portfolios": ("T0", "T1"),
        "binding": "canonical/governance/STRUCTURED_METHOD_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json",
        "binding_blob": "6d2e9adbd45af41c26c543f69769a6f9c69d52ac",
    },
    P2: {
        "portfolios": ("T1",),
        "binding": "canonical/governance/P2_PROFESSIONAL_QUALITY_T1_MULTIPLEX_TERMINAL_BINDING_V1.json",
        "binding_blob": "8d5888a8299d1b8addd629be01fe9a6dc46b1a7d",
    },
    P3: {
        "portfolios": ("T1", "T3"),
        "binding": "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json",
        "binding_blob": "ad790afa864bd8f770c3d8a6e3ac901ed2843d26",
    },
    CAD: {
        "portfolios": ("T0",),
        "binding": "canonical/governance/CAD_ACTIVE_CONTRACT_END_TO_END_PROOF_ROUTE_V1.json",
        "binding_blob": "c0f55a55091186c5ab785b670f935bbc6a2f9432",
    },
    P1: {
        "portfolios": ("T0", "T2"),
        "binding": "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json",
        "binding_blob": "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    },
}

FORBIDDEN_RECEIPT_KEYS = {
    "reference_solution",
    "gold",
    "hidden_oracle",
    "hidden_verifier",
    "expected_failure_reason",
    "mutation_identity",
}


def bound_behavior_ids() -> tuple[str, ...]:
    return tuple(sorted(BINDINGS))


def _nonempty(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value:
        errors.append(label + "_REQUIRED")
        return None
    return value


def validate_parent_observation(
    behavior_id: str,
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one route-specific instrumentation receipt from a parent portfolio.

    A receipt is evidence-bearing only when the behavior is declared load-bearing
    for that parent case and both its direct instrumentation and parent terminal
    acceptance pass. Non-load-bearing observations are recorded but grant no
    behavior evidence. This function never grants capability/family credit.
    """
    if behavior_id not in BINDINGS:
        raise ValueError("UNBOUND_MULTIPLEX_ROUTE:" + str(behavior_id))
    if not isinstance(observation, Mapping):
        raise ValueError("OBSERVATION_NOT_MAPPING")

    errors: list[str] = []
    binding = BINDINGS[behavior_id]

    if observation.get("behavior_id") != behavior_id:
        errors.append("BEHAVIOR_ID_MISMATCH")

    portfolio = observation.get("portfolio")
    if portfolio not in binding["portfolios"]:
        errors.append("PORTFOLIO_NOT_BOUND")

    _nonempty(observation.get("case_id"), "CASE_ID", errors)
    _nonempty(observation.get("candidate_package_commitment"), "CANDIDATE_PACKAGE_COMMITMENT", errors)
    _nonempty(observation.get("post_freeze_beacon"), "POST_FREEZE_BEACON", errors)

    if observation.get("binding_blob") != binding["binding_blob"]:
        errors.append("BINDING_BLOB_MISMATCH")

    load_bearing = observation.get("load_bearing")
    if load_bearing is not True and load_bearing is not False:
        errors.append("LOAD_BEARING_FLAG_REQUIRED")

    direct = observation.get("direct_instrumentation_pass")
    parent = observation.get("parent_terminal_acceptance_pass")
    if direct is not True and direct is not False:
        errors.append("DIRECT_INSTRUMENTATION_VERDICT_REQUIRED")
    if parent is not True and parent is not False:
        errors.append("PARENT_TERMINAL_ACCEPTANCE_VERDICT_REQUIRED")

    if observation.get("case_replaced") is not False:
        errors.append("CASE_REPLACEMENT_FORBIDDEN")
    if observation.get("tuning_replay") is not False:
        errors.append("TUNING_REPLAY_FORBIDDEN")
    if observation.get("result_to_runtime_feedback") is not False:
        errors.append("RESULT_TO_RUNTIME_FEEDBACK_FORBIDDEN")

    visible_keys = observation.get("candidate_visible_keys", [])
    if not isinstance(visible_keys, list) or any(not isinstance(x, str) for x in visible_keys):
        errors.append("CANDIDATE_VISIBLE_KEYS_INVALID")
    else:
        leaked = sorted(FORBIDDEN_RECEIPT_KEYS & set(visible_keys))
        if leaked:
            errors.append("HIDDEN_INFORMATION_LEAK:" + ",".join(leaked))

    if load_bearing is False and observation.get("claims_behavior_credit") is True:
        errors.append("NON_LOAD_BEARING_CREDIT_FORBIDDEN")

    valid = not errors
    evidence_pass = bool(
        valid and load_bearing is True and direct is True and parent is True
    )

    return {
        "schema": SCHEMA,
        "behavior_id": behavior_id,
        "portfolio": portfolio,
        "case_id": observation.get("case_id"),
        "binding": binding["binding"],
        "binding_blob": binding["binding_blob"],
        "valid": valid,
        "errors": sorted(set(errors)),
        "load_bearing": load_bearing if isinstance(load_bearing, bool) else None,
        "direct_instrumentation_pass": direct if isinstance(direct, bool) else None,
        "parent_terminal_acceptance_pass": parent if isinstance(parent, bool) else None,
        "behavior_evidence_pass": evidence_pass,
        "standalone_terminal_population": False,
        "terminal_result_component": bool(valid and load_bearing is True),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def reduce_behavior_receipts(
    behavior_id: str,
    observations: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Fail closed over already-created parent terminal observations."""
    if behavior_id not in BINDINGS:
        raise ValueError("UNBOUND_MULTIPLEX_ROUTE:" + str(behavior_id))
    if not isinstance(observations, list) or not observations:
        raise ValueError("OBSERVATIONS_REQUIRED")

    receipts = [validate_parent_observation(behavior_id, row) for row in observations]
    invalid = [r for r in receipts if not r["valid"]]
    load_bearing = [r for r in receipts if r["load_bearing"] is True]
    failures = [r for r in load_bearing if not r["behavior_evidence_pass"]]

    status = "PASS_COMPONENT" if not invalid and load_bearing and not failures else "FAIL_CLOSED"
    return {
        "schema": SCHEMA,
        "behavior_id": behavior_id,
        "status": status,
        "receipt_count": len(receipts),
        "load_bearing_receipt_count": len(load_bearing),
        "invalid_receipt_count": len(invalid),
        "failed_load_bearing_receipt_count": len(failures),
        "receipts": receipts,
        "standalone_terminal_population": False,
        "rule": (
            "ONLY_LOAD_BEARING_PARENT_PORTFOLIO_OBSERVATIONS_COUNT__"
            "DIRECT_INSTRUMENTATION_AND_PARENT_TERMINAL_ACCEPTANCE_MUST_BOTH_PASS__"
            "NO_CASE_REPLACEMENT__NO_TUNING_REPLAY__NO_CROSS_BEHAVIOR_INHERITANCE"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
