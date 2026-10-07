"""Fail-closed completeness certificate for authoritative pre-normalized finance packages.

This kernel is deliberately narrow. It does not infer semantics from raw text.
It proves that a frozen, authoritative normalized package is exhaustively represented
in the proof-carrying proposal consumed by the existing finance judgment route.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_STRUCTURED_SOURCE_COVERAGE_CERTIFICATE_V1"

LEAF_SUPERVISORY = "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
LEAF_DOCUMENT = "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"

CATEGORY_TO_PROPOSAL_FIELD = {
    LEAF_SUPERVISORY: {
        "APPLICABLE_RULE": "rule_evidence_ids",
        "MATERIAL_EXCEPTION": "exception_evidence_ids",
        "ESCALATION": "escalation_evidence_ids",
        "DISCLOSURE": "disclosure_evidence_ids",
    },
    LEAF_DOCUMENT: {
        "DECISION_RELEVANT_FACT": "fact_evidence_ids",
        "CROSS_REFERENCE": "cross_reference_evidence_ids",
        "CONTRADICTION_OR_EXCEPTION": "exception_evidence_ids",
        "RECONCILIATION": "reconciliation_evidence_ids",
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def package_sha256(package: Mapping[str, Any]) -> str:
    body = dict(package)
    body.pop("package_sha256", None)
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _norm_ids(value: Any, field: str, errors: list[str] | None = None) -> set[str]:
    sink = errors if errors is not None else []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        sink.append(f"{field}:NOT_LIST")
        return set()
    out: set[str] = set()
    for i, raw in enumerate(value):
        if not isinstance(raw, str) or not raw.strip():
            sink.append(f"{field}:INVALID_ID:{i}")
            continue
        rid = raw.strip()
        if rid in out:
            sink.append(f"{field}:DUPLICATE_ID:{rid}")
        out.add(rid)
    return out


def certify(package: Any, proposal: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(package, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["PACKAGE_NOT_OBJECT"],
        }
    if not isinstance(proposal, Mapping):
        proposal = {}
        errors.append("PROPOSAL_NOT_OBJECT")

    leaf_id = package.get("leaf_id")
    allowed_categories = CATEGORY_TO_PROPOSAL_FIELD.get(leaf_id)
    if allowed_categories is None:
        errors.append("LEAF_ID_INVALID")
        allowed_categories = {}

    source_id = package.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        errors.append("SOURCE_ID_MISSING")

    expected_hash = package.get("package_sha256")
    actual_hash = package_sha256(package)
    if not isinstance(expected_hash, str) or expected_hash != actual_hash:
        errors.append("PACKAGE_HASH_MISMATCH")

    items = package.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or not items:
        errors.append("ITEMS_EMPTY_OR_INVALID")
        items = []

    item_ids: set[str] = set()
    required_by_field: dict[str, set[str]] = {}
    owner_field_by_item: dict[str, str] = {}

    for i, row in enumerate(items):
        if not isinstance(row, Mapping):
            errors.append(f"ITEM_NOT_OBJECT:{i}")
            continue
        item_id = row.get("id")
        category = row.get("category")
        source_ref = row.get("source_ref")
        if not isinstance(item_id, str) or not item_id.strip():
            errors.append(f"ITEM_ID_INVALID:{i}")
            continue
        item_id = item_id.strip()
        if item_id in item_ids:
            errors.append(f"ITEM_ID_DUPLICATE:{item_id}")
            continue
        item_ids.add(item_id)

        field = allowed_categories.get(category)
        if field is None:
            errors.append(f"ITEM_CATEGORY_INVALID:{item_id}:{category}")
            continue
        owner_field_by_item[item_id] = field
        if not isinstance(source_ref, str) or not source_ref.strip():
            errors.append(f"ITEM_SOURCE_REF_MISSING:{item_id}")
        required_by_field.setdefault(field, set()).add(item_id)

    declared_by_field: dict[str, set[str]] = {}
    for field in sorted(set(allowed_categories.values())):
        declared_by_field[field] = _norm_ids(proposal.get(field, []), field, errors)

    for field, required_ids in sorted(required_by_field.items()):
        declared = declared_by_field.get(field, set())
        for item_id in sorted(required_ids - declared):
            errors.append(f"MISSING_REQUIRED_ITEM:{field}:{item_id}")

    for field, declared in sorted(declared_by_field.items()):
        for item_id in sorted(declared - item_ids):
            errors.append(f"UNKNOWN_PROPOSAL_ITEM:{field}:{item_id}")
        for item_id in sorted(declared & item_ids):
            owner = owner_field_by_item.get(item_id)
            if owner is not None and owner != field:
                errors.append(f"ITEM_WRONG_EVIDENCE_CHANNEL:{item_id}:{field}:{owner}")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS_STRUCTURED_SOURCE_COVERAGE" if passed else "FAIL_CLOSED",
        "leaf_id": leaf_id,
        "source_id": source_id,
        "package_sha256": actual_hash,
        "covered_item_count": len(item_ids) if passed else 0,
        "errors": sorted(set(errors)),
        "scope": "AUTHORITATIVE_PRE_NORMALIZED_FINANCE_PACKAGE_ONLY",
        "raw_text_semantics_claimed": False,
    }
