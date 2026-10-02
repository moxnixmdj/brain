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
    "calibration": "canonical/verification/OPUS55_ACCEPTANCE_CALIBRATION_AUDIT_20261002_V2.json",
    "residual": "canonical/verification/OPUS55_ACCEPTANCE_RESIDUAL_COMPILER_V2_VERDICT_20261002_V9.json",
    "plan": "canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_MINIMUM_PROOF_PLAN_V1.json",
    "kernel": "canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_PROOF_KERNEL_V2.json",
}

EXPECTED_CALIBRATED = {
    "EXACT_SYMBOLIC_COMPUTATION",
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
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
    actual_blob_shas: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    truth = authority.get("truth")
    if not isinstance(truth, Mapping):
        errors.append("AUTHORITY_TRUTH_MISSING")
        truth = {}
    if truth.get("opus55_acceptance") != "3/19_PASS__16/19_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_NOT_3_OF_19")
    if truth.get("achieved") is not False:
        errors.append("AUTHORITY_TERMINAL_GOAL_MUST_REMAIN_FALSE")

    cres = calibration.get("result")
    if not isinstance(cres, Mapping):
        errors.append("CALIBRATION_RESULT_MISSING")
        cres = {}
    if cres.get("acceptance_calibrated_family_count") != 3:
        errors.append("CALIBRATION_COUNT_NOT_3")
    if cres.get("acceptance_pending_family_count") != 16:
        errors.append("CALIBRATION_PENDING_NOT_16")
    if set(cres.get("acceptance_calibrated_families") or []) != EXPECTED_CALIBRATED:
        errors.append("CALIBRATION_FAMILY_SET_MISMATCH")
    if cres.get("terminal_goal_acceptance_closed") is not False:
        errors.append("CALIBRATION_TERMINAL_GOAL_MUST_REMAIN_FALSE")

    if residual.get("predicate_count") != 38:
        errors.append("RESIDUAL_PREDICATE_COUNT_NOT_38")
    if residual.get("proved_predicate_count") != 8:
        errors.append("RESIDUAL_PROVED_COUNT_NOT_8")
    if residual.get("open_predicate_count") != 0:
        errors.append("RESIDUAL_OPEN_COUNT_NOT_0")
    if residual.get("blocked_predicate_count") != 30:
        errors.append("RESIDUAL_BLOCKED_COUNT_NOT_30")
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
    if summary.get("calibrated_family_count") != 3 or summary.get("pending_family_count") != 16:
        errors.append("CLOSURE_ACCEPTANCE_SUMMARY_MISMATCH")
    if set(summary.get("calibrated_families") or []) != EXPECTED_CALIBRATED:
        errors.append("CLOSURE_ACCEPTANCE_FAMILY_SET_MISMATCH")
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
    if msum.get("calibrated_family_count") != 3 or msum.get("pending_acceptance_family_count") != 16:
        errors.append("MATRIX_ACCEPTANCE_SUMMARY_MISMATCH")
    if msum.get("verified_owned_family_count") != 2:
        errors.append("MATRIX_VERIFIED_OWNED_COUNT_NOT_2")
    rows = matrix.get("rows")
    tool = None
    if isinstance(rows, list):
        tool = next((r for r in rows if isinstance(r, Mapping) and r.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"), None)
    if not isinstance(tool, Mapping):
        errors.append("MATRIX_TOOL_DISCOVERY_ROW_MISSING")
    else:
        if tool.get("postwave_opus55_acceptance_status") != "PASS_VIA_FULL_SCOPE_ABSOLUTE_DOMINANCE_WITNESS":
            errors.append("MATRIX_TOOL_DISCOVERY_ACCEPTANCE_NOT_PASS")
        if tool.get("postwave_ownership_credit") != "ZERO_DIRECT_CREDIT__PROMOTION_AUTHORITY_FALSE":
            errors.append("MATRIX_TOOL_DISCOVERY_PROMOTION_OVERCLAIM")

    if plan.get("residual_family_count") != 16:
        errors.append("PLAN_PENDING_FAMILY_COUNT_NOT_16")
    pf = plan.get("residual_families")
    if not isinstance(pf, list):
        errors.append("PLAN_RESIDUAL_FAMILIES_MISSING")
    else:
        names = {r.get("family") for r in pf if isinstance(r, Mapping)}
        if "TOOL_DISCOVERY_SELECTION_AND_LEARNING" in names:
            errors.append("PLAN_RETAINS_ALREADY_CALIBRATED_TOOL_DISCOVERY")
        if len(names) != 16:
            errors.append("PLAN_RESIDUAL_FAMILY_SET_NOT_16")
    state = plan.get("current_acceptance_state")
    if not isinstance(state, Mapping):
        errors.append("PLAN_CURRENT_ACCEPTANCE_STATE_MISSING")
    else:
        expected = {
            "calibrated_family_count": 3,
            "pending_family_count": 16,
            "atomic_predicates_total": 38,
            "proved_atomic_predicates": 8,
            "blocked_atomic_predicates": 30,
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
            "acceptance_pending_families": 16,
            "atomic_predicates": 38,
            "receipt_saturation_complete": True,
            "proved_predicates": 8,
            "open_direct_predicates": 0,
            "blocked_predicates": 30,
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
        if (af.get("proved"), af.get("open_direct"), af.get("blocked"), af.get("total")) != (8, 0, 30, 38):
            errors.append("AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
        if af.get("authorized_acceptance_case_actions") != []:
            errors.append("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT")

    if actual_blob_shas is not None:
        sources = authority.get("sources")
        if not isinstance(sources, Mapping):
            errors.append("AUTHORITY_SOURCES_MISSING")
            sources = {}
        for key in ("terminal_closure_manifest", "ownership_matrix", "residual_plan", "acceptance_residual_proof_kernel_v2"):
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
        "acceptance_calibrated_families": 3,
        "acceptance_pending_families": 16,
        "atomic_predicates_proved": 8,
        "atomic_predicates_blocked": 30,
        "authorized_acceptance_case_actions": 0,
        "terminal_goal_achieved": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "execution_authority": False,
        "rule": "DERIVED_PROJECTIONS_MUST_AGREE_WITH_INDEPENDENT_CALIBRATION_AND_RESIDUAL_AUTHORITY__ALL_HASH_POINTERS_MUST_RESOLVE__NO_PROMOTION_CREDIT",
    }

def evaluate_live() -> dict[str, Any]:
    docs = {k: _load(v) for k, v in PATHS.items()}
    shas = {v: _git_blob_sha(v) for v in PATHS.values()}
    return evaluate_documents(
        docs["authority"], docs["closure"], docs["matrix"], docs["calibration"],
        docs["residual"], docs["plan"], docs["kernel"], shas,
    )

def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
