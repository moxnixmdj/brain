"""Audit whether immutable Terminal V3 archives can discharge the two P1 residuals."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_P1_TERMINAL_ARCHIVE_SUFFICIENCY_AUDIT_V1"
P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
EXPECTED_FULL_RESULT_SHA256 = "f4bec690aa0580cb532dbfd5985705bae8d153c9df31ffdf460b02f8b152e0f2"
EXPECTED_ARTIFACT_DIGEST = "sha256:e77e935b4612ecbe094e806f1f4da3dff0289552844b29e5a7a7bd99020503f2"
FORBIDDEN_CASE_LEVEL_KEYS = {
    "trajectory",
    "task",
    "case_results",
    "cases",
    "mechanism_classes",
    "mechanism_by_action",
    "cause_step",
    "cause_action_id",
    "cause_action_ids",
    "repair_id",
    "repair_targets",
    "intervention",
    "intervention_result",
    "rescue",
    "rescue_pass",
    "hidden_oracle",
    "_oracle",
}


def _p1_objects(value: Any) -> list[Mapping[str, Any]]:
    out: list[Mapping[str, Any]] = []
    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            if x.get("behavior_id") == P1:
                out.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(value)
    return out


def audit_document(doc: Mapping[str, Any], *, full_result_sha256: str) -> dict[str, Any]:
    errors: list[str] = []
    if full_result_sha256 != EXPECTED_FULL_RESULT_SHA256:
        errors.append("FULL_RESULT_SHA256_MISMATCH")
    if doc.get("schema") != "PROJECT_BRAIN_TERMINAL_PARENT_PORTFOLIO_LAUNCHER_V1":
        errors.append("FULL_RESULT_SCHEMA_DRIFT")
    if doc.get("status") != "PASS" or doc.get("pass") is not True:
        errors.append("TERMINAL_V3_FULL_RESULT_NOT_PASS")

    parent = doc.get("parent_portfolio_receipts")
    if not isinstance(parent, Mapping):
        errors.append("PARENT_RECEIPTS_MISSING")
        parent = {}

    aggregate: list[Mapping[str, Any]] = []
    for portfolio in ("T0", "T1", "T2", "T3"):
        rows = parent.get(portfolio) or []
        if not isinstance(rows, list):
            errors.append("PARENT_PORTFOLIO_ROWS_INVALID:"+portfolio)
            continue
        for row in rows:
            if isinstance(row, Mapping) and row.get("behavior_id") == P1:
                aggregate.append(row)

    aggregate_ids = sorted(str(x.get("case_id")) for x in aggregate)
    if aggregate_ids != [
        "T0::TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001::aggregate::30",
        "T2::TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001::aggregate::30",
    ]:
        errors.append("P1_AGGREGATE_RECEIPT_SET_DRIFT")

    rich_hits: list[dict[str, Any]] = []
    for obj in _p1_objects(doc):
        overlap = sorted(FORBIDDEN_CASE_LEVEL_KEYS & set(obj.keys()))
        if overlap:
            rich_hits.append({"case_id": obj.get("case_id"), "keys": overlap})
    if rich_hits:
        errors.append("P1_CASE_LEVEL_SEMANTICS_PRESENT")

    direct_routes = set(doc.get("direct_routes_executed_once") or [])
    if P1 in direct_routes:
        errors.append("P1_UNEXPECTED_DIRECT_ROUTE_PRESENT")

    reduction = (((doc.get("parent_reduction") or {}).get("reductions") or {}).get(P1) or {})
    reduction_receipts = reduction.get("receipts") or []
    if not isinstance(reduction_receipts, list) or len(reduction_receipts) != 2:
        errors.append("P1_REDUCTION_RECEIPT_COUNT_DRIFT")
    else:
        for row in reduction_receipts:
            if not isinstance(row, Mapping) or "::aggregate::30" not in str(row.get("case_id")):
                errors.append("P1_REDUCTION_NOT_AGGREGATE_ONLY")

    p1_objects = _p1_objects(doc)
    if len(p1_objects) != 5:
        errors.append("P1_OBJECT_COUNT_DRIFT")

    archive_has_case_level_scope_class = bool(rich_hits)
    archive_has_heterogeneous_intervention_rescue = bool(rich_hits)
    sufficient = archive_has_case_level_scope_class and archive_has_heterogeneous_intervention_rescue

    return {
        "schema": SCHEMA,
        "status": "PASS__ARCHIVE_INSUFFICIENT__NEW_OBSERVATION_IRREDUCIBLE" if not errors and not sufficient else "FAIL_CLOSED",
        "pass": not errors and not sufficient,
        "errors": sorted(set(errors)),
        "full_result_sha256": full_result_sha256,
        "expected_artifact_digest": EXPECTED_ARTIFACT_DIGEST,
        "p1_object_count": len(p1_objects),
        "p1_parent_aggregate_receipts": aggregate_ids,
        "case_level_semantic_key_hits": rich_hits,
        "archive_has_explicit_scope_failure_class_evidence": archive_has_case_level_scope_class,
        "archive_has_heterogeneous_intervention_rescue_evidence": archive_has_heterogeneous_intervention_rescue,
        "archive_can_discharge_two_residuals": sufficient,
        "new_observation_irreducible_for_two_residuals": not sufficient,
        "terminal_v3_replay_authorized": False,
        "fresh_observation_may_target_only": [
            "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
            "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
        ] if not errors and not sufficient else [],
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }


def audit_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    raw = p.read_bytes()
    doc = json.loads(raw)
    if not isinstance(doc, Mapping):
        raise ValueError("FULL_RESULT_NOT_OBJECT")
    return audit_document(doc, full_result_sha256=hashlib.sha256(raw).hexdigest())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-result", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = audit_file(args.full_result)
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.out:
        Path(args.out).write_text(payload+"\n", encoding="utf-8")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
