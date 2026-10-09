"""Fail-closed claim-scoped certificate registry for CCRT roots."""

from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import (
    CORE_FIELDS,
    validate_claim,
)

SCHEMA = "PROJECT_BRAIN_COVERAGE_COMPLETENESS_CLAIM_ROOT_CERTIFICATE_REGISTRY_V1"
NAMESPACE = "PROJECT_BRAIN_COVERAGE_COMPLETENESS_ROOTS_V1"
CLAIM_SCOPE_PATH = "canonical/governance/COVERAGE_COMPLETENESS_CLAIM_SCOPE_V1.json"
ROOT_IDS = (
    "CC_R1_REALITY_CONTAINMENT_V1",
    "CC_R2_MISSION_SOUNDNESS_V1",
    "CC_R3_TERMINAL_CLOSURE_V1",
)
OPEN = "OPEN_CLAIM_ROOT_CERTIFICATE"
PROVED = "PROVED_CURRENT"
ALLOWED_STATUSES = frozenset({OPEN, PROVED})


def canonical_claim_binding(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        **{field: claim.get(field) for field in CORE_FIELDS},
    }


def _authority_errors(
    payload: Any,
    *,
    label: str,
    root_id: str,
    claim_binding: Mapping[str, Any],
    current_mission_blob_sha: str,
) -> list[str]:
    if not isinstance(payload, Mapping):
        return [f"{label}_MISSING:{root_id}"]
    errors: list[str] = []
    if payload.get("root_id") != root_id:
        errors.append(f"{label}_ROOT_ID_MISMATCH:{root_id}")
    if payload.get("mission_blob_sha") != current_mission_blob_sha:
        errors.append(f"{label}_MISSION_DRIFT:{root_id}")
    if payload.get("claim_binding") != claim_binding:
        errors.append(f"{label}_CLAIM_BINDING_MISMATCH:{root_id}")
    if not isinstance(payload.get("path"), str) or not payload.get("path"):
        errors.append(f"{label}_PATH_MISSING:{root_id}")
    if not isinstance(payload.get("git_blob_sha"), str) or not payload.get("git_blob_sha"):
        errors.append(f"{label}_CONTENT_ADDRESS_MISSING:{root_id}")
    return errors


def validate(
    registry: Mapping[str, Any],
    *,
    current_mission_blob_sha: str,
    current_claim_scope_blob_sha: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(registry, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["REGISTRY_NOT_OBJECT"],
            "terminal_credit_delta": 0,
        }

    if registry.get("schema") != SCHEMA:
        errors.append("SCHEMA_DRIFT")
    if registry.get("namespace") != NAMESPACE:
        errors.append("NAMESPACE_DRIFT")

    mission = registry.get("mission_binding") or {}
    if mission.get("path") != "canonical/governance/CURRENT_MISSION_OBJECTIVE.json":
        errors.append("MISSION_PATH_DRIFT")
    if mission.get("git_blob_sha") != current_mission_blob_sha:
        errors.append("MISSION_BLOB_STALE")

    scope = registry.get("claim_scope_binding") or {}
    if scope.get("path") != CLAIM_SCOPE_PATH:
        errors.append("CLAIM_SCOPE_PATH_DRIFT")
    if scope.get("git_blob_sha") != current_claim_scope_blob_sha:
        errors.append("CLAIM_SCOPE_BLOB_STALE")

    instances = registry.get("claim_instances")
    if not isinstance(instances, list):
        errors.append("CLAIM_INSTANCES_NOT_LIST")
        instances = []

    seen_claim_ids: set[str] = set()
    closed_claim_ids: list[str] = []
    total_open = 0
    total_proved = 0

    for index, instance in enumerate(instances):
        prefix = f"CLAIM_{index}"
        if not isinstance(instance, Mapping):
            errors.append(prefix + ":INSTANCE_NOT_OBJECT")
            continue

        claim = instance.get("claim")
        claim_check = validate_claim(
            claim,
            current_mission_blob_sha=current_mission_blob_sha,
        )
        for err in claim_check.get("errors", []):
            errors.append(prefix + ":" + err)
        if not isinstance(claim, Mapping):
            continue

        claim_id = claim.get("claim_id")
        if isinstance(claim_id, str):
            if claim_id in seen_claim_ids:
                errors.append(prefix + ":DUPLICATE_CLAIM_ID")
            seen_claim_ids.add(claim_id)

        slots = instance.get("certificate_slots")
        if not isinstance(slots, list) or len(slots) != len(ROOT_IDS):
            errors.append(prefix + ":CERTIFICATE_SLOT_SHAPE_INVALID")
            continue

        expected_binding = canonical_claim_binding(claim)
        seen_roots: set[str] = set()
        local_open = 0
        local_proved = 0
        local_error_count_before = len(errors)

        for slot in slots:
            if not isinstance(slot, Mapping):
                errors.append(prefix + ":SLOT_NOT_OBJECT")
                continue
            root_id = slot.get("root_id")
            if root_id not in ROOT_IDS:
                errors.append(prefix + f":INVALID_ROOT_ID:{root_id}")
                continue
            if root_id in seen_roots:
                errors.append(prefix + f":DUPLICATE_ROOT_SLOT:{root_id}")
            seen_roots.add(root_id)

            if slot.get("claim_id") != claim_id:
                errors.append(prefix + f":SLOT_CLAIM_ID_MISMATCH:{root_id}")

            status = slot.get("status")
            if status not in ALLOWED_STATUSES:
                errors.append(prefix + f":INVALID_STATUS:{root_id}")
                continue

            if status == OPEN:
                local_open += 1
                if (
                    slot.get("certificate") is not None
                    or slot.get("independent_verification") is not None
                ):
                    errors.append(prefix + f":OPEN_SLOT_HAS_AUTHORITY_PAYLOAD:{root_id}")
                continue

            local_proved += 1
            cert = slot.get("certificate")
            verify = slot.get("independent_verification")
            for err in _authority_errors(
                cert,
                label="CERTIFICATE",
                root_id=root_id,
                claim_binding=expected_binding,
                current_mission_blob_sha=current_mission_blob_sha,
            ):
                errors.append(prefix + ":" + err)
            for err in _authority_errors(
                verify,
                label="VERIFICATION",
                root_id=root_id,
                claim_binding=expected_binding,
                current_mission_blob_sha=current_mission_blob_sha,
            ):
                errors.append(prefix + ":" + err)
            if isinstance(cert, Mapping) and isinstance(verify, Mapping):
                if (
                    cert.get("path") == verify.get("path")
                    and cert.get("git_blob_sha") == verify.get("git_blob_sha")
                ):
                    errors.append(prefix + f":VERIFICATION_NOT_INDEPENDENT:{root_id}")

        if seen_roots != set(ROOT_IDS):
            errors.append(prefix + ":ROOT_SLOT_COVERAGE_INCOMPLETE")
        if instance.get("proved_root_certificates") != local_proved:
            errors.append(prefix + ":PROVED_COUNT_DRIFT")
        if instance.get("open_root_certificates") != local_open:
            errors.append(prefix + ":OPEN_COUNT_DRIFT")

        locally_clean = len(errors) == local_error_count_before
        claim_closed = locally_clean and local_proved == len(ROOT_IDS)
        if instance.get("r4_claim_proof_closure") is not claim_closed:
            errors.append(prefix + ":R4_CLAIM_PROOF_CLOSURE_FLAG_DRIFT")
        if claim_closed and isinstance(claim_id, str):
            closed_claim_ids.append(claim_id)
        total_open += local_open
        total_proved += local_proved

    if registry.get("registered_claim_count") != len(instances):
        errors.append("REGISTERED_CLAIM_COUNT_DRIFT")
    if registry.get("currently_open_root_certificates") != total_open:
        errors.append("OPEN_COUNT_DRIFT")
    if registry.get("currently_proved_root_certificates") != total_proved:
        errors.append("PROVED_COUNT_DRIFT")
    if registry.get("claim_proof_closure_count") != len(closed_claim_ids):
        errors.append("CLAIM_PROOF_CLOSURE_COUNT_DRIFT")

    for forbidden in (
        "checkpoint_completion",
        "global_root_closure",
        "global_open_ended_mission_completion",
    ):
        if registry.get(forbidden) is not False:
            errors.append(forbidden.upper() + "_FORBIDDEN")

    if (registry.get("accounting") or {}).get("terminal_credit_delta") != 0:
        errors.append("UNAUTHORIZED_TERMINAL_CREDIT")

    return {
        "pass": not errors,
        "status": (
            "PASS__CLAIM_SCOPED_ROOT_CERTIFICATE_REGISTRY"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": errors,
        "registered_claim_count": len(instances),
        "open_root_certificate_count": total_open,
        "proved_root_certificate_count": total_proved,
        "claim_proof_closure_count": len(closed_claim_ids),
        "closed_claim_ids": closed_claim_ids,
        "checkpoint_completion": False,
        "global_root_closure": False,
        "global_open_ended_mission_completion": False,
        "terminal_credit_delta": 0,
    }
