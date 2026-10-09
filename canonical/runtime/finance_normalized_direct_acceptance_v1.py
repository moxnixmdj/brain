"""Independent acceptance verifier for authoritative normalized Finance packages.

This verifier does not infer finance semantics from prose. It accepts only a
structured package whose source universe is itself authoritative and fully
enumerated. Every material source record must map one-to-one to typed decision
evidence, and all quantitative reconciliations must independently pass.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import evidence_decision_verify as decision_verify

SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_DIRECT_ACCEPTANCE_V1"
PACKAGE_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_DECISION_PACKAGE_V1"
SUPERVISORY = "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
DOCUMENT = "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"

CATEGORY_KEYS = {
    SUPERVISORY: (
        "rules", "facts", "exceptions", "escalations", "disclosures", "ambiguities"
    ),
    DOCUMENT: (
        "facts", "cross_references", "contradictions", "exceptions",
        "reconciliations", "ambiguities"
    ),
}
SOURCE_MODES = {
    SUPERVISORY: "AUTHORITATIVE_NORMALIZED_RULES",
    DOCUMENT: "FROZEN_STRUCTURED_DOCUMENT",
}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "terminal_authority": False,
    }


def _reconciliation_ok(row: Mapping[str, Any]) -> bool:
    try:
        lhs = Decimal(str(row["lhs"]))
        rhs = Decimal(str(row["rhs"]))
        tolerance = Decimal(str(row.get("tolerance", "0")))
    except (KeyError, InvalidOperation, ValueError):
        return False
    return (
        lhs.is_finite()
        and rhs.is_finite()
        and tolerance.is_finite()
        and tolerance >= 0
        and abs(lhs - rhs) <= tolerance
    )


def verify(package: Any, result: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(package, Mapping) or package.get("schema") != PACKAGE_SCHEMA:
        return _fail("PACKAGE_SCHEMA_INVALID")
    leaf = str(package.get("leaf_id") or "")
    if leaf not in CATEGORY_KEYS:
        return _fail("FINANCE_LEAF_INVALID")
    if package.get("source_mode") != SOURCE_MODES[leaf]:
        errors.append("SOURCE_MODE_INVALID")
    source_id = str(package.get("source_id") or "").strip()
    if not source_id:
        errors.append("SOURCE_ID_REQUIRED")

    universe = package.get("source_universe")
    if not isinstance(universe, Mapping):
        return _fail("SOURCE_UNIVERSE_INVALID")
    expected_keys = set(CATEGORY_KEYS[leaf])
    if set(universe) != expected_keys:
        errors.append("SOURCE_UNIVERSE_CATEGORY_SET_INVALID")

    records_by_id: dict[str, Mapping[str, Any]] = {}
    evidence_to_record: dict[str, str] = {}
    for category in CATEGORY_KEYS[leaf]:
        rows = universe.get(category)
        if not isinstance(rows, list):
            errors.append("SOURCE_CATEGORY_NOT_LIST:" + category)
            continue
        if category == "ambiguities" and rows:
            errors.append("UNRESOLVED_AMBIGUITY_PRESENT")
        for i, row in enumerate(rows):
            if not isinstance(row, Mapping):
                errors.append(f"SOURCE_RECORD_INVALID:{category}:{i}")
                continue
            rid = str(row.get("id") or "").strip()
            claim = str(row.get("claim") or "").strip()
            eid = str(row.get("evidence_id") or "").strip()
            if not rid:
                errors.append(f"SOURCE_RECORD_ID_MISSING:{category}:{i}")
                continue
            if rid in records_by_id:
                errors.append("SOURCE_RECORD_ID_DUPLICATE:" + rid)
            records_by_id[rid] = row
            if not claim:
                errors.append("SOURCE_RECORD_CLAIM_MISSING:" + rid)
            if category != "ambiguities":
                if not eid:
                    errors.append("SOURCE_RECORD_EVIDENCE_ID_MISSING:" + rid)
                elif eid in evidence_to_record:
                    errors.append("SOURCE_RECORD_EVIDENCE_ID_DUPLICATE:" + eid)
                else:
                    evidence_to_record[eid] = rid
            if category == "reconciliations" and not _reconciliation_ok(row):
                errors.append("RECONCILIATION_FAILED:" + rid)

    if not records_by_id:
        errors.append("SOURCE_UNIVERSE_EMPTY")
    if leaf == SUPERVISORY and not universe.get("rules"):
        errors.append("SUPERVISORY_RULE_UNIVERSE_EMPTY")
    if leaf == DOCUMENT and not universe.get("facts"):
        errors.append("DOCUMENT_FACT_UNIVERSE_EMPTY")

    problem = package.get("decision_problem")
    if not isinstance(problem, Mapping):
        errors.append("DECISION_PROBLEM_INVALID")
        problem = {}
    evidence = problem.get("evidence") if isinstance(problem, Mapping) else None
    if not isinstance(evidence, list):
        errors.append("DECISION_EVIDENCE_INVALID")
        evidence = []

    observed_ids: set[str] = set()
    by_eid: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(evidence):
        if not isinstance(row, Mapping):
            errors.append(f"DECISION_EVIDENCE_ROW_INVALID:{i}")
            continue
        eid = str(row.get("id") or "").strip()
        if not eid:
            errors.append(f"DECISION_EVIDENCE_ID_MISSING:{i}")
            continue
        if eid in observed_ids:
            errors.append("DECISION_EVIDENCE_ID_DUPLICATE:" + eid)
        observed_ids.add(eid)
        by_eid[eid] = row

    if observed_ids != set(evidence_to_record):
        errors.append("SOURCE_TO_DECISION_EVIDENCE_SET_MISMATCH")

    for eid, rid in evidence_to_record.items():
        row = by_eid.get(eid)
        src = records_by_id.get(rid)
        if not isinstance(row, Mapping) or not isinstance(src, Mapping):
            continue
        if str(row.get("claim") or "").strip() != str(src.get("claim") or "").strip():
            errors.append("SOURCE_CLAIM_DECISION_CLAIM_MISMATCH:" + rid)
        if float(row.get("confidence", -1)) != 1.0 or float(row.get("strength", -1)) != 1.0:
            errors.append("AUTHORITATIVE_SOURCE_EVIDENCE_WEIGHT_NOT_ONE:" + eid)
        if str(row.get("independence_group") or "") != rid:
            errors.append("SOURCE_INDEPENDENCE_GROUP_MISMATCH:" + eid)
        provenance = row.get("provenance")
        if not isinstance(provenance, list) or {
            "source": source_id, "ref": rid
        } not in provenance:
            errors.append("SOURCE_PROVENANCE_BINDING_MISSING:" + eid)

    try:
        verified, reason = decision_verify.verify(dict(problem), dict(result))
    except Exception as exc:
        verified, reason = False, type(exc).__name__ + ":" + str(exc)
    if not verified:
        errors.append("INDEPENDENT_TYPED_DECISION_VERIFY_FAILED:" + str(reason))
    if isinstance(result, Mapping) and result.get("status") != "DECIDED":
        errors.append("FINANCE_DIRECT_ROUTE_REQUIRES_DECIDED_RESULT")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__AUTHORITATIVE_NORMALIZED_FINANCE_SOURCE_UNIVERSE_AND_DECISION_VERIFIED"
            if passed else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "leaf_id": leaf,
        "source_mode": package.get("source_mode"),
        "source_record_count": len(records_by_id),
        "decision_evidence_count": len(observed_ids),
        "semantic_acceptance_complete": passed,
        "actual_goal_satisfaction_verified": passed,
        "producer_independent": True,
        "raw_prose_semantic_extraction_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
