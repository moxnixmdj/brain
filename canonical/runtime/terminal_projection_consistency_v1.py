"""Fail-closed consistency reducer for Project Brain terminal projections.

This checker grants no capability or promotion credit. It verifies that the
derived control-plane projections agree with the current independently verified
Opus 5.5 acceptance calibration and residual frontier, and that authority blob
pointers match the actual Git blob identities of their source files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "closure": "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
    "matrix": "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "calibration": "canonical/verification/OPUS55_ACCEPTANCE_CALIBRATION_AUDIT_20261002_V3.json",
    "residual": "canonical/verification/OPUS55_ACCEPTANCE_RESIDUAL_COMPILER_V2_VERDICT_20261002_V10.json",
    "plan": "canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_MINIMUM_PROOF_PLAN_V1.json",
    "kernel": "canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_PROOF_KERNEL_V2.json",
    "eligibility": "canonical/verification/OPUS55_FAMILY_OWNERSHIP_PROMOTION_ELIGIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
}

EXPECTED_CALIBRATED = {
    "EXACT_SYMBOLIC_COMPUTATION",
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    "SUBAGENT_DELEGATION_AND_COORDINATION",
}

def _load(rel: str) -> dict[str, Any]:
    v = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(v, dict):
        raise ValueError(rel)
    return v

def _git_blob_sha(rel: str) -> str:
    b = (ROOT / rel).read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(b)}\0".encode())
    h.update(b)
    return h.hexdigest()

def evaluate_documents(
    authority: Mapping[str, Any],
    closure: Mapping[str, Any],
    matrix: Mapping[str, Any],
    calibration: Mapping[str, Any],
    residual: Mapping[str, Any],
    plan: Mapping[str, Any],
    kernel: Mapping[str, Any],
    eligibility: Mapping[str, Any],
    actual_blob_shas: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    truth = authority.get("truth")
    if not isinstance(truth, Mapping):
        errors.append("AUTHORITY_TRUTH_MISSING")
        truth = {}
    if truth.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_NOT_4_OF_19")
    if truth.get("verified_owned") != "4/19_VERIFIED_OWNED__15/19_NOT_YET_OWNED":
        errors.append("AUTHORITY_OWNERSHIP_NOT_4_OF_19")
    if truth.get("achieved") is not False:
        errors.append("AUTHORITY_TERMINAL_GOAL_MUST_REMAIN_FALSE")

    cres = calibration.get("result")
    if not isinstance(cres, Mapping):
        errors.append("CALIBRATION_RESULT_MISSING")
        cres = {}
    if cres.get("acceptance_calibrated_family_count") != 4:
        errors.append("CALIBRATION_COUNT_NOT_4")
    if cres.get("acceptance_pending_family_count") != 15:
        errors.append("CALIBRATION_PENDING_NOT_15")
    if set(cres.get("acceptance_calibrated_families") or []) != EXPECTED_CALIBRATED:
        errors.append("CALIBRATION_FAMILY_SET_MISMATCH")
    if cres.get("terminal_goal_acceptance_closed") is not False:
        errors.append("CALIBRATION_TERMINAL_GOAL_MUST_REMAIN_FALSE")

    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(eligibility.get("status", "")):
        errors.append("OWNERSHIP_ELIGIBILITY_NOT_INDEPENDENT_PASS")
    eres = eligibility.get("result")
    if not isinstance(eres, Mapping):
        errors.append("OWNERSHIP_ELIGIBILITY_RESULT_MISSING")
        eres = {}
    if eres.get("eligible_family_count") != 2:
        errors.append("OWNERSHIP_ELIGIBILITY_COUNT_NOT_2")
    if set(eres.get("eligible_families") or []) != {"TOOL_DISCOVERY_SELECTION_AND_LEARNING", "SUBAGENT_DELEGATION_AND_COORDINATION"}:
        errors.append("OWNERSHIP_ELIGIBILITY_FAMILY_SET_MISMATCH")
    if eres.get("projected_strict_owned_families_after_atomic_promotion") != 4:
        errors.append("OWNERSHIP_ELIGIBILITY_PROJECTION_NOT_4")
    if eres.get("terminal_goal_achieved") is not False:
        errors.append("OWNERSHIP_ELIGIBILITY_MUST_NOT_CLOSE_TERMINAL_GOAL")
    pv = eligibility.get("public_verifier")
    if not isinstance(pv, Mapping) or pv.get("conclusion") != "success":
        errors.append("OWNERSHIP_ELIGIBILITY_PUBLIC_VERIFIER_NOT_SUCCESS")

    if residual.get("predicate_count") != 38:
        errors.append("RESIDUAL_PREDICATE_COUNT_NOT_38")
    if residual.get("proved_predicate_count") != 9:
        errors.append("RESIDUAL_PROVED_COUNT_NOT_9")
    if residual.get("open_predicate_count") != 0:
        errors.append("RESIDUAL_OPEN_COUNT_NOT_0")
    if residual.get("blocked_predicate_count") != 29:
        errors.append("RESIDUAL_BLOCKED_COUNT_NOT_29")
    if residual.get("authorized_acceptance_case_actions") != []:
        errors.append("RESIDUAL_UNAUTHORIZED_CASE_ACTION_PRESENT")
    tb = residual.get("tb4_attainability")
    if not isinstance(tb, Mapping) or tb.get("reality_execution_authorized") is not False:
        errors.append("TB4_REALITY_MUST_REMAIN_REVOKED")
    elif not (
        isinstance(tb.get("maximum_attainable_successes"), int)
        and isinstance(tb.get("required_successes"), int)
        and tb["maximum_attainable_successes"] < tb["required_successes"]
    ):
        errors.append("TB4_ATTAINABILITY_INEQUALITY_INVALID")

    summary = closure.get("opus55_acceptance_summary")
    if not isinstance(summary, Mapping):
        errors.append("CLOSURE_ACCEPTANCE_SUMMARY_MISSING")
        summary = {}
    if summary.get("calibrated_family_count") != 4 or summary.get("pending_family_count") != 15:
        errors.append("CLOSURE_ACCEPTANCE_SUMMARY_MISMATCH")
    if set(summary.get("calibrated_families") or []) != EXPECTED_CALIBRATED:
        errors.append("CLOSURE_ACCEPTANCE_FAMILY_SET_MISMATCH")
    promotion = closure.get("family_local_ownership_promotion")
    if not isinstance(promotion, Mapping):
        errors.append("CLOSURE_FAMILY_LOCAL_PROMOTION_MISSING")
        promotion = {}
    if promotion.get("verified_owned_family_count") != 4:
        errors.append("CLOSURE_VERIFIED_OWNED_COUNT_NOT_4")
    if set(promotion.get("promoted_families") or []) != {"TOOL_DISCOVERY_SELECTION_AND_LEARNING", "SUBAGENT_DELEGATION_AND_COORDINATION"}:
        errors.append("CLOSURE_PROMOTED_FAMILY_SET_MISMATCH")
    if promotion.get("terminal_goal_achieved") is not False:
        errors.append("CLOSURE_PROMOTION_MUST_NOT_CLOSE_TERMINAL_GOAL")
    if promotion.get("eligibility_evidence") != PATHS["eligibility"]:
        errors.append("CLOSURE_PROMOTION_EVIDENCE_MISMATCH")

    predicates = closure.get("terminal_predicates")
    if not isinstance(predicates, Mapping):
        errors.append("CLOSURE_TERMINAL_PREDICATES_MISSING")
        predicates = {}
    if predicates.get("all_frozen_opus_acceptance_predicates_pass") is not False:
        errors.append("CLOSURE_MUST_NOT_CLAIM_ALL_ACCEPTANCE_PASS")
    if predicates.get("proof_bundle_frozen") is not False:
        errors.append("CLOSURE_PROOF_BUNDLE_MUST_REMAIN_UNFROZEN")

    msum = matrix.get("postwave_acceptance_summary")
    if not isinstance(msum, Mapping):
        errors.append("MATRIX_ACCEPTANCE_SUMMARY_MISSING")
        msum = {}
    if msum.get("calibrated_family_count") != 4 or msum.get("pending_acceptance_family_count") != 15:
        errors.append("MATRIX_ACCEPTANCE_SUMMARY_MISMATCH")
    if msum.get("verified_owned_family_count") != 4:
        errors.append("MATRIX_VERIFIED_OWNED_COUNT_NOT_4")
    expected_owned = {
        "EXACT_SYMBOLIC_COMPUTATION",
        "LONG_HORIZON_MEMORY_AND_CONTINUITY",
        "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        "SUBAGENT_DELEGATION_AND_COORDINATION",
    }
    if set(matrix.get("summary", {}).get("verified_owned_equal_or_better_capabilities") or []) != expected_owned:
        errors.append("MATRIX_VERIFIED_OWNED_SET_MISMATCH")
    rows = matrix.get("rows")
    tool = None
    if isinstance(rows, list):
        tool = next((r for r in rows if isinstance(r, Mapping) and r.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"), None)
    if not isinstance(tool, Mapping):
        errors.append("MATRIX_TOOL_DISCOVERY_ROW_MISSING")
    else:
        if tool.get("postwave_opus55_acceptance_status") != "PASS_VIA_FULL_SCOPE_ABSOLUTE_DOMINANCE_WITNESS":
            errors.append("MATRIX_TOOL_DISCOVERY_ACCEPTANCE_NOT_PASS")
        if tool.get("status") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
            errors.append("MATRIX_TOOL_DISCOVERY_NOT_VERIFIED_OWNED")
        if tool.get("postwave_ownership_credit") != "VERIFIED_OWNED_EQUAL_OR_BETTER__INDEPENDENT_FAMILY_LOCAL_PROMOTION":
            errors.append("MATRIX_TOOL_DISCOVERY_PROMOTION_MISMATCH")
        if tool.get("ownership_promotion_evidence") != PATHS["eligibility"]:
            errors.append("MATRIX_TOOL_DISCOVERY_PROMOTION_EVIDENCE_MISMATCH")

    delegation = None
    if isinstance(rows, list):
        delegation = next((r for r in rows if isinstance(r, Mapping) and r.get("family") == "SUBAGENT_DELEGATION_AND_COORDINATION"), None)
    if not isinstance(delegation, Mapping):
        errors.append("MATRIX_DELEGATION_ROW_MISSING")
    else:
        if delegation.get("postwave_opus55_acceptance_status") != "PASS_VIA_TEMPORALLY_TRANSPORTED_FULL_SCOPE_ABSOLUTE_DOMINANCE_WITNESS":
            errors.append("MATRIX_DELEGATION_ACCEPTANCE_NOT_PASS")
        if delegation.get("status") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
            errors.append("MATRIX_DELEGATION_NOT_VERIFIED_OWNED")
        if delegation.get("postwave_ownership_credit") != "VERIFIED_OWNED_EQUAL_OR_BETTER__INDEPENDENT_FAMILY_LOCAL_PROMOTION":
            errors.append("MATRIX_DELEGATION_PROMOTION_MISMATCH")
        if delegation.get("ownership_promotion_evidence") != PATHS["eligibility"]:
            errors.append("MATRIX_DELEGATION_PROMOTION_EVIDENCE_MISMATCH")

    if plan.get("residual_family_count") != 15:
        errors.append("PLAN_PENDING_FAMILY_COUNT_NOT_15")
    pf = plan.get("residual_families")
    if not isinstance(pf, list):
        errors.append("PLAN_RESIDUAL_FAMILIES_MISSING")
    else:
        names = {r if isinstance(r, str) else r.get("family") for r in pf if isinstance(r, (str, Mapping))}
        if "TOOL_DISCOVERY_SELECTION_AND_LEARNING" in names:
            errors.append("PLAN_RETAINS_ALREADY_CALIBRATED_TOOL_DISCOVERY")
        if "SUBAGENT_DELEGATION_AND_COORDINATION" in names:
            errors.append("PLAN_RETAINS_ALREADY_CALIBRATED_DELEGATION")
        if len(names) != 15:
            errors.append("PLAN_RESIDUAL_FAMILY_SET_NOT_15")
    state = plan.get("current_acceptance_state")
    if not isinstance(state, Mapping):
        errors.append("PLAN_CURRENT_ACCEPTANCE_STATE_MISSING")
    else:
        expected = {
            "calibrated_family_count": 4,
            "pending_family_count": 15,
            "atomic_predicates_total": 38,
            "proved_atomic_predicates": 9,
            "blocked_atomic_predicates": 29,
            "open_direct_atomic_predicates": 0,
        }
        for k, v in expected.items():
            if state.get(k) != v:
                errors.append(f"PLAN_STATE_MISMATCH:{k}")
        if state.get("authorized_acceptance_case_actions") != []:
            errors.append("PLAN_UNAUTHORIZED_CASE_ACTION_PRESENT")

    ks = kernel.get("current_expected_state")
    if not isinstance(ks, Mapping):
        errors.append("KERNEL_CURRENT_STATE_MISSING")
    else:
        expected = {
            "residual_registry_families": 17,
            "acceptance_pending_families": 15,
            "atomic_predicates": 38,
            "receipt_saturation_complete": True,
            "proved_predicates": 9,
            "open_direct_predicates": 0,
            "blocked_predicates": 29,
            "authorized_acceptance_case_actions": 0,
            "terminal_promotion_allowed": False,
        }
        for k, v in expected.items():
            if ks.get(k) != v:
                errors.append(f"KERNEL_STATE_MISMATCH:{k}")

    af = authority.get("atomic_acceptance_frontier")
    if not isinstance(af, Mapping):
        errors.append("AUTHORITY_ATOMIC_FRONTIER_MISSING")
    else:
        if (af.get("proved"), af.get("open_direct"), af.get("blocked"), af.get("total")) != (9, 0, 29, 38):
            errors.append("AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
        if af.get("authorized_acceptance_case_actions") != []:
            errors.append("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT")

    if actual_blob_shas is not None:
        sources = authority.get("sources")
        if not isinstance(sources, Mapping):
            errors.append("AUTHORITY_SOURCES_MISSING")
            sources = {}
        for key in ("terminal_closure_manifest", "ownership_matrix", "residual_plan", "acceptance_residual_proof_kernel_v2", "family_local_ownership_promotion_eligibility"):
            row = sources.get(key)
            if not isinstance(row, Mapping):
                errors.append(f"AUTHORITY_SOURCE_MISSING:{key}")
                continue
            path = row.get("path")
            expected_sha = row.get("git_blob_sha")
            if not isinstance(path, str) or actual_blob_shas.get(path) != expected_sha:
                errors.append(f"AUTHORITY_SOURCE_BLOB_MISMATCH:{key}")

    errors = sorted(set(errors))
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V1",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "acceptance_calibrated_families": 4,
        "acceptance_pending_families": 15,
        "verified_owned_families": 4,
        "atomic_predicates_proved": 9,
        "atomic_predicates_blocked": 29,
        "authorized_acceptance_case_actions": 0,
        "terminal_goal_achieved": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "execution_authority": False,
        "rule": "DERIVED_PROJECTIONS_MUST_AGREE_WITH_INDEPENDENT_CALIBRATION_RESIDUAL_AND_FAMILY_LOCAL_OWNERSHIP_PROMOTION_EVIDENCE__ALL_HASH_POINTERS_MUST_RESOLVE__FIREWALL_GRANTS_NO_NEW_CREDIT",
    }

def evaluate_live() -> dict[str, Any]:
    docs = {k: _load(v) for k, v in PATHS.items()}
    shas = {v: _git_blob_sha(v) for v in PATHS.values()}
    return evaluate_documents(
        docs["authority"], docs["closure"], docs["matrix"], docs["calibration"],
        docs["residual"], docs["plan"], docs["kernel"], docs["eligibility"], shas,
    )

def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
