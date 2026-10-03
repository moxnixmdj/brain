from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAND = "canonical/governance/TERMINAL_SCHEDULING_V12_ACTIVE_AUTHORITY_CANDIDATE_V1.json"
OLD = "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"
V11 = "canonical/governance/TERMINAL_SCHEDULING_V11_ACTIVE_AUTHORITY_CANDIDATE_V1.json"
POST = "canonical/governance/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_V1.json"
POSTV = "canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
V4 = "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V4_ACTIVATION_V1.json"
V4V = "canonical/verification/RETRIEVAL_V4_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
V4LIVE = "canonical/verification/RETRIEVAL_V4_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
GATE = "canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py"

EXPECTED = {
    CAND: "e9f0b028eeb6b1a36384bfc4f814f38a5ca79aa2",
    OLD: "54be838a5a0a9698398893ad113641496d5051b8",
    V11: "b2eae27ce999ce62105c9cbf7ed95048eb1fcac0",
    POST: "3b62096fdba09a41096f9aba12f9ec04d810cac8",
    POSTV: "f7f60a5932ac305aa0db8aef2643119dd10b33d9",
    V4: "643890c1d09844ea49de434df8ffec02962806e4",
    V4V: "e35dc954e0cf892d5522e62b5948bb64edeed4f7",
    V4LIVE: "ebb4ab1a05e47e20ecfacba41eb99d1f5c71694d",
    GATE: "b01292c1f198f251b8a9606b4de173541204c2dc",
}

def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def evaluate():
    drift = {
        path: {"expected": expected, "actual": blob(path)}
        for path, expected in EXPECTED.items()
        if blob(path) != expected
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

    c = load(CAND)
    old = load(OLD)
    v11 = load(V11)
    post = load(POST)
    postv = load(POSTV)
    v4 = load(V4)
    v4v = load(V4V)
    v4live = load(V4LIVE)
    errors = []

    if not str(old.get("status", "")).startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V10_CURRENT"):
        errors.append("PRIOR_CURRENT_POINTER_NOT_V10")
    if v11.get("live_world", {}).get("active_zero_reality_requirements") != 17:
        errors.append("V11_LINEAGE_REQUIREMENT_COUNT_DRIFT")
    if v11.get("fresh_reality_authority") is not False:
        errors.append("V11_LINEAGE_FRESH_REALITY_LEAK")

    pv = postv.get("verified") or {}
    if not str(postv.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POST_DUAL_FRONTIER_NOT_INDEPENDENT_PASS")
    expected_post = {
        "current_zero_reality_requirements": 17,
        "current_nondominated_zero_reality_certificates": 14,
        "zero_reality_covered_predicates": 25,
        "primitive_zero_reality_work_units": 31,
        "matched_priority_child_facts": 16,
    }
    for key, value in expected_post.items():
        if pv.get(key) != value:
            errors.append("POST_DUAL_VERIFIED_DRIFT:" + key)
    if pv.get("direct_reality_blocked_predicates") != [
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    ]:
        errors.append("POST_DUAL_DIRECT_REALITY_SET_DRIFT")
    if pv.get("current_global_fresh_reality_authority") is not False:
        errors.append("POST_DUAL_FRESH_REALITY_LEAK")

    if not str(v4v.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V4_ACTIVATION_NOT_INDEPENDENT_PASS")
    if not str(v4live.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V4_LIVE_GATE_NOT_INDEPENDENT_PASS")
    live_verified = v4live.get("verified") or {}
    for field in (
        "exact_dependency_chain_verified",
        "v2_and_v3_base_authority_preserved",
        "v4_activation_mandatory_in_live_gate",
        "v4_federated_router_receipts_mandatory",
        "unknown_preserved",
        "epoch_consumption_nonexistence_inference_forbidden",
        "zero_credit_preserved",
    ):
        if live_verified.get(field) is not True:
            errors.append("V4_LIVE_GATE_VERIFIED_FALSE:" + field)

    cl = c.get("live_world") or {}
    if (
        cl.get("registry_predicates"),
        cl.get("proved_predicates"),
        cl.get("unresolved_predicates"),
        cl.get("active_zero_reality_requirements"),
        cl.get("active_nondominated_certificates"),
        cl.get("zero_reality_covered_predicates"),
        cl.get("primitive_zero_reality_work_units"),
        cl.get("matched_priority_child_facts"),
    ) != (38, 11, 27, 17, 14, 25, 31, 16):
        errors.append("CANDIDATE_LIVE_WORLD_DRIFT")
    if cl.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        errors.append("CANDIDATE_ACCEPTANCE_DRIFT")
    if cl.get("direct_reality_blocked_predicates") != [
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    ]:
        errors.append("CANDIDATE_DIRECT_REALITY_SET_DRIFT")

    td = c.get("mandatory_tool_discovery_retrieval") or {}
    if td.get("authority") != "V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE":
        errors.append("CANDIDATE_TOOL_DISCOVERY_AUTHORITY_NOT_V4")
    if td.get("gate_git_blob_sha") != EXPECTED[GATE]:
        errors.append("CANDIDATE_GATE_HASH_DRIFT")
    if td.get("v4_activation_git_blob_sha") != EXPECTED[V4]:
        errors.append("CANDIDATE_V4_ACTIVATION_HASH_DRIFT")
    if td.get("v4_activation_verification_git_blob_sha") != EXPECTED[V4V]:
        errors.append("CANDIDATE_V4_ACTIVATION_VERIFICATION_HASH_DRIFT")
    if td.get("v4_live_gate_verification_git_blob_sha") != EXPECTED[V4LIVE]:
        errors.append("CANDIDATE_V4_LIVE_GATE_HASH_DRIFT")
    if td.get("mandatory") is not True:
        errors.append("CANDIDATE_V4_NOT_MANDATORY")
    if td.get("diversity_preserving_federation_required") is not True:
        errors.append("CANDIDATE_V4_DIVERSITY_NOT_REQUIRED")
    if td.get("one_router_attempt_receipt_per_selected_cell_required") is not True:
        errors.append("CANDIDATE_V4_RECEIPTS_NOT_REQUIRED")
    if td.get("backend_unbound_counts_as_attempt") is not False:
        errors.append("CANDIDATE_BACKEND_UNBOUND_ATTEMPT_LEAK")
    if td.get("empty_or_failed_attempt_proves_nonexistence") is not False:
        errors.append("CANDIDATE_NONEXISTENCE_LEAK")
    if td.get("consumed_source_epoch_replay_allowed") is not False:
        errors.append("CANDIDATE_SOURCE_EPOCH_REPLAY_LEAK")

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
            "PASS__V12_BINDS_POST_DUAL_31_WORK_UNIT_FRONTIER_AND_VERIFIED_V4_RETRIEVAL__ZERO_CREDIT__NO_FRESH_REALITY"
            if ok else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "active_zero_reality_requirements": 17 if ok else None,
        "active_nondominated_certificates": 14 if ok else None,
        "zero_reality_covered_predicates": 25 if ok else None,
        "primitive_zero_reality_work_units": 31 if ok else None,
        "direct_reality_blocked_predicates": (
            ["FINANCE_UNCOVERED_SCOPE_AUDIT", "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
            if ok else None
        ),
        "tool_discovery_retrieval_authority": (
            "V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE" if ok else None
        ),
        "opus55_acceptance": "4/19_PASS__15/19_OPEN",
        "fresh_reality_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
