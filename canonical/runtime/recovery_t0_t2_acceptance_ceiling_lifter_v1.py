"""Fail-closed lifter for the frozen T0/T2 recovery acceptance ceiling.

This compiler never grants ownership by itself. It recognizes only the exact
SELF_VERIFICATION_DEBUGGING_AND_RECOVERY -> TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001
scope relation, the exact pre-wave-admitted P1 route, and the immutable terminal
V3 T0/T2 receipts. Every one of the three frozen recovery acceptance predicates
must be explicitly covered; omission of one fails closed.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_RECOVERY_T0_T2_ACCEPTANCE_CEILING_LIFTER_V1"
FAMILY = "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
BINDING_PATH = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
BINDING_SHA = "8703c6aa08227467a619a7ae90d0d61f8e54da39"
BASIS_PATH = "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
BASIS_SHA = "9c60356ab509a16df5104777f360b9fb18255842"
EXECUTION_SNAPSHOT_COMMIT = "821712c059b139f3494723dca6e8d0fc82ee59a4"
TERMINAL_SHA256 = "f4bec690aa0580cb532dbfd5985705bae8d153c9df31ffdf460b02f8b152e0f2"

PREDICATE_TERMINAL = "RECOVERY_TERMINAL_NONINFERIOR"
PREDICATE_CAUSAL = "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR"
PREDICATE_INVARIANT = "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES"
TARGET_PREDICATES = {PREDICATE_TERMINAL, PREDICATE_CAUSAL, PREDICATE_INVARIANT}

REQ_CHECKS = {
    "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
    "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
    "NOMINATED_REPAIR_IS_FALSIFIABLE",
    "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
    "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
    "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
    "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
    "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}
TARGET_DIMS = {
    "semantic self-check",
    "counterexample discovery",
    "earliest causal failure localization",
    "repair selection",
    "recovery after injected failure",
}
MUTATION_RULE = (
    "ALL_APPLICABLE_LOAD_BEARING_P1_MUTATIONS_MUST_BE_REJECTED_OR_CAUSE_PARENT_TERMINAL_ACCEPTANCE_FAILURE"
)

EXPECTED_PREDICATE_ACCEPTANCE = {
    PREDICATE_TERMINAL: "Brain conservative terminal-recovery bound >= Opus matched bound on frozen intervention portfolio.",
    PREDICATE_CAUSAL: "Brain conservative causal-localization bound >= Opus matched bound on frozen intervention portfolio.",
    PREDICATE_INVARIANT: "Deterministic fail-closed invariants have zero critical misses.",
}


def _fail(errors: list[str]) -> dict[str, Any]:
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


def _protocol(doc: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = doc.get("protocols")
    if not isinstance(rows, list):
        return None
    found = [x for x in rows if isinstance(x, Mapping) and x.get("family") == FAMILY]
    return found[0] if len(found) == 1 else None


def _predicate(doc: Mapping[str, Any], pid: str) -> Mapping[str, Any] | None:
    rows = doc.get("predicates") or doc.get("claims")
    if not isinstance(rows, list):
        return None
    found = [
        x
        for x in rows
        if isinstance(x, Mapping) and (x.get("id") or x.get("predicate_id")) == pid
    ]
    return found[0] if len(found) == 1 else None


def _basis_row(basis: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = basis.get("contracts")
    if not isinstance(rows, list):
        return None
    found = [x for x in rows if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR]
    return found[0] if len(found) == 1 else None


def _receipt(terminal: Mapping[str, Any], portfolio: str) -> Mapping[str, Any] | None:
    wave = ((terminal.get("reduction_input") or {}).get("wave") or {})
    parents = wave.get("parent_portfolio_receipts")
    rows = parents.get(portfolio) if isinstance(parents, Mapping) else None
    if not isinstance(rows, list):
        return None
    found = [x for x in rows if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR]
    return found[0] if len(found) == 1 else None


def _check_bound(
    relation: Mapping[str, Any],
    key: str,
    *,
    predicate: str,
    direction: str,
    observed: int,
    theoretical: int,
    source_check: str,
    errors: list[str],
) -> None:
    bounds = relation.get("acceptance_to_objective_floor_ceiling")
    row = bounds.get(key) if isinstance(bounds, Mapping) else None
    if not isinstance(row, Mapping):
        errors.append("RELATION_OBJECTIVE_BOUND_MISSING:" + key)
        return
    if row.get("target_predicate") != predicate:
        errors.append("RELATION_OBJECTIVE_PREDICATE_DRIFT:" + key)
    if row.get("direction") != direction:
        errors.append("RELATION_OBJECTIVE_DIRECTION_DRIFT:" + key)
    if row.get("observed_bound") != observed or row.get("theoretical_bound") != theoretical:
        errors.append("RELATION_OBJECTIVE_CEILING_DRIFT:" + key)
    if row.get("source_check") != source_check:
        errors.append("RELATION_OBJECTIVE_SOURCE_CHECK_DRIFT:" + key)


def evaluate(
    *,
    protocols: Mapping[str, Any],
    registry: Mapping[str, Any],
    predicates: Mapping[str, Any],
    basis: Mapping[str, Any],
    binding: Mapping[str, Any],
    terminal: Mapping[str, Any],
    relation: Mapping[str, Any],
) -> dict[str, Any]:
    e: list[str] = []

    p = _protocol(protocols)
    if p is None:
        e.append("RECOVERY_PROTOCOL_MISSING_OR_DUPLICATE")
    else:
        if p.get("status") != "DEFINED_RESULT_OPEN":
            e.append("RECOVERY_PROTOCOL_NOT_OPEN")
        if p.get("proof_mode") != "MATCHED_CAUSAL_INTERVENTION_PROTOCOL":
            e.append("RECOVERY_PROTOCOL_MODE_DRIFT")
        dims = p.get("task_dimensions")
        if not isinstance(dims, list) or set(dims) != TARGET_DIMS:
            e.append("RECOVERY_TASK_DIMENSIONS_DRIFT")
        acc = str(p.get("acceptance") or "")
        for phrase in ("terminal-recovery", "causal-localization", "zero critical misses"):
            if phrase not in acc:
                e.append("RECOVERY_ACCEPTANCE_RULE_DRIFT:" + phrase)

    fmap = registry.get("family_to_residual_contracts")
    if not isinstance(fmap, Mapping) or fmap.get(FAMILY) != [BEHAVIOR]:
        e.append("RECOVERY_NOT_EXACT_SINGLE_RESIDUAL_CONTRACT")

    for pid, expected in EXPECTED_PREDICATE_ACCEPTANCE.items():
        row = _predicate(predicates, pid)
        if row is None:
            e.append("RECOVERY_PREDICATE_MISSING:" + pid)
        elif row.get("family") != FAMILY or str(row.get("acceptance") or "") != expected:
            e.append("RECOVERY_PREDICATE_DRIFT:" + pid)

    br = _basis_row(basis)
    if br is None:
        e.append("EXECUTION_BASIS_RECOVERY_ROUTE_MISSING_OR_DUPLICATE")
    else:
        if br.get("proof_state") != "TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
            e.append("EXECUTION_BASIS_ROUTE_NOT_ADMISSIBLE")
        if br.get("route") != BINDING_PATH:
            e.append("EXECUTION_BASIS_ROUTE_DRIFT")
        if br.get("blockers") != []:
            e.append("EXECUTION_BASIS_ROUTE_HAS_BLOCKERS")
        if br.get("prewave_admissible") is not True:
            e.append("EXECUTION_BASIS_PREWAVE_ADMISSION_MISSING")
        if not isinstance(br.get("independent_preflight"), str) or not br.get("independent_preflight"):
            e.append("EXECUTION_BASIS_INDEPENDENT_PREFLIGHT_MISSING")

    if binding.get("behavior_id") != BEHAVIOR:
        e.append("BINDING_BEHAVIOR_DRIFT")
    if binding.get("proof_mode") != "T0_T2_MULTIPLEXED_DETERMINISTIC_INTERVENTION_RESCUE_GATE":
        e.append("BINDING_PROOF_MODE_DRIFT")
    if binding.get("portfolio_bindings") != ["T0", "T2"]:
        e.append("BINDING_PORTFOLIO_DRIFT")
    checks = ((binding.get("evaluator") or {}).get("required_checks"))
    if not isinstance(checks, list) or not REQ_CHECKS.issubset(set(checks)):
        e.append("LOAD_BEARING_CHECKS_INCOMPLETE")
    if ((binding.get("evaluator") or {}).get("mutation_acceptance")) != MUTATION_RULE:
        e.append("FAIL_CLOSED_MUTATION_RULE_DRIFT")
    surfaces = ((binding.get("scope_accounting") or {}).get("represented_terminal_surfaces"))
    if not isinstance(surfaces, list) or "RECOVERY_SCOPE_COMPOSITION" not in surfaces:
        e.append("RECOVERY_SCOPE_SURFACE_MISSING")
    ta = binding.get("terminal_acceptance") or {}
    if ta.get("any_load_bearing_p1_failure_blocks_behavior_proof") is not True:
        e.append("LOAD_BEARING_FAILURE_NOT_BLOCKING")
    contamination = binding.get("contamination")
    if not isinstance(contamination, Mapping) or any(v is not False for v in contamination.values()):
        e.append("PREWAVE_BINDING_CONTAMINATION_GUARD_FAIL")

    if relation.get("schema") != "PROJECT_BRAIN_RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1":
        e.append("RELATION_SCHEMA_DRIFT")
    if relation.get("status") != "CANDIDATE_PROVEN_STRONGER_RELATION__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT":
        e.append("RELATION_STATUS_DRIFT")
    if relation.get("family") != FAMILY or relation.get("source_behavior_id") != BEHAVIOR:
        e.append("RELATION_SCOPE_DRIFT")
    if relation.get("relation") != "PROVEN_STRONGER_CANDIDATE":
        e.append("RELATION_CLASS_DRIFT")
    if set(relation.get("target_atomic_predicates") or []) != TARGET_PREDICATES:
        e.append("RELATION_ATOMIC_TARGET_SET_INCOMPLETE")
    if ((relation.get("source_binding") or {}).get("git_blob_sha")) != BINDING_SHA:
        e.append("RELATION_BINDING_SHA_DRIFT")
    rbasis = relation.get("source_execution_basis")
    if not isinstance(rbasis, Mapping):
        e.append("RELATION_EXECUTION_BASIS_MISSING")
    else:
        if rbasis.get("path") != BASIS_PATH or rbasis.get("git_blob_sha") != BASIS_SHA:
            e.append("RELATION_EXECUTION_BASIS_SHA_DRIFT")
        if rbasis.get("execution_snapshot_commit") != EXECUTION_SNAPSHOT_COMMIT:
            e.append("RELATION_EXECUTION_SNAPSHOT_DRIFT")

    maps = relation.get("target_dimension_to_source_checks")
    if not isinstance(maps, Mapping) or set(maps) != TARGET_DIMS:
        e.append("RELATION_DIMENSION_MAP_INCOMPLETE")
    else:
        for dim, src in maps.items():
            if not isinstance(src, list) or not src or not set(src).issubset(REQ_CHECKS):
                e.append("RELATION_CHECK_NOT_LOAD_BEARING:" + str(dim))

    _check_bound(
        relation,
        "terminal_recovery",
        predicate=PREDICATE_TERMINAL,
        direction="higher",
        observed=1,
        theoretical=1,
        source_check="NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
        errors=e,
    )
    _check_bound(
        relation,
        "causal_localization",
        predicate=PREDICATE_CAUSAL,
        direction="higher",
        observed=1,
        theoretical=1,
        source_check="EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
        errors=e,
    )
    _check_bound(
        relation,
        "critical_fail_closed_misses",
        predicate=PREDICATE_INVARIANT,
        direction="lower",
        observed=0,
        theoretical=0,
        source_check="AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
        errors=e,
    )
    invariant_bound = (relation.get("acceptance_to_objective_floor_ceiling") or {}).get(
        "critical_fail_closed_misses"
    )
    if not isinstance(invariant_bound, Mapping) or invariant_bound.get("enforcement") != MUTATION_RULE:
        e.append("RELATION_FAIL_CLOSED_ENFORCEMENT_DRIFT")

    if terminal.get("status") != "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        e.append("TERMINAL_RESULT_NOT_IMMUTABLE_PASS")
    if terminal.get("execution_snapshot_commit") != EXECUTION_SNAPSHOT_COMMIT:
        e.append("TERMINAL_EXECUTION_SNAPSHOT_DRIFT")
    if ((terminal.get("artifact") or {}).get("full_result_sha256")) != TERMINAL_SHA256:
        e.append("TERMINAL_FULL_RESULT_SHA_DRIFT")

    total = 0
    for portfolio in ("T0", "T2"):
        r = _receipt(terminal, portfolio)
        if r is None:
            e.append("RECOVERY_RECEIPT_MISSING:" + portfolio)
            continue
        if r.get("binding_blob") != BINDING_SHA:
            e.append("RECOVERY_BINDING_BLOB_DRIFT:" + portfolio)
        for k in ("direct_instrumentation_pass", "load_bearing", "parent_terminal_acceptance_pass"):
            if r.get(k) is not True:
                e.append("RECOVERY_RECEIPT_NOT_PASS:" + portfolio + ":" + k)
        if r.get("case_replaced") is not False or r.get("tuning_replay") is not False or r.get("result_to_runtime_feedback") is not False:
            e.append("RECOVERY_RECEIPT_CONTAMINATED:" + portfolio)
        if r.get("candidate_visible_keys") != ["PUBLIC_TASK_PAYLOAD_ONLY"]:
            e.append("RECOVERY_RECEIPT_INFORMATION_BOUNDARY_DRIFT:" + portfolio)
        cid = str(r.get("case_id") or "")
        try:
            n = int(cid.rsplit("::", 1)[-1])
        except Exception:
            n = -1
        if n != 30:
            e.append("RECOVERY_CASE_COUNT_DRIFT:" + portfolio)
        else:
            total += n

    guards = terminal.get("result_guards")
    if (
        not isinstance(guards, Mapping)
        or guards.get("no_case_replacement") is not True
        or guards.get("no_tuning_replay") is not True
        or guards.get("result_to_runtime_feedback_during_wave") is not False
    ):
        e.append("TERMINAL_CONTAMINATION_GUARDS_FAIL")

    if e:
        return _fail(e)

    witness = {
        "id": "RECOVERY_T0_T2_ABSOLUTE_DOMINANCE_20261002_V1",
        "family": FAMILY,
        "mode": "ABSOLUTE_DOMINANCE",
        "verified": False,
        "independent": False,
        "contamination_clean": True,
        "binds_frozen_protocol": True,
        "scope_relation": "PROVEN_STRONGER",
        "closes_entire_protocol": True,
        "source_behavior_id": BEHAVIOR,
        "source_case_count": total,
        "source_terminal_full_result_sha256": TERMINAL_SHA256,
        "covered_atomic_predicates": sorted(TARGET_PREDICATES),
        "result": {
            "direction": "higher",
            "brain_lower_bound": 1.0,
            "theoretical_upper_bound": 1.0,
        },
        "hard_invariants": {
            "critical_fail_closed_misses": {
                "direction": "lower",
                "brain_upper_bound": 0.0,
                "theoretical_lower_bound": 0.0,
            }
        },
        "reason": (
            "EXACT_SINGLE_RESIDUAL_RECOVERY_CONTRACT__EXECUTION_SNAPSHOT_PREWAVE_ADMISSION__"
            "FROZEN_T0_T2_CAUSAL_LOCALIZATION_RESCUE_AND_FAIL_CLOSED_CHECKS_ALL_PASS_AT_OBJECTIVE_BOUNDS"
        ),
    }
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        "pass": True,
        "errors": [],
        "source_case_count": total,
        "candidate_witness": witness,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }
