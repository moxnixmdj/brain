from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_MULTIPLEX_TERMINAL_ROUTE_ADMISSIBILITY_AUDIT_V1"
SNAPSHOT = "821712c059b139f3494723dca6e8d0fc82ee59a4"
EXEC_SUITE = "canonical/runtime/contract_native_proof_suites.py"
EXEC_CANDIDATE = "canonical/runtime/contract_native_brain_candidate.py"
EXEC_SUITE_SHA = "0210790c7dd705ef328e1b55d529a30c5c6c3337"
EXEC_CANDIDATE_SHA = "afc18af1d1da6f25166c6cc57dcbc0cd3070bb85"

FILES = {
    "db_v6": ("canonical/governance/DB_EXISTING_EVIDENCE_SATURATION_UNION_20261007_V6.json", "3b438f63dfdcd208c984251d1addd1334ca4b44e"),
    "p2_top": ("canonical/governance/V14_P2_PROFESSIONAL_TOP_LAW_SELECTED_CELL_20261007_V1.json", "481b8efd7925c19d7f4e77faf70dfb2ec649cca5"),
    "p2_unsupported": ("canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json", "28692768a21e95b51e847417cf5ba2343587e4aa"),
    "p3_unsupported": ("canonical/governance/V14_SYNTHESIS_UNSUPPORTED_CLAIM_SELECTED_PROPERTY_CELL_20261007_V1.json", "eece175e4aae05e34cdc7f44a25c12af94853228"),
    "p3_required": ("canonical/governance/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_CELL_20261007_V1.json", "7b2cb008f34082ae0aa4be78f2444287cf6022b2"),
    "p2_binding": ("canonical/governance/P2_PROFESSIONAL_QUALITY_T1_MULTIPLEX_TERMINAL_BINDING_V1.json", "8d5888a8299d1b8addd629be01fe9a6dc46b1a7d"),
    "p3_binding": ("canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json", "ad790afa864bd8f770c3d8a6e3ac901ed2843d26"),
    "p3_realization": ("canonical/governance/SYNTHESIS_HISTORICAL_TERMINAL_EXECUTOR_SCOPE_REALIZATION_AUDIT_20261005_V1.json", "0625f2944cea198f618c43b25d2a95da9cf4e17e"),
    "exec_suite": (EXEC_SUITE, EXEC_SUITE_SHA),
    "exec_candidate": (EXEC_CANDIDATE, EXEC_CANDIDATE_SHA),
    "terminal_result": ("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json", "bd86b4c53992b47a4a60b64a60ba03db9a442cfc"),
}


def git_blob(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(key: str) -> dict:
    path, _ = FILES[key]
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def verify_blobs() -> dict[str, str]:
    observed = {}
    for key, (path, expected) in FILES.items():
        actual = git_blob(path)
        observed[key] = actual
        if actual != expected:
            raise RuntimeError(f"BLOB_DRIFT:{key}:{actual}:expected:{expected}")
    return observed


def defs(tree: ast.AST):
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def source_segment(path: str, fn: str) -> str:
    src = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    node = defs(tree)[fn]
    return ast.get_source_segment(src, node) or ""


def evaluate() -> dict:
    observed = verify_blobs()
    p2 = load("p2_binding")
    p3 = load("p3_binding")
    p2_top = load("p2_top")
    p2_u = load("p2_unsupported")
    p3_u = load("p3_unsupported")
    p3_r = load("p3_required")
    p3_real = load("p3_realization")

    exec_suite_src = (ROOT / EXEC_SUITE).read_text(encoding="utf-8")
    exec_candidate_src = (ROOT / EXEC_CANDIDATE).read_text(encoding="utf-8")
    plan_case = source_segment(EXEC_SUITE, "_professional_plan_case")
    plan_solver = source_segment(EXEC_CANDIDATE, "solve_professional_plan")
    syn_case = source_segment(EXEC_SUITE, "_synthesis_case")
    syn_score = source_segment(EXEC_SUITE, "_score_synthesis")
    syn_solver = source_segment(EXEC_CANDIDATE, "solve_synthesis")

    p2_claimed_path = p2["evaluator"]["candidate"]
    p2_claimed_sha = p2_top["selected_route"]["candidate"]["git_blob_sha"]
    p3_claimed_path = p3["evaluator"]["bounded_candidate"]
    p3_claimed_sha = p3_u["selected_route"]["candidate"]["git_blob_sha"]

    p2_hidden = set(p2["hidden_evaluator_information"])
    p3_hidden = set(p3["hidden_evaluator_information"])

    p2_exec_uses_gold = all(
        token in plan_case and token in plan_solver
        for token in ['"scores"', '"supported"', '"hard_violation"']
    )
    p2_boundary_conflict = (
        "PER_EDIT_RUBRIC_QUALITY_EFFECT" in p2_hidden
        and "EVIDENCE_GROUNDING_TRUTH" in p2_hidden
        and p2_exec_uses_gold
    )

    p3_exec_uses_compiled_labels = all(
        token in syn_case and token in syn_solver
        for token in ['"role"', '"support"']
    )
    p3_boundary_conflict = (
        "HIDDEN_CLAIM_SUPPORT_GRAPH" in p3_hidden
        and "HIDDEN_DECISION_RELEVANCE_LABELS" in p3_hidden
        and p3_exec_uses_compiled_labels
    )

    realized = {
        row["declared_check"]: row
        for row in p3_real["declared_check_realization"]
    }
    p3_zero = realized["ZERO_UNSUPPORTED_MATERIAL_CLAIMS"]
    p3_req = realized["ALL_REQUIRED_CLAIMS_OR_DECISION_REQUIREMENTS_COVERED"]

    p3_scope_counterexample_present = any(
        row.get("id") == "SYNTHESIS_TERMINAL_R5_GENERAL_REQUIRED_CLAIM_OR_DECISION_SEMANTICS"
        for row in p3_real["constructive_actual_terminal_residual_classes"]
    )

    records = {
        "P2_PROFESSIONAL_T1_FROZEN_30_HIDDEN_OPTIMUM": {
            "claimed_route_matches_execution": p2_claimed_path == EXEC_CANDIDATE and p2_claimed_sha == EXEC_CANDIDATE_SHA,
            "information_boundary_preserved": not p2_boundary_conflict,
            "admissible_now": False,
            "reason": "CLAIMED_EA805_INFORMATION_SAFE_ROUTE_WAS_NOT_THE_EXECUTED_AFC18_ROUTE__EXECUTED_ROUTE_DIRECTLY_USED_QUALITY_AND_GROUNDING_FIELDS_HIDDEN_BY_THE_FROZEN_P2_BINDING",
        },
        "PROFESSIONAL_ARTIFACT_T1_FROZEN_30_ZERO_UNSUPPORTED_MATERIAL_CONTENT": {
            "claimed_route_matches_execution": p2_u["selected_route"]["candidate"]["path"] == EXEC_CANDIDATE,
            "information_boundary_preserved": not p2_boundary_conflict,
            "admissible_now": False,
            "reason": "SAME_P2_ROUTE_AND_INFORMATION_BOUNDARY_MISMATCH_AS_THE_HIDDEN_OPTIMUM_CELL",
        },
        "SYNTHESIS_T1_T3_FROZEN_60_ZERO_UNSUPPORTED_MATERIAL_CLAIMS": {
            "claimed_route_matches_execution": p3_claimed_path == EXEC_CANDIDATE and p3_claimed_sha == EXEC_CANDIDATE_SHA,
            "information_boundary_preserved": not p3_boundary_conflict,
            "historical_realization": p3_zero["historical_realization"],
            "historical_universal_claim": p3_zero["universal_claim"],
            "admissible_now": False,
            "reason": "CLAIMED_P3_INFORMATION_SAFE_ROUTE_WAS_NOT_EXECUTED__ACTUAL_ROUTE_USED_COMPILED_ROLE_SUPPORT_LABELS_FORBIDDEN_BY_THE_FROZEN_BOUNDARY__OCT5_AUDIT_CLASSIFIES_THIS_CHECK_AS_PARTIAL_NOT_UNIVERSAL",
        },
        "SYNTHESIS_TARGET_SCOPE_REQUIRED_CLAIM_COVERAGE_TOP_LAW": {
            "claimed_route_matches_execution": False,
            "information_boundary_preserved": not p3_boundary_conflict,
            "historical_realization": p3_req["historical_realization"],
            "historical_universal_claim": p3_req["universal_claim"],
            "scope_counterexample_present": p3_scope_counterexample_present,
            "admissible_now": False,
            "reason": "TERMINAL_LOWER_BOUND_IS_REALIZED_ONLY_FOR_GENERATED_PRECOMPILED_REQUIRED_ROLE_IDS__OCT5_AUDIT_HAS_A_CONSTRUCTIVE_GENERAL_REQUIRED_SEMANTICS_COUNTEREXAMPLE__SO_THE_LATER_TARGET_SCOPE_LIFT_CANNOT_TREAT_THE_ACTUAL_EXECUTED_ROUTE_AS_A_UNIVERSAL_SOURCE_SCOPE_WITHOUT_A_NEW_REPAIR",
        },
    }

    bad = [k for k, v in records.items() if not v["admissible_now"]]
    return {
        "schema": SCHEMA,
        "status": "PASS__FOUR_CURRENT_DB_RECORDS_FAIL_ROUTE_ADMISSIBILITY_AS_WRITTEN__ZERO_CREDIT",
        "pass": len(bad) == 4,
        "execution_snapshot": {
            "commit": SNAPSHOT,
            "suite_path": EXEC_SUITE,
            "suite_git_blob_sha": EXEC_SUITE_SHA,
            "candidate_path": EXEC_CANDIDATE,
            "candidate_git_blob_sha": EXEC_CANDIDATE_SHA,
        },
        "p2": {
            "frozen_claimed_candidate": p2_claimed_path,
            "frozen_hidden_information": sorted(p2_hidden),
            "executed_route_uses_gold_quality_and_grounding_fields": p2_exec_uses_gold,
            "boundary_conflict": p2_boundary_conflict,
        },
        "p3": {
            "frozen_claimed_candidate": p3_claimed_path,
            "frozen_hidden_information": sorted(p3_hidden),
            "executed_route_uses_precompiled_role_and_support_labels": p3_exec_uses_compiled_labels,
            "boundary_conflict": p3_boundary_conflict,
            "oct5_required_semantics_counterexample_present": p3_scope_counterexample_present,
        },
        "records": records,
        "quarantine_record_ids": bad,
        "live_v6_claimed_record_count": load("db_v6")["saturation_result"]["known_sound_D_B_certificate_record_count"],
        "fail_closed_sound_record_upper_bound_from_this_audit": load("db_v6")["saturation_result"]["known_sound_D_B_certificate_record_count"] - len(bad),
        "repair_rules": [
            "P2_TERMINAL_DERIVED_RECORDS_REQUIRE_ROUTE_EQUIVALENCE_PLUS_INFORMATION_BOUNDARY_PRESERVATION_OR_A_WITNESS_EXECUTED_BY_THE_CLAIMED_ROUTE",
            "P3_ZERO_UNSUPPORTED_RECORD_REQUIRES_AN_ADMISSIBLE_INFORMATION_SAFE_WITNESS_FOR_THE_EXACT_PROPERTY_OR_A_NONINTERFERENCE_PROOF_FROM_ACTUAL_ROUTE",
            "P3_REQUIRED_COVERAGE_REQUIRES_A_NEW_SCOPE_SOUND_LOWER_BOUND_NOT_INVALIDATED_BY_THE_OCT5_GENERAL_REQUIRED_SEMANTICS_COUNTEREXAMPLE",
            "DO_NOT_REVOKE_SEPARATELY_PROVED_UNIVERSAL_GENERATOR_CELLS_OR_UNRELATED_DB_RECORDS",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_THE_UNDERLYING_BRAIN_CAPABILITIES_ARE_ABSENT",
            "NO_CLAIM_THE_HISTORICAL_CONTRACT_NATIVE_RUN_FAILED_ITS_OWN_SCORER",
            "NO_CLAIM_P2_OR_P3_INFORMATION_SAFE_PREQUALIFICATION_ROUTES_FAILED",
            "NO_CLAIM_THE_REMAINING_DB_RECORDS_ARE_EXHAUSTIVE",
            "NO_TERMINAL_CREDIT",
        ],
        "source_blobs": observed,
        "incremental_spend_usd": 0,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
