"""Fail-closed semantic implication audit for the frozen Opus55 recovery residual.

This module grants no acceptance/family/capability credit.  It checks whether the
immutable P1 trajectory evidence can be used as an explicit witness-side input
for the normalized recovery targets without mapping by name or family analogy.

The current audit intentionally proves only the narrow intervention/rescue
causality requirement.  It also emits an explicit countermodel showing why the
P1 literal EARLIEST_OR_CRITICAL... cannot establish the stricter target atom
EARLIEST causal failure localization.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_RECOVERY_SEMANTIC_IMPLICATION_AUDIT_V1"
BEHAVIOR_ID = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P1_BINDING_BLOB = "8703c6aa08227467a619a7ae90d0d61f8e54da39"

RECOVERY_TARGETS = {
    "RECOVERY_TERMINAL_NONINFERIOR",
    "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
    "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
}

CAUSAL_TARGET_ATOM = "requirement:intervention_or_rescue_establishes_causality"
EARLIEST_TARGET_ATOM = "dimension:earliest_causal_failure_localization"

REQUIRED_P1_CHECKS = {
    "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
    "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
}
DISJUNCTIVE_P1_CHECK = (
    "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE"
)


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "candidate_positive_atom_bindings": [],
        "nonimplication_certificates": [],
        "metric_bounds": [],
        "closed_predicates": [],
        "predicate_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }


def _target_map(doc: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = doc.get("targets")
    if not isinstance(rows, list):
        return {}
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("predicate_id"), str):
            out[str(row["predicate_id"])] = row
    return out


def _atoms(row: Mapping[str, Any]) -> set[str]:
    src = row.get("atom_sources")
    if not isinstance(src, list):
        return set()
    return {
        str(x.get("atom"))
        for x in src
        if isinstance(x, Mapping) and isinstance(x.get("atom"), str)
    }


def _metrics(row: Mapping[str, Any]) -> set[str]:
    src = row.get("metric_requirement_sources")
    if not isinstance(src, list):
        return set()
    return {
        str(x.get("metric"))
        for x in src
        if isinstance(x, Mapping) and isinstance(x.get("metric"), str)
    }


def _p1_receipts(wave: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    reduction = wave.get("reduction_input")
    inner = reduction.get("wave") if isinstance(reduction, Mapping) else None
    parents = inner.get("parent_portfolio_receipts") if isinstance(inner, Mapping) else None
    if not isinstance(parents, Mapping):
        return {}
    out: dict[str, Mapping[str, Any]] = {}
    for portfolio in ("T0", "T2"):
        rows = parents.get(portfolio)
        if not isinstance(rows, list):
            continue
        found = [
            r for r in rows
            if isinstance(r, Mapping) and r.get("behavior_id") == BEHAVIOR_ID
        ]
        if len(found) == 1:
            out[portfolio] = found[0]
    return out


def evaluate(
    *,
    target_normalization: Mapping[str, Any],
    p1_binding: Mapping[str, Any],
    terminal_wave: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    targets = _target_map(target_normalization)
    if set(targets) & RECOVERY_TARGETS != RECOVERY_TARGETS:
        errors.append("RECOVERY_TARGET_SET_INCOMPLETE")
    else:
        if CAUSAL_TARGET_ATOM not in _atoms(
            targets["RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR"]
        ):
            errors.append("CAUSAL_TARGET_ATOM_NOT_SOURCE_BOUND")
        if EARLIEST_TARGET_ATOM not in _atoms(
            targets["RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR"]
        ):
            errors.append("EARLIEST_TARGET_ATOM_NOT_SOURCE_BOUND")
        if "causal_localization_noninferiority" not in _metrics(
            targets["RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR"]
        ):
            errors.append("CAUSAL_NONINFERIORITY_METRIC_NOT_SOURCE_BOUND")
        if "terminal_recovery_noninferiority" not in _metrics(
            targets["RECOVERY_TERMINAL_NONINFERIOR"]
        ):
            errors.append("TERMINAL_RECOVERY_METRIC_NOT_SOURCE_BOUND")
        if "critical_fail_closed_misses" not in _metrics(
            targets["RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES"]
        ):
            errors.append("FAIL_CLOSED_MISS_METRIC_NOT_SOURCE_BOUND")

    if p1_binding.get("behavior_id") != BEHAVIOR_ID:
        errors.append("P1_BEHAVIOR_ID_MISMATCH")
    evaluator = p1_binding.get("evaluator")
    checks = evaluator.get("required_checks") if isinstance(evaluator, Mapping) else None
    check_set = set(checks) if isinstance(checks, list) else set()
    missing_checks = sorted(REQUIRED_P1_CHECKS - check_set)
    if missing_checks:
        errors.append("P1_CAUSAL_RESCUE_CHECKS_MISSING:" + ",".join(missing_checks))
    if DISJUNCTIVE_P1_CHECK not in check_set:
        errors.append("P1_EARLIEST_OR_CRITICAL_CHECK_MISSING")

    terminal_acceptance = p1_binding.get("terminal_acceptance")
    if not isinstance(terminal_acceptance, Mapping):
        errors.append("P1_TERMINAL_ACCEPTANCE_MISSING")
    else:
        if terminal_acceptance.get("any_load_bearing_p1_failure_blocks_behavior_proof") is not True:
            errors.append("P1_LOAD_BEARING_FAILURE_NOT_BLOCKING")
        rule = str(terminal_acceptance.get("proof_rule", ""))
        if "DIRECT_P1_INTERVENTION_RESCUE_INSTRUMENTATION_MUST_PASS" not in rule:
            errors.append("P1_INTERVENTION_RESCUE_PROOF_RULE_MISSING")

    contamination = p1_binding.get("contamination")
    if not isinstance(contamination, Mapping):
        errors.append("P1_CONTAMINATION_GUARDS_MISSING")
    else:
        for key in (
            "post_freeze_case_specific_tuning",
            "case_replacement",
            "result_to_runtime_feedback_during_wave",
            "evaluator_or_threshold_edit_after_first_terminal_result",
            "terminal_case_selection_before_route_freeze",
        ):
            if contamination.get(key) is not False:
                errors.append("P1_CONTAMINATION_GUARD_FAILED:" + key)

    if terminal_wave.get("status") != (
        "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED"
    ):
        errors.append("TERMINAL_WAVE_NOT_IMMUTABLE_ONE_SHOT_PASS")
    guards = terminal_wave.get("result_guards")
    if not isinstance(guards, Mapping):
        errors.append("TERMINAL_WAVE_GUARDS_MISSING")
    else:
        if guards.get("no_case_replacement") is not True:
            errors.append("TERMINAL_CASE_REPLACEMENT_GUARD_FAILED")
        if guards.get("no_tuning_replay") is not True:
            errors.append("TERMINAL_TUNING_REPLAY_GUARD_FAILED")
        if guards.get("result_to_runtime_feedback_during_wave") is not False:
            errors.append("TERMINAL_RESULT_FEEDBACK_GUARD_FAILED")

    receipts = _p1_receipts(terminal_wave)
    if set(receipts) != {"T0", "T2"}:
        errors.append("P1_T0_T2_RECEIPTS_INCOMPLETE")
    else:
        for portfolio, row in receipts.items():
            if row.get("binding_blob") != P1_BINDING_BLOB:
                errors.append("P1_BINDING_BLOB_MISMATCH:" + portfolio)
            if row.get("direct_instrumentation_pass") is not True:
                errors.append("P1_DIRECT_INSTRUMENTATION_NOT_PASS:" + portfolio)
            if row.get("load_bearing") is not True:
                errors.append("P1_RECEIPT_NOT_LOAD_BEARING:" + portfolio)
            if row.get("parent_terminal_acceptance_pass") is not True:
                errors.append("P1_PARENT_TERMINAL_NOT_PASS:" + portfolio)
            if row.get("case_replaced") is not False:
                errors.append("P1_RECEIPT_CASE_REPLACED:" + portfolio)
            if row.get("tuning_replay") is not False:
                errors.append("P1_RECEIPT_TUNING_REPLAY:" + portfolio)
            if row.get("result_to_runtime_feedback") is not False:
                errors.append("P1_RECEIPT_RESULT_FEEDBACK:" + portfolio)

    if errors:
        return _fail(*errors)

    positive = [{
        "predicate_id": "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
        "atom": CAUSAL_TARGET_ATOM,
        "relation": "CONJUNCTIVE_OPERATIONAL_REFINEMENT",
        "basis": [
            "P1_REQUIRES_NOMINATED_REPAIR_RESCUE_WHEN_CAUSE_IDENTIFIABLE",
            "P1_DENIES_CAUSAL_CREDIT_TO_SYMPTOM_ONLY_OR_COMPETING_REPAIR",
            "T0_AND_T2_LOAD_BEARING_P1_INTERVENTION_RESCUE_INSTRUMENTATION_PASS",
            "PARENT_TERMINAL_ACCEPTANCE_PASS",
        ],
        "scope": "FROZEN_T0_T2_P1_DECLARED_SCOPE_ONLY",
        "acceptance_credit": False,
    }]

    nonimplication = [{
        "predicate_id": "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
        "atom": EARLIEST_TARGET_ATOM,
        "state": "NOT_IMPLIED_BY_CURRENT_P1_LITERAL",
        "countermodel": {
            "critical_causal_failure_localized": True,
            "earliest_causal_failure_localized": False,
            "p1_disjunction_satisfied": True,
            "target_atom_satisfied": False,
        },
        "reason": (
            "The frozen P1 requirement accepts EARLIEST_OR_CRITICAL causal "
            "localization.  Therefore a critical-but-not-earliest result satisfies "
            "the P1 literal while violating the stricter normalized target atom."
        ),
    }]

    metric_bounds = [
        {
            "predicate_id": "RECOVERY_TERMINAL_NONINFERIOR",
            "metric": "terminal_recovery_noninferiority",
            "state": "OPEN",
            "reason": "NO_EXPLICIT_BRAIN_VS_OPUS_MATCHED_BOUND_BOUND_TO_THIS_P1_WITNESS",
        },
        {
            "predicate_id": "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
            "metric": "causal_localization_noninferiority",
            "state": "OPEN",
            "reason": "NO_EXPLICIT_BRAIN_VS_OPUS_MATCHED_BOUND_BOUND_TO_THIS_P1_WITNESS",
        },
        {
            "predicate_id": "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
            "metric": "critical_fail_closed_misses",
            "state": "OPEN",
            "reason": "NO_SCOPE_COMPLETE_ZERO_MISS_RECEIPT_BOUND_TO_THIS_P1_WITNESS",
        },
    ]

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_SEMANTIC_SCOPE_BINDING_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        "pass": True,
        "errors": [],
        "family": "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
        "behavior_id": BEHAVIOR_ID,
        "candidate_positive_atom_bindings": positive,
        "nonimplication_certificates": nonimplication,
        "metric_bounds": metric_bounds,
        "p1_receipt_portfolios": ["T0", "T2"],
        "p1_load_bearing_receipt_count": 2,
        "closed_predicates": [],
        "predicate_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "next": (
            "INDEPENDENTLY_VERIFY_THIS_BINDING__THEN_FEED_ONLY_THE_POSITIVE_ATOM_"
            "BINDING_TO_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA__KEEP_EARLIEST_AND_ALL_"
            "THREE_METRIC_BOUNDS_OPEN"
        ),
    }
