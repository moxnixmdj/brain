"""Fail-closed verifier for the frozen P1 one-batch transport package.

This proves only that the exact pre-case package is internally consistent and
information-safe. It consumes zero fresh reality and grants zero execution,
acceptance, capability, family, or promotion credit.
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
EXPECTED_FREEZE_BLOB = "6a4b606a759d5479bb5ddbdf29426b1a1808b007"

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
    "batch_harness_v2": (
        "canonical/runtime/p1_shared_failure_semantics_batch_v1.py",
        "695cfe3f283723a52bafb6299236a2d0378dc79e",
    ),
    "batch_harness_tests_v2": (
        "canonical/tests/test_p1_shared_failure_semantics_batch_v1.py",
        "7512a920c72d7bdeb2b072788e4c4bc8d2ff2d08",
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


def _need(errors: list[str], cond: bool, code: str) -> None:
    if not cond:
        errors.append(code)


def evaluate(*, freeze_override: Mapping[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    live = freeze_override is None
    freeze = _load(FREEZE) if live else copy.deepcopy(dict(freeze_override))

    if live:
        _need(errors, _blob_sha(FREEZE) == EXPECTED_FREEZE_BLOB, "FREEZE_BLOB_DRIFT")

    _need(errors, freeze.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", "BEHAVIOR_ID")
    _need(errors, freeze.get("selected_observation") == "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH", "SELECTED_OBSERVATION")
    _need(errors, freeze.get("minimum_new_reality_units") == 1, "MINIMUM_REALITY_NOT_ONE")

    authority = freeze.get("exact_authority")
    if not isinstance(authority, Mapping):
        errors.append("EXACT_AUTHORITY_MISSING")
        authority = {}
    _need(errors, set(authority) == set(EXPECTED_AUTHORITY), "EXACT_AUTHORITY_SET")
    for key, (path, sha) in EXPECTED_AUTHORITY.items():
        row = authority.get(key)
        if not isinstance(row, Mapping):
            errors.append("AUTHORITY_ROW:" + key)
            continue
        _need(errors, row.get("path") == path, "AUTHORITY_PATH:" + key)
        _need(errors, row.get("git_blob_sha") == sha, "AUTHORITY_DECLARED_SHA:" + key)
        try:
            _need(errors, _blob_sha(path) == sha, "AUTHORITY_SOURCE_BLOB:" + key)
        except FileNotFoundError:
            errors.append("AUTHORITY_SOURCE_MISSING:" + key)

    cut = _load(EXPECTED_AUTHORITY["minimum_reality_cut"][0])
    observations = {
        x.get("id"): x
        for x in cut.get("observations", [])
        if isinstance(x, Mapping) and isinstance(x.get("id"), str)
    }
    shared = observations.get("P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH") or {}
    _need(errors, set(shared.get("covers") or []) == set(cut.get("requirements") or []), "CUT_COVERAGE")
    _need(errors, shared.get("cost") == 1, "CUT_COST")
    for item in (
        "FREEZE_V7_CANDIDATE_SCORER_NORMALIZER_AND_SURFACE_MAPPING_BEFORE_CASE_SELECTION",
        "CANDIDATE_VISIBLE_FAILURE_SEMANTICS_BOUND_AT_NORMALIZATION_OR_INSTRUMENTATION_TIME",
        "DIRECT_CONTRACT_AND_DERIVED_UPSTREAM_BOTH_PRESENT",
        "NONEMPTY_CAUSALLY_RELEVANT_SUPPORTING_RECEIPTS_REQUIRED_FOR_FAILED_CHECKS",
        "ALL_THREE_FROZEN_P1_DIRECT_SURFACE_IDENTITIES_INCLUDED",
        "V7_INTERVENTION_RESCUE_SCORER_USED_UNCHANGED",
        "NO_TERMINAL_V3_CASE_REPLAY",
        "POST_FREEZE_UNCONTROLLABLE_CASE_SELECTION",
        "ZERO_INCREMENTAL_SPEND",
    ):
        _need(errors, item in set(shared.get("admissibility") or []), "CUT_ADMISSIBILITY:" + item)

    receipt = _load(EXPECTED_AUTHORITY["minimum_reality_independent_verification"][0])
    rr = receipt.get("result") or {}
    _need(errors, str(receipt.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), "CUT_RECEIPT")
    _need(errors, (receipt.get("public_runner") or {}).get("conclusion") == "success", "CUT_RUNNER")
    _need(errors, rr.get("exact_minimum_reality") is True, "CUT_NOT_EXACT")
    _need(errors, rr.get("minimum_new_reality_units") == 1, "CUT_NOT_ONE")
    _need(errors, rr.get("execution_authority") is False, "CUT_PREMATURE_AUTHORITY")

    surfaces = set(freeze.get("frozen_direct_surfaces") or [])
    _need(errors, surfaces == EXPECTED_SURFACES, "FROZEN_SURFACES")
    _need(errors, set(batch.SURFACES) == EXPECTED_SURFACES, "HARNESS_SURFACES")

    src = freeze.get("source_native_case_contract") or {}
    _need(errors, src.get("generator") == "canonical/runtime/contract_native_proof_suites.py::generate_case", "SOURCE_GENERATOR")
    _need(errors, src.get("public_projection") == "canonical/runtime/contract_native_proof_suites.py::public_task", "SOURCE_PUBLIC_PROJECTION")
    _need(errors, src.get("semantics_binder") == "canonical/runtime/p1_shared_failure_semantics_batch_v1.py::bind_public_source_case", "SOURCE_BINDER")
    _need(errors, src.get("semantics_binder_receives_only") == "PUBLIC_SOURCE_CASE_WITH_ORACLE_REMOVED", "SOURCE_BINDER_BOUNDARY")
    _need(errors, src.get("candidate_oracle_exposure") is False, "SOURCE_ORACLE_EXPOSURE")
    _need(
        errors,
        set(src.get("hidden_source_truth_used_only_for_post_candidate_scoring") or [])
        == {"_oracle.cause_step", "_oracle.repair_id"},
        "SOURCE_HIDDEN_TRUTH_ROLE",
    )
    _need(
        errors,
        src.get("noninterference_rule")
        == "MUTATING_HIDDEN_ORACLE_WHILE_HOLDING_PUBLIC_SOURCE_CASE_FIXED_MUST_NOT_CHANGE_SEMANTICS_BINDING",
        "SOURCE_NONINTERFERENCE_RULE",
    )

    pipe = freeze.get("frozen_pipeline") or {}
    expected_pipe = {
        "candidate": "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
        "source_semantics_normalizer": "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py",
        "source_generator": "canonical/runtime/contract_native_proof_suites.py",
        "batch_harness": "canonical/runtime/p1_shared_failure_semantics_batch_v1.py",
        "semantics_binder": "canonical/runtime/p1_shared_failure_semantics_batch_v1.py::bind_public_source_case",
        "semantics_binder_input_boundary": "SOURCE_PUBLIC_TASK_ONLY__HIDDEN_ORACLE_INPUT_FORBIDDEN",
        "v7_intervention_scorer": "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py::score_case",
        "independent_source_native_rescue_scorer": "canonical/runtime/contract_native_proof_suites.py::score_case",
    }
    for key, val in expected_pipe.items():
        _need(errors, pipe.get(key) == val, "PIPE:" + key)
    _need(errors, set(pipe.get("semantic_classes") or []) == {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}, "SEMANTIC_CLASSES")

    selector = freeze.get("frozen_selection") or {}
    _need(errors, selector.get("namespace") == batch.BEACON_NAMESPACE == "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH_V2", "SELECTOR_NAMESPACE")
    _need(errors, selector.get("cases_per_surface") == batch.CASES_PER_SURFACE == 64, "SELECTOR_CASES")
    _need(errors, selector.get("surface_count") == 3, "SELECTOR_SURFACE_COUNT")
    _need(errors, selector.get("total_cases") == batch.TOTAL_CASES == 192, "SELECTOR_TOTAL")
    _need(errors, tuple(selector.get("difficulty_schedule") or []) == batch.DIFFICULTIES, "SELECTOR_DIFFICULTY")
    _need(errors, selector.get("case_selection_uncontrollable_after_freeze") is True, "SELECTOR_POST_FREEZE")
    _need(errors, selector.get("candidate_receives_beacon") is False, "SELECTOR_BEACON_LEAK")
    _need(errors, selector.get("first_attempt_only_for_terminal_credit") is True, "SELECTOR_FIRST_ATTEMPT")
    _need(errors, selector.get("same_selected_cases_may_not_be_used_for_tuning") is True, "SELECTOR_NO_TUNING")

    contract = freeze.get("shared_batch_contract") or {}
    required_true = (
        "one_batch_covers_all_three_surfaces",
        "all_three_surface_identities_required",
        "both_failure_semantics_classes_required_per_admitted_case",
        "v7_candidate_frozen_before_case_selection",
        "source_generator_frozen_before_case_selection",
        "source_native_scorer_frozen_before_case_selection",
        "v7_scorer_frozen_before_case_selection",
        "normalizer_frozen_before_case_selection",
        "batch_executor_frozen_before_case_selection",
        "batch_harness_frozen_before_case_selection",
        "semantics_binder_frozen_before_case_selection",
        "semantics_binder_hidden_oracle_input_forbidden",
        "semantics_binding_must_depend_only_on_public_source_fields",
        "runtime_cannot_self_claim_fresh_reality",
        "surface_mapping_frozen_before_case_selection",
        "selection_function_frozen_before_case_selection",
        "post_freeze_case_selection_required",
        "candidate_must_not_receive_case_selection_information_before_freeze",
        "fresh_case_source_is_source_native_and_not_chosen_from_result_feedback",
        "synthetic_v7_only_credit_forbidden",
    )
    for key in required_true:
        _need(errors, contract.get(key) is True, "CONTRACT_TRUE:" + key)
    for key in ("terminal_v3_replay", "post_result_case_replacement", "post_result_tuning"):
        _need(errors, contract.get(key) is False, "CONTRACT_FALSE:" + key)
    _need(errors, contract.get("incremental_spend_usd") == 0, "CONTRACT_SPEND")

    boundary = freeze.get("admission_boundary") or {}
    _need(errors, boundary.get("this_freeze_consumes_fresh_reality") is False, "FREEZE_REALITY")
    _need(errors, boundary.get("this_freeze_authorizes_execution") is False, "FREEZE_AUTHORITY")
    _need(errors, boundary.get("hidden_oracle_may_be_used_only_after_candidate_output_for_independent_scoring") is True, "HIDDEN_ORACLE_POST_ONLY")
    _need(errors, boundary.get("batch_harness_preflight_and_unit_runs_are_spent_nonterminal_evidence") is True, "SPENT_PREFLIGHT_RULE")
    _need(errors, boundary.get("batch_result_alone_lifts_p1_quarantine") is False, "BATCH_QUARANTINE_GUARD")
    _need(errors, boundary.get("separate_independent_transport_adjudication_required_after_batch") is True, "TRANSPORT_ADJUDICATION")
    _need(errors, boundary.get("separate_acceptance_reduction_required_after_transport_adjudication") is True, "ACCEPTANCE_REDUCTION")

    neg = batch.mutation_preflight()
    _need(errors, neg.get("pass") is True, "MUTATION_PREFLIGHT")
    _need(errors, neg.get("fresh_reality_units_consumed") == 0, "MUTATION_PREFLIGHT_REALITY")
    _need(errors, neg.get("hidden_oracle_input", {}).get("reason") == "HIDDEN_ORACLE_INPUT_FORBIDDEN", "ORACLE_FIREWALL")

    # Binder noninterference: hidden truth can change while its public projection
    # is held fixed, and binding must remain byte-identical.
    full = source.generate_case(CONTRACT, 991337, 4)
    public = source.public_task(full)
    base = batch.bind_public_source_case(public, surface_id=sorted(EXPECTED_SURFACES)[0], case_index=0)
    mutant = copy.deepcopy(full)
    mutant["_oracle"]["cause_step"] = 0
    mutant["_oracle"]["repair_id"] = "repair_0"
    same_public = source.public_task(mutant)
    alt = batch.bind_public_source_case(same_public, surface_id=sorted(EXPECTED_SURFACES)[0], case_index=0)
    _need(errors, base.get("status") == "PASS", "BINDER_BASE")
    _need(errors, base == alt, "BINDER_HIDDEN_ORACLE_NONINTERFERENCE")
    hidden_input = batch.bind_public_source_case(full, surface_id=sorted(EXPECTED_SURFACES)[0], case_index=0)
    _need(errors, hidden_input.get("reason") == "HIDDEN_ORACLE_INPUT_FORBIDDEN", "BINDER_FULL_CASE_REJECT")

    spent_beacon = "spent-p1-prefreeze-public-only-v2"
    for surface in sorted(EXPECTED_SURFACES):
        for i in (0, 17, 63):
            row = batch.evaluate_one(beacon=spent_beacon, surface_id=surface, case_index=i)
            _need(errors, row.get("pass") is True, f"SPENT_CASE:{surface}:{i}")
            _need(errors, row.get("v7_intervention_scorer_pass") is True, f"SPENT_V7:{surface}:{i}")
            _need(errors, row.get("source_native_rescue_scorer_pass") is True, f"SPENT_SOURCE:{surface}:{i}")
            _need(
                errors,
                row.get("semantic_binding_basis")
                == "FROZEN_PUBLIC_SOURCE_STATE_AND_INVARIANT_RESULT_ONLY__HIDDEN_ORACLE_INPUT_FORBIDDEN",
                f"SPENT_BINDING_BASIS:{surface}:{i}",
            )
            counts = row.get("semantics_counts") or {}
            _need(errors, counts.get("DIRECT_CONTRACT", 0) >= 1, f"SPENT_DIRECT:{surface}:{i}")
            _need(errors, counts.get("DERIVED_UPSTREAM", 0) >= 1, f"SPENT_DERIVED:{surface}:{i}")

    full_shape = batch.run_batch("spent-p1-full-shape-v2")
    _need(errors, full_shape.get("pass") is True, "FULL_SHAPE")
    _need(errors, full_shape.get("fresh_reality_units_consumed") == 0, "FULL_SHAPE_SELF_PROMOTION")
    _need(errors, full_shape.get("execution_authority") is False, "FULL_SHAPE_EXECUTION_AUTHORITY")
    _need(errors, full_shape.get("promotion_authority") is False, "FULL_SHAPE_PROMOTION_AUTHORITY")

    _need(errors, freeze.get("new_reality_units_consumed") == 0, "TOP_REALITY")
    _need(errors, freeze.get("terminal_results_replayed") == 0, "TOP_REPLAY")
    _need(errors, freeze.get("incremental_spend_usd") == 0, "TOP_SPEND")
    _need(errors, freeze.get("capability_credit_delta") == 0, "TOP_CAPABILITY_CREDIT")
    _need(errors, freeze.get("family_credit_delta") == 0, "TOP_FAMILY_CREDIT")
    _need(errors, freeze.get("execution_authority") is False, "TOP_EXECUTION_AUTHORITY")
    _need(errors, freeze.get("promotion_authority") is False, "TOP_PROMOTION_AUTHORITY")

    return {
        "schema": "PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_PREFLIGHT_VERDICT_V3",
        "status": "PASS__PUBLIC_ONLY_BINDER_DUAL_SCORER_ONE_BATCH_FREEZE__ZERO_REALITY" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "selected_observation": freeze.get("selected_observation"),
        "minimum_new_reality_units": freeze.get("minimum_new_reality_units"),
        "surface_count": len(surfaces),
        "cases_per_surface_frozen": selector.get("cases_per_surface"),
        "total_cases_frozen": selector.get("total_cases"),
        "semantics_binder_hidden_oracle_input_forbidden": not errors,
        "runtime_self_promotion_forbidden": not errors,
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
