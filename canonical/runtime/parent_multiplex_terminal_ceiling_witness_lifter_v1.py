"""Fail-closed ceiling-witness lifter for load-bearing parent multiplex routes.

This compiler is the parent-portfolio analogue of terminal_ceiling_witness_lifter_v1.
It never grants acceptance, family, capability, execution, or promotion credit.
It emits only an unverified candidate witness when exact current artifacts prove:

* the family maps to exactly one residual behavioral contract;
* the current binding bytes were independently revalidated;
* the exact executor was bound as parent-multiplex-only and consumed once;
* every required parent portfolio contains exactly one load-bearing receipt for the
  behavior and that receipt passed both direct instrumentation and parent terminal
  acceptance under the exact current binding;
* no replay, replacement, result feedback, or duplicate direct-route execution
  occurred; and
* the frozen parent binding makes intervention/rescue scope load-bearing and
  forbids synthetic whole-domain score substitution.

Independent verification remains mandatory before the candidate can enter the
acceptance-proof transmutation input.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PARENT_MULTIPLEX_TERMINAL_CEILING_WITNESS_LIFTER_V1"


def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


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
        "new_reality_units_consumed": 0,
    }


def _unique_protocol(protocols: Mapping[str, Any], family: str) -> Mapping[str, Any] | None:
    rows = protocols.get("protocols")
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get("family") == family]
    return found[0] if len(found) == 1 else None


def _executor_row(manifest: Mapping[str, Any], behavior_id: str) -> Mapping[str, Any] | None:
    for key in ("executors", "routes", "bindings"):
        rows = manifest.get(key)
        if isinstance(rows, list):
            found = [
                r for r in rows
                if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id
            ]
            return found[0] if len(found) == 1 else None
    return None


def _current_binding_verified(
    verification: Mapping[str, Any],
    behavior_id: str,
    binding_blob_sha: str,
) -> bool:
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(verification.get("status", "")):
        return False
    rows = verification.get("verified_jobs")
    if not isinstance(rows, list):
        return False
    found = [
        row
        for row in rows
        if isinstance(row, Mapping)
        and row.get("behavior_id") == behavior_id
        and row.get("binding_blob_sha") == binding_blob_sha
        and row.get("conclusion") == "success"
    ]
    return len(found) == 1


def _aggregate_count(case_id: Any, portfolio: str, behavior_id: str) -> int | None:
    if not isinstance(case_id, str):
        return None
    prefix = f"{portfolio}::{behavior_id}::aggregate::"
    if not case_id.startswith(prefix):
        return None
    suffix = case_id[len(prefix):]
    try:
        n = int(suffix)
    except ValueError:
        return None
    return n if n > 0 and str(n) == suffix else None


def evaluate(
    *,
    family: str,
    behavior_id: str,
    binding_path: str,
    binding_blob_sha: str,
    protocols: Mapping[str, Any],
    registry: Mapping[str, Any],
    binding: Mapping[str, Any],
    current_binding_verification: Mapping[str, Any],
    executor_manifest: Mapping[str, Any],
    terminal_result: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if not all(isinstance(x, str) and x for x in (family, behavior_id, binding_path, binding_blob_sha)):
        return _fail("IDENTIFIERS_REQUIRED")

    protocol = _unique_protocol(protocols, family)
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

    portfolios = binding.get("portfolio_bindings")
    if (
        not isinstance(portfolios, list)
        or not portfolios
        or any(not isinstance(x, str) or not x for x in portfolios)
        or len(portfolios) != len(set(portfolios))
    ):
        errors.append("BINDING_PARENT_PORTFOLIOS_INVALID")
        portfolios = []

    terminal_acceptance = binding.get("terminal_acceptance")
    if not isinstance(terminal_acceptance, Mapping):
        errors.append("BINDING_TERMINAL_ACCEPTANCE_MISSING")
    else:
        if terminal_acceptance.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
            errors.append("SYNTHETIC_WHOLE_DOMAIN_SUBSTITUTION_NOT_FORBIDDEN")
        if terminal_acceptance.get("parent_or_direct_surface_credit_only_for_declared_scope") is not True:
            errors.append("DECLARED_SCOPE_CREDIT_NOT_ENFORCED")
        if terminal_acceptance.get("any_load_bearing_p1_failure_blocks_behavior_proof") is not True:
            errors.append("LOAD_BEARING_FAILURE_NOT_FATAL")
        if terminal_acceptance.get("no_exact_opus_case_level_comparator_required_for_prewave_admission") is not True:
            errors.append("OBJECTIVE_COMPARATOR_DELETION_NOT_PREDECLARED")
        proof_rule = terminal_acceptance.get("proof_rule")
        if not isinstance(proof_rule, str) or "INTERVENTION_RESCUE_INSTRUMENTATION_MUST_PASS" not in proof_rule:
            errors.append("INTERVENTION_RESCUE_GATE_NOT_FROZEN")

    evaluator = binding.get("evaluator")
    checks = evaluator.get("required_checks") if isinstance(evaluator, Mapping) else None
    required_check_fragments = (
        "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION",
        "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME",
        "SYMPTOM_ONLY_OR_COMPETING_REPAIR",
        "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE",
        "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES",
        "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS",
    )
    if not isinstance(checks, list) or any(
        not any(fragment in str(check) for check in checks)
        for fragment in required_check_fragments
    ):
        errors.append("FROZEN_CAUSAL_RECOVERY_SCOPE_CHECKS_INCOMPLETE")

    if not _current_binding_verified(
        current_binding_verification,
        behavior_id,
        binding_blob_sha,
    ):
        errors.append("CURRENT_BINDING_EXACT_BYTE_VERIFICATION_MISSING")

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
        if executor.get("standalone_terminal_population") is not False:
            errors.append("EXECUTOR_NOT_PARENT_MULTIPLEX_ONLY")
        if executor.get("binding_mode") != "LOAD_BEARING_PARENT_PORTFOLIO_OBSERVATION_ONLY":
            errors.append("EXECUTOR_PARENT_BINDING_MODE_INVALID")
        if executor.get("rerun_allowed") is not False:
            errors.append("RERUN_NOT_FORBIDDEN")

    if terminal_result.get("status") != "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        errors.append("TERMINAL_RESULT_NOT_IMMUTABLE_ONE_SHOT_PASS")

    package_commitment = terminal_result.get("package_commitment")
    beacon = terminal_result.get("canonical_beacon")
    if not isinstance(package_commitment, str) or not package_commitment:
        errors.append("TERMINAL_PACKAGE_COMMITMENT_MISSING")
    if not isinstance(beacon, str) or not beacon:
        errors.append("TERMINAL_BEACON_MISSING")

    parent = terminal_result.get("parent_terminal_population")
    if not isinstance(parent, Mapping):
        errors.append("PARENT_TERMINAL_POPULATION_MISSING")
    else:
        if parent.get("parent_reduction_status") != "PASS":
            errors.append("PARENT_REDUCTION_NOT_PASS")
        if parent.get("parent_reduction_errors") != []:
            errors.append("PARENT_REDUCTION_ERRORS_PRESENT")
        if parent.get("multiplex_behavior_failures") != 0:
            errors.append("PARENT_MULTIPLEX_FAILURES_PRESENT")

    reduction = terminal_result.get("reduction_input")
    wave = reduction.get("wave") if isinstance(reduction, Mapping) else None
    receipts_by_portfolio = wave.get("parent_portfolio_receipts") if isinstance(wave, Mapping) else None
    if not isinstance(receipts_by_portfolio, Mapping):
        errors.append("PARENT_PORTFOLIO_RECEIPTS_MISSING")
        receipts_by_portfolio = {}

    total_cases = 0
    observed_receipts: list[dict[str, Any]] = []
    required_set = set(portfolios)
    for portfolio in portfolios:
        rows = receipts_by_portfolio.get(portfolio)
        if not isinstance(rows, list):
            errors.append(f"REQUIRED_PARENT_RECEIPT_COUNT_MISMATCH:{portfolio}")
            continue
        found = [
            row
            for row in rows
            if isinstance(row, Mapping) and row.get("behavior_id") == behavior_id
        ]
        if len(found) != 1:
            errors.append(f"REQUIRED_PARENT_RECEIPT_COUNT_MISMATCH:{portfolio}")
            continue
        row = found[0]
        count = _aggregate_count(row.get("case_id"), portfolio, behavior_id)
        if count is None:
            errors.append(f"PARENT_AGGREGATE_CASE_ID_INVALID:{portfolio}")
        else:
            total_cases += count

        if row.get("binding_blob") != binding_blob_sha:
            errors.append(f"PARENT_BINDING_BLOB_MISMATCH:{portfolio}")
        if row.get("candidate_package_commitment") != package_commitment:
            errors.append(f"PARENT_PACKAGE_COMMITMENT_MISMATCH:{portfolio}")
        if row.get("post_freeze_beacon") != beacon:
            errors.append(f"PARENT_BEACON_MISMATCH:{portfolio}")
        if row.get("load_bearing") is not True:
            errors.append(f"PARENT_RECEIPT_NOT_LOAD_BEARING:{portfolio}")
        if row.get("direct_instrumentation_pass") is not True:
            errors.append(f"PARENT_DIRECT_INSTRUMENTATION_NOT_PASS:{portfolio}")
        if row.get("parent_terminal_acceptance_pass") is not True:
            errors.append(f"PARENT_TERMINAL_ACCEPTANCE_NOT_PASS:{portfolio}")
        if row.get("case_replaced") is not False:
            errors.append(f"PARENT_CASE_REPLACED:{portfolio}")
        if row.get("tuning_replay") is not False:
            errors.append(f"PARENT_TUNING_REPLAY:{portfolio}")
        if row.get("result_to_runtime_feedback") is not False:
            errors.append(f"PARENT_RESULT_FEEDBACK:{portfolio}")
        if row.get("candidate_visible_keys") != ["PUBLIC_TASK_PAYLOAD_ONLY"]:
            errors.append(f"PARENT_INFORMATION_BOUNDARY_DIRTY:{portfolio}")
        observed_receipts.append(dict(row))

    # The behavior must not also appear in an undeclared parent portfolio.
    for portfolio, rows in receipts_by_portfolio.items():
        if portfolio in required_set or not isinstance(rows, list):
            continue
        if any(isinstance(row, Mapping) and row.get("behavior_id") == behavior_id for row in rows):
            errors.append(f"UNDECLARED_PARENT_RECEIPT:{portfolio}")

    direct_population = terminal_result.get("direct_terminal_population")
    direct_routes = direct_population.get("routes") if isinstance(direct_population, Mapping) else None
    if isinstance(direct_routes, Mapping) and behavior_id in direct_routes:
        errors.append("DUPLICATE_STANDALONE_DIRECT_ROUTE_PRESENT")

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

    witness = {
        "id": f"PARENT_MULTIPLEX_TERMINAL_CEILING::{family}::{behavior_id}",
        "family": family,
        "mode": "ABSOLUTE_DOMINANCE",
        "verified": False,
        "independent": False,
        "contamination_clean": True,
        "binds_frozen_protocol": True,
        "scope_relation": "PROVEN_STRONGER",
        "closes_entire_protocol": True,
        "source_behavior_id": behavior_id,
        "source_binding_path": binding_path,
        "source_binding_blob_sha": binding_blob_sha,
        "source_terminal_full_result_sha256": terminal_result.get("artifact", {}).get("full_result_sha256"),
        "source_case_count": total_cases,
        "source_portfolios": list(portfolios),
        "result": {
            "direction": "higher",
            "brain_lower_bound": 1.0,
            "theoretical_upper_bound": 1.0,
        },
        "reason": (
            "ENTIRE_FROZEN_LOAD_BEARING_PARENT_MULTIPLEX_INTERVENTION_RESCUE_"
            "POPULATION_PASSED_AT_THEORETICAL_BINARY_CEILING"
        ),
    }
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        "pass": True,
        "errors": [],
        "family": family,
        "behavior_id": behavior_id,
        "source_parent_receipt_count": len(observed_receipts),
        "source_case_count": total_cases,
        "candidate_witness": witness,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "new_reality_units_consumed": 0,
    }
