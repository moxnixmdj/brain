#!/usr/bin/env python3
"""Independent reducer for the one-use Unknown-Domain production result.

Consumes only the immutable production result and the reduction rule frozen
before the production outcome was observed. It never reads hidden records,
beacon material, evaluator secrets, or terminal case content.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_REDUCER_V1"
PRECOMMIT_SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_REDUCTION_PRECOMMIT_V2"
TARGET = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"


class ReductionError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ReductionError(code)


def reduce_result(precommit: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    _require(precommit.get("schema") == PRECOMMIT_SCHEMA, "PRECOMMIT_SCHEMA_INVALID")
    _require(precommit.get("target_predicate") == TARGET, "PRECOMMIT_TARGET_INVALID")
    rule = precommit.get("acceptance_reduction")
    _require(isinstance(rule, Mapping), "PRECOMMIT_RULE_MISSING")

    _require(result.get("schema") == rule.get("required_result_schema"), "RESULT_SCHEMA_MISMATCH")
    _require(result.get("status") == rule.get("required_result_status"), "RESULT_STATUS_MISMATCH")
    _require(result.get("target_predicate") == rule.get("required_target_predicate"), "RESULT_TARGET_MISMATCH")
    _require(result.get("authority_claim_id") == rule.get("required_authority_claim_id"), "CLAIM_ID_MISMATCH")
    _require(result.get("claim_response_ref") == rule.get("required_authority_claim_id"), "CLAIM_RESPONSE_REF_MISMATCH")
    _require(result.get("claim_create_http_status") == rule.get("required_claim_create_http_status"), "CLAIM_HTTP_STATUS_MISMATCH")
    _require(result.get("claim_uniqueness_source") == rule.get("required_claim_uniqueness_source"), "CLAIM_UNIQUENESS_SOURCE_MISMATCH")
    _require(result.get("execution_lease_sha256") == rule.get("required_execution_lease_sha256"), "LEASE_DIGEST_MISMATCH")
    _require(result.get("production_cases_generated") == rule.get("required_production_cases_generated"), "PRODUCTION_CASE_COUNT_MISMATCH")

    rows = result.get("case_results")
    _require(isinstance(rows, list), "CASE_RESULTS_NOT_LIST")
    _require(len(rows) == rule.get("required_case_result_count"), "CASE_RESULT_COUNT_MISMATCH")
    ids = [str(row.get("case_id") or "") for row in rows if isinstance(row, Mapping)]
    _require(len(ids) == len(rows) and all(ids) and len(set(ids)) == rule.get("required_unique_case_ids"), "CASE_IDS_INVALID")

    leaf_counts = Counter(str(row.get("leaf_id") or "") for row in rows)
    _require(dict(leaf_counts) == dict(rule.get("required_leaf_counts") or {}), "LEAF_COUNTS_MISMATCH")

    max_probes = int(rule.get("max_probe_count_per_case"))
    classes = Counter()
    for row in rows:
        _require(isinstance(row, Mapping), "CASE_ROW_NOT_OBJECT")
        probe_count = row.get("probe_count")
        _require(isinstance(probe_count, int) and not isinstance(probe_count, bool) and 0 <= probe_count <= max_probes, "PROBE_COUNT_INVALID")
        scorer_result = row.get("scorer_result")
        _require(isinstance(scorer_result, Mapping), "SCORER_RESULT_MISSING")
        _require(scorer_result.get("case_id") == row.get("case_id"), "SCORER_CASE_ID_MISMATCH")
        _require(scorer_result.get("leaf_id") == row.get("leaf_id"), "SCORER_LEAF_ID_MISMATCH")
        _require(scorer_result.get("pass") is rule.get("required_every_case_scorer_pass"), "CASE_SCORER_NOT_PASS")
        if row.get("leaf_id") == ABSTAIN:
            classes[str(scorer_result.get("case_class") or "")] += 1

    _require(dict(classes) == dict(rule.get("required_abstention_class_balance") or {}), "ABSTENTION_CLASS_BALANCE_MISMATCH")

    aggregate = result.get("aggregate")
    _require(isinstance(aggregate, Mapping), "AGGREGATE_MISSING")
    _require(aggregate.get("case_count") == rule.get("required_case_result_count"), "AGGREGATE_CASE_COUNT_MISMATCH")
    _require(aggregate.get("transfer_leaf_pass") is rule.get("required_transfer_leaf_pass"), "TRANSFER_LEAF_NOT_PASS")
    _require(aggregate.get("abstention_leaf_pass") is rule.get("required_abstention_leaf_pass"), "ABSTENTION_LEAF_NOT_PASS")
    _require(aggregate.get("all_27_cases_pass") is rule.get("required_all_27_cases_pass"), "ALL_CASES_NOT_PASS")
    _require(dict(aggregate.get("class_balance") or {}) == dict(rule.get("required_abstention_class_balance") or {}), "AGGREGATE_CLASS_BALANCE_MISMATCH")

    exact_scalars = {
        "persistent_learned_bytes": rule.get("required_persistent_learned_bytes"),
        "external_frontier_model_calls": rule.get("required_external_frontier_model_calls"),
        "external_learned_capability_calls": rule.get("required_external_learned_capability_calls"),
        "incremental_spend_usd": rule.get("required_incremental_spend_usd"),
        "raw_hidden_records_persisted": rule.get("required_raw_hidden_records_persisted"),
        "raw_evaluator_secret_persisted": rule.get("required_raw_evaluator_secret_persisted"),
        "raw_beacon_persisted": rule.get("required_raw_beacon_persisted"),
        "replay_allowed": rule.get("required_replay_allowed"),
        "replacement_allowed": rule.get("required_replacement_allowed"),
        "promotion_authority": rule.get("required_result_promotion_authority"),
        "separate_independent_reduction_required": rule.get("required_separate_independent_reduction"),
    }
    for field, expected in exact_scalars.items():
        _require(result.get(field) == expected, "RESULT_FIELD_MISMATCH:" + field)

    return {
        "schema": SCHEMA,
        "status": "PASS__PREDICATE_LOCAL_PROOF_CANDIDATE__READY_FOR_SEPARATE_ACCEPTANCE_PROMOTION",
        "target_predicate": TARGET,
        "execution_lease_sha256": result.get("execution_lease_sha256"),
        "authority_claim_id": result.get("authority_claim_id"),
        "production_cases_verified": len(rows),
        "unique_case_ids_verified": len(set(ids)),
        "leaf_counts_verified": dict(leaf_counts),
        "abstention_class_balance_verified": dict(classes),
        "every_case_frozen_scorer_pass": True,
        "all_27_cases_pass": True,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "incremental_spend_usd": 0,
        "raw_hidden_material_read": False,
        "post_result_threshold_change": False,
        "post_result_case_replacement": False,
        "post_result_tuning": False,
        "acceptance_promotion_eligible": True,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authority": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--precommit", required=True)
    ap.add_argument("--result", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    precommit = json.loads(Path(ns.precommit).read_text())
    result = json.loads(Path(ns.result).read_text())
    try:
        receipt = reduce_result(precommit, result)
    except ReductionError as exc:
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT_REMAINS_OPEN",
            "target_predicate": TARGET,
            "error": str(exc),
            "acceptance_promotion_eligible": False,
            "acceptance_credit_delta": 0,
            "promotion_authority": False,
        }
    Path(ns.output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
