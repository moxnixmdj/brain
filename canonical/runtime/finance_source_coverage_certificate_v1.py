"""Fail-closed source-coverage certificate for the two selected finance leaves.

This module does not infer finance semantics. It closes a narrower but load-bearing
hole: a FINANCE conclusion may not silently omit a deterministic raw-source unit.
Every derived source unit must be bound to evidence that actually contributes to
the selected Brain decision.

The remaining semantic question is explicit: whether the evidence bound to each
unit correctly captures all material meaning. That obligation is not self-certified.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_SOURCE_COVERAGE_CERTIFICATE_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_FINANCE_SOURCE_COVERAGE_MANIFEST_V1"

FINANCE_SUPERVISORY = "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
FINANCE_DOCUMENT = "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"
FINANCE_LEAVES = {FINANCE_SUPERVISORY, FINANCE_DOCUMENT}

_BOUNDARY = re.compile(r"(?:[.!?]+(?:\s+|$)|\n+)")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_source_units(text: str) -> list[dict[str, Any]]:
    """Derive a deterministic non-empty clause/sentence partition from raw text."""
    if not isinstance(text, str) or not text.strip():
        return []
    units: list[dict[str, Any]] = []
    start = 0
    idx = 1
    for match in _BOUNDARY.finditer(text):
        end = match.end()
        chunk = text[start:end]
        if chunk.strip():
            units.append({"id": f"u{idx:04d}", "start": start, "end": end, "text": chunk})
            idx += 1
        start = end
    if start < len(text):
        chunk = text[start:]
        if chunk.strip():
            units.append({"id": f"u{idx:04d}", "start": start, "end": len(text), "text": chunk})
    return units


def build_manifest(
    source_text: str,
    evidence_ids_by_unit: Sequence[Sequence[str]],
    *,
    source_id: str = "judgment-source",
) -> dict[str, Any]:
    """Build a manifest only when the caller already has source-grounded evidence."""
    units = derive_source_units(source_text)
    if len(units) != len(evidence_ids_by_unit):
        raise ValueError("evidence_ids_by_unit length must equal deterministic source-unit count")
    rows = []
    for unit, ids in zip(units, evidence_ids_by_unit):
        rows.append({
            "id": unit["id"],
            "start": unit["start"],
            "end": unit["end"],
            "evidence_ids": [str(x).strip() for x in ids],
        })
    return {
        "schema": MANIFEST_SCHEMA,
        "source_id": source_id,
        "source_sha256": _sha256(source_text),
        "units": rows,
    }


def verify_finance_source_coverage(
    bundle: Any,
    *,
    contributing_evidence: set[str],
    leaf_id: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if leaf_id not in FINANCE_LEAVES:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["LEAF_NOT_FINANCE_SELECTED_SCOPE"],
        }
    if not isinstance(bundle, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["PROOF_BUNDLE_NOT_OBJECT"],
        }

    text = bundle.get("source_text")
    if not isinstance(text, str) or not text.strip():
        errors.append("SOURCE_TEXT_MISSING")
        text = ""

    manifest = bundle.get("source_coverage_manifest")
    if not isinstance(manifest, Mapping):
        errors.append("SOURCE_COVERAGE_MANIFEST_MISSING")
        manifest = {}

    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("SOURCE_COVERAGE_MANIFEST_SCHEMA_INVALID")
    if manifest.get("source_sha256") != _sha256(text):
        errors.append("SOURCE_COVERAGE_SOURCE_HASH_MISMATCH")

    expected = derive_source_units(text)
    rows = manifest.get("units")
    if not isinstance(rows, list):
        errors.append("SOURCE_COVERAGE_UNITS_INVALID")
        rows = []

    if len(rows) != len(expected):
        errors.append("SOURCE_COVERAGE_UNIT_COUNT_MISMATCH")

    bound_evidence: set[str] = set()
    for i, exp in enumerate(expected):
        if i >= len(rows) or not isinstance(rows[i], Mapping):
            errors.append(f"SOURCE_UNIT_MISSING:{exp['id']}")
            continue
        row = rows[i]
        if row.get("id") != exp["id"]:
            errors.append(f"SOURCE_UNIT_ID_MISMATCH:{exp['id']}")
        if row.get("start") != exp["start"] or row.get("end") != exp["end"]:
            errors.append(f"SOURCE_UNIT_SPAN_MISMATCH:{exp['id']}")
        raw_ids = row.get("evidence_ids")
        if not isinstance(raw_ids, list) or not raw_ids:
            errors.append(f"SOURCE_UNIT_EVIDENCE_MISSING:{exp['id']}")
            continue
        ids = [str(x).strip() for x in raw_ids if str(x).strip()]
        if len(ids) != len(raw_ids):
            errors.append(f"SOURCE_UNIT_EVIDENCE_INVALID:{exp['id']}")
        missing = sorted(set(ids) - contributing_evidence)
        if missing:
            errors.extend(f"SOURCE_UNIT_EVIDENCE_NOT_CONTRIBUTING:{exp['id']}:{x}" for x in missing)
        bound_evidence.update(ids)

    extra = rows[len(expected):]
    if extra:
        errors.append("SOURCE_COVERAGE_EXTRA_UNITS")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_DETERMINISTIC_RAW_SOURCE_UNITS_BOUND_TO_CONTRIBUTING_EVIDENCE"
            if passed else
            "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": sorted(set(errors)),
        "leaf_id": leaf_id,
        "source_sha256": _sha256(text),
        "derived_source_unit_count": len(expected),
        "bound_contributing_evidence_ids": sorted(bound_evidence),
        "semantic_completeness_self_certified": False,
        "remaining_obligation": (
            "PROVE_EACH_BOUND_EVIDENCE_ITEM_SOUNDLY_CAPTURES_ALL_LOAD_BEARING_SEMANTICS_"
            "OF_ITS_DERIVED_SOURCE_UNIT_OR_FAIL_CLOSED"
        ),
    }
