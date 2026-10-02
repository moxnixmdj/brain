"""Compile fail-closed theoretical-ceiling witnesses from an immutable terminal wave.

This module never grants family/capability credit. It only emits a typed candidate
witness for the existing acceptance-proof transmuter when pre-existing canonical
artifacts prove that:
- one active behavioral contract is the whole residual contract for the family;
- a frozen prewave route explicitly declared comparator-deletion intent;
- that exact route/executor was independently bound into the consumed one-shot wave;
- the entire frozen direct population passed with no replay/replacement/feedback; and
- every selected case was required to pass under the frozen route acceptance.
- or, when stale embedded prewave booleans lag reality, an independent exact-blob
  receipt proves that the current binding is the identical binding consumed by the terminal snapshot.

The output remains non-authoritative until independently verified.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_CEILING_WITNESS_LIFTER_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "candidate_witness": None,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }


def _protocol(protocols: Mapping[str, Any], family: str) -> Mapping[str, Any] | None:
    rows = protocols.get("protocols")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("family") == family]
    return found[0] if len(found) == 1 else None


def _executor_row(manifest: Mapping[str, Any], behavior_id: str) -> Mapping[str, Any] | None:
    rows = manifest.get("executors")
    if not isinstance(rows, list):
        rows = manifest.get("routes")
    if not isinstance(rows, list):
        rows = manifest.get("bindings")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id]
    return found[0] if len(found) == 1 else None


def evaluate(
    *,
    family: str,
    behavior_id: str,
    binding_path: str,
    protocols: Mapping[str, Any],
    registry: Mapping[str, Any],
    binding: Mapping[str, Any],
    executor_manifest: Mapping[str, Any],
    terminal_result: Mapping[str, Any],
    binding_blob_sha: str | None = None,
    terminal_snapshot_binding_blob_sha: str | None = None,
    binding_verification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    protocol = _protocol(protocols, family)
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

    acceptance = binding.get("acceptance")
    if not isinstance(acceptance, Mapping):
        errors.append("BINDING_ACCEPTANCE_MISSING")
    else:
        if acceptance.get("every_selected_case_must_pass") is not True:
            errors.append("EVERY_CASE_PASS_NOT_REQUIRED")
        if acceptance.get("every_class_must_be_present") is not True:
            errors.append("COMPLETE_CLASS_COVERAGE_NOT_REQUIRED")
        source = acceptance.get("family_credit_source")
        if not isinstance(source, str) or "TERMINAL_ACCEPTANCE" not in source:
            errors.append("FAMILY_TERMINAL_CREDIT_SOURCE_NOT_PREDECLARED")
        checks = acceptance.get("direct_checks")
        if not isinstance(checks, list) or not checks:
            errors.append("DIRECT_CHECKS_NOT_FROZEN")

    route_gates = binding.get("route_gates")
    embedded_preflight = (
        isinstance(route_gates, Mapping)
        and route_gates.get("independent_verification_pass") is True
        and binding.get("prewave_admissible") is True
    )
    receipt_preflight = False
    if not embedded_preflight and isinstance(binding_verification, Mapping):
        status = str(binding_verification.get("status", ""))
        jobs = binding_verification.get("verified_jobs")
        if (
            "INDEPENDENT_PUBLIC_RUNNER_PASS" in status
            and isinstance(binding_blob_sha, str)
            and binding_blob_sha
            and binding_blob_sha == terminal_snapshot_binding_blob_sha
            and isinstance(jobs, list)
        ):
            matches = [
                row for row in jobs
                if isinstance(row, Mapping)
                and row.get("binding_path") == binding_path
                and row.get("binding_blob_sha") == binding_blob_sha
                and row.get("conclusion") == "success"
            ]
            receipt_preflight = len(matches) == 1
    if not embedded_preflight and not receipt_preflight:
        errors.append("BINDING_NOT_INDEPENDENTLY_VERIFIED")
        errors.append("BINDING_NOT_PREWAVE_ADMISSIBLE")
    if receipt_preflight and binding_blob_sha != terminal_snapshot_binding_blob_sha:
        errors.append("BINDING_CHANGED_SINCE_TERMINAL_SNAPSHOT")

    info = binding.get("information_boundary")
    if not isinstance(info, Mapping) or info.get("candidate_receives_hidden_oracle") is not False:
        errors.append("INFORMATION_BOUNDARY_NOT_CLEAN")

    executor = _executor_row(executor_manifest, behavior_id)
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

    assert protocol is not None and isinstance(observed, Mapping)
    cases = int(observed["cases"])
    witness = {
        "id": f"TERMINAL_CEILING::{family}::{behavior_id}",
        "family": family,
        "mode": "ABSOLUTE_DOMINANCE",
        "verified": False,
        "independent": False,
        "contamination_clean": True,
        "binds_frozen_protocol": True,
        "scope_relation": "PROVEN_STRONGER",
        "closes_entire_protocol": True,
        "source_behavior_id": behavior_id,
        "source_terminal_full_result_sha256": terminal_result.get("artifact", {}).get("full_result_sha256"),
        "source_case_count": cases,
        "result": {
            "direction": "higher",
            "brain_lower_bound": 1.0,
            "theoretical_upper_bound": 1.0,
        },
        "reason": "ENTIRE_FROZEN_PREWAVE_COMPARATOR_DELETION_ROUTE_POPULATION_PASSED_AT_THEORETICAL_CEILING",
    }
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        "pass": True,
        "errors": [],
        "family": family,
        "behavior_id": behavior_id,
        "candidate_witness": witness,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }
