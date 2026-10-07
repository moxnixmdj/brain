"""Fail-closed finance source-universe coverage gate.

This gate closes one specific hole: a finance route may not claim a conclusion merely
because every declared evidence id contributes. A trusted, pre-frozen authority must
also enumerate the complete material source universe for the selected case, and the
proof must bind every required source id into the terminal evidence set.

It does not infer source semantics, decide what is material, or create an authority
manifest. Missing or inconsistent authority is a hard block rather than an invitation
to guess.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_SOURCE_UNIVERSE_GATE_V1"
SUPERVISORY = "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
DOCUMENT = "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"

_REQUIRED_AUTHORITY_FIELDS = {
    SUPERVISORY: (
        "all_material_rule_ids",
        "all_material_exception_ids",
        "required_disclosure_ids",
        "required_escalation_ids",
    ),
    DOCUMENT: (
        "document_fact_universe",
        "decision_relevant_fact_universe",
        "cross_reference_universe",
        "material_exception_ids",
    ),
}

def _ids(value: Any, field: str, errors: list[str]) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        errors.append(f"AUTHORITY_FIELD_INVALID:{field}")
        return set()
    out: set[str] = set()
    for i, raw in enumerate(value):
        if not isinstance(raw, str) or not raw.strip():
            errors.append(f"AUTHORITY_ID_INVALID:{field}:{i}")
            continue
        item = raw.strip()
        if item in out:
            errors.append(f"AUTHORITY_ID_DUPLICATE:{field}:{item}")
        out.add(item)
    return out

def canonical_authority_sha256(authority: Mapping[str, Any]) -> str:
    payload = dict(authority)
    payload.pop("authority_sha256", None)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def verify_finance_source_universe(
    *,
    leaf_id: str,
    authority: Any,
    coverage_manifest: Any,
    contributing_evidence_ids: Sequence[str],
) -> dict[str, Any]:
    errors: list[str] = []
    required_fields = _REQUIRED_AUTHORITY_FIELDS.get(leaf_id)
    if required_fields is None:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED",
                "errors": ["FINANCE_LEAF_UNSUPPORTED:" + str(leaf_id)]}
    if not isinstance(authority, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED",
                "errors": ["SOURCE_UNIVERSE_AUTHORITY_MISSING"]}
    if not isinstance(coverage_manifest, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED",
                "errors": ["SOURCE_COVERAGE_MANIFEST_MISSING"]}

    authority_id = str(authority.get("authority_id") or "").strip()
    manifest_authority_id = str(coverage_manifest.get("authority_id") or "").strip()
    if not authority_id:
        errors.append("AUTHORITY_ID_MISSING")
    if manifest_authority_id != authority_id:
        errors.append("COVERAGE_AUTHORITY_ID_MISMATCH")

    expected_sha = str(authority.get("authority_sha256") or "").strip().lower()
    actual_sha = canonical_authority_sha256(authority)
    if len(expected_sha) != 64 or expected_sha != actual_sha:
        errors.append("AUTHORITY_CONTENT_HASH_INVALID")
    if authority.get("frozen_before_candidate") is not True:
        errors.append("AUTHORITY_NOT_PRE_FROZEN")
    if authority.get("candidate_can_modify_authority") is not False:
        errors.append("AUTHORITY_MUTABILITY_NOT_FORBIDDEN")

    required: set[str] = set()
    by_field: dict[str, list[str]] = {}
    for field in required_fields:
        ids = _ids(authority.get(field), field, errors)
        by_field[field] = sorted(ids)
        required.update(ids)

    covered = _ids(coverage_manifest.get("covered_source_ids"), "covered_source_ids", errors)
    bound = _ids(coverage_manifest.get("semantic_binding_source_ids"), "semantic_binding_source_ids", errors)
    contributing = {str(x).strip() for x in contributing_evidence_ids
                    if isinstance(x, str) and str(x).strip()}

    for prefix, missing in (
        ("SOURCE_UNIVERSE_NOT_COVERED:", required - covered),
        ("SOURCE_NOT_SEMANTICALLY_BOUND:", required - bound),
        ("SOURCE_NOT_TERMINALLY_CONTRIBUTING:", required - contributing),
    ):
        errors.extend(prefix + x for x in sorted(missing))
    errors.extend("UNAUTHORIZED_SOURCE_IN_COVERAGE:" + x for x in sorted(covered - required))

    declared_sha = str(coverage_manifest.get("authority_sha256") or "").strip().lower()
    if declared_sha != actual_sha:
        errors.append("COVERAGE_AUTHORITY_HASH_MISMATCH")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS__CLOSED_SOURCE_UNIVERSE_COVERED" if passed else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "leaf_id": leaf_id,
        "authority_id": authority_id or None,
        "authority_sha256": actual_sha,
        "required_source_ids": sorted(required),
        "required_source_ids_by_field": by_field,
        "covered_source_ids": sorted(covered),
        "semantic_binding_source_ids": sorted(bound),
        "terminally_contributing_source_ids": sorted(contributing),
        "scope_limit": (
            "PROVES_CLOSED_WORLD_SOURCE_COVERAGE_ONLY_FOR_A_TRUSTED_PRE_FROZEN_AUTHORITY_UNIVERSE__"
            "DOES_NOT_INFER_RAW_SEMANTICS_MATERIALITY_OR_FINANCE_CORRECTNESS"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
