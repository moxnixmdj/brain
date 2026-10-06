from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Mapping, Sequence

CLASSIFICATIONS = {
    "INTRINSIC_FAMILY_UNION",
    "CROSS_CUTTING_CONDITION",
    "MODEL_INTRINSIC_SECURITY_DIMENSION",
    "DEPLOYMENT_OR_INTERFACE_ONLY",
    "UNRESOLVED_ESCAPE",
}

@dataclass(frozen=True)
class SurfaceVerdict:
    surface_id: str
    classification: str
    valid: bool
    reason: str

@dataclass(frozen=True)
class SurfaceCompilation:
    surface_count: int
    valid_surface_count: int
    invalid_surface_count: int
    unresolved_escape_count: int
    finite_source_accounting_complete: bool
    literal_target_universe_complete: bool
    terminal_credit_delta: int
    invalid_surface_ids: Sequence[str]
    unresolved_escape_ids: Sequence[str]
    verdicts: Sequence[Dict[str, Any]]

def _sha1(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(c in "0123456789abcdef" for c in value)
    )

def _binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value["path"].strip())
        and _sha1(value.get("git_blob_sha"))
    )

def _validate_surface(
    surface: Mapping[str, Any],
    family_ids: set[str],
) -> SurfaceVerdict:
    sid = surface.get("id")
    if not isinstance(sid, str) or not sid.strip():
        return SurfaceVerdict("<missing>", "<missing>", False, "SURFACE_ID_REQUIRED")

    classification = surface.get("classification")
    if classification not in CLASSIFICATIONS:
        return SurfaceVerdict(sid, str(classification), False, "UNKNOWN_OR_MISSING_CLASSIFICATION")

    source_receipts = surface.get("source_receipts")
    if not isinstance(source_receipts, list) or not source_receipts or not all(_binding(x) for x in source_receipts):
        return SurfaceVerdict(sid, classification, False, "CONTENT_ADDRESSED_SOURCE_RECEIPTS_REQUIRED")

    if classification == "INTRINSIC_FAMILY_UNION":
        families = surface.get("families")
        if not isinstance(families, list) or not families:
            return SurfaceVerdict(sid, classification, False, "NONEMPTY_FAMILY_UNION_REQUIRED")
        unknown = sorted(set(families) - family_ids)
        if unknown:
            return SurfaceVerdict(sid, classification, False, f"UNKNOWN_FAMILY_REFERENCES:{','.join(unknown)}")
        if surface.get("condition_id") or surface.get("security_dimension_id") or surface.get("exclusion_reason"):
            return SurfaceVerdict(sid, classification, False, "CONTRADICTORY_CLASSIFICATION_FIELDS")
        return SurfaceVerdict(sid, classification, True, "VALID_EXISTING_FAMILY_UNION_MAPPING")

    if classification == "CROSS_CUTTING_CONDITION":
        condition_id = surface.get("condition_id")
        if not isinstance(condition_id, str) or not condition_id.strip():
            return SurfaceVerdict(sid, classification, False, "CONDITION_ID_REQUIRED")
        if surface.get("exclusion_reason") or surface.get("security_dimension_id"):
            return SurfaceVerdict(sid, classification, False, "CONTRADICTORY_CLASSIFICATION_FIELDS")
        return SurfaceVerdict(sid, classification, True, "VALID_CROSS_CUTTING_CONDITION")

    if classification == "MODEL_INTRINSIC_SECURITY_DIMENSION":
        dimension_id = surface.get("security_dimension_id")
        if not isinstance(dimension_id, str) or not dimension_id.strip():
            return SurfaceVerdict(sid, classification, False, "SECURITY_DIMENSION_ID_REQUIRED")
        if surface.get("exclusion_reason") or surface.get("condition_id"):
            return SurfaceVerdict(sid, classification, False, "CONTRADICTORY_CLASSIFICATION_FIELDS")
        return SurfaceVerdict(sid, classification, True, "VALID_MODEL_INTRINSIC_SECURITY_DIMENSION")

    if classification == "DEPLOYMENT_OR_INTERFACE_ONLY":
        reason = surface.get("exclusion_reason")
        if not isinstance(reason, str) or not reason.strip():
            return SurfaceVerdict(sid, classification, False, "EXCLUSION_REASON_REQUIRED")
        if surface.get("families") or surface.get("condition_id") or surface.get("security_dimension_id"):
            return SurfaceVerdict(sid, classification, False, "DEPLOYMENT_CLASS_MUST_NOT_RECEIVE_INTRINSIC_CREDIT_FIELDS")
        return SurfaceVerdict(sid, classification, True, "VALID_NON_INTRINSIC_DEPLOYMENT_OR_INTERFACE_CLASS")

    # UNRESOLVED_ESCAPE is an explicit fail-closed classification. It is valid
    # accounting but keeps the target-universe lane open.
    escape = surface.get("escape_statement")
    if not isinstance(escape, str) or not escape.strip():
        return SurfaceVerdict(sid, classification, False, "ESCAPE_STATEMENT_REQUIRED")
    return SurfaceVerdict(sid, classification, True, "VALID_EXPLICIT_UNRESOLVED_ESCAPE")

def compile_surface_manifest(
    manifest: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> SurfaceCompilation:
    families = envelope.get("families")
    if not isinstance(families, list) or not families:
        raise ValueError("envelope families must be a non-empty list")
    family_ids = {
        f.get("id") for f in families
        if isinstance(f, Mapping) and isinstance(f.get("id"), str)
    }
    if len(family_ids) != len(families):
        raise ValueError("envelope family ids must be present and unique")

    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("manifest surfaces must be a non-empty list")

    raw_ids = [s.get("id") for s in surfaces if isinstance(s, Mapping)]
    if len(raw_ids) != len(surfaces) or len(set(raw_ids)) != len(raw_ids):
        raise ValueError("surface ids must be present and unique")

    verdicts: List[SurfaceVerdict] = []
    for surface in surfaces:
        if not isinstance(surface, Mapping):
            verdicts.append(SurfaceVerdict("<nonmapping>", "<missing>", False, "SURFACE_MUST_BE_MAPPING"))
            continue
        verdicts.append(_validate_surface(surface, family_ids))

    invalid = [v.surface_id for v in verdicts if not v.valid]
    unresolved = [
        v.surface_id for v in verdicts
        if v.valid and v.classification == "UNRESOLVED_ESCAPE"
    ]
    finite_source_accounting_complete = len(invalid) == 0

    literal_claim = manifest.get("literal_target_universe_complete", False)
    if not isinstance(literal_claim, bool):
        raise ValueError("literal_target_universe_complete must be boolean")

    completeness_receipts = manifest.get("target_universe_completeness_proof_receipts", [])
    receipts_valid = (
        isinstance(completeness_receipts, list)
        and bool(completeness_receipts)
        and all(_binding(x) for x in completeness_receipts)
    )

    # A finite manifest can close its own source-accounting slice, but it may
    # not certify the open-world target. Literal completeness needs a separate
    # content-addressed theorem/attestation and zero unresolved escapes.
    literal_target_universe_complete = (
        literal_claim
        and finite_source_accounting_complete
        and not unresolved
        and receipts_valid
    )

    if literal_claim and not literal_target_universe_complete:
        raise ValueError(
            "literal target-universe completeness claim requires valid separate "
            "content-addressed completeness proof receipts and zero unresolved escapes"
        )

    return SurfaceCompilation(
        surface_count=len(surfaces),
        valid_surface_count=len(surfaces) - len(invalid),
        invalid_surface_count=len(invalid),
        unresolved_escape_count=len(unresolved),
        finite_source_accounting_complete=finite_source_accounting_complete,
        literal_target_universe_complete=literal_target_universe_complete,
        terminal_credit_delta=0,
        invalid_surface_ids=tuple(invalid),
        unresolved_escape_ids=tuple(unresolved),
        verdicts=tuple(asdict(v) for v in verdicts),
    )
