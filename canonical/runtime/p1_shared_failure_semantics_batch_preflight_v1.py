"""Fail-closed pre-case-selection verifier for the exact P1 shared batch.

This verifier checks the *actual* hardened freeze: source-native case generation,
source-bound failure semantics, the V7 candidate, both independent scorers, the
post-freeze selector, all three frozen surfaces, and negative controls.

A pass consumes zero fresh reality and grants zero execution/promotion/acceptance
credit. It only makes the one-shot execution package eligible for independent
public verification.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_proof_suites as source
from canonical.runtime import p1_shared_failure_semantics_batch_v1 as batch

ROOT = Path(__file__).resolve().parents[2]
FREEZE = "canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json"
EXPECTED_FREEZE_BLOB = "cbf16a1c8d11bc147a972df39b9adb390b64c861"

EXPECTED_SURFACES = {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}

EXPECTED_AUTHORITY = {
    "minimum_reality_cut": (
        "canonical/governance/P1_MINIMUM_REALITY_CUT_INPUT_V1.json",
        "cbcb2faff8404623846e77e19fcc5b0ad00e81d9",
    ),
    "minimum_reality_independent_verification": (
        "canonical/verification/P1_V7_PROVENANCE_AND_MINIMUM_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
        "01ca625add4db7035224f0d4cb9efb406d17362d",
    ),
    "multiplex_binding": (
        "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json",
        "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    ),
    "portfolio_manifest": (
        "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
        "8b439403a05b4a912f06a8866db25f6e53b52473",
    ),
    "prewave_protocol": (
        "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json",
        "46cce2be4e277485b7c83233630d0e2fe57d06d1",
    ),
    "direct_proof_routes": (
        "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json",
        "75cd1ad0ec0739ebd894cf6075af5837b93d83f8",
    ),
    "direct_proof_contract": (
        "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json",
        "8c7ffe3d9ff789eddd286496f6de3ce84472c909",
    ),
    "source_generator": (
        "canonical/runtime/contract_native_proof_suites.py",
        "0210790c7dd705ef328e1b55d529a30c5c6c3337",
    ),
    "source_generator_independent_verification": (
        "canonical/verification/CONTRACT_NATIVE_PROOF_SUITES_PUBLIC_VERIFICATION_20261002_V1.json",
        "068af9e16bdd03dcc54b1de7065958fe01ba3466",
    ),
    "source_mutation_preflight_independent_verification": (
        "canonical/verification/FOUR_DIRECT_PROOF_MUTATION_PREFLIGHT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        "d4abf1dbda1328674489afca49bbece93c794cd1",
    ),
    "candidate_v7": (
        "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
        "28940387bd6c11671035ad9201e37bba13fd9bc9",
    ),
    "intervention_scorer_v6": (
        "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py",
        "0f41a36e6ad16722ce05b180e036fb921a2ef886",
    ),
    "normalizer_v1": (
        "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py",
        "b6ba06fc6a35fa132eb19389ee256e74a63a4849",
    ),
    "shared_batch_executor_v1": (
        "canonical/runtime/p1_shared_failure_semantics_batch_v1.py",
        "fa92b6021e9a7aed9347fb80f5ad55b8652b7a0c",
    ),
    "shared_batch_tests_v1": (
        "canonical/tests/test_p1_shared_failure_semantics_batch_v1.py",
        "9433835e6996705c11e4de4e1a58beaf45886319",
    ),
}


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def _error(errors: list[str], cond: bool, code: str) -> None:
    if not cond:
        errors.append(code)


def evaluate(*, freeze_override: Mapping[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    live_freeze = freeze_override is None
    freeze = (
        _load(FREEZE)
        if live_freeze
        else copy.deepcopy(dict(freeze_override))
    )

    if live_freeze:
        _error(errors, _blob_sha(FREEZE) == EXPECTED_FREEZE_BLOB, "FREEZE_BLOB_DRIFT")

    _error(errors, freeze.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", "BEHAVIOR_ID")
    _error(errors, freeze.get("selected_observation") == "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH", "SELECTED_OBSERVATION")
    _error(errors, freeze.get("minimum_new_reality_units") == 1, "MINIMUM_REALITY_NOT_ONE")

    authority = freeze.get("exact_authority")
    if not isinstance(authority, Mapping):
        errors.append("EXACT_AUTHORITY_MISSING")
        authority = {}
    _error(errors, set(authority) == set(EXPECTED_AUTHORITY), "EXACT_AUTHORITY_SET")

    for key, (path, sha) in EXPECTED_AUTHORITY.items():
        row = authority.get(key)
        if not isinstance(row, Mapping):
            errors.append("AUTHORITY_ROW:" + key)
            continue
        _error(errors, row.get("path") == path, "AUTHORITY_PATH:" + key)
        _error(errors, row.get("git_blob_sha") == sha, "AUTHORITY_DECLARED_SHA:" + key)
        try:
            _error(errors, _blob_sha(path) == sha, "AUTHORITY_SOURCE_BLOB:" + key)
        except FileNotFoundError:
            errors.append("AUTHORITY_SOURCE_MISSING:" + key)

    cut = _load(EXPECTED_AUTHORITY["minimum_reality_cut"][0])
    observations = {
        x.get("id"): x
        for x in cut.get("observations", [])
        if isinstance(x, Mapping) and isinstance(x.get("id"), str)
    }
    shared = observations.get("P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH") or {}
    _error(errors, set(shared.get("covers") or []) == set(cut.get("requirements") or []), "CUT_SHARED_BATCH_NOT_COMPLETE")
    _error(errors, shared.get("cost") == 1, "CUT_SHARED_BATCH_COST")
    for required in (
        "CANDIDATE_VISIBLE_FAILURE_SEMANTICS_BOUND_AT_NORMALIZATION_OR_INSTRUMENTATION_TIME",
        "DIRECT_CONTRACT_AND_DERIVED_UPSTREAM_BOTH_PRESENT",
        "NONEMPTY_CAUSALLY_RELEVANT_SUPPORTING_RECEIPTS_REQUIRED_FOR_FAILED_CHECKS",
        "ALL_THREE_FROZEN_P1_DIRECT_SURFACE_IDENTITIES_INCLUDED",
        "V7_INTERVENTION_RESCUE_SCORER_USED_UNCHANGED",
        "NO_TERMINAL_V3_CASE_REPLAY",
        "POST_FREEZE_UNCONTROLLABLE_CASE_SELECTION",
        "ZERO_INCREMENTAL_SPEND",
    ):
        _error(errors, required in set(shared.get("admissibility") or []), "CUT_ADMISSIBILITY:" + required)

    receipt = _load(EXPECTED_AUTHORITY["minimum_reality_independent_verification"][0])
    rr = receipt.get("result") or {}
    _error(errors, str(receipt.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), "MINIMUM_CUT_RECEIPT_NOT_PASS")
    _error(errors, (receipt.get("public_runner") or {}).get("conclusion") == "success", "MINIMUM_CUT_RUNNER_NOT_SUCCESS")
    _error(errors, rr.get("exact_minimum_reality") is True, "MINIMUM_CUT_NOT_EXACT")
    _error(errors, rr.get("minimum_new_reality_units") == 1, "MINIMUM_CUT_RECEIPT_NOT_ONE")
    _error(errors, rr.get("selected_observation") == "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH", "MINIMUM_CUT_RECEIPT_OBSERVATION")
    _error(errors, rr.get("execution_authority") is False, "MINIMUM_CUT_PREMATURE_AUTHORITY")

    surfaces = set(freeze.get("frozen_direct_surfaces") or [])
    _error(errors, surfaces == EXPECTED_SURFACES, "FROZEN_SURFACE_SET")
    _error(errors, set(batch.SURFACES) == EXPECTED_SURFACES, "EXECUTOR_SURFACE_SET")

    source_contract = freeze.get("source_native_case_contract") or {}
    _error(errors, source_contract.get("generator") == "canonical/runtime/contract_native_proof_suites.py::generate_case", "SOURCE_GENERATOR_BINDING")
    _error(errors, source_contract.get("contract") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", "SOURCE_CONTRACT_BINDING")
    _error(errors, source_contract.get("candidate_oracle_exposure") is False, "ORACLE_EXPOSURE_GUARD")
    _error(errors, set(source_contract.get("hidden_source_truth_used_only_for_instrumentation") or []) == {"_oracle.cause_step", "_oracle.repair_id"}, "HIDDEN_SOURCE_TRUTH_SET")

    pipe = freeze.get("frozen_pipeline") or {}
    expected_pipe = {
        "candidate": "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
        "source_semantics_normalizer": "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py",
        "batch_executor": "canonical/runtime/p1_shared_failure_semantics_batch_v1.py",
        "v7_intervention_scorer": "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py::score_case",
        "v7_intervention_replay": "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py::execute_intervention",
        "independent_source_native_rescue_scorer": "canonical/runtime/contract_native_proof_suites.py::score_case",
    }
    for key, value in expected_pipe.items():
        _error(errors, pipe.get(key) == value, "PIPE:" + key)
    _error(errors, set(pipe.get("semantic_classes") or []) == {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}, "SEMANTIC_CLASSES")
    _error(errors, "EVERY_ADMITTED_CASE_MUST_PASS" in str(pipe.get("dual_scorer_pass_rule") or ""), "DUAL_SCORER_PASS_RULE")

    selector = freeze.get("frozen_selection") or {}
    _error(errors, selector.get("namespace") == batch.BEACON_NAMESPACE, "SELECTOR_NAMESPACE")
    _error(errors, selector.get("cases_per_surface") == batch.CASES_PER_SURFACE == 64, "SELECTOR_CASES_PER_SURFACE")
    _error(errors, selector.get("surface_count") == 3, "SELECTOR_SURFACE_COUNT")
    _error(errors, selector.get("total_cases") == batch.TOTAL_CASES == 192, "SELECTOR_TOTAL_CASES")
    _error(errors, tuple(selector.get("difficulty_schedule") or []) == batch.DIFFICULTIES, "SELECTOR_DIFFICULTIES")
    _error(errors, selector.get("case_selection_uncontrollable_after_freeze") is True, "SELECTOR_POST_FREEZE")
    _error(errors, selector.get("candidate_receives_beacon") is False, "SELECTOR_BEACON_LEAK")
    _error(errors, selector.get("first_attempt_only_for_terminal_credit") is True, "SELECTOR_FIRST_ATTEMPT")
    _error(errors, selector.get("same_selected_cases_may_not_be_used_for_tuning") is True, "SELECTOR_NO_TUNING")

    contract = freeze.get("shared_batch_contract") or {}
    for key in (
        "one_batch_covers_all_three_surfaces",
        "all_three_surface_identities_required",
        "both_failure_semantics_classes_required_per_admitted_case",
        "v7_candidate_frozen_before_case_selection",
        "source_generator_frozen_before_case_selection",
        "source_native_scorer_frozen_before_case_selection",
        "v7_scorer_frozen_before_case_selection",
        "normalizer_frozen_before_case_selection",
        "batch_executor_frozen_before_case_selection",
        "surface_mapping_frozen_before_case_selection",
        "selection_function_frozen_before_case_selection",
        "post_freeze_case_selection_required",
        "candidate_must_not_receive_case_selection_information_before_freeze",
        "fresh_case_source_is_source_native_and_not_chosen_from_result_feedback",
        "synthetic_v7_only_credit_forbidden",
    ):
        _error(errors, contract.get(key) is True, "BATCH_CONTRACT_TRUE:" + key)
    for key in ("terminal_v3_replay", "post_result_case_replacement", "post_result_tuning"):
        _error(errors, contract.get(key) is False, "BATCH_CONTRACT_FALSE:" + key)
    _error(errors, contract.get("incremental_spend_usd") == 0, "BATCH_SPEND_NONZERO")

    boundary = freeze.get("admission_boundary") or {}
    _error(errors, boundary.get("this_freeze_consumes_fresh_reality") is False, "PREFLIGHT_CONSUMED_REALITY")
    _error(errors, boundary.get("this_freeze_authorizes_execution") is False, "PREFLIGHT_AUTHORITY_OVERCLAIM")
    _error(errors, boundary.get("execution_may_be_authorized_only_after_independent_public_verification_of_exact_freeze_normalizer_batch_executor_tests_source_generator_candidate_scorers_and_surface_bindings") is True, "INDEPENDENT_VERIFICATION_GATE")
    _error(errors, boundary.get("batch_result_alone_lifts_p1_quarantine") is False, "BATCH_ALONE_QUARANTINE_GUARD")
    _error(errors, boundary.get("separate_independent_transport_adjudication_required_after_batch") is True, "TRANSPORT_ADJUDICATION_GATE")
    _error(errors, boundary.get("separate_acceptance_reduction_required_after_transport_adjudication") is True, "ACCEPTANCE_REDUCTION_GATE")

    neg = batch.mutation_preflight()
    _error(errors, neg.get("pass") is True, "MUTATION_PREFLIGHT")
    _error(errors, neg.get("fresh_reality_units_consumed") == 0, "MUTATION_PREFLIGHT_REALITY")

    # Spent deterministic samples prove the source/native bridge and dual scorers
    # before any uncontrollable terminal beacon is used.
    spent_beacon = "spent-p1-prefreeze-preflight-v1"
    for surface in sorted(EXPECTED_SURFACES):
        for i in (0, 17, 63):
            row = batch.evaluate_one(beacon=spent_beacon, surface_id=surface, case_index=i)
            _error(errors, row.get("pass") is True, f"SPENT_DUAL_SCORER:{surface}:{i}")
            _error(errors, row.get("v7_intervention_scorer_pass") is True, f"SPENT_V7_SCORER:{surface}:{i}")
            _error(errors, row.get("source_native_rescue_scorer_pass") is True, f"SPENT_SOURCE_SCORER:{surface}:{i}")
            counts = row.get("semantics_counts") or {}
            _error(errors, counts.get("DIRECT_CONTRACT", 0) >= 1, f"SPENT_DIRECT:{surface}:{i}")
            _error(errors, counts.get("DERIVED_UPSTREAM", 0) >= 1, f"SPENT_DERIVED:{surface}:{i}")

    # Directly check that instrumentation removes the source oracle before the
    # V7 candidate receives the case.
    fixture = source.generate_case("TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", 991337, 4)
    bound = batch.instrument_source_case(fixture, surface_id=sorted(EXPECTED_SURFACES)[0], case_index=0)
    _error(errors, bound.get("status") == "PASS", "ORACLE_LEAK_FIXTURE_BIND")
    if bound.get("status") == "PASS":
        candidate_case = bound.get("candidate_case") or {}
        _error(errors, "_oracle" not in candidate_case, "ORACLE_LEAK")
        _error(errors, "source_case" not in candidate_case, "SOURCE_CASE_LEAK")
        _error(errors, bound.get("cause_step") == fixture["_oracle"]["cause_step"], "SOURCE_CAUSE_BINDING")

    _error(errors, freeze.get("new_reality_units_consumed") == 0, "NEW_REALITY_ALREADY_CONSUMED")
    _error(errors, freeze.get("terminal_results_replayed") == 0, "TERMINAL_REPLAY")
    _error(errors, freeze.get("incremental_spend_usd") == 0, "SPEND")
    _error(errors, freeze.get("capability_credit_delta") == 0, "CAPABILITY_CREDIT")
    _error(errors, freeze.get("family_credit_delta") == 0, "FAMILY_CREDIT")
    _error(errors, freeze.get("execution_authority") is False, "PREMATURE_EXECUTION_AUTHORITY")
    _error(errors, freeze.get("promotion_authority") is False, "PREMATURE_PROMOTION_AUTHORITY")

    return {
        "schema": "PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_PREFLIGHT_VERDICT_V2",
        "status": "PASS__SOURCE_NATIVE_DUAL_SCORER_ONE_BATCH_FREEZE__ZERO_REALITY" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "selected_observation": freeze.get("selected_observation"),
        "minimum_new_reality_units": freeze.get("minimum_new_reality_units"),
        "surface_count": len(surfaces),
        "cases_per_surface_frozen": selector.get("cases_per_surface"),
        "total_cases_frozen": selector.get("total_cases"),
        "source_native_dual_scorer_frozen": not errors,
        "spent_preflight_cases_executed": 9,
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
