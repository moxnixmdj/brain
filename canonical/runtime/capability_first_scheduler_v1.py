"""Capability-first development scheduler.

This module ranks work by conservative reusable capability gain per resource and
keeps benchmark activity as instrumentation unless it localizes a real
capability defect, validates a new capability, falsifies a capability claim, or
certifies a frontier milestone.

Planning only. It does not grant execution, acceptance, capability, ownership,
or terminal credit by itself.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import r2_semantic_residual_ledger_v1 as residual_ledger

SCHEMA = "PROJECT_BRAIN_CAPABILITY_FIRST_SCHEDULER_V1"
MISSION_OBJECTIVE = "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"
MILESTONE = "OPUS_5_5_FIRST_FRONTIER_CHECKPOINT__NOT_TERMINAL_OBJECTIVE"
OPTION_PRESERVATION_POLICY = "canonical/governance/CURRENT_OPTION_PRESERVING_OPTIMIZATION.json"
CAPABILITY_LEARNING_LOOP = (
    "SOLVE",
    "VERIFY",
    "EXTRACT_MECHANISM",
    "GENERALIZE",
    "COMPRESS",
    "PRESERVE_OPTIONS",
    "REUSE_CHEAPER",
)
ALLOWED_BENCHMARK_ROLES = frozenset(
    {
        "CAPABILITY_DEFECT_LOCALIZATION",
        "NEW_CAPABILITY_VALIDATION",
        "CAPABILITY_CLAIM_FALSIFICATION",
        "MILESTONE_CERTIFICATION",
    }
)
WORK_TYPES = frozenset(
    {
        "CAPABILITY_BUILD",
        "EFFICIENCY_IMPROVEMENT",
        "RELIABILITY_IMPROVEMENT",
        "BENCHMARK_INSTRUMENTATION",
        "FALSIFICATION",
    }
)

LOAD_BEARING_PRIMARY_LANE = "LOAD_BEARING_PRIMARY"
SECONDARY_CAPABILITY_LANE = "SECONDARY_CAPABILITY"
OPEN_WORLD_EVIDENCE_FRONTIER = "OPEN_WORLD_EVIDENCE_FRONTIER"
NEW_PRIMITIVE_ADMISSION_FIELDS = (
    "exact_unsatisfied_predicate",
    "existing_mechanisms_searched",
    "existing_mechanism_unsoundness_reasons",
    "independently_verified_missing_primitive_or_counterexample",
    "minimum_new_primitive_scope",
    "falsifier_and_promotion_criteria",
)

LIVE_SCORE_FIELDS = (
    "expected_capability_gain_lcb",
    "expected_efficiency_gain_lcb",
    "expected_reliability_gain_lcb",
    "reuse_breadth_lcb",
    "generalization_lcb",
    "success_probability_lcb",
    "wall_clock_cost_ub",
    "compute_cost_ub",
    "memory_cost_ub",
    "complexity_cost_ub",
)
LIVE_SCORE_CONTRACT_SCALE = "COMMON_DIMENSIONLESS_MISSION_UTILITY_RESOURCE_SCALE_V1"
CURRENT_TERMINAL_AUTHORITY = (
    Path(__file__).resolve().parents[1] / "governance" / "CURRENT_TERMINAL_AUTHORITY.json"
)


def _ids(raw: Mapping[str, Any], key: str) -> list[str]:
    value = raw.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and _s(x) for x in value):
        raise CapabilityFirstSchedulerError(key.upper() + "_INVALID")
    return sorted(set(_s(x) for x in value))


def _new_primitive_admission(
    raw: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    """Require proof before treating a residual as a genuinely new primitive gap."""
    if raw.get("claims_new_primitive") is not True:
        return True, []

    missing: list[str] = []
    if not _s(raw.get("exact_unsatisfied_predicate")):
        missing.append("EXACT_UNSATISFIED_PREDICATE")

    mechanisms = _ids(raw, "existing_mechanisms_searched")
    if not mechanisms:
        missing.append("EXISTING_MECHANISMS_SEARCHED")

    reasons = raw.get("existing_mechanism_unsoundness_reasons")
    if not isinstance(reasons, Mapping):
        missing.append("WHY_EACH_EXISTING_MECHANISM_CANNOT_SOUNDLY_CLOSE_THE_PREDICATE")
    elif mechanisms and any(not _s(reasons.get(mid)) for mid in mechanisms):
        missing.append("WHY_EACH_EXISTING_MECHANISM_CANNOT_SOUNDLY_CLOSE_THE_PREDICATE")

    if not _s(raw.get("independently_verified_missing_primitive_or_counterexample")):
        missing.append("INDEPENDENTLY_VERIFIED_MISSING_PRIMITIVE_OR_COUNTEREXAMPLE")
    if not _s(raw.get("minimum_new_primitive_scope")):
        missing.append("MINIMUM_NEW_PRIMITIVE_SCOPE")
    if not _s(raw.get("falsifier_and_promotion_criteria")):
        missing.append("FALSIFIER_AND_PROMOTION_CRITERIA")

    return not missing, missing


def _current_open_obligation_count() -> int:
    """Read the current independent load-bearing acceptance count fail-closed."""
    try:
        doc = json.loads(CURRENT_TERMINAL_AUTHORITY.read_text(encoding="utf-8"))
        live = doc.get("live_truth", {})
        value = live.get("independent_open_acceptance_obligations")
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    except Exception:
        pass
    # Unknown current authority is not permission to schedule generic side work.
    raise CapabilityFirstSchedulerError("CURRENT_OPEN_OBLIGATION_COUNT_UNAVAILABLE")


def _load_bearing_score(raw: Mapping[str, Any]) -> Fraction:
    discharge = _f(
        raw.get("expected_obligation_discharge_lcb", 0),
        "expected_obligation_discharge_lcb",
    )
    unlock = _f(
        raw.get("expected_obligation_unlock_lcb", 0),
        "expected_obligation_unlock_lcb",
    )
    success = _f(raw.get("success_probability_lcb", 0), "success_probability_lcb")
    if success > 1:
        raise CapabilityFirstSchedulerError("SUCCESS_PROBABILITY_LCB_GT_ONE")
    wall = _f(raw.get("wall_clock_cost_ub", 0), "wall_clock_cost_ub")
    if wall <= 0:
        raise CapabilityFirstSchedulerError("WALL_CLOCK_COST_MUST_BE_POSITIVE")
    return (discharge + unlock) * success / wall


def _has_load_bearing_path(raw: Mapping[str, Any]) -> bool:
    return bool(
        _ids(raw, "open_obligation_ids")
        or _ids(raw, "constructive_gap_for_open_obligation_ids")
        or raw.get("scope_complete_discharge") is True
    )


def _shared_residual_fanout(
    raw: Mapping[str, Any],
) -> tuple[Fraction, list[str]]:
    cause_ids = _ids(raw, "shared_residual_cause_ids")
    if not cause_ids:
        return Fraction(0), []

    try:
        ledger = residual_ledger.load_current_ledger()
    except residual_ledger.R2SemanticResidualLedgerError as exc:
        raise CapabilityFirstSchedulerError(
            "CURRENT_R2_RESIDUAL_LEDGER_UNAVAILABLE"
        ) from exc

    if ledger.get("classification_complete") is not True:
        raise CapabilityFirstSchedulerError(
            "CURRENT_R2_RESIDUAL_LEDGER_CLASSIFICATION_INCOMPLETE"
        )

    cause_to_clauses: dict[str, set[str]] = {}
    for key in ("fine_causes", "shared_causes"):
        rows = ledger.get(key, [])
        if not isinstance(rows, list):
            raise CapabilityFirstSchedulerError(
                "CURRENT_R2_RESIDUAL_LEDGER_INVALID"
            )
        for row in rows:
            if not isinstance(row, Mapping):
                raise CapabilityFirstSchedulerError(
                    "CURRENT_R2_RESIDUAL_LEDGER_INVALID"
                )
            cause_id = _s(row.get("cause_id"))
            clause_ids = row.get("clause_ids", [])
            if (
                not cause_id
                or not isinstance(clause_ids, list)
                or not all(isinstance(x, str) and _s(x) for x in clause_ids)
            ):
                raise CapabilityFirstSchedulerError(
                    "CURRENT_R2_RESIDUAL_LEDGER_INVALID"
                )
            cause_to_clauses[cause_id] = set(_s(x) for x in clause_ids)

    unknown = [cause_id for cause_id in cause_ids if cause_id not in cause_to_clauses]
    if unknown:
        raise CapabilityFirstSchedulerError(
            "UNKNOWN_SHARED_RESIDUAL_CAUSE:" + ",".join(unknown)
        )

    covered: set[str] = set()
    for cause_id in cause_ids:
        covered.update(cause_to_clauses[cause_id])
    return Fraction(len(covered), 1), cause_ids


class CapabilityFirstSchedulerError(ValueError):
    pass


def _s(x: Any) -> str:
    return " ".join(str(x or "").split())


def _f(x: Any, name: str) -> Fraction:
    if isinstance(x, bool):
        raise CapabilityFirstSchedulerError(name.upper() + "_INVALID")
    try:
        out = x if isinstance(x, Fraction) else Fraction(str(x))
    except Exception as exc:
        raise CapabilityFirstSchedulerError(name.upper() + "_INVALID") from exc
    if out < 0:
        raise CapabilityFirstSchedulerError(name.upper() + "_NEGATIVE")
    return out


def _eligible(
    raw: Mapping[str, Any], checkpoint_open_obligation_count: int
) -> tuple[bool, str]:
    work_type = _s(raw.get("work_type"))
    if work_type not in WORK_TYPES:
        raise CapabilityFirstSchedulerError("WORK_TYPE_INVALID")

    new_primitive_ok, _ = _new_primitive_admission(raw)
    if not new_primitive_ok:
        return False, "DEMOTED_UNPROVED_NEW_PRIMITIVE_CLAIM"

    # Open-world incompleteness is not, by itself, a capability defect. Once a
    # general mechanism can acquire minimum task-local information on demand,
    # endless global ontology/evidence completion must not consume primary
    # development priority. It wakes only when a concrete task/counterexample or
    # independently verified capability defect binds the frontier to real work.
    frontier_class = _s(raw.get("frontier_class"))
    if frontier_class == OPEN_WORLD_EVIDENCE_FRONTIER:
        task_counterexamples = _ids(raw, "task_local_counterexample_ids")
        verified_defects = _ids(raw, "verified_capability_defect_ids")
        if not task_counterexamples and not verified_defects:
            return (
                False,
                "DEMOTED_OPEN_WORLD_EVIDENCE_FRONTIER_WITHOUT_CURRENT_CAPABILITY_DEFECT",
            )

    # Opus/terminal bookkeeping is instrumentation. Open checkpoint obligations
    # may add an audit signal, but they never turn the checkpoint into the
    # optimization target or demote unrelated reusable capability work.
    if work_type != "BENCHMARK_INSTRUMENTATION":
        return True, "ELIGIBLE"
    role = _s(raw.get("benchmark_role"))
    if role in ALLOWED_BENCHMARK_ROLES:
        return True, "ELIGIBLE"
    return False, "DEMOTED_BENCHMARK_BOOKKEEPING"


def _score(raw: Mapping[str, Any]) -> Fraction:
    capability = _f(raw.get("expected_capability_gain_lcb", 0), "expected_capability_gain_lcb")
    efficiency = _f(raw.get("expected_efficiency_gain_lcb", 0), "expected_efficiency_gain_lcb")
    reliability = _f(raw.get("expected_reliability_gain_lcb", 0), "expected_reliability_gain_lcb")
    breadth = _f(raw.get("reuse_breadth_lcb", 0), "reuse_breadth_lcb")
    generalization = _f(raw.get("generalization_lcb", 0), "generalization_lcb")
    success = _f(raw.get("success_probability_lcb", 0), "success_probability_lcb")
    if success > 1:
        raise CapabilityFirstSchedulerError("SUCCESS_PROBABILITY_LCB_GT_ONE")
    costs = (
        _f(raw.get("wall_clock_cost_ub", 0), "wall_clock_cost_ub")
        + _f(raw.get("compute_cost_ub", 0), "compute_cost_ub")
        + _f(raw.get("memory_cost_ub", 0), "memory_cost_ub")
        + _f(raw.get("complexity_cost_ub", 0), "complexity_cost_ub")
    )
    if costs <= 0:
        raise CapabilityFirstSchedulerError("TOTAL_RESOURCE_COST_MUST_BE_POSITIVE")
    return (capability + efficiency + reliability) * breadth * generalization * success / costs


def rank_work(
    work: Sequence[Mapping[str, Any]],
    *,
    checkpoint_open_obligation_count: int | None = None,
) -> dict[str, Any]:
    if checkpoint_open_obligation_count is None:
        checkpoint_open_obligation_count = _current_open_obligation_count()
    if (
        isinstance(checkpoint_open_obligation_count, bool)
        or not isinstance(checkpoint_open_obligation_count, int)
        or checkpoint_open_obligation_count < 0
    ):
        raise CapabilityFirstSchedulerError("CHECKPOINT_OPEN_OBLIGATION_COUNT_INVALID")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in work:
        work_id = _s(raw.get("work_id"))
        if not work_id:
            raise CapabilityFirstSchedulerError("WORK_ID_REQUIRED")
        if work_id in seen:
            raise CapabilityFirstSchedulerError("WORK_ID_DUPLICATE:" + work_id)
        seen.add(work_id)

        eligible, eligibility = _eligible(raw, checkpoint_open_obligation_count)
        new_primitive_proof_complete, new_primitive_missing = _new_primitive_admission(raw)
        shared_residual_score, shared_residual_cause_ids = _shared_residual_fanout(raw)
        capability_score = _score(raw) if eligible else Fraction(0)
        if not eligible:
            shared_residual_score = Fraction(0)
        checkpoint_score = Fraction(0)
        if (
            eligible
            and checkpoint_open_obligation_count > 0
            and _has_load_bearing_path(raw)
        ):
            checkpoint_score = _load_bearing_score(raw)

        rows.append(
            {
                "work_id": work_id,
                "work_type": _s(raw.get("work_type")),
                "benchmark_role": _s(raw.get("benchmark_role")) or None,
                "scheduling_lane": _s(raw.get("scheduling_lane")) or None,
                "frontier_class": _s(raw.get("frontier_class")) or None,
                "claims_new_primitive": raw.get("claims_new_primitive") is True,
                "new_primitive_proof_complete": new_primitive_proof_complete,
                "new_primitive_missing_requirements": new_primitive_missing,
                "task_local_counterexample_ids": _ids(
                    raw, "task_local_counterexample_ids"
                ),
                "verified_capability_defect_ids": _ids(
                    raw, "verified_capability_defect_ids"
                ),
                "open_obligation_ids": _ids(raw, "open_obligation_ids"),
                "constructive_gap_for_open_obligation_ids": _ids(
                    raw, "constructive_gap_for_open_obligation_ids"
                ),
                "scope_complete_discharge": raw.get("scope_complete_discharge") is True,
                "shared_residual_cause_ids": shared_residual_cause_ids,
                "eligibility": eligibility,
                "capability_priority_score_fraction": capability_score,
                "shared_residual_fanout_score_fraction": shared_residual_score,
                "checkpoint_audit_score_fraction": checkpoint_score,
            }
        )

    # The real mission is lexicographically primary. Checkpoint/audit leverage is
    # only a secondary tie-breaker among work with equal capability/resource
    # leverage. This prevents an open milestone ledger from hijacking development.
    rows.sort(
        key=lambda x: (
            0 if x["eligibility"] == "ELIGIBLE" else 1,
            -x["capability_priority_score_fraction"],
            -x["shared_residual_fanout_score_fraction"],
            -x["checkpoint_audit_score_fraction"],
            x["work_id"],
        )
    )
    audit_active = checkpoint_open_obligation_count > 0
    return {
        "schema": SCHEMA,
        "status": (
            "CAPABILITY_FIRST_RANKING_WITH_CHECKPOINT_AUDIT"
            if audit_active
            else "CAPABILITY_FIRST_RANKING"
        ),
        "objective": "MAXIMIZE_REUSABLE_VERIFIED_CAPABILITY_GENERALIZATION_RELIABILITY_AND_EFFICIENCY_PER_RESOURCE",
        "mission_objective": MISSION_OBJECTIVE,
        "milestone": MILESTONE,
        "checkpoint_open_obligation_count": checkpoint_open_obligation_count,
        "load_bearing_primary_gate_active": False,
        "checkpoint_audit_active": audit_active,
        "primary_admission_rule": (
            "REUSABLE_CAPABILITY_RESOURCE_LEVERAGE_IS_PRIMARY__"
            "CURRENT_R2_SHARED_CAUSE_FANOUT_BREAKS_EQUAL_CAPABILITY_TIES__"
            "OPUS_CHECKPOINT_LEVERAGE_IS_TERTIARY_AUDIT_SIGNAL__"
            "BENCHMARK_BOOKKEEPING_REMAINS_DEMOTED__"
            "NEW_PRIMITIVE_CLAIMS_REQUIRE_REUSE_FIRST_EXHAUSTION_PROOF"
        ),
        "checkpoint_policy": (
            "OPEN_CHECKPOINT_OBLIGATIONS_DO_NOT_DEMOTE_GENERAL_CAPABILITY_WORK__"
            "CHECKPOINT_SCORE_BREAKS_TIES_ONLY"
        ),
        "reuse_first_policy": (
            "UNSUPPORTED_NEW_PRIMITIVE_CLAIMS_ARE_DEMOTED_TO_REUSE_ADAPTATION_"
            "PROMOTION_VERIFICATION_OR_EVIDENCE_ACQUISITION"
        ),
        "open_world_frontier_policy": (
            "GLOBAL_OPEN_WORLD_EVIDENCE_INCOMPLETENESS_IS_NOT_A_PRIMARY_"
            "CAPABILITY_DEFECT__WAKE_ONLY_ON_TASK_LOCAL_COUNTEREXAMPLE_OR_"
            "INDEPENDENTLY_VERIFIED_CAPABILITY_DEFECT"
        ),
        "option_preservation_policy": OPTION_PRESERVATION_POLICY,
        "optimization_rule": "OPTIMIZE_IMPLEMENTATIONS_NOT_POSSIBILITIES",
        "capability_learning_loop": list(CAPABILITY_LEARNING_LOOP),
        "ranked": [
            {
                "rank": i + 1,
                "work_id": row["work_id"],
                "work_type": row["work_type"],
                "benchmark_role": row["benchmark_role"],
                "scheduling_lane": row["scheduling_lane"],
                "frontier_class": row["frontier_class"],
                "claims_new_primitive": row["claims_new_primitive"],
                "new_primitive_proof_complete": row["new_primitive_proof_complete"],
                "new_primitive_missing_requirements": row["new_primitive_missing_requirements"],
                "task_local_counterexample_ids": row[
                    "task_local_counterexample_ids"
                ],
                "verified_capability_defect_ids": row[
                    "verified_capability_defect_ids"
                ],
                "open_obligation_ids": row["open_obligation_ids"],
                "constructive_gap_for_open_obligation_ids": row[
                    "constructive_gap_for_open_obligation_ids"
                ],
                "scope_complete_discharge": row["scope_complete_discharge"],
                "shared_residual_cause_ids": row["shared_residual_cause_ids"],
                "eligibility": row["eligibility"],
                "priority_score": str(row["capability_priority_score_fraction"]),
                "shared_residual_fanout_score": str(
                    row["shared_residual_fanout_score_fraction"]
                ),
                "checkpoint_audit_score": str(row["checkpoint_audit_score_fraction"]),
            }
            for i, row in enumerate(rows)
        ],
        "planning_only": True,
        "execution_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "physical_deletion_authority": False,
    }


def _validate_live_score_contract(work: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Fail closed unless live candidates share one verified evidence-bound score contract."""
    if not work:
        raise CapabilityFirstSchedulerError("LIVE_WORK_FRONTIER_EMPTY")

    calibration_ids: set[str] = set()
    frontier_ids: set[str] = set()
    verification_refs: set[str] = set()

    for raw in work:
        work_id = _s(raw.get("work_id"))
        if not work_id:
            raise CapabilityFirstSchedulerError("WORK_ID_REQUIRED")

        contract = raw.get("live_score_contract")
        if not isinstance(contract, Mapping):
            raise CapabilityFirstSchedulerError("LIVE_SCORE_CONTRACT_REQUIRED:" + work_id)
        if contract.get("dimensionless_normalized") is not True:
            raise CapabilityFirstSchedulerError("LIVE_SCORE_CONTRACT_NOT_DIMENSIONLESS:" + work_id)
        if _s(contract.get("scale")) != LIVE_SCORE_CONTRACT_SCALE:
            raise CapabilityFirstSchedulerError("LIVE_SCORE_CONTRACT_SCALE_INVALID:" + work_id)
        calibration_id = _s(contract.get("calibration_id"))
        frontier_id = _s(contract.get("frontier_id"))
        calibration_evidence = _s(contract.get("calibration_evidence_ref"))
        frontier_evidence = _s(contract.get("frontier_completeness_evidence_ref"))
        independent_verification = _s(contract.get("independent_verification_ref"))
        if not calibration_id:
            raise CapabilityFirstSchedulerError("LIVE_SCORE_CALIBRATION_ID_REQUIRED:" + work_id)
        if not frontier_id:
            raise CapabilityFirstSchedulerError("LIVE_WORK_FRONTIER_ID_REQUIRED:" + work_id)
        if not calibration_evidence:
            raise CapabilityFirstSchedulerError("LIVE_SCORE_CALIBRATION_EVIDENCE_REQUIRED:" + work_id)
        if contract.get("frontier_complete") is not True or not frontier_evidence:
            raise CapabilityFirstSchedulerError("LIVE_WORK_FRONTIER_COMPLETENESS_EVIDENCE_REQUIRED:" + work_id)
        if not independent_verification:
            raise CapabilityFirstSchedulerError("LIVE_SCORE_INDEPENDENT_VERIFICATION_REQUIRED:" + work_id)

        metric_evidence = contract.get("metric_evidence")
        if not isinstance(metric_evidence, Mapping):
            raise CapabilityFirstSchedulerError("LIVE_SCORE_METRIC_EVIDENCE_REQUIRED:" + work_id)
        missing = [field for field in LIVE_SCORE_FIELDS if not _s(metric_evidence.get(field))]
        if missing:
            raise CapabilityFirstSchedulerError(
                "LIVE_SCORE_METRIC_EVIDENCE_MISSING:" + work_id + ":" + ",".join(missing)
            )

        for field in LIVE_SCORE_FIELDS:
            _f(raw.get(field, 0), field)
        success = _f(raw.get("success_probability_lcb", 0), "success_probability_lcb")
        if success > 1:
            raise CapabilityFirstSchedulerError("SUCCESS_PROBABILITY_LCB_GT_ONE")

        calibration_ids.add(calibration_id)
        frontier_ids.add(frontier_id)
        verification_refs.add(independent_verification)

    if len(calibration_ids) != 1:
        raise CapabilityFirstSchedulerError("LIVE_SCORE_CALIBRATION_MISMATCH")
    if len(frontier_ids) != 1:
        raise CapabilityFirstSchedulerError("LIVE_WORK_FRONTIER_MISMATCH")
    if len(verification_refs) != 1:
        raise CapabilityFirstSchedulerError("LIVE_SCORE_VERIFICATION_MISMATCH")

    return {
        "calibration_id": next(iter(calibration_ids)),
        "frontier_id": next(iter(frontier_ids)),
        "independent_verification_ref": next(iter(verification_refs)),
        "scale": LIVE_SCORE_CONTRACT_SCALE,
    }


def rank_live_work(work: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Canonical live scheduler: provenance-gated before scalar ranking."""
    contract = _validate_live_score_contract(work)
    out = rank_work(work, checkpoint_open_obligation_count=_current_open_obligation_count())
    out["live_score_contract_verified"] = True
    out["live_score_contract"] = contract
    out["live_ranking_semantics"] = "ONLY_COMMON_DIMENSIONLESS_EVIDENCE_BOUND_COMPLETE_FRONTIER_SCORES_RANK"
    return out


_BENEFITS = ("capability", "generalization", "reliability")
_COSTS = ("latency", "compute", "memory", "incremental_spend_usd")


def _metrics(raw: Mapping[str, Any]) -> dict[str, Fraction]:
    return {k: _f(raw.get(k, 0), k) for k in (*_BENEFITS, *_COSTS)}


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_contract = _s(a.get("semantic_contract_sha256"))
    b_contract = _s(b.get("semantic_contract_sha256"))
    if a_contract and b_contract and a_contract != b_contract:
        return False
    am, bm = _metrics(a), _metrics(b)
    weak = all(am[k] >= bm[k] for k in _BENEFITS) and all(am[k] <= bm[k] for k in _COSTS)
    strict = any(am[k] > bm[k] for k in _BENEFITS) or any(am[k] < bm[k] for k in _COSTS)
    return weak and strict


def update_pareto_frontier(
    frontier: Sequence[Mapping[str, Any]], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    cid = _s(candidate.get("capability_id"))
    if not cid:
        raise CapabilityFirstSchedulerError("CAPABILITY_ID_REQUIRED")
    if candidate.get("reusable_capability") is not True:
        return {"admitted": False, "reason": "REUSABLE_CAPABILITY_REQUIRED", "frontier": list(frontier)}
    if candidate.get("independently_verified") is not True:
        return {"admitted": False, "reason": "INDEPENDENT_VERIFICATION_REQUIRED", "frontier": list(frontier)}
    _metrics(candidate)
    for incumbent in frontier:
        if _dominates(incumbent, candidate):
            return {
                "admitted": False,
                "reason": "DOMINATED_BY_EXISTING_FRONTIER",
                "dominated_by": _s(incumbent.get("capability_id")),
                "frontier": list(frontier),
                "preserve_candidate_evidence": True,
                "dominated_means_deleted": False,
                "physical_deletion_authority": False,
                "option_preservation_policy": OPTION_PRESERVATION_POLICY,
            }
    removed = [_s(x.get("capability_id")) for x in frontier if _dominates(candidate, x)]
    # "removed" is strictly active-frontier retirement. The implementation,
    # semantic contract, evidence, and reconstruction state remain preserved.
    # Permanent destruction is governed separately by
    # option_preserving_capability_optimizer_v1.
    kept = [dict(x) for x in frontier if not _dominates(candidate, x)]
    kept.append(dict(candidate))
    kept.sort(key=lambda x: _s(x.get("capability_id")))
    return {
        "admitted": True,
        "reason": "NONDOMINATED_VERIFIED_REUSABLE_CAPABILITY",
        "removed_dominated": removed,
        "retired_from_active_frontier": removed,
        "dominated_means_deleted": False,
        "physical_deletion_authority": False,
        "option_preservation_policy": OPTION_PRESERVATION_POLICY,
        "frontier": kept,
    }
