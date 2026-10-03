"""Pre-case-selection verifier for the exact one-batch P1 minimum reality cut.

A pass here freezes bytes and semantics. It does not consume the batch and does
not itself authorize execution. Independent verification of these exact bytes is
the next gate.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p1_shared_failure_semantics_normalizer_v1 import normalize_case

ROOT = Path(__file__).resolve().parents[2]
FREEZE = "canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json"

EXPECTED_SURFACES = {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
REQUIRED_ADMISSIBILITY = {
    "FREEZE_V7_CANDIDATE_SCORER_NORMALIZER_AND_SURFACE_MAPPING_BEFORE_CASE_SELECTION",
    "CANDIDATE_VISIBLE_FAILURE_SEMANTICS_BOUND_AT_NORMALIZATION_OR_INSTRUMENTATION_TIME",
    "DIRECT_CONTRACT_AND_DERIVED_UPSTREAM_BOTH_PRESENT",
    "NONEMPTY_CAUSALLY_RELEVANT_SUPPORTING_RECEIPTS_REQUIRED_FOR_FAILED_CHECKS",
    "ALL_THREE_FROZEN_P1_DIRECT_SURFACE_IDENTITIES_INCLUDED",
    "V7_INTERVENTION_RESCUE_SCORER_USED_UNCHANGED",
    "NO_TERMINAL_V3_CASE_REPLAY",
    "POST_FREEZE_UNCONTROLLABLE_CASE_SELECTION",
    "ZERO_INCREMENTAL_SPEND",
}


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def _sample(surface: str, *, missing_semantics: bool = False, omit_derived: bool = False) -> dict[str, Any]:
    direct = {
        "kind": "SCOPE",
        "id": "A1:SCOPE",
        "pass": False,
        "evidence": ["receipt:A1", "check:A1:SCOPE"],
        "failure_semantics": "DIRECT_CONTRACT",
    }
    if missing_semantics:
        direct.pop("failure_semantics")
    checks2 = [{"kind": "INVARIANT", "id": "A2:INVARIANT", "pass": True, "evidence": ["check:A2"]}]
    if not omit_derived:
        checks2.append({
            "kind": "INVARIANT",
            "id": "A2:DERIVED",
            "pass": False,
            "evidence": ["receipt:A2", "check:A2:DERIVED"],
            "failure_semantics": "DERIVED_UPSTREAM",
        })
    return {
        "surface_id": surface,
        "case_id": "PREFLIGHT-SAMPLE",
        "source_observation_receipt": "source:preflight",
        "trajectory": [
            {
                "step": 1,
                "action_id": "A1",
                "domain": "CODE",
                "reads": [],
                "writes": ["x"],
                "depends_on": [],
                "dependency_composition": "SEQUENTIAL",
                "checks": [
                    {"kind": "INVARIANT", "id": "A1:I", "pass": True, "evidence": ["check:A1:I"]},
                    direct,
                ],
            },
            {
                "step": 2,
                "action_id": "A2",
                "domain": "CODE",
                "reads": ["x"],
                "writes": ["terminal"],
                "depends_on": ["A1"],
                "dependency_composition": "SEQUENTIAL",
                "checks": checks2,
            },
        ],
        "terminal_failed_resources": ["terminal"],
    }


def evaluate(*, freeze_override: Mapping[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    freeze = copy.deepcopy(dict(freeze_override)) if freeze_override is not None else _load(FREEZE)

    if freeze.get("behavior_id") != "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        errors.append("BEHAVIOR_ID")
    if freeze.get("selected_observation") != "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH":
        errors.append("SELECTED_OBSERVATION")
    if freeze.get("minimum_new_reality_units") != 1:
        errors.append("MINIMUM_REALITY_NOT_ONE")

    authority = freeze.get("exact_authority")
    if not isinstance(authority, Mapping):
        errors.append("EXACT_AUTHORITY_MISSING")
        authority = {}
    required_authority = {
        "minimum_reality_cut",
        "minimum_reality_independent_verification",
        "multiplex_binding",
        "portfolio_manifest",
        "candidate_v7",
        "intervention_scorer_v6",
        "normalizer_v1",
    }
    if set(authority) != required_authority:
        errors.append("EXACT_AUTHORITY_SET")
    for key in required_authority & set(authority):
        row = authority.get(key)
        if not isinstance(row, Mapping):
            errors.append("AUTHORITY_ROW:" + key)
            continue
        path = row.get("path")
        sha = row.get("git_blob_sha")
        if not isinstance(path, str) or not isinstance(sha, str):
            errors.append("AUTHORITY_BINDING:" + key)
            continue
        try:
            if _blob_sha(path) != sha:
                errors.append("SOURCE_BLOB_DRIFT:" + key)
        except FileNotFoundError:
            errors.append("SOURCE_MISSING:" + key)

    receipt_path = (authority.get("minimum_reality_independent_verification") or {}).get("path")
    if isinstance(receipt_path, str):
        receipt = _load(receipt_path)
        rr = receipt.get("result") or {}
        if not str(receipt.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
            errors.append("MINIMUM_CUT_RECEIPT_NOT_PASS")
        if receipt.get("public_runner", {}).get("conclusion") != "success":
            errors.append("MINIMUM_CUT_RUNNER_NOT_SUCCESS")
        if rr.get("exact_minimum_reality") is not True:
            errors.append("MINIMUM_CUT_NOT_EXACT")
        if rr.get("minimum_new_reality_units") != 1:
            errors.append("MINIMUM_CUT_RECEIPT_NOT_ONE")
        if rr.get("selected_observation") != "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH":
            errors.append("MINIMUM_CUT_RECEIPT_OBSERVATION")
        if rr.get("execution_authority") is not False:
            errors.append("MINIMUM_CUT_RECEIPT_PREMATURE_AUTHORITY")

    cut_path = (authority.get("minimum_reality_cut") or {}).get("path")
    if isinstance(cut_path, str):
        cut = _load(cut_path)
        rows = {
            x.get("id"): x for x in cut.get("observations", [])
            if isinstance(x, Mapping) and isinstance(x.get("id"), str)
        }
        shared = rows.get("P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH") or {}
        if set(shared.get("covers") or []) != set(cut.get("requirements") or []):
            errors.append("SHARED_BATCH_NOT_COMPLETE_COVER")
        if shared.get("cost") != 1:
            errors.append("SHARED_BATCH_COST")
        if set(shared.get("admissibility") or []) != REQUIRED_ADMISSIBILITY:
            errors.append("SHARED_BATCH_ADMISSIBILITY_DRIFT")
        if cut.get("incremental_spend_usd") != 0:
            errors.append("CUT_SPEND_NONZERO")
        if cut.get("execution_authority") is not False:
            errors.append("CUT_PREMATURE_AUTHORITY")

    surfaces = set(freeze.get("frozen_direct_surfaces") or [])
    if surfaces != EXPECTED_SURFACES:
        errors.append("FROZEN_SURFACE_SET")

    binding_path = (authority.get("multiplex_binding") or {}).get("path")
    if isinstance(binding_path, str):
        binding = _load(binding_path)
        if set(binding.get("direct_surface_bindings") or []) != EXPECTED_SURFACES:
            errors.append("BINDING_SURFACE_SET")
        if binding.get("behavior_id") != "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
            errors.append("BINDING_BEHAVIOR")

    manifest_path = (authority.get("portfolio_manifest") or {}).get("path")
    if isinstance(manifest_path, str):
        manifest = _load(manifest_path)
        observed: set[str] = set()
        for portfolio, body in (manifest.get("portfolios") or {}).items():
            if not isinstance(body, Mapping):
                continue
            for row in body.get("surfaces") or []:
                if not isinstance(row, Mapping):
                    continue
                if "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF" in (row.get("proof_routes") or []):
                    observed.add(f"{portfolio}/{row.get('id')}::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF")
        if not EXPECTED_SURFACES <= observed:
            errors.append("MANIFEST_P1_SURFACE_BINDING")

    pipe = freeze.get("frozen_pipeline") or {}
    if pipe.get("candidate") != "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py":
        errors.append("CANDIDATE_PATH")
    if pipe.get("source_semantics_normalizer") != "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py":
        errors.append("NORMALIZER_PATH")
    if pipe.get("scorer") != "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py::score_case":
        errors.append("SCORER_PATH")
    if set(pipe.get("semantic_classes") or []) != {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}:
        errors.append("SEMANTIC_CLASSES")

    contract = freeze.get("shared_batch_contract") or {}
    required_true = (
        "one_batch_covers_all_three_surfaces",
        "all_three_surface_identities_required",
        "both_failure_semantics_classes_required_per_admitted_case",
        "v7_candidate_frozen_before_case_selection",
        "scorer_frozen_before_case_selection",
        "normalizer_frozen_before_case_selection",
        "surface_mapping_frozen_before_case_selection",
        "post_freeze_case_selection_required",
        "candidate_must_not_receive_case_selection_information_before_freeze",
        "fresh_case_source_must_be_external_or_source_native_and_not_chosen_from_result_feedback",
    )
    for key in required_true:
        if contract.get(key) is not True:
            errors.append("BATCH_CONTRACT_TRUE:" + key)
    for key in ("terminal_v3_replay", "post_result_case_replacement", "post_result_tuning"):
        if contract.get(key) is not False:
            errors.append("BATCH_CONTRACT_FALSE:" + key)
    if contract.get("synthetic_v7_only_credit_forbidden") is not True:
        errors.append("SYNTHETIC_CREDIT_GUARD")
    if contract.get("incremental_spend_usd") != 0:
        errors.append("BATCH_SPEND_NONZERO")

    boundary = freeze.get("admission_boundary") or {}
    if boundary.get("this_freeze_consumes_fresh_reality") is not False:
        errors.append("PREFLIGHT_CONSUMED_REALITY")
    if boundary.get("this_freeze_authorizes_execution") is not False:
        errors.append("PREFLIGHT_AUTHORITY_OVERCLAIM")
    if boundary.get("execution_may_be_authorized_only_after_independent_verification_of_exact_freeze_and_normalizer_bytes") is not True:
        errors.append("INDEPENDENT_VERIFICATION_GATE")
    if boundary.get("fresh_batch_must_still_supply_source_bound_semantics_and_receipts") is not True:
        errors.append("FRESH_BATCH_SOURCE_BINDING_GATE")

    for surface in sorted(EXPECTED_SURFACES):
        good = normalize_case(_sample(surface))
        if good.get("status") != "PASS":
            errors.append("NORMALIZER_VALID_SAMPLE:" + surface)
        missing = normalize_case(_sample(surface, missing_semantics=True))
        if missing.get("status") != "FAIL_CLOSED":
            errors.append("NORMALIZER_GUESSES_MISSING_SEMANTICS:" + surface)
        one_class = normalize_case(_sample(surface, omit_derived=True))
        if one_class.get("status") != "FAIL_CLOSED":
            errors.append("NORMALIZER_ALLOWS_ONE_SEMANTIC_CLASS:" + surface)

    if freeze.get("new_reality_units_consumed") != 0:
        errors.append("NEW_REALITY_ALREADY_CONSUMED")
    if freeze.get("terminal_results_replayed") != 0:
        errors.append("TERMINAL_REPLAY")
    if freeze.get("incremental_spend_usd") != 0:
        errors.append("SPEND")
    if freeze.get("capability_credit_delta") != 0 or freeze.get("family_credit_delta") != 0:
        errors.append("CREDIT_DELTA")
    if freeze.get("execution_authority") is not False or freeze.get("promotion_authority") is not False:
        errors.append("PREMATURE_AUTHORITY")

    return {
        "schema": "PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_PREFLIGHT_VERDICT_V1",
        "status": "PASS__ONE_SHARED_P1_BATCH_PRECASE_FREEZE" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "selected_observation": freeze.get("selected_observation"),
        "minimum_new_reality_units": freeze.get("minimum_new_reality_units"),
        "surface_count": len(surfaces),
        "candidate_scorer_normalizer_surface_mapping_frozen": not errors,
        "fresh_case_selection_permitted_before_independent_verification": False,
        "execution_authority": False,
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
