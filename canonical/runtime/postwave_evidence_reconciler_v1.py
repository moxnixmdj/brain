"""Chronology-safe postwave evidence reconciler for Project Brain.

This compiler joins immutable prewave route identity to the consumed V3 terminal
wave without mutating historical binding files. Stale embedded booleans may not
block a later proof chain when independent exact-byte receipts and the execution
snapshot prove the same frozen bytes were used.

Scheduling/evidence-routing only. It never grants predicate, capability, family,
execution, or promotion authority.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_POSTWAVE_EVIDENCE_RECONCILER_V1"
IMMUTABLE_WAVE_STATUS = "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "routes": [],
        "candidate_predicate_witnesses": [],
        "scope_valid_terminal_evidence": [],
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _executor_row(manifest: Mapping[str, Any], behavior_id: str) -> Mapping[str, Any] | None:
    rows = manifest.get("routes")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id]
    return found[0] if len(found) == 1 else None


def _verified_job(receipt: Mapping[str, Any], behavior_id: str) -> Mapping[str, Any] | None:
    rows = receipt.get("verified_jobs")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id]
    return found[0] if len(found) == 1 else None


def _route_scope(reopened: Mapping[str, Any], behavior_id: str, target_predicate: str) -> bool:
    rows = reopened.get("routes")
    if not isinstance(rows, list):
        return False
    for row in rows:
        if not isinstance(row, Mapping) or row.get("behavior_id") != behavior_id:
            continue
        if row.get("scope_relation") != "FULL_PROTOCOL_REPLACEMENT_CANDIDATE":
            continue
        targets = row.get("target_predicates")
        if isinstance(targets, list) and target_predicate in targets:
            return True
    return False


def _wave_guards_ok(terminal_result: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if terminal_result.get("status") != IMMUTABLE_WAVE_STATUS:
        errors.append("TERMINAL_RESULT_NOT_IMMUTABLE_ONE_SHOT_PASS")
    guards = terminal_result.get("result_guards")
    if not isinstance(guards, Mapping):
        return errors + ["RESULT_GUARDS_MISSING"]
    if guards.get("no_case_replacement") is not True:
        errors.append("CASE_REPLACEMENT_GUARD_FAILED")
    if guards.get("no_tuning_replay") is not True:
        errors.append("TUNING_REPLAY_GUARD_FAILED")
    if guards.get("result_to_runtime_feedback_during_wave") is not False:
        errors.append("RESULT_FEEDBACK_GUARD_FAILED")
    if guards.get("direct_route_duplicate_execution_count") != 0:
        errors.append("DIRECT_ROUTE_DUPLICATE_EXECUTION")
    return errors


def evaluate(
    spec: Mapping[str, Any],
    current_binding_verification: Mapping[str, Any],
    reopened_routes: Mapping[str, Any],
    executor_manifest: Mapping[str, Any],
    terminal_result: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if spec.get("schema") != "PROJECT_BRAIN_POSTWAVE_EVIDENCE_RECONCILIATION_INPUT_V1":
        return _fail("SPEC_SCHEMA_INVALID")
    routes = spec.get("routes")
    if not isinstance(routes, list) or not routes:
        return _fail("SPEC_ROUTES_INVALID")

    expected_snapshot = spec.get("execution_snapshot_commit")
    if terminal_result.get("execution_snapshot_commit") != expected_snapshot:
        errors.append("EXECUTION_SNAPSHOT_COMMIT_MISMATCH")
    errors.extend(_wave_guards_ok(terminal_result))

    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(current_binding_verification.get("status", "")):
        errors.append("CURRENT_BINDING_VERIFICATION_NOT_INDEPENDENT_PASS")

    out_rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    scope_ready: list[dict[str, Any]] = []

    for row in routes:
        if not isinstance(row, Mapping):
            errors.append("MALFORMED_ROUTE_SPEC")
            continue
        rid = row.get("id")
        behavior = row.get("behavior_id")
        family = row.get("family")
        predicate = row.get("target_predicate")
        binding_path = row.get("binding_path")
        current_blob = row.get("current_binding_blob_sha")
        snapshot_blob = row.get("execution_snapshot_binding_blob_sha")
        mode = row.get("observation_mode")
        if not all(isinstance(x, str) and x for x in [rid, behavior, family, predicate, binding_path, current_blob, snapshot_blob, mode]):
            errors.append("ROUTE_SPEC_FIELDS_INVALID:" + str(rid))
            continue

        rerrors: list[str] = []
        if current_blob != snapshot_blob:
            rerrors.append("CURRENT_BINDING_DIFFERS_FROM_EXECUTION_SNAPSHOT")

        job = _verified_job(current_binding_verification, behavior)
        if job is None:
            rerrors.append("CURRENT_BINDING_JOB_MISSING")
        else:
            if job.get("conclusion") != "success":
                rerrors.append("CURRENT_BINDING_JOB_NOT_SUCCESS")
            if job.get("binding_path") != binding_path:
                rerrors.append("CURRENT_BINDING_PATH_MISMATCH")
            if job.get("binding_blob_sha") != current_blob:
                rerrors.append("CURRENT_BINDING_BLOB_MISMATCH")

        if not _route_scope(reopened_routes, behavior, predicate):
            rerrors.append("FULL_PROTOCOL_REPLACEMENT_SCOPE_NOT_DECLARED")

        executor = _executor_row(executor_manifest, behavior)
        if executor is None:
            rerrors.append("EXECUTOR_ROW_MISSING")
        else:
            if executor.get("frozen_route") != binding_path:
                rerrors.append("EXECUTOR_FROZEN_ROUTE_MISMATCH")
            if executor.get("terminal_result_status") != "CONSUMED_IN_TERMINAL_V3_WAVE":
                rerrors.append("EXECUTOR_NOT_CONSUMED_IN_V3")
            if executor.get("rerun_allowed") is not False:
                rerrors.append("RERUN_NOT_FORBIDDEN")
            status = str(executor.get("executor_status", ""))
            if "PASS" not in status and "INDEPENDENTLY_BOUND" not in status:
                rerrors.append("EXECUTOR_NOT_INDEPENDENTLY_BOUND")

        evidence: dict[str, Any] | None = None
        if mode == "DIRECT_CEILING":
            population = terminal_result.get("direct_terminal_population")
            population_routes = population.get("routes") if isinstance(population, Mapping) else None
            observed = population_routes.get(behavior) if isinstance(population_routes, Mapping) else None
            reduction = terminal_result.get("reduction_input")
            wave = reduction.get("wave") if isinstance(reduction, Mapping) else None
            direct_results = wave.get("direct_results") if isinstance(wave, Mapping) else None
            direct = direct_results.get(behavior) if isinstance(direct_results, Mapping) else None
            expected_cases = row.get("expected_case_count")
            if not isinstance(observed, Mapping):
                rerrors.append("DIRECT_TERMINAL_POPULATION_MISSING")
            else:
                cases = observed.get("cases")
                passes = observed.get("passes")
                if not isinstance(cases, int) or isinstance(cases, bool) or cases <= 0:
                    rerrors.append("DIRECT_CASE_COUNT_INVALID")
                if expected_cases != cases:
                    rerrors.append("DIRECT_FROZEN_CASE_COUNT_MISMATCH")
                if passes != cases:
                    rerrors.append("DIRECT_NOT_ALL_CASES_PASS")
            if not isinstance(direct, Mapping) or direct.get("pass") is not True or direct.get("terminal_result") is not True:
                rerrors.append("DIRECT_TERMINAL_VERDICT_NOT_PASS")
            if not rerrors and isinstance(observed, Mapping):
                cases = int(observed["cases"])
                evidence = {
                    "id": "POSTWAVE_ATOMIC_CEILING::" + predicate,
                    "predicate_id": predicate,
                    "family": family,
                    "behavior_id": behavior,
                    "mode": "ABSOLUTE_DOMINANCE",
                    "scope_relation": "EXACT_FROZEN_ACCEPTANCE_PREDICATE",
                    "verified": False,
                    "independent": False,
                    "contamination_clean": True,
                    "binds_frozen_protocol": True,
                    "closes_entire_predicate": True,
                    "source_case_count": cases,
                    "source_terminal_full_result_sha256": terminal_result.get("artifact", {}).get("full_result_sha256"),
                    "result": {
                        "direction": "higher",
                        "brain_lower_bound": 1.0,
                        "theoretical_upper_bound": 1.0,
                    },
                    "reason": "EXACT_UNCHANGED_FROZEN_DIRECT_ROUTE_PASSED_ENTIRE_PRECOMMITTED_TERMINAL_POPULATION_AT_THEORETICAL_CEILING",
                }
                candidates.append(evidence)
        elif mode == "PARENT_MULTIPLEX_SCOPE_EVIDENCE":
            required = row.get("required_portfolios")
            if not isinstance(required, list) or not required or any(not isinstance(x, str) for x in required):
                rerrors.append("REQUIRED_PORTFOLIOS_INVALID")
            reduction = terminal_result.get("reduction_input")
            wave = reduction.get("wave") if isinstance(reduction, Mapping) else None
            parent = wave.get("parent_portfolio_receipts") if isinstance(wave, Mapping) else None
            matched: list[dict[str, Any]] = []
            if isinstance(required, list):
                for portfolio in required:
                    entries = parent.get(portfolio) if isinstance(parent, Mapping) else None
                    found = [x for x in entries or [] if isinstance(x, Mapping) and x.get("behavior_id") == behavior]
                    if len(found) != 1:
                        rerrors.append("PARENT_RECEIPT_NOT_UNIQUE:" + str(portfolio))
                        continue
                    rec = found[0]
                    if rec.get("binding_blob") != current_blob:
                        rerrors.append("PARENT_RECEIPT_BINDING_BLOB_MISMATCH:" + str(portfolio))
                    if rec.get("direct_instrumentation_pass") is not True:
                        rerrors.append("PARENT_DIRECT_INSTRUMENTATION_FAIL:" + str(portfolio))
                    if rec.get("load_bearing") is not True:
                        rerrors.append("PARENT_NOT_LOAD_BEARING:" + str(portfolio))
                    if rec.get("parent_terminal_acceptance_pass") is not True:
                        rerrors.append("PARENT_ACCEPTANCE_FAIL:" + str(portfolio))
                    if rec.get("case_replaced") is not False:
                        rerrors.append("PARENT_CASE_REPLACED:" + str(portfolio))
                    if rec.get("tuning_replay") is not False:
                        rerrors.append("PARENT_TUNING_REPLAY:" + str(portfolio))
                    if rec.get("result_to_runtime_feedback") is not False:
                        rerrors.append("PARENT_RESULT_FEEDBACK:" + str(portfolio))
                    matched.append(dict(rec))
            if not rerrors:
                evidence = {
                    "id": "POSTWAVE_SCOPE_EVIDENCE::" + predicate,
                    "predicate_id": predicate,
                    "family": family,
                    "behavior_id": behavior,
                    "mode": "FULL_PROTOCOL_REPLACEMENT_EVIDENCE_READY",
                    "scope_relation": "EXACT_FROZEN_ACCEPTANCE_PREDICATE_CANDIDATE",
                    "verified": False,
                    "independent": False,
                    "contamination_clean": True,
                    "binds_frozen_protocol": True,
                    "closes_entire_predicate": False,
                    "required_portfolios": list(required),
                    "terminal_receipts": matched,
                    "reason": "EXACT_UNCHANGED_FROZEN_BINDING_HAS_LOAD_BEARING_POSTWAVE_PARENT_ACCEPTANCE_EVIDENCE__BOUND_OR_NONINFERIORITY_ADJUDICATION_STILL_REQUIRED",
                }
                scope_ready.append(evidence)
        else:
            rerrors.append("UNKNOWN_OBSERVATION_MODE")

        out_rows.append({
            "id": rid,
            "family": family,
            "behavior_id": behavior,
            "target_predicate": predicate,
            "observation_mode": mode,
            "pass": not rerrors,
            "errors": sorted(set(rerrors)),
            "candidate": evidence,
            "stale_embedded_binding_booleans_authoritative": False,
        })
        errors.extend(rid + ":" + x for x in rerrors)

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "execution_snapshot_commit": expected_snapshot,
        "routes": out_rows,
        "candidate_predicate_witnesses": candidates,
        "scope_valid_terminal_evidence": scope_ready,
        "rule": "HISTORICAL_BINDING_METADATA_IS_NOT_REWRITTEN__LATER_EXACT_BYTE_INDEPENDENT_RECEIPTS_MAY_SUPERSEDE_STALE_EMBEDDED_BOOLEANS_ONLY_WHEN_CURRENT_BINDING_EQUALS_EXECUTION_SNAPSHOT_BINDING_AND_IMMUTABLE_NO_REPLAY_TERMINAL_RECEIPTS_BIND_THE_SAME_ROUTE",
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
