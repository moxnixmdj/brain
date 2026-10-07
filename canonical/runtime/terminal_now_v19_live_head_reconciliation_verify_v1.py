from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "authority": (
        ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json",
        "c1bc4543860be08f9014f69a212ba2222d8dba7c",
    ),
    "trace_verify": (
        ROOT / "canonical/verification/ABC_OBSERVABLE_TRACE_SCOPE_REBIND_SPRITE_VERIFICATION_20261007_V1.json",
        "5853776c01c928202722211126009db905c49629",
    ),
    "db": (
        ROOT / "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V5.json",
        "6b389699903b63f1350dd922064888e74201f687",
    ),
    "db_verify": (
        ROOT / "canonical/verification/V16_DB_EXISTING_EVIDENCE_SATURATION_WOLFRAM_CONNECTOR_VERIFY_20261007_V5.json",
        "d7b4f99fdde85983cfbb72f777edcef2075d74af",
    ),
    "unknown": (
        ROOT / "canonical/governance/UNKNOWN_DOMAIN_SHARED_SEMANTIC_TAIL_COLLAPSE_20261007_V1.json",
        "069dd49aa1be27b218a66eb2f91c6de5cd49ff27",
    ),
    "unknown_verify": (
        ROOT / "canonical/verification/UNKNOWN_DOMAIN_SHARED_SEMANTIC_TAIL_COLLAPSE_WOLFRAM_VERIFICATION_20261007_V1.json",
        "771cacd2de47025b6e546eb9cc18fb3cb0a56a3b",
    ),
    "router": (
        ROOT / "canonical/runtime/certificate_gated_selected_route_router_v1.py",
        "4b99ef1e95e033badfb21ab7af7355122933224a",
    ),
    "router_test": (
        ROOT / "canonical/tests/test_certificate_gated_selected_route_router_v1.py",
        "b33717611b21f01f11d570d894aeee7f010231fc",
    ),
}


def git_blob(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    cp = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", f"HEAD:{rel}"],
        text=True,
        capture_output=True,
        check=False,
    )
    return cp.stdout.strip() if cp.returncode == 0 else ""


def load(name: str) -> dict:
    return json.loads(SOURCES[name][0].read_text(encoding="utf-8"))


def verify() -> dict:
    errors: list[str] = []

    for name, (path, expected) in SOURCES.items():
        actual = git_blob(path)
        if actual != expected:
            errors.append(f"SOURCE_DRIFT:{name}:{actual}:{expected}")

    authority = load("authority")
    trace = load("trace_verify")
    db = load("db")
    dbv = load("db_verify")
    unknown = load("unknown")
    unknownv = load("unknown_verify")
    router_text = SOURCES["router"][0].read_text(encoding="utf-8")
    router_test_text = SOURCES["router_test"][0].read_text(encoding="utf-8")

    truth = authority["truth_repair"]
    if truth["fixed_authorized_opus55_target_interface_scope_superset_closed"] is not True:
        errors.append("TARGET_SCOPE_NOT_CLOSED")
    if truth["literal_all_target_universe_exhaustiveness_is_separate_open_task"] is not False:
        errors.append("STALE_LITERAL_ALL_SEPARATE_BLOCKER")
    if trace["result"]["target_scope_superset_closed"] is not True:
        errors.append("TRACE_SCOPE_REPLAY_NOT_CLOSED")
    if trace["result"]["abc_closed"] is not False:
        errors.append("TRACE_SCOPE_REPLAY_SMEARS_SCOPE_INTO_ABC")

    if db["reconciliation"]["known_sound_region_certificate_count"] != 12:
        errors.append("DB_REGION_COUNT_NOT_12")
    if dbv["delta_check"]["reconciled_certificate_count"] != 12:
        errors.append("DB_VERIFICATION_REGION_COUNT_NOT_12")
    if dbv["formal_check"]["result"] is not True:
        errors.append("DB_MONOTONICITY_VERIFICATION_FAILED")

    udf = unknown["unknown_domain_frontier_after"]
    if udf["separate_named_behavior_mechanism_residual_count"] != 0:
        errors.append("UNKNOWN_DOMAIN_DUPLICATE_MECHANISM_RESIDUALS_REMAIN")
    if udf["shared_semantic_tail_still_open"] is not True:
        errors.append("UNKNOWN_DOMAIN_SEMANTIC_TAIL_FALSELY_CLOSED")
    if unknownv["wolfram"]["result"] is not True:
        errors.append("UNKNOWN_DOMAIN_DEPENDENCY_REDUCTION_NOT_VERIFIED")
    if unknownv["verified_consequence"]["terminal"] is not False:
        errors.append("UNKNOWN_DOMAIN_VERIFICATION_FALSE_TERMINAL_CREDIT")

    if 'type(r.admitted) is not bool' not in router_text:
        errors.append("ROUTER_NON_BOOLEAN_FAIL_CLOSED_GUARD_MISSING")
    if "test_non_boolean_admission_fails_closed" not in router_test_text:
        errors.append("ROUTER_NON_BOOLEAN_NEGATIVE_TEST_MISSING")

    if truth["complete_selected_context_ABC_closed"] is not False:
        errors.append("ABC_FALSE_BOUNDARY_DRIFT")
    if truth["D_finality_closed"] is not False:
        errors.append("D_FINALITY_FALSE_BOUNDARY_DRIFT")
    if truth["terminal"] is not False:
        errors.append("TERMINAL_FALSE_BOUNDARY_DRIFT")

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_NOW_V19_LIVE_HEAD_RECONCILIATION_VERIFY_V1",
        "pass": not errors,
        "status": "PASS__LIVE_TRUTH_RECONCILED__TERMINAL_REMAINS_FAIL_CLOSED" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "target_scope_structurally_closed": not errors,
        "known_sound_D_B_region_certificate_count": 12 if not errors else None,
        "unknown_domain_separate_named_behavior_mechanism_residual_count": 0 if not errors else None,
        "router_non_boolean_admission_fails_closed": not errors,
        "complete_selected_context_ABC_closed": False,
        "D_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
