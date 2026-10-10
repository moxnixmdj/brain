"""Fail-closed temporal proof transport for immutable terminal receipts.

This module does not grant capability, family, execution, or promotion credit.
It emits a candidate ceiling witness only when:
- the transport certificate says the load-bearing binding/scope identities are
  content-identical between the terminal execution snapshot and current state;
- a later independent receipt verifies the exact current binding blob;
- the frozen family still maps exactly to the same sole residual behavior;
- the stronger objective route remains scope-admissible;
- the same route-specific executor was consumed in the immutable one-shot wave;
- the whole frozen direct population passed with no replay/replacement/feedback.

Historical Git-object identity is deliberately outside this pure evaluator and
must be independently checked by the full-history CI workflow before any
transport certificate may be marked verified.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TEMPORAL_PROOF_TRANSPORT_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "candidate_witness": None,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _protocol(protocols: Mapping[str, Any], family: str) -> Mapping[str, Any] | None:
    rows = protocols.get("protocols")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("family") == family]
    return found[0] if len(found) == 1 else None


def _executor_row(manifest: Mapping[str, Any], behavior_id: str) -> Mapping[str, Any] | None:
    for key in ("executors", "routes", "bindings"):
        rows = manifest.get(key)
        if isinstance(rows, list):
            found = [r for r in rows if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id]
            return found[0] if len(found) == 1 else None
    return None


def _binding_job(receipt: Mapping[str, Any], behavior_id: str) -> Mapping[str, Any] | None:
    rows = receipt.get("verified_jobs")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id]
    return found[0] if len(found) == 1 else None


def evaluate(
    *,
    transport: Mapping[str, Any],
    protocols: Mapping[str, Any],
    registry: Mapping[str, Any],
    binding: Mapping[str, Any],
    binding_verification: Mapping[str, Any],
    scope_relation: Mapping[str, Any],
    scope_verification: Mapping[str, Any],
    executor_manifest: Mapping[str, Any],
    terminal_result: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    family = transport.get("family")
    behavior_id = transport.get("behavior_id")
    binding_path = transport.get("binding_path")
    if not isinstance(family, str) or not family:
        errors.append("FAMILY_INVALID")
    if not isinstance(behavior_id, str) or not behavior_id:
        errors.append("BEHAVIOR_INVALID")
    if not isinstance(binding_path, str) or not binding_path:
        errors.append("BINDING_PATH_INVALID")

    history = transport.get("history_identity")
    if not isinstance(history, Mapping):
        errors.append("HISTORY_IDENTITY_MISSING")
    else:
        hbind = history.get("historical_binding_blob_sha")
        cbind = history.get("current_binding_blob_sha")
        hscope = history.get("historical_scope_relation_blob_sha")
        cscope = history.get("current_scope_relation_blob_sha")
        if not isinstance(hbind, str) or hbind != cbind:
            errors.append("BINDING_BLOB_NOT_IDENTICAL_ACROSS_TIME")
        if not isinstance(hscope, str) or hscope != cscope:
            errors.append("SCOPE_RELATION_BLOB_NOT_IDENTICAL_ACROSS_TIME")
        if history.get("full_history_ci_required") is not True:
            errors.append("FULL_HISTORY_CI_NOT_REQUIRED")

    snapshot = transport.get("terminal_execution_snapshot_commit")
    if terminal_result.get("execution_snapshot_commit") != snapshot:
        errors.append("TERMINAL_SNAPSHOT_COMMIT_MISMATCH")

    protocol = _protocol(protocols, str(family))
    if protocol is None:
        errors.append("FAMILY_PROTOCOL_NOT_UNIQUE_OR_MISSING")
    elif protocol.get("status") != "DEFINED_RESULT_OPEN":
        errors.append("FAMILY_PROTOCOL_NOT_OPEN")

    family_map = registry.get("family_to_residual_contracts")
    mapped = family_map.get(family) if isinstance(family_map, Mapping) else None
    if mapped != [behavior_id]:
        errors.append("BEHAVIOR_NOT_EXACT_WHOLE_FAMILY_RESIDUAL")

    if binding.get("behavior_id") != behavior_id:
        errors.append("BINDING_BEHAVIOR_MISMATCH")
    purpose = binding.get("purpose")
    if not isinstance(purpose, str) or "DELETE_EXACT_OPUS_COMPARATOR_DEPENDENCY" not in purpose:
        errors.append("PREWAVE_COMPARATOR_DELETION_INTENT_MISSING")

    structural_gate_names = (
        "candidate_package_frozen",
        "executable_evaluator_bound",
        "population_or_source_pool_frozen",
        "information_boundary_frozen",
        "post_freeze_selector_frozen",
        "terminal_parent_binding_frozen",
    )
    gates = binding.get("route_gates")
    if not isinstance(gates, Mapping):
        errors.append("ROUTE_GATES_MISSING")
    else:
        for key in structural_gate_names:
            if gates.get(key) is not True:
                errors.append(f"STRUCTURAL_ROUTE_GATE_FALSE:{key}")

    job = _binding_job(binding_verification, str(behavior_id))
    expected_current_binding_sha = history.get("current_binding_blob_sha") if isinstance(history, Mapping) else None
    if job is None:
        errors.append("EXTERNAL_EXACT_BINDING_VERIFICATION_MISSING")
    else:
        if job.get("binding_path") != binding_path:
            errors.append("EXTERNAL_BINDING_PATH_MISMATCH")
        if job.get("binding_blob_sha") != expected_current_binding_sha:
            errors.append("EXTERNAL_BINDING_BLOB_MISMATCH")
        if job.get("conclusion") != "success":
            errors.append("EXTERNAL_BINDING_VERIFICATION_NOT_SUCCESS")
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(binding_verification.get("status", "")):
        errors.append("EXTERNAL_BINDING_RECEIPT_NOT_INDEPENDENT_PASS")

    if scope_relation.get("behavior_id") != behavior_id:
        errors.append("SCOPE_RELATION_BEHAVIOR_MISMATCH")
    cand_rel = scope_relation.get("candidate_population_relation")
    if not isinstance(cand_rel, Mapping) or cand_rel.get("relation") != "CANDIDATE_SUPERSET_PROVEN":
        errors.append("CANDIDATE_SCOPE_NOT_PROVEN_SUPERSET")
    oracle_rel = scope_relation.get("oracle_relation")
    if not isinstance(oracle_rel, Mapping) or oracle_rel.get("relation") != "CANDIDATE_STRONGER_PROVEN":
        errors.append("ORACLE_NOT_PROVEN_STRONGER")
    if scope_relation.get("environment_relation") != "EXACT":
        errors.append("ENVIRONMENT_RELATION_NOT_EXACT")
    if scope_relation.get("information_relation") != "EXACT_CANDIDATE_VISIBLE_INFORMATION":
        errors.append("INFORMATION_RELATION_NOT_EXACT")

    verdict = scope_verification.get("verdict")
    if scope_verification.get("behavior_id") != behavior_id:
        errors.append("SCOPE_VERIFICATION_BEHAVIOR_MISMATCH")
    if "INDEPENDENT_PASS" not in str(scope_verification.get("status", "")):
        errors.append("SCOPE_VERIFICATION_NOT_INDEPENDENT_PASS")
    if not isinstance(verdict, Mapping) or verdict.get("admissible") is not True or verdict.get("status") != "ADMISSIBLE_SUBSTITUTION":
        errors.append("SCOPE_SUBSTITUTION_NOT_ADMISSIBLE")

    info = binding.get("information_boundary")
    if not isinstance(info, Mapping) or info.get("candidate_receives_hidden_oracle") is not False:
        errors.append("INFORMATION_BOUNDARY_NOT_CLEAN")

    acceptance = binding.get("acceptance")
    if not isinstance(acceptance, Mapping):
        errors.append("BINDING_ACCEPTANCE_MISSING")
    else:
        if acceptance.get("every_selected_case_must_pass") is not True:
            errors.append("EVERY_CASE_PASS_NOT_REQUIRED")
        if acceptance.get("every_class_must_be_present") is not True:
            errors.append("COMPLETE_CLASS_COVERAGE_NOT_REQUIRED")
        if not isinstance(acceptance.get("direct_checks"), list) or not acceptance.get("direct_checks"):
            errors.append("DIRECT_CHECKS_NOT_FROZEN")
        source = acceptance.get("family_credit_source")
        if not isinstance(source, str) or "TERMINAL_ACCEPTANCE" not in source:
            errors.append("FAMILY_TERMINAL_CREDIT_SOURCE_NOT_PREDECLARED")

    executor = _executor_row(executor_manifest, str(behavior_id))
    if executor is None:
        errors.append("EXACT_EXECUTOR_BINDING_MISSING")
    else:
        if executor.get("frozen_route") != binding_path:
            errors.append("EXECUTOR_FROZEN_ROUTE_MISMATCH")
        if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(executor.get("executor_status", "")):
            errors.append("EXECUTOR_NOT_INDEPENDENTLY_VERIFIED")
        if executor.get("terminal_result_status") != "CONSUMED_IN_TERMINAL_V3_WAVE":
            errors.append("EXECUTOR_NOT_CONSUMED_IN_TERMINAL_WAVE")
        if executor.get("rerun_allowed") is not False:
            errors.append("RERUN_NOT_FORBIDDEN")
        stable = transport.get("stable_executor_identity")
        if not isinstance(stable, Mapping):
            errors.append("STABLE_EXECUTOR_IDENTITY_MISSING")
        else:
            if executor.get("executor_blob_sha") != stable.get("executor_blob_sha"):
                errors.append("EXECUTOR_BLOB_CHANGED")
            if executor.get("executor_test_blob_sha") != stable.get("executor_test_blob_sha"):
                errors.append("EXECUTOR_TEST_BLOB_CHANGED")

    if terminal_result.get("status") != "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        errors.append("TERMINAL_RESULT_NOT_IMMUTABLE_ONE_SHOT_PASS")

    population = terminal_result.get("direct_terminal_population")
    routes = population.get("routes") if isinstance(population, Mapping) else None
    observed = routes.get(behavior_id) if isinstance(routes, Mapping) else None
    source_pool = binding.get("source_pool")
    expected_cases = source_pool.get("terminal_sample_count") if isinstance(source_pool, Mapping) else None
    if not isinstance(observed, Mapping):
        errors.append("DIRECT_TERMINAL_POPULATION_RESULT_MISSING")
    else:
        cases = observed.get("cases")
        passes = observed.get("passes")
        if not isinstance(cases, int) or isinstance(cases, bool) or cases <= 0:
            errors.append("OBSERVED_CASE_COUNT_INVALID")
        if expected_cases != cases:
            errors.append("FROZEN_POPULATION_COUNT_MISMATCH")
        if passes != cases:
            errors.append("NOT_ALL_FROZEN_CASES_PASS")

    reduction = terminal_result.get("reduction_input")
    wave = reduction.get("wave") if isinstance(reduction, Mapping) else None
    direct_results = wave.get("direct_results") if isinstance(wave, Mapping) else None
    direct = direct_results.get(behavior_id) if isinstance(direct_results, Mapping) else None
    if not isinstance(direct, Mapping) or direct.get("pass") is not True or direct.get("terminal_result") is not True:
        errors.append("DIRECT_TERMINAL_VERDICT_NOT_PASS")

    guards = terminal_result.get("result_guards")
    if not isinstance(guards, Mapping):
        errors.append("RESULT_GUARDS_MISSING")
    else:
        if guards.get("no_case_replacement") is not True:
            errors.append("CASE_REPLACEMENT_GUARD_FAILED")
        if guards.get("no_tuning_replay") is not True:
            errors.append("TUNING_REPLAY_GUARD_FAILED")
        if guards.get("result_to_runtime_feedback_during_wave") is not False:
            errors.append("RESULT_FEEDBACK_GUARD_FAILED")
        if guards.get("direct_route_duplicate_execution_count") != 0:
            errors.append("DIRECT_ROUTE_DUPLICATE_EXECUTION")

    if errors:
        return _fail(*errors)

    assert isinstance(observed, Mapping)
    cases = int(observed["cases"])
    return {
        "schema": SCHEMA,
        "status": "TRANSPORT_CANDIDATE_READY__FULL_HISTORY_CI_AND_INDEPENDENT_WITNESS_VERIFICATION_REQUIRED",
        "pass": True,
        "errors": [],
        "transported_terminal_receipt": {
            "family": family,
            "behavior_id": behavior_id,
            "source_snapshot_commit": snapshot,
            "source_case_count": cases,
            "source_terminal_full_result_sha256": terminal_result.get("artifact", {}).get("full_result_sha256"),
            "binding_blob_sha": expected_current_binding_sha,
            "scope_relation_blob_sha": history.get("current_scope_relation_blob_sha") if isinstance(history, Mapping) else None,
        },
        "candidate_witness": {
            "id": f"TEMPORAL_TERMINAL_CEILING::{family}::{behavior_id}",
            "family": family,
            "mode": "ABSOLUTE_DOMINANCE",
            "verified": False,
            "independent": False,
            "contamination_clean": True,
            "binds_frozen_protocol": True,
            "scope_relation": "PROVEN_STRONGER",
            "closes_entire_protocol": True,
            "source_behavior_id": behavior_id,
            "source_case_count": cases,
            "source_terminal_full_result_sha256": terminal_result.get("artifact", {}).get("full_result_sha256"),
            "result": {
                "direction": "higher",
                "brain_lower_bound": 1.0,
                "theoretical_upper_bound": 1.0,
            },
            "reason": "UNCHANGED_LOAD_BEARING_DEPENDENCY_CONE_TRANSPORTS_IMMUTABLE_FULL_FROZEN_OBJECTIVE_CEILING_RESULT",
        },
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
