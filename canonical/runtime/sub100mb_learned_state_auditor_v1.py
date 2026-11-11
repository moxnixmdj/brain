#!/usr/bin/env python3
"""Fail-closed byte auditor for the sub-100MB learned-state experiment.

This module is accounting/research infrastructure only. It grants no
capability, acceptance, family, ownership, execution, or promotion credit.

The scored capsule must place every persistent state artifact inside one
dedicated state root. Every file in that root must be present in the manifest,
content-addressed, classified, and byte-counted. Unknown state fails closed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_SCHEMA = "PROJECT_BRAIN_SUB100MB_LEARNED_STATE_CONTRACT_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_LEARNED_STATE_MANIFEST_V1"
MAX_LEARNED_BYTES_EXCLUSIVE = 100_000_000

LEARNED = "LEARNED"
NONLEARNED = "NONLEARNED"
ALLOWED_CLASSIFICATIONS = {LEARNED, NONLEARNED}

FORBIDDEN_PROVIDER_ROLES = {
    "REMOTE_FRONTIER_MODEL",
    "REMOTE_GENERAL_REASONING_MODEL",
    "REMOTE_LEARNED_CAPABILITY_PROVIDER",
}

ALLOWED_EXTERNAL_PROVIDER_ROLES = {
    "RAW_KNOWLEDGE_SOURCE",
    "STRUCTURED_KNOWLEDGE_SOURCE",
    "SEARCH_INDEX",
    "DETERMINISTIC_TOOL",
}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _valid_sha256(value: Any) -> bool:
    s = _norm(value).lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _safe_relpath(value: Any) -> str | None:
    raw = _norm(value).replace("\\", "/")
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute() or ".." in p.parts:
        return None
    normalized = p.as_posix()
    if normalized in {".", ""}:
        return None
    return normalized


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Audit declarations without touching the filesystem.

    This is useful for planning and schema checks. A real scored pass must use
    audit_state_root(), which verifies exact file bytes and full inventory.
    """
    reasons: list[str] = []

    if _norm(manifest.get("schema")) != MANIFEST_SCHEMA:
        reasons.append("INVALID_MANIFEST_SCHEMA")

    if not _norm(manifest.get("capsule_id")):
        reasons.append("MISSING_CAPSULE_ID")

    if manifest.get("inventory_complete") is not True:
        reasons.append("INVENTORY_COMPLETENESS_NOT_ASSERTED")

    if manifest.get("dependency_closure_complete") is not True:
        reasons.append("DEPENDENCY_CLOSURE_NOT_ASSERTED")

    if manifest.get("same_capsule_for_all_predicates") is not True:
        reasons.append("SAME_CAPSULE_FOR_ALL_PREDICATES_NOT_ASSERTED")

    if manifest.get("frozen_acceptance_predicate_count") != 38:
        reasons.append("FROZEN_ACCEPTANCE_PREDICATE_COUNT_MUST_EQUAL_38")

    artifacts: Sequence[Any] = manifest.get("artifacts") or ()
    seen_paths: set[str] = set()
    learned_bytes = 0
    learned_artifact_count = 0

    for index, raw in enumerate(artifacts):
        if not isinstance(raw, Mapping):
            reasons.append(f"ARTIFACT_{index}_NOT_OBJECT")
            continue

        relpath = _safe_relpath(raw.get("path"))
        if relpath is None:
            reasons.append(f"ARTIFACT_{index}_INVALID_PATH")
        elif relpath in seen_paths:
            reasons.append(f"DUPLICATE_ARTIFACT_PATH:{relpath}")
        else:
            seen_paths.add(relpath)

        if not _valid_sha256(raw.get("sha256")):
            reasons.append(f"ARTIFACT_{index}_INVALID_SHA256")

        size = raw.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            reasons.append(f"ARTIFACT_{index}_INVALID_BYTE_COUNT")
            size = 0

        classification = _norm(raw.get("classification")).upper()
        if classification not in ALLOWED_CLASSIFICATIONS:
            reasons.append(f"ARTIFACT_{index}_UNKNOWN_CLASSIFICATION")
            continue

        if classification == LEARNED:
            learned_artifact_count += 1
            learned_bytes += size
            if not _norm(raw.get("learned_kind")):
                reasons.append(f"ARTIFACT_{index}_MISSING_LEARNED_KIND")
        else:
            if raw.get("deterministic_or_static") is not True:
                reasons.append(
                    f"ARTIFACT_{index}_NONLEARNED_NOT_PROVED_DETERMINISTIC_OR_STATIC"
                )
            if raw.get("fit_or_optimized_from_data") is True:
                reasons.append(
                    f"ARTIFACT_{index}_DATA_FIT_STATE_MISCLASSIFIED_AS_NONLEARNED"
                )

    providers: Sequence[Any] = manifest.get("runtime_providers") or ()
    for index, raw in enumerate(providers):
        if not isinstance(raw, Mapping):
            reasons.append(f"PROVIDER_{index}_NOT_OBJECT")
            continue

        role = _norm(raw.get("role")).upper()
        if not role:
            reasons.append(f"PROVIDER_{index}_MISSING_ROLE")
            continue

        if role in FORBIDDEN_PROVIDER_ROLES:
            reasons.append(f"FORBIDDEN_PROVIDER_ROLE:{role}")

        if raw.get("supplies_missing_target_capability") is True:
            reasons.append(f"PROVIDER_{index}_SUPPLIES_MISSING_TARGET_CAPABILITY")

        if raw.get("learned_general_reasoning") is True:
            reasons.append(f"PROVIDER_{index}_LEARNED_GENERAL_REASONING_FORBIDDEN")

        if raw.get("external") is True and role not in ALLOWED_EXTERNAL_PROVIDER_ROLES:
            reasons.append(f"PROVIDER_{index}_UNAPPROVED_EXTERNAL_ROLE:{role}")

    under_budget = learned_bytes < MAX_LEARNED_BYTES_EXCLUSIVE
    if not under_budget:
        reasons.append("LEARNED_STATE_BUDGET_EXCEEDED")

    return {
        "schema": CONTRACT_SCHEMA,
        "capsule_id": _norm(manifest.get("capsule_id")),
        "learned_bytes": learned_bytes,
        "learned_artifact_count": learned_artifact_count,
        "budget_bytes_exclusive": MAX_LEARNED_BYTES_EXCLUSIVE,
        "remaining_bytes": MAX_LEARNED_BYTES_EXCLUSIVE - learned_bytes,
        "under_budget": under_budget,
        "manifest_mechanically_complete": not reasons,
        "reasons": reasons,
        "scored_pass_authorized": False,
        "requires_exact_state_root_audit": True,
        "requires_separate_38_predicate_acceptance": True,
    }


def audit_state_root(state_root: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify exact bytes plus complete inventory of a dedicated state root."""
    base = audit_manifest(manifest)
    reasons = list(base["reasons"])
    root = Path(state_root).resolve()

    if not root.exists() or not root.is_dir():
        reasons.append("STATE_ROOT_MISSING_OR_NOT_DIRECTORY")
        return {
            **base,
            "exact_state_root_verified": False,
            "manifest_mechanically_complete": False,
            "reasons": reasons,
        }

    artifacts: Sequence[Any] = manifest.get("artifacts") or ()
    declared: dict[str, Mapping[str, Any]] = {}
    for raw in artifacts:
        if not isinstance(raw, Mapping):
            continue
        relpath = _safe_relpath(raw.get("path"))
        if relpath is not None:
            declared[relpath] = raw

    actual_paths = sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file()
    )
    declared_paths = sorted(declared)

    undeclared = sorted(set(actual_paths) - set(declared_paths))
    missing = sorted(set(declared_paths) - set(actual_paths))
    for relpath in undeclared:
        reasons.append(f"UNDECLARED_STATE_FILE:{relpath}")
    for relpath in missing:
        reasons.append(f"DECLARED_STATE_FILE_MISSING:{relpath}")

    for relpath in sorted(set(actual_paths) & set(declared_paths)):
        path = (root / relpath).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            reasons.append(f"STATE_FILE_ESCAPES_ROOT:{relpath}")
            continue

        raw = declared[relpath]
        expected_size = raw.get("bytes")
        actual_size = path.stat().st_size
        if expected_size != actual_size:
            reasons.append(
                f"STATE_FILE_SIZE_MISMATCH:{relpath}:{expected_size}:{actual_size}"
            )

        expected_sha = _norm(raw.get("sha256")).lower()
        actual_sha = _sha256_file(path)
        if expected_sha != actual_sha:
            reasons.append(f"STATE_FILE_SHA256_MISMATCH:{relpath}")

    exact = not reasons
    return {
        **base,
        "exact_state_root_verified": exact,
        "actual_state_file_count": len(actual_paths),
        "declared_state_file_count": len(declared_paths),
        "manifest_mechanically_complete": exact,
        "reasons": reasons,
        "scored_pass_authorized": False,
    }


def theoretical_parameter_capacity(bits_per_parameter: float) -> int:
    """Planning-only upper bound. Never substitutes for exact byte accounting."""
    if bits_per_parameter <= 0:
        raise ValueError("BITS_PER_PARAMETER_MUST_BE_POSITIVE")
    total_bits = MAX_LEARNED_BYTES_EXCLUSIVE * 8
    return int(total_bits // bits_per_parameter)
