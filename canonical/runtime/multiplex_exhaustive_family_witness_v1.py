"""Fail-closed lifter for a parent-multiplex exhaustive family witness.

This module can only emit a candidate acceptance witness. It never grants
capability/family credit. The intended first use is COMMUNICATION_AND_SYNTHESIS,
whose canonical residual registry maps exactly to EVIDENCE_TO_AUDIENCE_SYNTHESIS_001.

The lift is allowed only when:
- the frozen family protocol remains open and unchanged;
- exactly one residual behavioral contract backs the family;
- that contract was frozen as exhaustive finite verification with a 100% pass rule;
- the exact prewave binding was independently verified;
- the exact route was consumed in the immutable one-shot terminal wave;
- the independent postwave reducer says the residual contract and family both pass;
- all bound parent observations are load-bearing direct-instrumentation passes;
- contamination/replay guards are clean.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MULTIPLEX_EXHAUSTIVE_FAMILY_WITNESS_LIFTER_V1"


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


def _unique(rows: Any, key: str, value: str) -> Mapping[str, Any] | None:
    if not isinstance(rows, list):
        return None
    found = [r for r in rows if isinstance(r, Mapping) and r.get(key) == value]
    return found[0] if len(found) == 1 else None


def evaluate(
    *,
    family: str,
    behavior_id: str,
    binding_path: str,
    binding_blob_sha: str,
    protocols: Mapping[str, Any],
    registry: Mapping[str, Any],
    direct_contracts: Mapping[str, Any],
    binding: Mapping[str, Any],
    binding_verification: Mapping[str, Any],
    executor_manifest: Mapping[str, Any],
    terminal_result: Mapping[str, Any],
    postwave_reduction: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    protocol = _unique(protocols.get("protocols"), "family", family)
    if protocol is None:
        errors.append("FAMILY_PROTOCOL_NOT_UNIQUE_OR_MISSING")
    elif protocol.get("status") != "DEFINED_RESULT_OPEN":
        errors.append("FAMILY_PROTOCOL_NOT_OPEN")

    fmap = registry.get("family_to_residual_contracts")
    mapped = fmap.get(family) if isinstance(fmap, Mapping) else None
    if mapped != [behavior_id]:
        errors.append("BEHAVIOR_NOT_EXACT_WHOLE_FAMILY_RESIDUAL")

    obligation = _unique(direct_contracts.get("obligations"), "behavior_id", behavior_id)
    if obligation is None:
        errors.append("DIRECT_CONTRACT_NOT_UNIQUE_OR_MISSING")
    else:
        if obligation.get("proof_mode") != "EXHAUSTIVE_FINITE_STATE_OR_CASE_VERIFICATION":
            errors.append("DIRECT_CONTRACT_NOT_EXHAUSTIVE_FINITE")
        rule = str(obligation.get("pass_rule") or "")
        if "100_PERCENT" not in rule or "ALL_MUTATIONS_DETECTED" not in rule:
            errors.append("DIRECT_CONTRACT_NOT_FULL_PASS_RULE")

    if binding.get("behavior_id") != behavior_id:
        errors.append("BINDING_BEHAVIOR_MISMATCH")
    terminal_acceptance = binding.get("terminal_acceptance")
    if not isinstance(terminal_acceptance, Mapping):
        errors.append("BINDING_TERMINAL_ACCEPTANCE_MISSING")
    elif terminal_acceptance.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("STANDALONE_SYNTHETIC_SCORE_NOT_FORBIDDEN")

    exact = binding_verification.get("exact_brain_blobs")
    if not isinstance(exact, Mapping) or exact.get(binding_path) != binding_blob_sha:
        errors.append("BINDING_NOT_EXACTLY_INDEPENDENTLY_VERIFIED")
    if binding_verification.get("workflow_conclusion") != "success":
        errors.append("BINDING_INDEPENDENT_VERIFICATION_NOT_SUCCESS")
    if binding_verification.get("prewave_admission_only") is not True:
        errors.append("BINDING_VERIFICATION_NOT_PREWAVE")

    exec_rows = executor_manifest.get("executors")
    if not isinstance(exec_rows, list):
        exec_rows = executor_manifest.get("routes")
    if not isinstance(exec_rows, list):
        exec_rows = executor_manifest.get("bindings")
    executor = _unique(exec_rows, "behavior_id", behavior_id)
    if executor is None:
        errors.append("EXECUTOR_ROW_MISSING")
    else:
        if executor.get("frozen_route") != binding_path:
            errors.append("EXECUTOR_FROZEN_ROUTE_MISMATCH")
        if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(executor.get("executor_status", "")):
            errors.append("EXECUTOR_NOT_INDEPENDENTLY_BOUND")
        if executor.get("terminal_result_status") != "CONSUMED_IN_TERMINAL_V3_WAVE":
            errors.append("EXECUTOR_NOT_CONSUMED")
        if executor.get("rerun_allowed") is not False:
            errors.append("RERUN_NOT_FORBIDDEN")

    if terminal_result.get("status") != "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        errors.append("TERMINAL_RESULT_NOT_IMMUTABLE_ONE_SHOT_PASS")
    terminal_runner = terminal_result.get("public_runner")
    if not isinstance(terminal_runner, Mapping) or terminal_runner.get("conclusion") != "success":
        errors.append("TERMINAL_PUBLIC_RUNNER_NOT_SUCCESS")
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

    reduction = terminal_result.get("reduction_input")
    wave = reduction.get("wave") if isinstance(reduction, Mapping) else None
    by_portfolio = wave.get("parent_portfolio_receipts") if isinstance(wave, Mapping) else None
    portfolios = binding.get("portfolio_bindings")
    if not isinstance(portfolios, list) or not portfolios:
        errors.append("BINDING_PORTFOLIOS_MISSING")
        portfolios = []

    evidence_rows: list[Mapping[str, Any]] = []
    if not isinstance(by_portfolio, Mapping):
        errors.append("PARENT_PORTFOLIO_RECEIPTS_MISSING")
    else:
        for portfolio in portfolios:
            rows = by_portfolio.get(portfolio)
            if not isinstance(rows, list):
                errors.append("BOUND_PORTFOLIO_RECEIPTS_MISSING:" + str(portfolio))
                continue
            matches = [r for r in rows if isinstance(r, Mapping) and r.get("behavior_id") == behavior_id]
            if len(matches) != 1:
                errors.append("BOUND_PORTFOLIO_BEHAVIOR_ROW_NOT_UNIQUE:" + str(portfolio))
                continue
            row = matches[0]
            evidence_rows.append(row)
            if row.get("binding_blob") != binding_blob_sha:
                errors.append("TERMINAL_BINDING_BLOB_MISMATCH:" + str(portfolio))
            for k, v in (
                ("load_bearing", True),
                ("direct_instrumentation_pass", True),
                ("parent_terminal_acceptance_pass", True),
                ("case_replaced", False),
                ("tuning_replay", False),
                ("result_to_runtime_feedback", False),
            ):
                if row.get(k) is not v:
                    errors.append("TERMINAL_ROW_GUARD_FAILED:" + str(portfolio) + ":" + k)

    full_result_sha = (terminal_result.get("artifact") or {}).get("full_result_sha256")
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(postwave_reduction.get("status", "")):
        errors.append("POSTWAVE_NOT_INDEPENDENT_PUBLIC_RUNNER_PASS")
    postwave_runner = postwave_reduction.get("public_verifier")
    if not isinstance(postwave_runner, Mapping) or postwave_runner.get("conclusion") != "success":
        errors.append("POSTWAVE_PUBLIC_VERIFIER_NOT_SUCCESS")
    if postwave_reduction.get("source_full_result_sha256") != full_result_sha:
        errors.append("POSTWAVE_TERMINAL_RESULT_IDENTITY_MISMATCH")
    if postwave_reduction.get("terminal_replay_permitted") is not False:
        errors.append("POSTWAVE_REPLAY_NOT_FORBIDDEN")

    contract_verdict = postwave_reduction.get("contract_verdict")
    passed_contracts = contract_verdict.get("passed_contracts") if isinstance(contract_verdict, Mapping) else None
    if (
        not isinstance(contract_verdict, Mapping)
        or contract_verdict.get("all_contracts_pass") is not True
        or not isinstance(passed_contracts, list)
        or behavior_id not in passed_contracts
    ):
        errors.append("POSTWAVE_CONTRACT_NOT_PASS")

    family_verdict = postwave_reduction.get("family_verdict")
    passed_families = family_verdict.get("passed_families") if isinstance(family_verdict, Mapping) else None
    if (
        not isinstance(family_verdict, Mapping)
        or family_verdict.get("all_families_pass") is not True
        or not isinstance(passed_families, list)
        or family not in passed_families
    ):
        errors.append("POSTWAVE_FAMILY_NOT_PASS")

    contamination = binding.get("contamination")
    if not isinstance(contamination, Mapping):
        errors.append("CONTAMINATION_DECLARATION_MISSING")
    else:
        for key in (
            "post_freeze_case_specific_tuning",
            "case_replacement",
            "result_to_runtime_feedback_during_wave",
            "evaluator_or_threshold_edit_after_first_terminal_result",
            "terminal_case_selection_before_route_freeze",
        ):
            if contamination.get(key) is not False:
                errors.append("CONTAMINATION_FLAG_NOT_CLEAN:" + key)

    if errors:
        return _fail(*errors)

    candidate = {
        "id": f"MULTIPLEX_EXHAUSTIVE::{family}::{behavior_id}",
        "family": family,
        "mode": "EXHAUSTIVE_FINITE",
        "verified": False,
        "independent": False,
        "contamination_clean": True,
        "binds_frozen_protocol": True,
        "scope_relation": "PROVEN_STRONGER",
        "closes_entire_protocol": True,
        "source_behavior_id": behavior_id,
        "source_terminal_full_result_sha256": (terminal_result.get("artifact") or {}).get("full_result_sha256"),
        "source_parent_portfolios": list(portfolios),
        "source_parent_observation_count": len(evidence_rows),
        "result": {"exhaustive": True, "all_cases_pass": True},
        "reason": (
            "SOLE_FAMILY_RESIDUAL_CONTRACT_IS_FROZEN_EXHAUSTIVE_FINITE_AND_"
            "INDEPENDENT_POSTWAVE_REDUCTION_REPORTS_THAT_CONTRACT_AND_FAMILY_PASS_"
            "WITH_ALL_BOUND_LOAD_BEARING_PARENT_OBSERVATIONS_PASSING_UNDER_CLEAN_GUARDS"
        ),
    }
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        "pass": True,
        "errors": [],
        "candidate_witness": candidate,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }
