"""Structural R10 proof-slot verifier.

This module converts the conservative R10 decision constitution into executable
proof-slot checks. It verifies policy structure and content-addressed receipts;
it does not assert that the underlying world facts are true.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

CLAIM_ID = "205a864e7d7a56a14a46bb75923cc9b11126d479676d26d88803831da1197294"
ROOT_ID = "R10_ANALYSIS_DECISION"
LEAF_ID = "PQ::R10_ANALYSIS_DECISION::EXECUTION"
CONSTITUTION_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_DECISION_CONSTITUTION_V1"
DECISION_SCHEMA = "PROJECT_BRAIN_DECISION_SUFFICIENT_GAP_CONTRACT_V1"
MINIMUM_INFORMATION_SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT_V1"

REQUIRED_SLOTS = (
    "target_and_hard_constraints_frozen",
    "decision_state_lossless",
    "uncertainty_semantics_typed",
    "aggregation_and_risk_policy_precommitted",
    "veto_constraints_preserved",
    "model_or_analysis_multiplicity_resolved_or_escalated",
    "evidence_packet_complete",
    "stopping_rule_precommitted",
    "absolute_floor_not_inferred_from_weak_baseline",
)

_HEX = frozenset("0123456789abcdef")


def _sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in _HEX for ch in value.lower())
    )


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_PROOF_SLOT_VERIFIER_V1",
        "status": status,
        "pass": passed,
        "claim_id": CLAIM_ID,
        "root_id": ROOT_ID,
        "leaf_id": LEAF_ID,
        "structural_policy_compliance_only": True,
        "underlying_fact_truth_authority": False,
        "detection_completeness_proved": False,
        "whole_leaf_property_truth_proved": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _result(ok: bool, reason: str | None = None, **extra: Any) -> dict[str, Any]:
    if ok:
        return {**_base("PASS__R10_STRUCTURAL_PROOF_SLOTS_SATISFIED", passed=True), **extra}
    return {
        **_base("OPEN__R10_STRUCTURAL_PROOF_SLOT_REQUIRED", passed=False),
        "reason": reason,
        **extra,
    }


def _constitution_ok(c: Mapping[str, Any]) -> tuple[bool, str | None]:
    if c.get("schema") != CONSTITUTION_SCHEMA:
        return False, "CONSTITUTION_SCHEMA_INVALID"
    if c.get("root_id") != ROOT_ID or c.get("leaf_id") != LEAF_ID:
        return False, "CONSTITUTION_SCOPE_MISMATCH"
    if c.get("claim_id") != CLAIM_ID:
        return False, "CONSTITUTION_CLAIM_MISMATCH"
    boundary = c.get("authority_boundary")
    if not isinstance(boundary, Mapping):
        return False, "CONSTITUTION_AUTHORITY_BOUNDARY_MISSING"
    for key in (
        "policy_file_can_invent_user_utility",
        "policy_file_can_invent_risk_tolerance",
        "policy_file_can_invent_normative_weights",
        "policy_file_can_waive_hard_constraint",
        "policy_file_can_grant_property_truth",
        "policy_file_can_grant_quality_authority",
    ):
        if boundary.get(key) is not False:
            return False, "CONSTITUTION_AUTHORITY_OVERCLAIM:" + key
    return True, None


def evaluate(
    *,
    claim_id: str,
    constitution: Mapping[str, Any],
    decision_contract: Mapping[str, Any],
    minimum_information_contract: Mapping[str, Any],
    case_context: Mapping[str, Any],
) -> dict[str, Any]:
    if claim_id != CLAIM_ID:
        return _result(False, "CLAIM_ID_MISMATCH")

    ok, reason = _constitution_ok(constitution)
    if not ok:
        return _result(False, reason)

    slots: dict[str, bool] = {}
    blockers: dict[str, list[str]] = {slot: [] for slot in REQUIRED_SLOTS}

    # 1. Frozen target and hard constraints.
    target = case_context.get("target")
    target = target if isinstance(target, Mapping) else {}
    slots["target_and_hard_constraints_frozen"] = (
        _sha(target.get("target_spec_sha256"))
        and _sha(target.get("hard_constraints_sha256"))
        and _sha(target.get("freeze_receipt_sha256"))
    )
    if not slots["target_and_hard_constraints_frozen"]:
        blockers["target_and_hard_constraints_frozen"].append(
            "CONTENT_ADDRESSED_TARGET_CONSTRAINT_FREEZE_RECEIPT_REQUIRED"
        )

    # 2. Lossless decision state.
    slots["decision_state_lossless"] = (
        decision_contract.get("schema") == DECISION_SCHEMA
        and decision_contract.get("pass") is True
        and decision_contract.get("reduction_mode")
        == "LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION"
        and decision_contract.get("omitted_evidence") == []
        and _sha(decision_contract.get("source_contract_sha256"))
        and _sha(decision_contract.get("representation_sha256"))
    )
    if not slots["decision_state_lossless"]:
        blockers["decision_state_lossless"].append("LOSSLESS_DECISION_CONTRACT_REQUIRED")

    # 3. Typed uncertainty semantics.
    allowed_types = set(constitution.get("uncertainty_types") or [])
    uncertainty = case_context.get("uncertainty_claims")
    uncertainty = uncertainty if isinstance(uncertainty, list) else []
    uncertainty_ok = True
    for row in uncertainty:
        if not isinstance(row, Mapping) or row.get("type") not in allowed_types:
            uncertainty_ok = False
            break
        source_type = row.get("source_type")
        if source_type is not None and source_type != row.get("type"):
            if not _sha(row.get("adapter_receipt_sha256")):
                uncertainty_ok = False
                break
    slots["uncertainty_semantics_typed"] = uncertainty_ok
    if not uncertainty_ok:
        blockers["uncertainty_semantics_typed"].append(
            "TYPED_UNCERTAINTY_OR_CROSS_TYPE_ADAPTER_REQUIRED"
        )

    # 4. Aggregation + risk policy precommit.
    policy = case_context.get("decision_policy")
    policy = policy if isinstance(policy, Mapping) else {}
    safe_modes = set(
        (constitution.get("safe_default_modes") or {}).get(
            "aggregation_modes_without_extra_normative_authority"
        )
        or []
    )
    aggregation_mode = policy.get("aggregation_mode")
    aggregation_ok = aggregation_mode in safe_modes
    if not aggregation_ok:
        aggregation_ok = (
            isinstance(aggregation_mode, str)
            and bool(aggregation_mode)
            and _sha(policy.get("aggregation_authority_receipt_sha256"))
        )
    risk_required = policy.get("risk_threshold_required") is True
    risk_ok = (
        not risk_required
        or (
            _sha(policy.get("risk_policy_sha256"))
            and _sha(policy.get("risk_authority_receipt_sha256"))
        )
    )
    precommit_ok = _sha(policy.get("precommit_receipt_sha256"))
    slots["aggregation_and_risk_policy_precommitted"] = (
        aggregation_ok and risk_ok and precommit_ok
    )
    if not slots["aggregation_and_risk_policy_precommitted"]:
        blockers["aggregation_and_risk_policy_precommitted"].append(
            "AUTHORIZED_PRECOMMITTED_AGGREGATION_AND_RISK_POLICY_OR_ABSTENTION_REQUIRED"
        )

    # 5. Noncompensatory hard constraints / vetoes.
    vetoes = case_context.get("veto_constraints")
    vetoes = vetoes if isinstance(vetoes, list) else []
    veto_ok = True
    for row in vetoes:
        if (
            not isinstance(row, Mapping)
            or not isinstance(row.get("id"), str)
            or not row.get("id")
            or row.get("noncompensatory") is not True
            or row.get("satisfied") is not True
        ):
            veto_ok = False
            break
    slots["veto_constraints_preserved"] = veto_ok
    if not veto_ok:
        blockers["veto_constraints_preserved"].append(
            "ALL_DECLARED_VETOES_MUST_BE_NONCOMPENSATORY_AND_SATISFIED"
        )

    # 6. Model / analysis multiplicity.
    models = case_context.get("analysis_models")
    models = models if isinstance(models, list) else []
    decisions = {
        row.get("decision")
        for row in models
        if isinstance(row, Mapping) and row.get("decision") is not None
    }
    multiplicity_ok = len(decisions) <= 1
    if not multiplicity_ok:
        multiplicity_ok = _sha(
            case_context.get("multiplicity_escalation_receipt_sha256")
        )
    slots["model_or_analysis_multiplicity_resolved_or_escalated"] = multiplicity_ok
    if not multiplicity_ok:
        blockers["model_or_analysis_multiplicity_resolved_or_escalated"].append(
            "DECISION_SENSITIVE_MULTIPLICITY_REQUIRES_COMMON_DECISION_OR_ESCALATION"
        )

    # 7. Evidence packet completeness relative to declared evidence basis.
    packet = case_context.get("evidence_packet")
    packet = packet if isinstance(packet, Mapping) else {}
    declared = packet.get("declared_evidence_ids")
    included = packet.get("included_evidence_ids")
    omissions = packet.get("omissions")
    declared_set = set(declared) if isinstance(declared, list) else set()
    included_set = set(included) if isinstance(included, list) else set()
    omissions = omissions if isinstance(omissions, list) else []
    omission_ids: set[str] = set()
    omission_ok = True
    for row in omissions:
        if (
            not isinstance(row, Mapping)
            or not isinstance(row.get("evidence_id"), str)
            or not _sha(row.get("omission_certificate_sha256"))
        ):
            omission_ok = False
            break
        omission_ids.add(row["evidence_id"])
    packet_ok = (
        isinstance(declared, list)
        and isinstance(included, list)
        and omission_ok
        and declared_set == included_set | omission_ids
        and not (included_set & omission_ids)
        and _sha(packet.get("packet_sha256"))
        and _sha(packet.get("declared_basis_sha256"))
    )
    slots["evidence_packet_complete"] = packet_ok
    if not packet_ok:
        blockers["evidence_packet_complete"].append(
            "DECLARED_EVIDENCE_BASIS_MUST_EQUAL_INCLUDED_PLUS_CERTIFIED_OMISSIONS"
        )

    # Minimum-information contract is an additional anti-broad-acquisition fence.
    if minimum_information_contract.get("schema") != MINIMUM_INFORMATION_SCHEMA:
        slots["evidence_packet_complete"] = False
        blockers["evidence_packet_complete"].append(
            "MINIMUM_INFORMATION_CONTRACT_REQUIRED"
        )
    else:
        requests = minimum_information_contract.get("requests")
        if not isinstance(requests, list) or any(
            not isinstance(row, Mapping)
            or row.get("broad_acquisition_forbidden_without_minimality_proof")
            is not True
            for row in requests
        ):
            slots["evidence_packet_complete"] = False
            blockers["evidence_packet_complete"].append(
                "BROAD_ACQUISITION_MINIMALITY_FENCE_REQUIRED"
            )

    # 8. Stopping rule precommit.
    stopping = case_context.get("stopping_rule")
    stopping = stopping if isinstance(stopping, Mapping) else {}
    slots["stopping_rule_precommitted"] = (
        _sha(stopping.get("rule_sha256"))
        and _sha(stopping.get("precommit_receipt_sha256"))
        and stopping.get("frozen_before_outcome_reveal") is True
    )
    if not slots["stopping_rule_precommitted"]:
        blockers["stopping_rule_precommitted"].append(
            "CONTENT_ADDRESSED_PREOUTCOME_STOPPING_RULE_REQUIRED"
        )

    # 9. Absolute floor semantics.
    quality = case_context.get("quality_claim")
    quality = quality if isinstance(quality, Mapping) else {}
    absolute_claim = quality.get("claim_level") == "ABSOLUTE_PROFESSIONAL_EXCELLENCE"
    floor_ok = (
        not absolute_claim
        or (
            _sha(quality.get("absolute_floor_definition_sha256"))
            and _sha(quality.get("absolute_floor_evidence_sha256"))
        )
    )
    slots["absolute_floor_not_inferred_from_weak_baseline"] = floor_ok
    if not floor_ok:
        blockers["absolute_floor_not_inferred_from_weak_baseline"].append(
            "ABSOLUTE_EXCELLENCE_REQUIRES_INDEPENDENT_ABSOLUTE_FLOOR_EVIDENCE"
        )

    missing = [slot for slot in REQUIRED_SLOTS if not slots[slot]]
    if missing:
        return _result(
            False,
            "R10_STRUCTURAL_PROOF_SLOTS_INCOMPLETE",
            slot_results=slots,
            missing_slots=missing,
            slot_blockers={k: v for k, v in blockers.items() if v},
        )
    return _result(
        True,
        slot_results=slots,
        missing_slots=[],
        slot_blockers={},
    )
