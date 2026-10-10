"""Claim-bound R10 execution enforcement guard.

This guard closes the detection-to-enforcement seam for the admitted R10
execution whole-leaf claim. It consumes already-detected decision-relevant
defeaters and already-compiled lossless decision/minimum-information contracts.
It does NOT claim that every real defeater is detected.

A detected known R10 defeater, an unmapped material false-certification signal,
or an escalation-triggering near miss blocks ordinary certification and routes
to escalation/abstention. A clean path is merely eligible for downstream scoped
certificate verification.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

CLAIM_ID = "205a864e7d7a56a14a46bb75923cc9b11126d479676d26d88803831da1197294"
LEAF_ID = "PQ::R10_ANALYSIS_DECISION::EXECUTION"
ROOT_ID = "R10_ANALYSIS_DECISION"

DECISION_SCHEMA = "PROJECT_BRAIN_DECISION_SUFFICIENT_GAP_CONTRACT_V1"
MINIMUM_INFORMATION_SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT_V1"

KNOWN_R10_DEFEATERS = frozenset({
    "C03_AGENDA_OMISSION",
    "C14_ONTOLOGY_CLONING",
    "C15_NORMALIZATION_RANGE_EXPLOIT",
    "C26_UNCERTAINTY_SEMANTICS_LAUNDERING",
    "C37_STRATEGIC_PREFERENCE_REPORT",
    "C38_ELICITATION_PERFORMATIVITY",
    "C44_TAIL_RISK_AVERAGE_MASKING",
    "C48_ANALYSIS_CHERRY_PICK",
    "C49_FORBIDDEN_COMPENSATION",
    "C50_BASELINE_LAUNDERED_EXCELLENCE",
    "C51_MODEL_MULTIPLICITY_DECISION_SENSITIVE",
    "C52_RISK_POLICY_POST_HOC",
    "C69_CROSS_MODEL_CALIBRATION_SIGN_REVERSAL",
    "C71_JOINT_ASSURANCE_MULTIPLICITY",
    "C72_UNGROUNDED_RISK_TOLERANCE",
    "C76_SELECTIVE_EVIDENCE_PACKET",
    "C80_OPTIONAL_STOPPING_OR_REPEATED_TESTING",
})

NEAR_MISS_TO_TRIGGER = {
    "near_decision_boundary": "NEAR_DECISION_BOUNDARY",
    "model_or_analysis_multiplicity_decision_sensitive":
        "MODEL_OR_ANALYSIS_MULTIPLICITY_DECISION_SENSITIVE",
    "high_consequence_or_veto_dimension": "HIGH_CONSEQUENCE_OR_VETO_DIMENSION",
    "material_invariance_failure": "MATERIAL_INVARIANCE_FAILURE",
    "population_context_operator_or_time_transport_gap":
        "POPULATION_CONTEXT_OPERATOR_OR_TIME_TRANSPORT_GAP",
}

REQUIRED_PROOF_SLOTS = frozenset({
    "target_and_hard_constraints_frozen",
    "decision_state_lossless",
    "uncertainty_semantics_typed",
    "aggregation_and_risk_policy_precommitted",
    "veto_constraints_preserved",
    "model_or_analysis_multiplicity_resolved_or_escalated",
    "evidence_packet_complete",
    "stopping_rule_precommitted",
    "absolute_floor_not_inferred_from_weak_baseline",
})


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_EXECUTION_GUARD_V1",
        "status": status,
        "pass": passed,
        "leaf_id": LEAF_ID,
        "claim_id": CLAIM_ID,
        "root_id": ROOT_ID,
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


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {**_base("FAIL_CLOSED", passed=False), "reason": reason, **extra}


def _r10_catalog_ids(catalog: Mapping[str, Any]) -> set[str]:
    rows = catalog.get("defeaters")
    if not isinstance(rows, list):
        rows = catalog.get("attack_classes")
    if not isinstance(rows, list):
        rows = catalog.get("nodes")
    if not isinstance(rows, list):
        rows = catalog.get("challenges")
    if not isinstance(rows, list):
        return set()
    out: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        targets = row.get("root_ids")
        if not isinstance(targets, list):
            targets = row.get("target_root_ids")
        if ROOT_ID in (targets or []):
            did = row.get("id")
            if isinstance(did, str) and did:
                out.add(did)
    return out


def _profile_triggers(profile: Mapping[str, Any]) -> set[str]:
    values = profile.get("escalation_triggers")
    return {x for x in (values or []) if isinstance(x, str) and x}


def evaluate(
    *,
    claim_id: str,
    decision_contract: Mapping[str, Any],
    minimum_information_contract: Mapping[str, Any],
    execution_profile: Mapping[str, Any],
    defeater_catalog: Mapping[str, Any],
    detected_defeater_ids: Sequence[str] = (),
    near_miss_signals: Mapping[str, bool] | None = None,
    proof_slots: Mapping[str, bool] | None = None,
    unmapped_material_false_certification_defeater: bool = False,
) -> dict[str, Any]:
    if claim_id != CLAIM_ID:
        return _fail("CLAIM_ID_MISMATCH")

    catalog_ids = _r10_catalog_ids(defeater_catalog)
    if catalog_ids != set(KNOWN_R10_DEFEATERS):
        return _fail(
            "R10_DEFEATER_CATALOG_DRIFT",
            expected_ids=sorted(KNOWN_R10_DEFEATERS),
            observed_ids=sorted(catalog_ids),
        )

    triggers = _profile_triggers(execution_profile)
    required_profile_triggers = set(NEAR_MISS_TO_TRIGGER.values()) | {
        "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
    }
    missing_triggers = sorted(required_profile_triggers - triggers)
    if missing_triggers:
        return _fail("PROFILE_ESCALATION_TRIGGER_MISSING", missing_triggers=missing_triggers)

    if decision_contract.get("schema") != DECISION_SCHEMA:
        return _fail("DECISION_CONTRACT_SCHEMA_INVALID")
    if decision_contract.get("pass") is not True:
        return _fail("DECISION_CONTRACT_NOT_PASS")
    if decision_contract.get("reduction_mode") != "LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION":
        return _fail("DECISION_CONTRACT_NOT_LOSSLESS")
    if decision_contract.get("omitted_evidence") != []:
        return _fail("DECISION_CONTRACT_OMITS_EVIDENCE")

    if minimum_information_contract.get("schema") != MINIMUM_INFORMATION_SCHEMA:
        return _fail("MINIMUM_INFORMATION_SCHEMA_INVALID")
    requests = minimum_information_contract.get("requests")
    if not isinstance(requests, list):
        return _fail("MINIMUM_INFORMATION_REQUESTS_INVALID")
    if any(
        not isinstance(row, Mapping)
        or row.get("broad_acquisition_forbidden_without_minimality_proof") is not True
        for row in requests
    ):
        return _fail("MINIMUM_INFORMATION_BROAD_ACQUISITION_NOT_FORBIDDEN")

    detected = [x for x in detected_defeater_ids if isinstance(x, str)]
    unknown_detected = sorted(set(detected) - set(KNOWN_R10_DEFEATERS))
    if unknown_detected:
        return {
            **_base("ESCALATE__UNMAPPED_DETECTED_DEFEATER", passed=False),
            "detected_defeater_ids": sorted(set(detected)),
            "unknown_detected_defeater_ids": unknown_detected,
            "required_trigger": "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
            "ordinary_certificate_path_allowed": False,
        }
    if detected:
        return {
            **_base("ABSTAIN_OR_ESCALATE__KNOWN_R10_DEFEATER_ACTIVE", passed=False),
            "detected_defeater_ids": sorted(set(detected)),
            "ordinary_certificate_path_allowed": False,
        }

    if unmapped_material_false_certification_defeater:
        return {
            **_base("ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER", passed=False),
            "required_trigger": "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
            "ordinary_certificate_path_allowed": False,
        }

    active_near_misses: list[str] = []
    for signal, trigger in NEAR_MISS_TO_TRIGGER.items():
        if (near_miss_signals or {}).get(signal) is True:
            active_near_misses.append(trigger)
    if active_near_misses:
        return {
            **_base("ESCALATE__R10_NEAR_MISS_TRIGGER", passed=False),
            "active_escalation_triggers": sorted(active_near_misses),
            "ordinary_certificate_path_allowed": False,
        }

    slots = proof_slots or {}
    missing_slots = sorted(
        slot for slot in REQUIRED_PROOF_SLOTS if slots.get(slot) is not True
    )
    if missing_slots:
        return {
            **_base("OPEN__R10_EXECUTION_PROOF_SLOT_REQUIRED", passed=False),
            "missing_proof_slots": missing_slots,
            "ordinary_certificate_path_allowed": False,
        }

    return {
        **_base("PASS__R10_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION", passed=True),
        "detected_defeater_ids": [],
        "active_escalation_triggers": [],
        "proof_slots_satisfied": sorted(REQUIRED_PROOF_SLOTS),
        "ordinary_certificate_path_allowed": True,
        "property_scope": (
            "DETECTION_TO_ENFORCEMENT_AND_DECLARED_PROOF_SLOT_GATE_ONLY__"
            "DEFEATER_DETECTION_COMPLETENESS_SEPARATE"
        ),
    }
