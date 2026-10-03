from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "candidate": "canonical/governance/TERMINAL_SCHEDULING_V13_ACTIVE_AUTHORITY_CANDIDATE_V1.json",
    "v12": "canonical/governance/TERMINAL_SCHEDULING_V12_ACTIVE_AUTHORITY_V1.json",
    "v12v": "canonical/verification/TERMINAL_SCHEDULING_V12_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "post": "canonical/governance/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_V1.json",
    "postv": "canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "v5": "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V5_ACTIVATION_V1.json",
    "v5v": "canonical/verification/RETRIEVAL_V5_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "v5e": "canonical/verification/RETRIEVAL_V5_FEDERATION_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "v5live": "canonical/verification/RETRIEVAL_V5_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "gate": "canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py",
}

EXPECTED = {
    PATHS["candidate"]: "2b597ea1840196623a2d7e31f9c613cd993ec6ba",
    PATHS["v12"]: "43108097f5542e5aa15cd2452125f52a863fa2ba",
    PATHS["v12v"]: "b075e9f0d97f8d72db7e74bc36bb378e34b8fead",
    PATHS["post"]: "3b62096fdba09a41096f9aba12f9ec04d810cac8",
    PATHS["postv"]: "f7f60a5932ac305aa0db8aef2643119dd10b33d9",
    PATHS["v5"]: "8b8b80d43972bb7113b193baaf21dbda292d595e",
    PATHS["v5v"]: "acd898bdea67ef0337e33b4335426fbe0dd7320d",
    PATHS["v5e"]: "cd1501e167a5429ad0d918e080c527e6d43b8a4d",
    PATHS["v5live"]: "aa3a1ff960ba0f02ff5ad118053cf1b7d382d91b",
    PATHS["gate"]: "c3324e574c1fafb6aaab443f49b7a9600966e754",
}

def blob(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def evaluate():
    drift = {
        p: {"expected": h, "actual": blob(p)}
        for p, h in EXPECTED.items()
        if blob(p) != h
    }
    if drift:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "errors": ["SOURCE_BLOB_DRIFT"],
            "drift": drift,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }

    c = load(PATHS["candidate"])
    v12 = load(PATHS["v12"])
    v12v = load(PATHS["v12v"])
    postv = load(PATHS["postv"])
    v5v = load(PATHS["v5v"])
    v5e = load(PATHS["v5e"])
    v5live = load(PATHS["v5live"])
    errors = []

    if c.get("schema") != "PROJECT_BRAIN_TERMINAL_SCHEDULING_V13_ACTIVE_AUTHORITY_CANDIDATE_V1":
        errors.append("CANDIDATE_SCHEMA_INVALID")
    if not str(v12.get("status", "")).startswith("CANDIDATE_CURRENT_AUTHORITY__V12_INDEPENDENT_PASS"):
        errors.append("V12_LINEAGE_NOT_INDEPENDENT_PASS")
    if not str(v12v.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V12_VERIFICATION_NOT_PASS")
    if not str(postv.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POST_DUAL_FRONTIER_NOT_PASS")
    if not str(v5v.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V5_ACTIVATION_NOT_PASS")
    if not str(v5e.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V5_EXECUTION_NOT_PASS")
    if not str(v5live.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V5_LIVE_GATE_NOT_PASS")

    live = c.get("live_world") or {}
    expected_live = (38, 11, 27, "4/19_PASS__15/19_OPEN", 17, 14, 25, 31, 16)
    actual_live = (
        live.get("registry_predicates"),
        live.get("proved_predicates"),
        live.get("unresolved_predicates"),
        live.get("opus55_acceptance"),
        live.get("active_zero_reality_requirements"),
        live.get("active_nondominated_certificates"),
        live.get("zero_reality_covered_predicates"),
        live.get("primitive_zero_reality_work_units"),
        live.get("matched_priority_child_facts"),
    )
    if actual_live != expected_live:
        errors.append("LIVE_WORLD_DRIFT")
    if live.get("direct_reality_blocked_predicates") != [
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    ]:
        errors.append("DIRECT_REALITY_SET_DRIFT")

    r = c.get("mandatory_tool_discovery_retrieval") or {}
    if r.get("authority") != "V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE":
        errors.append("RETRIEVAL_AUTHORITY_NOT_V5")
    if r.get("gate_git_blob_sha") != EXPECTED[PATHS["gate"]]:
        errors.append("RETRIEVAL_GATE_HASH_DRIFT")
    if r.get("v5_activation_git_blob_sha") != EXPECTED[PATHS["v5"]]:
        errors.append("V5_ACTIVATION_HASH_DRIFT")
    if r.get("v5_activation_verification_git_blob_sha") != EXPECTED[PATHS["v5v"]]:
        errors.append("V5_ACTIVATION_VERIFICATION_HASH_DRIFT")
    if r.get("v5_execution_verification_git_blob_sha") != EXPECTED[PATHS["v5e"]]:
        errors.append("V5_EXECUTION_VERIFICATION_HASH_DRIFT")
    if r.get("v5_live_gate_verification_git_blob_sha") != EXPECTED[PATHS["v5live"]]:
        errors.append("V5_LIVE_GATE_HASH_DRIFT")

    required_true = [
        "mandatory",
        "strict_success_only_source_cell_consumption_required",
        "transient_failures_retryable_and_unconsumed",
        "all_selected_cells_required_before_epoch_consumption",
    ]
    for key in required_true:
        if r.get(key) is not True:
            errors.append("REQUIRED_TRUE_FALSE:" + key)
    required_false = [
        "partial_batch_epoch_consumption_allowed",
        "off_domain_result_may_satisfy_source_cell",
        "consumed_cell_replay_allowed",
        "empty_or_failed_attempt_proves_nonexistence",
    ]
    for key in required_false:
        if r.get(key) is not False:
            errors.append("REQUIRED_FALSE_TRUE:" + key)

    lv = v5live.get("verified") or {}
    for key in (
        "v2_v3_v4_v5_chain_passes",
        "v5_success_only_epoch_consumption_mandatory",
        "missing_retry_rule_fails_closed",
        "missing_partial_batch_rule_fails_closed",
        "failed_v5_activation_receipt_fails_closed",
        "failed_v5_execution_receipt_fails_closed",
        "stale_v5_executor_hash_fails_closed",
        "zero_credit_preserved",
    ):
        if lv.get(key) is not True:
            errors.append("V5_LIVE_GATE_VERIFIED_FALSE:" + key)

    policy = c.get("execution_policy") or {}
    for key in (
        "run_all_31_zero_reality_work_units_concurrently",
        "matched_16_child_facts_first_resource_priority_without_serializing_siblings",
        "fixed_point_after_every_independently_verified_delta",
        "recompute_frontier_after_every_verified_delta",
        "cancel_newly_dominated_branches",
        "ownership_reconciliation_parallel_with_acceptance",
    ):
        if policy.get(key) is not True:
            errors.append("EXECUTION_POLICY_FALSE:" + key)
    if policy.get("fresh_reality_before_zero_reality_fixed_point") is not False:
        errors.append("FRESH_REALITY_POLICY_LEAK")

    for key in (
        "new_reality_units_consumed",
        "incremental_spend_usd",
        "acceptance_credit_delta",
        "capability_credit_delta",
        "family_credit_delta",
        "ownership_credit_delta",
    ):
        if c.get(key) != 0:
            errors.append("NONZERO_CREDIT_OR_REALITY:" + key)
    if c.get("execution_authority") is not False:
        errors.append("EXECUTION_AUTHORITY_LEAK")
    if c.get("promotion_authority") is not False:
        errors.append("PROMOTION_AUTHORITY_LEAK")
    if c.get("fresh_reality_authority") is not False:
        errors.append("FRESH_REALITY_AUTHORITY_LEAK")

    ok = not errors
    return {
        "pass": ok,
        "status": (
            "PASS__V13_PRESERVES_POST_DUAL_31_WORK_UNIT_FRONTIER__STRICT_RETRIEVAL_V5_BOUND__ZERO_CREDIT__NO_FRESH_REALITY"
            if ok else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "active_zero_reality_requirements": 17 if ok else None,
        "active_nondominated_certificates": 14 if ok else None,
        "primitive_zero_reality_work_units": 31 if ok else None,
        "tool_discovery_retrieval_authority": (
            "V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE" if ok else None
        ),
        "opus55_acceptance": "4/19_PASS__15/19_OPEN",
        "proved_predicates": 11,
        "unresolved_predicates": 27,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out.get("pass") is True else 1)
