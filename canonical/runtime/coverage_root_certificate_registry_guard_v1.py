"""Fail-closed validator for the coverage-completeness root certificate registry."""

from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import ALLOWED_KINDS, CORE_FIELDS, compute_claim_id


SCHEMA = "PROJECT_BRAIN_COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1"
NAMESPACE = "PROJECT_BRAIN_COVERAGE_COMPLETENESS_ROOTS_V1"
ROOTS = (
    ("CC_R1_REALITY_CONTAINMENT_V1", "R1", "B_real SUBSETEQ B_plus"),
    ("CC_R2_MISSION_SOUNDNESS_V1", "R2", "G_minus SUBSETEQ G_real"),
    ("CC_R3_TERMINAL_CLOSURE_V1", "R3", "B_plus SUBSETEQ G_minus"),
    ("CC_R4_PROOF_AUTHORITY_V1", "R4", "TRUSTWORTHY_PROOF_AND_REALIZATION(CC_R1,CC_R2,CC_R3)"),
)
CERTIFICATE_ROOT_IDS = tuple(x[0] for x in ROOTS[:3])
ALLOWED_SLOT_STATUSES = frozenset({"OPEN_NO_GLOBAL_CERTIFICATE_BOUND", "PROVED_CURRENT"})
CLAIM_BINDING_FIELDS = ("claim_id",) + CORE_FIELDS


def validate(
    registry: Mapping[str, Any],
    *,
    current_mission_pointer: Mapping[str, Any],
    current_mission_authority_blob_sha: str,
    current_mission_pointer_blob_sha: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(registry, Mapping):
        return {"pass": False, "status": "FAIL_CLOSED", "errors": ["REGISTRY_NOT_OBJECT"], "terminal_credit_delta": 0}

    if registry.get("schema") != SCHEMA:
        errors.append("SCHEMA_DRIFT")
    if registry.get("namespace") != NAMESPACE:
        errors.append("NAMESPACE_DRIFT")

    mission = registry.get("mission_binding") or {}
    if mission.get("pointer_path") != "canonical/governance/CURRENT_MISSION_OBJECTIVE.json":
        errors.append("MISSION_POINTER_PATH_DRIFT")
    authority = current_mission_pointer.get("authoritative_source") or {}
    if mission.get("authority_path") != authority.get("path"):
        errors.append("MISSION_AUTHORITY_PATH_DRIFT")
    if mission.get("authority_git_blob_sha") != current_mission_authority_blob_sha:
        errors.append("MISSION_AUTHORITY_BLOB_STALE")
    if mission.get("real_objective") != current_mission_pointer.get("real_objective"):
        errors.append("MISSION_OBJECTIVE_DRIFT")

    identities = registry.get("root_identities")
    if not isinstance(identities, list) or len(identities) != 4:
        errors.append("ROOT_IDENTITIES_SHAPE_INVALID")
        identities = []
    else:
        seen: set[str] = set()
        for i, expected in enumerate(ROOTS):
            row = identities[i]
            if not isinstance(row, Mapping):
                errors.append(f"ROOT_IDENTITY_NOT_OBJECT:{i}")
                continue
            cid, alias, claim = expected
            if row.get("canonical_id") != cid:
                errors.append(f"CANONICAL_ROOT_ID_DRIFT:{i}")
            if row.get("display_alias") != alias:
                errors.append(f"DISPLAY_ALIAS_DRIFT:{i}")
            if row.get("claim") != claim:
                errors.append(f"ROOT_CLAIM_DRIFT:{i}")
            if row.get("canonical_id") in seen:
                errors.append(f"DUPLICATE_CANONICAL_ROOT_ID:{i}")
            seen.add(row.get("canonical_id"))

    active_claim = registry.get("active_claim")
    active_claim_valid = active_claim is None or isinstance(active_claim, Mapping)
    if active_claim is not None:
        if not isinstance(active_claim, Mapping):
            errors.append("ACTIVE_CLAIM_NOT_OBJECT")
        else:
            for field in CORE_FIELDS:
                value = active_claim.get(field)
                if not isinstance(value, str) or not value:
                    errors.append("ACTIVE_CLAIM_INVALID_FIELD:" + field)
            if active_claim.get("claim_kind") not in ALLOWED_KINDS:
                errors.append("ACTIVE_CLAIM_KIND_NOT_ALLOWED")
            if current_mission_pointer_blob_sha is None:
                errors.append("CURRENT_MISSION_POINTER_BLOB_REQUIRED_FOR_ACTIVE_CLAIM")
            elif active_claim.get("mission_blob_sha") != current_mission_pointer_blob_sha:
                errors.append("ACTIVE_CLAIM_MISSION_BINDING_STALE")
            for field in ("scope_sha256", "target_predicate_sha256", "semantics_sha256"):
                value = active_claim.get(field)
                if isinstance(value, str) and (
                    len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
                ):
                    errors.append("ACTIVE_CLAIM_INVALID_SHA256:" + field)
            if active_claim.get("claim_id") != compute_claim_id(active_claim):
                errors.append("ACTIVE_CLAIM_ID_MISMATCH")
            if active_claim.get("terminal_credit_delta", 0) != 0:
                errors.append("ACTIVE_CLAIM_NONZERO_CREDIT_FORBIDDEN")

    alias = registry.get("alias_policy") or {}
    if alias.get("short_aliases_are_display_only") is not True:
        errors.append("SHORT_ALIAS_AUTHORITY_ENABLED")
    if alias.get("short_aliases_have_zero_cross_artifact_authority") is not True:
        errors.append("SHORT_ALIAS_CROSS_ARTIFACT_AUTHORITY_ENABLED")
    if alias.get("cross_artifact_binding_requires_namespace_and_canonical_id") is not True:
        errors.append("CANONICAL_ID_BINDING_NOT_REQUIRED")

    slots = registry.get("certificate_slots")
    if not isinstance(slots, list) or len(slots) != 3:
        errors.append("CERTIFICATE_SLOT_SHAPE_INVALID")
        slots = []

    open_ids: list[str] = []
    proved_ids: list[str] = []
    seen_slots: set[str] = set()
    for i, slot in enumerate(slots):
        if not isinstance(slot, Mapping):
            errors.append(f"CERTIFICATE_SLOT_NOT_OBJECT:{i}")
            continue
        root_id = slot.get("root_id")
        if root_id not in CERTIFICATE_ROOT_IDS:
            errors.append(f"INVALID_CERTIFICATE_ROOT_ID:{root_id}")
            continue
        if root_id in seen_slots:
            errors.append(f"DUPLICATE_CERTIFICATE_SLOT:{root_id}")
        seen_slots.add(root_id)
        status = slot.get("status")
        if status not in ALLOWED_SLOT_STATUSES:
            errors.append(f"INVALID_CERTIFICATE_STATUS:{root_id}")
            continue

        if status == "OPEN_NO_GLOBAL_CERTIFICATE_BOUND":
            open_ids.append(root_id)
            if slot.get("certificate") is not None or slot.get("independent_verification") is not None:
                errors.append(f"OPEN_SLOT_HAS_AUTHORITY_PAYLOAD:{root_id}")
        else:
            proved_ids.append(root_id)
            cert = slot.get("certificate")
            verify = slot.get("independent_verification")
            if active_claim is None:
                errors.append(f"PROVED_SLOT_WITHOUT_ACTIVE_CLAIM:{root_id}")
            if not isinstance(cert, Mapping):
                errors.append(f"PROVED_SLOT_CERTIFICATE_MISSING:{root_id}")
            else:
                if cert.get("root_id") != root_id:
                    errors.append(f"PROVED_SLOT_ROOT_ID_MISMATCH:{root_id}")
                if cert.get("mission_authority_blob_sha") != current_mission_authority_blob_sha:
                    errors.append(f"PROVED_SLOT_MISSION_AUTHORITY_DRIFT:{root_id}")
                if not isinstance(cert.get("path"), str) or not isinstance(cert.get("git_blob_sha"), str):
                    errors.append(f"PROVED_SLOT_CONTENT_ADDRESS_MISSING:{root_id}")
                claim_binding = cert.get("claim_binding")
                if isinstance(active_claim, Mapping):
                    if not isinstance(claim_binding, Mapping):
                        errors.append(f"PROVED_SLOT_CLAIM_BINDING_MISSING:{root_id}")
                    else:
                        for field in CLAIM_BINDING_FIELDS:
                            if claim_binding.get(field) != active_claim.get(field):
                                errors.append(f"PROVED_SLOT_CLAIM_BINDING_MISMATCH:{root_id}:{field}")
            if not isinstance(verify, Mapping) or not isinstance(verify.get("path"), str) or not isinstance(verify.get("git_blob_sha"), str):
                errors.append(f"PROVED_SLOT_INDEPENDENT_VERIFICATION_MISSING:{root_id}")
            elif isinstance(active_claim, Mapping) and verify.get("claim_id") != active_claim.get("claim_id"):
                errors.append(f"PROVED_SLOT_VERIFICATION_CLAIM_MISMATCH:{root_id}")

    if set(seen_slots) != set(CERTIFICATE_ROOT_IDS):
        errors.append("CERTIFICATE_SLOT_COVERAGE_INCOMPLETE")

    claimed_proved = registry.get("currently_proved_root_certificates")
    claimed_open = registry.get("currently_open_root_certificates")
    if claimed_proved != len(proved_ids):
        errors.append("PROVED_COUNT_DRIFT")
    if claimed_open != len(open_ids):
        errors.append("OPEN_COUNT_DRIFT")

    proof_closed = len(proved_ids) == 3 and not errors
    if registry.get("r4_proof_closure") is not proof_closed:
        errors.append("R4_PROOF_CLOSURE_FLAG_DRIFT")

    if (registry.get("accounting") or {}).get("terminal_credit_delta") != 0:
        errors.append("UNAUTHORIZED_TERMINAL_CREDIT")

    return {
        "pass": not errors,
        "status": "PASS__ROOT_CERTIFICATE_REGISTRY" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "open_root_ids": open_ids,
        "proved_root_ids": proved_ids,
        "r4_proof_closure": proof_closed,
        "terminal_credit_delta": 0,
    }
