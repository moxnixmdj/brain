from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PTR = "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V12_CANDIDATE_V1.json"
ACTIVE = "canonical/governance/TERMINAL_SCHEDULING_V12_ACTIVE_AUTHORITY_V1.json"
VERIFY = "canonical/verification/TERMINAL_SCHEDULING_V12_POST_DUAL_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
EXPECTED = {
    PTR: "bc578e6db4eedcefbed61f6860e1cc5192cf05f4",
    ACTIVE: "43108097f5542e5aa15cd2452125f52a863fa2ba",
    VERIFY: "86f4ec2da215491bf4de9812cf76e3e1f5120ee2",
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

    p = load(PTR)
    a = load(ACTIVE)
    v = load(VERIFY)
    errors = []

    if not str(a.get("status", "")).startswith(
        "CANDIDATE_CURRENT_AUTHORITY__V12_INDEPENDENT_PASS"
    ):
        errors.append("ACTIVE_AUTHORITY_STATUS_INVALID")
    if not str(v.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V12_VERIFICATION_NOT_INDEPENDENT_PASS")

    ca = p.get("current_authority") or {}
    if ca.get("path") != ACTIVE or ca.get("git_blob_sha") != EXPECTED[ACTIVE]:
        errors.append("POINTER_ACTIVE_AUTHORITY_BINDING_INVALID")
    iv = p.get("independent_verification") or {}
    if iv.get("path") != VERIFY or iv.get("git_blob_sha") != EXPECTED[VERIFY]:
        errors.append("POINTER_VERIFICATION_BINDING_INVALID")
    if iv.get("conclusion") != "success":
        errors.append("POINTER_VERIFICATION_CONCLUSION_INVALID")

    live = p.get("live_world") or {}
    if (
        live.get("registry_predicates"),
        live.get("proved_predicates"),
        live.get("unresolved_predicates"),
        live.get("active_zero_reality_requirements"),
        live.get("active_nondominated_certificates"),
        live.get("zero_reality_covered_predicates"),
        live.get("primitive_zero_reality_work_units"),
        live.get("matched_priority_child_facts"),
    ) != (38, 11, 27, 17, 14, 25, 31, 16):
        errors.append("POINTER_LIVE_WORLD_INVALID")
    if live.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        errors.append("POINTER_ACCEPTANCE_INVALID")
    if live.get("direct_reality_blocked_predicates") != [
        "FINANCE_UNCOVERED_SCOPE_AUDIT",
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    ]:
        errors.append("POINTER_DIRECT_REALITY_SET_INVALID")

    vv = v.get("verified") or {}
    for key, expected in (
        ("active_zero_reality_requirements", 17),
        ("active_nondominated_certificates", 14),
        ("zero_reality_covered_predicates", 25),
        ("primitive_zero_reality_work_units", 31),
        ("matched_priority_child_facts", 16),
        ("proved_predicates", 11),
        ("unresolved_predicates", 27),
    ):
        if vv.get(key) != expected:
            errors.append("VERIFICATION_COUNT_DRIFT:" + key)
    if vv.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        errors.append("VERIFICATION_ACCEPTANCE_DRIFT")
    if vv.get("fresh_reality_authority") is not False:
        errors.append("VERIFICATION_FRESH_REALITY_LEAK")

    td = p.get("mandatory_tool_discovery_retrieval") or {}
    if td.get("authority") != "V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE":
        errors.append("POINTER_TOOL_DISCOVERY_AUTHORITY_INVALID")
    if td.get("mandatory") is not True:
        errors.append("POINTER_TOOL_DISCOVERY_NOT_MANDATORY")
    if td.get("direct_bypass_allowed") is not False:
        errors.append("POINTER_DIRECT_BYPASS_LEAK")
    if td.get("stale_authority_allowed") is not False:
        errors.append("POINTER_STALE_AUTHORITY_LEAK")
    if td.get("pre_v4_epoch_exhaustion_allowed") is not False:
        errors.append("POINTER_PRE_V4_EXHAUSTION_LEAK")
    if td.get("consumed_source_epoch_replay_allowed") is not False:
        errors.append("POINTER_SOURCE_EPOCH_REPLAY_LEAK")
    if td.get("no_result_means_nonexistence") is not False:
        errors.append("POINTER_NONEXISTENCE_LEAK")
    if td.get("diversity_preserving_federation_required") is not True:
        errors.append("POINTER_DIVERSITY_REQUIREMENT_MISSING")
    if td.get("one_router_attempt_receipt_per_selected_cell_required") is not True:
        errors.append("POINTER_ROUTER_RECEIPT_REQUIREMENT_MISSING")

    for key in (
        "new_reality_units_consumed",
        "incremental_spend_usd",
        "acceptance_credit_delta",
        "capability_credit_delta",
        "family_credit_delta",
        "ownership_credit_delta",
    ):
        if p.get(key) != 0:
            errors.append("POINTER_NONZERO_CREDIT_OR_REALITY:" + key)
    if p.get("execution_authority") is not False:
        errors.append("POINTER_EXECUTION_AUTHORITY_LEAK")
    if p.get("promotion_authority") is not False:
        errors.append("POINTER_PROMOTION_AUTHORITY_LEAK")
    if p.get("fresh_reality_authority") is not False:
        errors.append("POINTER_FRESH_REALITY_AUTHORITY_LEAK")

    ok = not errors
    return {
        "pass": ok,
        "status": (
            "PASS__V12_FINAL_POINTER_EXACT_BLOB_VERIFIED__17_REQUIREMENTS__31_WORK_UNITS__V4_MANDATORY__ZERO_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "pointer_blob_sha": EXPECTED[PTR] if ok else None,
        "active_authority_blob_sha": EXPECTED[ACTIVE] if ok else None,
        "active_zero_reality_requirements": 17 if ok else None,
        "primitive_zero_reality_work_units": 31 if ok else None,
        "tool_discovery_retrieval_authority": (
            "V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE" if ok else None
        ),
        "fresh_reality_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
    }

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
