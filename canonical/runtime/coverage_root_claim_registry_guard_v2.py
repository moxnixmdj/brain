"""Claim-scoped authority guard for coverage-completeness root certificates V2."""

from __future__ import annotations

from hashlib import sha1
from pathlib import Path
from typing import Any, Mapping, Optional

SCHEMA = "PROJECT_BRAIN_COVERAGE_COMPLETENESS_CLAIM_CERTIFICATE_REGISTRY_V2"
NAMESPACE = "PROJECT_BRAIN_COVERAGE_COMPLETENESS_ROOTS_V1"
ROOT_IDS = (
    "CC_R1_REALITY_CONTAINMENT_V1",
    "CC_R2_MISSION_SOUNDNESS_V1",
    "CC_R3_TERMINAL_CLOSURE_V1",
)
BINDING_FIELDS = (
    "claim_id",
    "scope_sha256",
    "semantics_sha256",
    "carrier_schema_id",
    "mission_id",
    "epoch_id",
    "canonical_generation",
)
HASH_FIELDS = ("claim_id", "scope_sha256", "semantics_sha256")
STATUSES = frozenset({"OPEN_NO_CLAIM_CERTIFICATE_BOUND", "PROVED_CURRENT"})


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def binding_key(value: Any) -> Optional[tuple[str, ...]]:
    if not isinstance(value, Mapping):
        return None
    if any(not isinstance(value.get(k), str) or not value.get(k) for k in BINDING_FIELDS):
        return None
    if any(not _is_sha256(value[k]) for k in HASH_FIELDS):
        return None
    return tuple(value[k] for k in BINDING_FIELDS)


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return sha1(header + payload).hexdigest()


def _check_ref(
    ref: Any,
    *,
    root_id: str,
    field: str,
    binding: Mapping[str, Any],
    mission_authority_blob_sha: str,
    repo_root: Optional[Path],
    errors: list[str],
) -> None:
    if not isinstance(ref, Mapping):
        errors.append(f"{field.upper()}_MISSING:{root_id}")
        return
    if ref.get("root_id") != root_id:
        errors.append(f"{field.upper()}_ROOT_ID_MISMATCH:{root_id}")
    if ref.get("claim_id") != binding.get("claim_id"):
        errors.append(f"{field.upper()}_CLAIM_ID_MISMATCH:{root_id}")
    if ref.get("mission_authority_blob_sha") != mission_authority_blob_sha:
        errors.append(f"{field.upper()}_MISSION_AUTHORITY_DRIFT:{root_id}")
    path = ref.get("path")
    blob = ref.get("git_blob_sha")
    if not isinstance(path, str) or not path or not isinstance(blob, str) or not blob:
        errors.append(f"{field.upper()}_CONTENT_ADDRESS_MISSING:{root_id}")
        return
    if path.startswith("/") or ".." in Path(path).parts:
        errors.append(f"{field.upper()}_PATH_INVALID:{root_id}")
        return
    if repo_root is not None:
        target = repo_root / path
        try:
            actual = _git_blob_sha(target)
        except OSError:
            errors.append(f"{field.upper()}_FILE_MISSING:{root_id}")
            return
        if actual != blob:
            errors.append(f"{field.upper()}_CONTENT_ADDRESS_MISMATCH:{root_id}")


def validate(
    registry: Mapping[str, Any],
    *,
    current_mission_pointer: Mapping[str, Any],
    current_mission_authority_blob_sha: str,
    repo_root: Optional[Path] = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(registry, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["REGISTRY_NOT_OBJECT"],
            "claims": [],
            "terminal_credit_delta": 0,
        }

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

    claims = registry.get("claims")
    if not isinstance(claims, list):
        errors.append("CLAIMS_NOT_LIST")
        claims = []

    summaries = []
    seen_keys: set[tuple[str, ...]] = set()
    seen_claim_ids: set[str] = set()

    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        binding = claim.get("binding")
        key = binding_key(binding)
        if key is None:
            errors.append(f"CLAIM_BINDING_INVALID:{i}")
            continue
        claim_id = binding["claim_id"]
        if key in seen_keys:
            errors.append(f"DUPLICATE_CLAIM_BINDING:{claim_id}")
        seen_keys.add(key)
        if claim_id in seen_claim_ids:
            errors.append(f"DUPLICATE_CLAIM_ID:{claim_id}")
        seen_claim_ids.add(claim_id)

        slots = claim.get("certificate_slots")
        if not isinstance(slots, list) or len(slots) != 3:
            errors.append(f"CERTIFICATE_SLOT_SHAPE_INVALID:{claim_id}")
            slots = []

        proved = []
        open_ids = []
        seen_roots = set()
        for slot in slots:
            if not isinstance(slot, Mapping):
                errors.append(f"CERTIFICATE_SLOT_NOT_OBJECT:{claim_id}")
                continue
            root_id = slot.get("root_id")
            if root_id not in ROOT_IDS:
                errors.append(f"INVALID_CERTIFICATE_ROOT_ID:{claim_id}:{root_id}")
                continue
            if root_id in seen_roots:
                errors.append(f"DUPLICATE_CERTIFICATE_SLOT:{claim_id}:{root_id}")
            seen_roots.add(root_id)
            status = slot.get("status")
            if status not in STATUSES:
                errors.append(f"INVALID_CERTIFICATE_STATUS:{claim_id}:{root_id}")
                continue
            if status == "OPEN_NO_CLAIM_CERTIFICATE_BOUND":
                open_ids.append(root_id)
                if slot.get("certificate") is not None or slot.get("independent_verification") is not None:
                    errors.append(f"OPEN_SLOT_HAS_AUTHORITY_PAYLOAD:{claim_id}:{root_id}")
            else:
                proved.append(root_id)
                _check_ref(
                    slot.get("certificate"),
                    root_id=root_id,
                    field="certificate",
                    binding=binding,
                    mission_authority_blob_sha=current_mission_authority_blob_sha,
                    repo_root=repo_root,
                    errors=errors,
                )
                _check_ref(
                    slot.get("independent_verification"),
                    root_id=root_id,
                    field="independent_verification",
                    binding=binding,
                    mission_authority_blob_sha=current_mission_authority_blob_sha,
                    repo_root=repo_root,
                    errors=errors,
                )

        if set(seen_roots) != set(ROOT_IDS):
            errors.append(f"CERTIFICATE_SLOT_COVERAGE_INCOMPLETE:{claim_id}")

        closure = len(proved) == 3 and not open_ids
        if claim.get("r4_proof_closure") is not closure:
            errors.append(f"R4_PROOF_CLOSURE_FLAG_DRIFT:{claim_id}")

        summaries.append({
            "binding": dict(binding),
            "proved_root_ids": proved,
            "open_root_ids": open_ids,
            "r4_proof_closure": closure,
        })

    if registry.get("global_mission_completion_derivable") is not False:
        errors.append("GLOBAL_MISSION_COMPLETION_AUTHORITY_ENABLED")
    if (registry.get("accounting") or {}).get("terminal_credit_delta") != 0:
        errors.append("UNAUTHORIZED_TERMINAL_CREDIT")

    return {
        "pass": not errors,
        "status": "PASS__CLAIM_ROOT_CERTIFICATE_REGISTRY" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "claims": summaries,
        "registered_claim_count": len(summaries),
        "closed_claim_count": sum(1 for x in summaries if x["r4_proof_closure"]),
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }


def find_exact_claim(
    checked: Mapping[str, Any],
    expected_binding: Mapping[str, Any],
) -> Optional[Mapping[str, Any]]:
    expected = binding_key(expected_binding)
    if expected is None:
        return None
    for claim in checked.get("claims", []):
        if binding_key(claim.get("binding")) == expected:
            return claim
    return None
