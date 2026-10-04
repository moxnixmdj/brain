"""Pre-result frozen reducer for the one-use Unknown-Domain production receipt.

This module is intentionally frozen before the production outcome is observed.
It grants no acceptance authority. It only decides whether an immutable
production result is structurally eligible to support exactly the frozen
UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT predicate.

A later independent exact-byte verifier must bind this reducer, the immutable
result blob/commit, and the canonical acceptance state before any promotion.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_PRODUCTION_RESULT_REDUCER_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1"
TARGET = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
LEASE_SHA256 = "76e8040db826990a90f5ab36b833c40af1ade15c89c579eeef2ca44bf1d0c7e9"
LEASE_GIT_BLOB_SHA = "26f98012ecf01c6a3f20e855bdebf60cf70d1c1f"
LAUNCH_REF = "refs/heads/unknown-domain-direct-launch/" + LEASE_SHA256
CLAIM_REF = "refs/heads/unknown-domain-direct-claims/" + LEASE_SHA256
EXPECTED_BALANCE = {"IDENTIFIABLE": 5, "NONIDENTIFIABLE": 5, "UNDERSPECIFIED": 5}


def _seq(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def evaluate(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    def req(cond: bool, code: str) -> None:
        if not cond:
            errors.append(code)

    if not isinstance(result, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["RESULT_NOT_OBJECT"],
            "predicate_promotion_eligible": False,
            "newly_proved_predicates": [],
            "promotion_authority": False,
            "execution_authority": False,
        }

    req(result.get("schema") == RESULT_SCHEMA, "RESULT_SCHEMA_MISMATCH")
    req(result.get("status") == "PRODUCTION_PASS", "PRODUCTION_STATUS_NOT_PASS")
    req(result.get("target_predicate") == TARGET, "TARGET_PREDICATE_MISMATCH")
    req(result.get("authority_claim_id") == CLAIM_REF, "AUTHORITY_CLAIM_ID_MISMATCH")
    req(result.get("claim_create_http_status") == 201, "ATOMIC_CLAIM_HTTP_STATUS_NOT_201")
    req(result.get("claim_response_ref") == CLAIM_REF, "CLAIM_RESPONSE_REF_MISMATCH")
    req(result.get("claim_uniqueness_source") == "ATOMIC_CREATE_RESPONSE", "CLAIM_UNIQUENESS_SOURCE_INVALID")
    req(result.get("execution_lease_sha256") == LEASE_SHA256, "EXECUTION_LEASE_SHA256_MISMATCH")
    req(result.get("execution_lease_git_blob_sha") == LEASE_GIT_BLOB_SHA, "EXECUTION_LEASE_BLOB_MISMATCH")
    req(result.get("launch_ref") == LAUNCH_REF, "LAUNCH_REF_MISMATCH")

    req(result.get("production_cases_generated") == 27, "PRODUCTION_CASE_COUNT_MISMATCH")
    req(result.get("persistent_learned_bytes") == 0, "PERSISTENT_LEARNED_BYTES_NONZERO")
    req(result.get("external_frontier_model_calls") == 0, "EXTERNAL_FRONTIER_MODEL_CALLS_NONZERO")
    req(result.get("external_learned_capability_calls") == 0, "EXTERNAL_LEARNED_CAPABILITY_CALLS_NONZERO")
    req(result.get("incremental_spend_usd") == 0, "INCREMENTAL_SPEND_NONZERO")
    req(result.get("raw_hidden_records_persisted") is False, "RAW_HIDDEN_RECORDS_PERSISTED")
    req(result.get("raw_evaluator_secret_persisted") is False, "RAW_EVALUATOR_SECRET_PERSISTED")
    req(result.get("raw_beacon_persisted") is False, "RAW_BEACON_PERSISTED")
    req(result.get("replay_allowed") is False, "REPLAY_ALLOWED")
    req(result.get("replacement_allowed") is False, "REPLACEMENT_ALLOWED")
    req(result.get("acceptance_credit_delta") == 0, "RESULT_SELF_AWARDS_ACCEPTANCE_CREDIT")
    req(result.get("family_credit_delta") == 0, "RESULT_SELF_AWARDS_FAMILY_CREDIT")
    req(result.get("capability_credit_delta") == 0, "RESULT_SELF_AWARDS_CAPABILITY_CREDIT")
    req(result.get("ownership_credit_delta") == 0, "RESULT_SELF_AWARDS_OWNERSHIP_CREDIT")
    req(result.get("promotion_authority") is False, "RESULT_SELF_GRANTS_PROMOTION_AUTHORITY")
    req(result.get("separate_independent_reduction_required") is True, "SEPARATE_REDUCTION_FLAG_MISSING")

    rows = result.get("case_results")
    transfer_count = 0
    abstain_count = 0
    ids: list[str] = []
    classes = {"IDENTIFIABLE": 0, "NONIDENTIFIABLE": 0, "UNDERSPECIFIED": 0}
    if not _seq(rows):
        errors.append("CASE_RESULTS_NOT_LIST")
        rows = []
    else:
        req(len(rows) == 27, "CASE_RESULTS_COUNT_NOT_27")

    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"CASE_RESULT_NOT_OBJECT:{i}")
            continue
        case_id = str(row.get("case_id") or "")
        leaf_id = row.get("leaf_id")
        scorer = row.get("scorer_result")
        if not case_id:
            errors.append(f"CASE_ID_MISSING:{i}")
        else:
            ids.append(case_id)
        if leaf_id == TRANSFER:
            transfer_count += 1
            probe_count = row.get("probe_count")
            req(isinstance(probe_count, int) and not isinstance(probe_count, bool) and 0 <= probe_count <= 2,
                f"TRANSFER_PROBE_COUNT_INVALID:{i}")
        elif leaf_id == ABSTAIN:
            abstain_count += 1
        else:
            errors.append(f"UNKNOWN_LEAF:{i}")
        if not isinstance(scorer, Mapping):
            errors.append(f"SCORER_RESULT_NOT_OBJECT:{i}")
            continue
        req(scorer.get("case_id") == case_id, f"SCORER_CASE_ID_MISMATCH:{i}")
        req(scorer.get("leaf_id") == leaf_id, f"SCORER_LEAF_MISMATCH:{i}")
        req(scorer.get("pass") is True, f"SCORER_CASE_NOT_PASS:{i}")
        req(scorer.get("errors") == [], f"SCORER_ERRORS_NONEMPTY:{i}")
        req(scorer.get("acceptance_credit_delta") == 0, f"SCORER_SELF_AWARDS_ACCEPTANCE:{i}")
        req(scorer.get("family_credit_delta") == 0, f"SCORER_SELF_AWARDS_FAMILY:{i}")
        req(scorer.get("promotion_authority") is False, f"SCORER_SELF_GRANTS_PROMOTION:{i}")
        if leaf_id == ABSTAIN:
            cls = str(scorer.get("case_class") or "")
            if cls not in classes:
                errors.append(f"ABSTENTION_CLASS_INVALID:{i}")
            else:
                classes[cls] += 1

    req(len(ids) == 27 and len(set(ids)) == 27, "CASE_IDS_INVALID_OR_DUPLICATE")
    req(transfer_count == 12, "TRANSFER_CASE_COUNT_NOT_12")
    req(abstain_count == 15, "ABSTENTION_CASE_COUNT_NOT_15")
    req(classes == EXPECTED_BALANCE, "ABSTENTION_CLASS_BALANCE_MISMATCH")

    agg = result.get("aggregate")
    if not isinstance(agg, Mapping):
        errors.append("AGGREGATE_NOT_OBJECT")
    else:
        req(agg.get("status") == "TWO_FROZEN_LEAVES_PASS", "AGGREGATE_STATUS_NOT_PASS")
        req(agg.get("transfer_leaf_pass") is True, "TRANSFER_LEAF_NOT_PASS")
        req(agg.get("abstention_leaf_pass") is True, "ABSTENTION_LEAF_NOT_PASS")
        req(agg.get("all_27_cases_pass") is True, "ALL_27_CASES_NOT_PASS")
        req(agg.get("case_count") == 27, "AGGREGATE_CASE_COUNT_NOT_27")
        req(agg.get("class_balance") == EXPECTED_BALANCE, "AGGREGATE_CLASS_BALANCE_MISMATCH")
        req(agg.get("acceptance_credit_delta") == 0, "AGGREGATE_SELF_AWARDS_ACCEPTANCE")
        req(agg.get("family_credit_delta") == 0, "AGGREGATE_SELF_AWARDS_FAMILY")
        req(agg.get("promotion_authority") is False, "AGGREGATE_SELF_GRANTS_PROMOTION")
        req(agg.get("separate_independent_reduction_required") is True, "AGGREGATE_SEPARATE_REDUCTION_FLAG_MISSING")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_UNKNOWN_DOMAIN_DIRECT_AUDIT_ELIGIBLE__SEPARATE_CANONICAL_INTEGRATION_REQUIRED" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(set(errors)),
        "target_predicate": TARGET,
        "newly_proved_predicates": [TARGET] if ok else [],
        "predicate_promotion_eligible": ok,
        "family_promotion_eligible": False,
        "family_closure_inferred": False,
        "promotion_authority": False,
        "execution_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "required_next_gate": "INDEPENDENT_EXACT_BYTE_VERIFICATION_OF_REDUCER_AND_IMMUTABLE_PRODUCTION_RESULT__THEN_CURRENT_STATE_FIXED_POINT_RECOMPUTATION",
        "hard_nonclaims": [
            "THIS_REDUCER_DOES_NOT_MUTATE_CANONICAL_ACCEPTANCE_STATE",
            "THIS_REDUCER_DOES_NOT_INFER_UNKNOWN_DOMAIN_FAMILY_CLOSURE",
            "NO_OTHER_PREDICATE_OR_FAMILY_RECEIVES_CREDIT",
            "NO_POST_RESULT_THRESHOLD_OR_SCORER_TUNING",
            "SEPARATE_INDEPENDENT_EXACT_BYTE_VERIFICATION_REQUIRED",
        ],
    }


def main(path: str) -> int:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    out = evaluate(obj)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m canonical.runtime.unknown_domain_production_result_reducer_v1 RESULT.json")
    raise SystemExit(main(sys.argv[1]))
