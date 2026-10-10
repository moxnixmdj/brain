"""Conflict-aware, option-preserving live work frontier controller.

This layer does not invent scalar trade-offs. It reuses the Brain's verified
option-preservation law at the work-scheduling level:

* stale source bindings fail closed,
* explicit dependencies gate readiness,
* evidence-complete work may be Pareto dominated only dimension-by-dimension,
* incomplete metric vectors are never treated as dominated,
* mutation/authority conflicts prevent simultaneous full execution,
* incomplete-vector work may run only as explicitly read-only evidence acquisition,
* incomparable conflicting work remains unresolved instead of receiving fake weights.

The output is a dispatch plan only. Downstream execution still requires the
candidate's own authority and lease machinery.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "PROJECT_BRAIN_CAPABILITY_PARALLEL_FRONTIER_V2"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_FRONTIER_PATH = ROOT / "canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json"
CURRENT_PROFESSIONAL_PATH = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
CURRENT_ASSURANCE_REL = "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
EXPECTED_ASSURANCE_PROMOTION_BLOCKERS = {
    "FULL_PRIVATE_CURRENT_MAIN_FULL_SYSTEM_REGRESSION",
    "DOMAIN_SEMANTIC_AND_EXECUTION_EVIDENCE_BINDING",
}
PROFESSIONAL_ROOT_NAMES = {
    1: "TARGET_SPECIFICATION",
    2: "CANDIDATE_SEARCH",
    3: "REALIZATION_OBSERVATION",
    4: "MEASUREMENT_CONSTRUCT",
    5: "EVALUATOR_REFERENCE",
    6: "EVIDENCE_GROUNDING_DEPENDENCE",
    7: "CAUSAL_PRESCRIPTIVE",
    8: "POPULATION_CONTEXT_OPERATOR",
    9: "TEMPORAL_DEPLOYMENT",
    10: "ANALYSIS_DECISION",
    11: "ADAPTIVE_INTEGRITY_SECURITY",
    12: "META_COMPOSITION_CLOSURE",
}
PROFESSIONAL_SOURCE_REL = "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
PROFESSIONAL_COMPOSITION_GATE_RUNTIME = "canonical/runtime/professional_quality_same_subject_composition_gate_v3.py"
PROFESSIONAL_COMPOSITION_GATE_RUNTIME_SHA = "ddbe6ec92fef405b8909a161ef9acd685ec7317b"
PROFESSIONAL_COMPOSITION_GATE_VERIFY = "canonical/verification/PROFESSIONAL_QUALITY_SAME_SUBJECT_GATE_V3_RECEIPT_ADAPTER_PUBLIC_VERIFY_20261010_V1.json"
PROFESSIONAL_COMPOSITION_GATE_VERIFY_SHA = "79910bf40700ddf000630a7169566fef91e6c939"

BENEFIT_INTERVALS = (
    ("expected_capability_gain_lcb", "expected_capability_gain_ucb"),
    ("expected_efficiency_gain_lcb", "expected_efficiency_gain_ucb"),
    ("expected_reliability_gain_lcb", "expected_reliability_gain_ucb"),
    ("reuse_breadth_lcb", "reuse_breadth_ucb"),
    ("generalization_lcb", "generalization_ucb"),
    ("success_probability_lcb", "success_probability_ucb"),
)
COST_INTERVALS = (
    ("wall_clock_cost_lcb", "wall_clock_cost_ub"),
    ("compute_cost_lcb", "compute_cost_ub"),
    ("memory_cost_lcb", "memory_cost_ub"),
    ("complexity_cost_lcb", "complexity_cost_ub"),
)
BENEFIT_FIELDS = tuple(field for pair in BENEFIT_INTERVALS for field in pair)
COST_FIELDS = tuple(field for pair in COST_INTERVALS for field in pair)
VECTOR_FIELDS = (*BENEFIT_FIELDS, *COST_FIELDS)
READY_STATES = {
    "READY_EXECUTION",
    "READY_PREACTIVATION",
    "READY_EVIDENCE",
}
NONPRIMARY_STATES = {
    "SLEEPING",
    "BLOCKED",
    "AUDIT_ONLY",
    "PARKED",
    "HISTORICAL",
}


class ParallelFrontierError(ValueError):
    pass


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def _ids(raw: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ParallelFrontierError(key.upper() + "_NOT_LIST")
    out = tuple(sorted({_s(x) for x in value if _s(x)}))
    return out


def _f(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ParallelFrontierError(name.upper() + "_INVALID")
    try:
        out = value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise ParallelFrontierError(name.upper() + "_INVALID") from exc
    if out < 0:
        raise ParallelFrontierError(name.upper() + "_NEGATIVE")
    return out


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(
        b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
    ).hexdigest()


def _current_professional_next_root(raw: Mapping[str, Any]) -> tuple[int, str]:
    frontier = raw.get("same_subject_root_binding_frontier")
    if not isinstance(frontier, Mapping):
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_FRONTIER_MISSING")
    count = frontier.get("verified_root_subject_binding_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 12:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_VERIFIED_COUNT_INVALID")
    if count >= 12:
        return 13, "COMPLETE"
    next_index = count + 1
    expected_name = PROFESSIONAL_ROOT_NAMES[next_index]
    next_text = _s(raw.get("next"))
    status = _s(raw.get("status"))
    if next_text and f"R{next_index}_" not in next_text:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_NEXT_ROOT_INCOHERENT")
    if status and f"__R{next_index}_NEXT" not in status:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_NEXT_ROOT_INCOHERENT")
    return next_index, expected_name


def refresh_supported_dynamic_sources(
    frontier: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Refresh only explicitly supported moving current-pointer families.

    Professional same-subject work advances frequently and has a strict,
    mechanically checkable sequential frontier. Assurance is a blocked dependent
    projection and may follow only when its subject identity, root count, next edge,
    authority boundary, and promotion blockers exactly match current Professional.
    All other source-family drift fails closed until an explicit adapter exists.
    """
    out = json.loads(json.dumps(frontier))
    source_set = out.get("scope", {}).get("source_set")
    if not isinstance(source_set, list):
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_SET_MISSING")

    source_row = next(
        (
            row
            for row in source_set
            if isinstance(row, Mapping)
            and _s(row.get("path")) == PROFESSIONAL_SOURCE_REL
        ),
        None,
    )
    if source_row is None:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_SOURCE_BINDING_MISSING")

    professional_path = root / PROFESSIONAL_SOURCE_REL
    if not professional_path.is_file():
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_SOURCE_UNAVAILABLE")
    actual_sha = _git_blob_sha(professional_path)
    professional_changed = _s(source_row.get("git_blob_sha")) != actual_sha

    try:
        professional = json.loads(professional_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_SOURCE_INVALID") from exc
    if not isinstance(professional, Mapping):
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_SOURCE_INVALID")

    next_index, next_name = _current_professional_next_root(professional)
    candidates = out.get("candidates")
    if not isinstance(candidates, list):
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATES_INVALID")
    positions = [
        i
        for i, row in enumerate(candidates)
        if isinstance(row, Mapping)
        and (
            _s(row.get("work_id")).startswith("PROFESSIONAL_QUALITY_V7_R")
            or _s(row.get("work_id")) in {
                "PROFESSIONAL_QUALITY_V7_SAME_SUBJECT_BINDINGS_COMPLETE",
                "PROFESSIONAL_QUALITY_V7_SAME_SUBJECT_COMPOSITION_GATE",
            }
        )
    ]
    if len(positions) != 1:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_CANDIDATE_CARDINALITY_INVALID")
    i = positions[0]

    expected_id = (
        "PROFESSIONAL_QUALITY_V7_SAME_SUBJECT_COMPOSITION_GATE"
        if next_index == 13
        else "PROFESSIONAL_QUALITY_V7_R" + str(next_index) + "_" + next_name + "_BINDING"
    )
    if professional_changed:
        source_row["git_blob_sha"] = actual_sha
        if next_index == 13:
            row = dict(candidates[i])
            row.update(
                {
                    "work_id": expected_id,
                    "work_type": "RELIABILITY_IMPROVEMENT",
                    "causal_role": (
                        "VERIFY_ALL_12_INDEPENDENT_ROOT_SUBJECT_BINDINGS_COMPOSE_"
                        "TO_THE_SAME_FROZEN_V7_SUBJECT__UPSTREAM_OF_DOMAIN_LEVEL_"
                        "CHALLENGES_AND_REMAINING_SEMANTIC_EXECUTION_EVIDENCE"
                    ),
                    "scheduler_state": "READY_EVIDENCE",
                    "prerequisites_satisfied": True,
                    "prerequisite_work_ids": [],
                    "readiness": (
                        "ALL_12_ROOT_BINDINGS_COMPLETE__RUN_VERIFIED_V3_"
                        "SAME_SUBJECT_COMPOSITION_GATE_READ_ONLY"
                    ),
                    "mutation_keys": ["canonical:professional-quality"],
                    "authority_keys": ["authority:professional-v7-composition"],
                    "explicit_conflict_work_ids": [],
                    "evidence_conflict_keys": [],
                    "evidence_acquisition_mode": "READ_ONLY",
                    "vector_evidence_state": "PARTIAL",
                    "vector_evidence": {},
                }
            )
            row["read_only_evidence"] = {
                "source": PROFESSIONAL_SOURCE_REL,
                "source_git_blob_sha": actual_sha,
                "verified_root_subject_binding_count": 12,
                "required_root_count": 12,
                "next_action": "RUN_SAME_SUBJECT_COMPOSITION_GATE",
                "composition_gate_runtime": PROFESSIONAL_COMPOSITION_GATE_RUNTIME,
                "composition_gate_runtime_git_blob_sha": PROFESSIONAL_COMPOSITION_GATE_RUNTIME_SHA,
                "composition_gate_independent_verification": PROFESSIONAL_COMPOSITION_GATE_VERIFY,
                "composition_gate_independent_verification_git_blob_sha": PROFESSIONAL_COMPOSITION_GATE_VERIFY_SHA,
                "composition_gate_authority_boundary": (
                    "READ_ONLY_COMPOSITION_ADMISSIBILITY_ONLY__NO_QUALITY_"
                    "ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY"
                ),
                "vector_bounds_complete": False,
                "dynamic_current_pointer_follow": True,
            }
            candidates[i] = row
        else:
            row = dict(candidates[i])
            row["work_id"] = expected_id
            row["causal_role"] = (
                "NEXT_EXACT_SAME_SUBJECT_BINDING_EDGE__R"
                + str(next_index)
                + "_"
                + next_name
                + "__UPSTREAM_OF_REMAINING_COMPOSITION_AND_DOMAIN_EVIDENCE"
            )
            row["readiness"] = (
                "ACTIONABLE_ON_CURRENT_V7_SUBJECT_AFTER_R1_R"
                + str(next_index - 1)
                + "_VERIFIED"
            )
            row["scheduler_state"] = "READY_EXECUTION"
            row["prerequisites_satisfied"] = True
            row["vector_evidence_state"] = "PARTIAL"
            row["vector_evidence"] = {}
            evidence = dict(row.get("read_only_evidence") or {})
            evidence.update(
                {
                    "source": PROFESSIONAL_SOURCE_REL,
                    "source_git_blob_sha": actual_sha,
                    "verified_root_subject_binding_count": next_index - 1,
                    "required_root_count": 12,
                    "next_root": "R" + str(next_index) + "_" + next_name,
                    "vector_bounds_complete": False,
                    "dynamic_current_pointer_follow": True,
                }
            )
            row["read_only_evidence"] = evidence
            candidates[i] = row
    elif _s(candidates[i].get("work_id")) != expected_id:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_CANDIDATE_NOT_ALIGNED")

    findings = out.get("currentness_findings")
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict) and finding.get("id") == "PROFESSIONAL_CURRENT":
                finding["truth"] = (
                    "R1_R12_V7_BINDINGS_VERIFIED__12_OF_12__SAME_SUBJECT_COMPOSITION_GATE_NEXT"
                    if next_index == 13
                    else "R1_R"
                    + str(next_index - 1)
                    + "_V7_BINDINGS_VERIFIED__"
                    + str(next_index - 1)
                    + "_OF_12__R"
                    + str(next_index)
                    + "_NEXT"
                )
                finding["source"] = PROFESSIONAL_SOURCE_REL
                finding["dynamic_current_pointer_follow"] = True

    out["dynamic_currentness"] = {
        "professional_current_pointer_follow": True,
        "professional_current_git_blob_sha": actual_sha,
        "professional_next_root": (
            "SAME_SUBJECT_COMPOSITION_GATE"
            if next_index == 13
            else "R" + str(next_index) + "_" + next_name
        ),
        "assurance_current_pointer_follow": False,
        "other_source_families_dynamic_follow": False,
    }
    _refresh_assurance_currentness(
        out,
        professional,
        actual_sha,
        root=root,
    )
    return out

def _refresh_assurance_currentness(
    frontier: dict[str, Any],
    professional: Mapping[str, Any],
    professional_sha: str,
    *,
    root: Path,
) -> None:
    source_set = frontier.get("scope", {}).get("source_set")
    if not isinstance(source_set, list):
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_SET_MISSING")
    source_row = next(
        (
            row
            for row in source_set
            if isinstance(row, Mapping) and _s(row.get("path")) == CURRENT_ASSURANCE_REL
        ),
        None,
    )
    if source_row is None:
        raise ParallelFrontierError("CURRENT_ASSURANCE_SOURCE_BINDING_MISSING")

    assurance_path = root / CURRENT_ASSURANCE_REL
    if not assurance_path.is_file():
        raise ParallelFrontierError("CURRENT_ASSURANCE_SOURCE_UNAVAILABLE")
    try:
        assurance = json.loads(assurance_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ParallelFrontierError("CURRENT_ASSURANCE_SOURCE_INVALID") from exc
    if not isinstance(assurance, Mapping):
        raise ParallelFrontierError("CURRENT_ASSURANCE_SOURCE_INVALID")
    if _s(assurance.get("schema")) != "PROJECT_BRAIN_CURRENT_ASSURANCE_CLOSURE_COMPILER_POINTER_V1":
        raise ParallelFrontierError("CURRENT_ASSURANCE_SCHEMA_INVALID")
    if assurance.get("terminal_authority") is not False or assurance.get("live_default") is not False:
        raise ParallelFrontierError("CURRENT_ASSURANCE_AUTHORITY_BOUNDARY_CHANGED")

    activation = assurance.get("activation")
    if not isinstance(activation, Mapping) or activation.get("live_default") is not False:
        raise ParallelFrontierError("CURRENT_ASSURANCE_ACTIVATION_INVALID")
    blockers = activation.get("required_before_promotion")
    normalized_blockers = {_s(x) for x in blockers} if isinstance(blockers, list) else set()
    if normalized_blockers != EXPECTED_ASSURANCE_PROMOTION_BLOCKERS:
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROMOTION_BLOCKERS_CHANGED")

    prof_frontier = professional.get("same_subject_root_binding_frontier")
    final_subject = professional.get("final_subject")
    if not isinstance(prof_frontier, Mapping) or not isinstance(final_subject, Mapping):
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_IDENTITY_INCOMPLETE")
    count = prof_frontier.get("verified_root_subject_binding_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 12:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_VERIFIED_COUNT_INVALID")
    subject_id = _s(final_subject.get("subject_id"))
    subject_sha = _s(final_subject.get("subject_sha256"))
    if not subject_id or not subject_sha:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_SUBJECT_IDENTITY_MISSING")

    projection = assurance.get("professional_quality_same_subject_frontier")
    if not isinstance(projection, Mapping):
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROFESSIONAL_PROJECTION_MISSING")
    if _s(projection.get("subject_id")) != subject_id or _s(projection.get("subject_sha256")) != subject_sha:
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROFESSIONAL_SUBJECT_MISMATCH")
    if projection.get("verified_root_subject_binding_count") != count:
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROFESSIONAL_COUNT_MISMATCH")
    if projection.get("root_count") != 12:
        raise ParallelFrontierError("CURRENT_ASSURANCE_ROOT_COUNT_INVALID")

    status = _s(assurance.get("status"))
    if "__" + str(count) + "_OF_12_CURRENT_ROOT_SUBJECT_BINDINGS__" not in status:
        raise ParallelFrontierError("CURRENT_ASSURANCE_STATUS_COUNT_MISMATCH")
    next_index, next_name = _current_professional_next_root(professional)
    if next_index <= 12:
        expected_next = "R" + str(next_index) + "_" + next_name
        if expected_next not in _s(projection.get("next")):
            raise ParallelFrontierError("CURRENT_ASSURANCE_NEXT_ROOT_MISMATCH")
        if "__R" + str(next_index) + "_" not in status:
            raise ParallelFrontierError("CURRENT_ASSURANCE_STATUS_NEXT_ROOT_MISMATCH")
    else:
        expected_next = "COMPOSITION"
        if "COMPOSITION" not in _s(projection.get("next")).upper():
            raise ParallelFrontierError("CURRENT_ASSURANCE_NEXT_COMPOSITION_MISMATCH")

    actual_sha = _git_blob_sha(assurance_path)
    source_row["git_blob_sha"] = actual_sha

    candidates = frontier.get("candidates")
    if not isinstance(candidates, list):
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATES_INVALID")
    positions = [
        i
        for i, row in enumerate(candidates)
        if isinstance(row, Mapping)
        and _s(row.get("work_id")) == "ASSURANCE_UVCK_V2_PROMOTION_GATES"
    ]
    if len(positions) != 1:
        raise ParallelFrontierError("CURRENT_ASSURANCE_CANDIDATE_CARDINALITY_INVALID")
    row = dict(candidates[positions[0]])
    evidence = dict(row.get("read_only_evidence") or {})
    evidence.update(
        {
            "source": CURRENT_ASSURANCE_REL,
            "source_git_blob_sha": actual_sha,
            "promotion_blockers": sorted(EXPECTED_ASSURANCE_PROMOTION_BLOCKERS),
            "embedded_professional_snapshot_lags_live_frontier": False,
            "professional_verified_root_subject_binding_count": count,
            "professional_current_git_blob_sha": professional_sha,
            "professional_next": expected_next,
            "vector_bounds_complete": False,
            "dynamic_current_pointer_follow": True,
        }
    )
    row["read_only_evidence"] = evidence
    candidates[positions[0]] = row

    findings = frontier.get("currentness_findings")
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict) and finding.get("id") == "ASSURANCE_CURRENT_PATH":
                finding["truth"] = (
                    "UVCK_V2_CURRENT_POINTER_COHERENT_WITH_PROFESSIONAL_"
                    + str(count)
                    + "_OF_12__"
                    + expected_next
                    + "_NEXT__PROMOTION_REMAINS_BLOCKED"
                )
                finding["source"] = CURRENT_ASSURANCE_REL
                finding["dynamic_current_pointer_follow"] = True

    dynamic = frontier.setdefault("dynamic_currentness", {})
    if not isinstance(dynamic, dict):
        raise ParallelFrontierError("DYNAMIC_CURRENTNESS_NOT_OBJECT")
    dynamic.update(
        {
            "assurance_current_pointer_follow": True,
            "assurance_current_git_blob_sha": actual_sha,
            "assurance_professional_count": count,
            "assurance_professional_next": expected_next,
        }
    )

def load_current_frontier(
    frontier_path: Path = CURRENT_FRONTIER_PATH,
) -> dict[str, Any]:
    try:
        raw = json.loads(frontier_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_UNAVAILABLE") from exc
    if not isinstance(raw, dict):
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_NOT_OBJECT")
    return raw


def verify_frontier_currentness(
    frontier: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    frontier_id = _s(frontier.get("frontier_id"))
    if not frontier_id:
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_ID_MISSING")
    source_set = frontier.get("scope", {}).get("source_set")
    if not isinstance(source_set, list) or not source_set:
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_SET_MISSING")

    stale: list[str] = []
    for row in source_set:
        if not isinstance(row, Mapping):
            raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_SET_INVALID")
        rel = _s(row.get("path"))
        expected = _s(row.get("git_blob_sha"))
        if not rel or not expected:
            raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_BINDING_INVALID")
        path = root / rel
        if not path.is_file() or _git_blob_sha(path) != expected:
            stale.append(rel)
    if stale:
        raise ParallelFrontierError(
            "LIVE_WORK_FRONTIER_STALE:" + ",".join(sorted(stale))
        )
    return {
        "frontier_id": frontier_id,
        "source_count": len(source_set),
        "currentness_verified": True,
    }


def _candidate(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ParallelFrontierError("CANDIDATE_NOT_OBJECT")
    out = dict(raw)
    work_id = _s(out.get("work_id"))
    if not work_id:
        raise ParallelFrontierError("WORK_ID_REQUIRED")
    scheduler_state = _s(out.get("scheduler_state"))
    if scheduler_state not in READY_STATES | NONPRIMARY_STATES:
        raise ParallelFrontierError("SCHEDULER_STATE_INVALID:" + work_id)
    out["work_id"] = work_id
    out["scheduler_state"] = scheduler_state
    out["prerequisite_work_ids"] = list(_ids(out, "prerequisite_work_ids"))
    out["mutation_keys"] = list(_ids(out, "mutation_keys"))
    out["authority_keys"] = list(_ids(out, "authority_keys"))
    out["explicit_conflict_work_ids"] = list(_ids(out, "explicit_conflict_work_ids"))
    out["evidence_conflict_keys"] = list(_ids(out, "evidence_conflict_keys"))
    if out.get("prerequisites_satisfied") is not True and scheduler_state in READY_STATES:
        raise ParallelFrontierError("READY_CANDIDATE_PREREQUISITES_NOT_SATISFIED:" + work_id)
    mode = _s(out.get("evidence_acquisition_mode"))
    if mode not in {"READ_ONLY", "MUTATING", "NONE"}:
        raise ParallelFrontierError("EVIDENCE_ACQUISITION_MODE_INVALID:" + work_id)
    out["evidence_acquisition_mode"] = mode
    return out


def _vector_complete(raw: Mapping[str, Any]) -> bool:
    if _s(raw.get("vector_evidence_state")) != "COMPLETE":
        return False
    evidence = raw.get("vector_evidence")
    if not isinstance(evidence, Mapping):
        return False
    for field in VECTOR_FIELDS:
        if field not in raw or not _s(evidence.get(field)):
            return False
        _f(raw[field], field)

    for lcb_field, ucb_field in BENEFIT_INTERVALS:
        lcb = _f(raw[lcb_field], lcb_field)
        ucb = _f(raw[ucb_field], ucb_field)
        if lcb > ucb:
            raise ParallelFrontierError(
                "BENEFIT_INTERVAL_INVERTED:" + lcb_field + ":" + ucb_field
            )

    for lcb_field, ucb_field in COST_INTERVALS:
        lcb = _f(raw[lcb_field], lcb_field)
        ucb = _f(raw[ucb_field], ucb_field)
        if lcb > ucb:
            raise ParallelFrontierError(
                "COST_INTERVAL_INVERTED:" + lcb_field + ":" + ucb_field
            )

    success_lcb = _f(raw["success_probability_lcb"], "success_probability_lcb")
    success_ucb = _f(raw["success_probability_ucb"], "success_probability_ucb")
    if success_lcb > 1 or success_ucb > 1:
        raise ParallelFrontierError("SUCCESS_PROBABILITY_BOUND_GT_ONE")
    return True


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Return true only for interval-robust dominance.

    A dominates B only when A's worst admissible benefit is at least B's best
    admissible benefit on every benefit dimension, and A's worst admissible
    cost is at most B's best admissible cost on every cost dimension.  This
    prevents lower-bound-vs-lower-bound or upper-bound-vs-upper-bound pruning
    from converting uncertainty into fake certainty.
    """
    if not (_vector_complete(a) and _vector_complete(b)):
        return False

    benefit_weak = all(
        _f(a[lcb], lcb) >= _f(b[ucb], ucb)
        for lcb, ucb in BENEFIT_INTERVALS
    )
    cost_weak = all(
        _f(a[ucb], ucb) <= _f(b[lcb], lcb)
        for lcb, ucb in COST_INTERVALS
    )
    strict = any(
        _f(a[lcb], lcb) > _f(b[ucb], ucb)
        for lcb, ucb in BENEFIT_INTERVALS
    ) or any(
        _f(a[ucb], ucb) < _f(b[lcb], lcb)
        for lcb, ucb in COST_INTERVALS
    )
    return benefit_weak and cost_weak and strict


def _full_conflict(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    aid, bid = _s(a.get("work_id")), _s(b.get("work_id"))
    if bid in set(_ids(a, "explicit_conflict_work_ids")):
        return True
    if aid in set(_ids(b, "explicit_conflict_work_ids")):
        return True
    if set(_ids(a, "mutation_keys")) & set(_ids(b, "mutation_keys")):
        return True
    if set(_ids(a, "authority_keys")) & set(_ids(b, "authority_keys")):
        return True
    return False


def _evidence_conflict(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return bool(
        set(_ids(a, "evidence_conflict_keys"))
        & set(_ids(b, "evidence_conflict_keys"))
    )


def _components(
    rows: Sequence[Mapping[str, Any]],
    conflict_fn,
) -> list[list[dict[str, Any]]]:
    by_id = {_s(row.get("work_id")): dict(row) for row in rows}
    unseen = set(by_id)
    result: list[list[dict[str, Any]]] = []
    while unseen:
        seed = min(unseen)
        stack = [seed]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            unseen.discard(current)
            for other in list(unseen):
                if conflict_fn(by_id[current], by_id[other]):
                    stack.append(other)
        result.append([by_id[x] for x in sorted(component)])
    return result


def plan_current_parallel_frontier() -> dict[str, Any]:
    """Canonical current-frontier planning entrypoint with bounded dynamic follow."""
    frontier = refresh_supported_dynamic_sources(load_current_frontier())
    return plan_parallel_frontier(frontier)



def plan_parallel_frontier(
    frontier: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    currentness = verify_frontier_currentness(frontier, root=root)
    raw_candidates = frontier.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATES_INVALID")
    rows = [_candidate(row) for row in raw_candidates]
    ids = [row["work_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ParallelFrontierError("WORK_ID_DUPLICATE")

    ready = [row for row in rows if row["scheduler_state"] in READY_STATES]
    nonprimary = [row for row in rows if row["scheduler_state"] in NONPRIMARY_STATES]

    complete = [row for row in ready if _vector_complete(row)]
    incomplete = [row for row in ready if not _vector_complete(row)]

    dominated_by: dict[str, list[str]] = {}
    for row in complete:
        dominators = [
            other["work_id"]
            for other in complete
            if other["work_id"] != row["work_id"] and _dominates(other, row)
        ]
        if dominators:
            dominated_by[row["work_id"]] = sorted(dominators)

    nondominated_complete = [
        row for row in complete if row["work_id"] not in dominated_by
    ]

    execution_components = _components(nondominated_complete, _full_conflict)
    parallel_execution: list[str] = []
    unresolved_execution_components: list[list[str]] = []
    for component in execution_components:
        if len(component) == 1:
            parallel_execution.append(component[0]["work_id"])
        else:
            unresolved_execution_components.append(
                sorted(row["work_id"] for row in component)
            )

    evidence_rows = [
        row
        for row in incomplete
        if row["evidence_acquisition_mode"] == "READ_ONLY"
    ]
    evidence_components = _components(evidence_rows, _evidence_conflict)
    parallel_evidence: list[str] = []
    unresolved_evidence_components: list[list[str]] = []
    for component in evidence_components:
        if len(component) == 1:
            parallel_evidence.append(component[0]["work_id"])
        else:
            unresolved_evidence_components.append(
                sorted(row["work_id"] for row in component)
            )

    mutating_incomplete = sorted(
        row["work_id"]
        for row in incomplete
        if row["evidence_acquisition_mode"] != "READ_ONLY"
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PARALLEL_FRONTIER_PLAN_READY"
            if parallel_execution or parallel_evidence
            else "OPEN__NO_SAFE_PARALLEL_DISPATCH"
        ),
        "frontier_id": currentness["frontier_id"],
        "frontier_currentness": currentness,
        "ready_candidate_ids": sorted(row["work_id"] for row in ready),
        "nonprimary_candidate_ids": sorted(row["work_id"] for row in nonprimary),
        "vector_complete_candidate_ids": sorted(row["work_id"] for row in complete),
        "vector_incomplete_candidate_ids": sorted(row["work_id"] for row in incomplete),
        "dominated_by": dominated_by,
        "nondominated_complete_candidate_ids": sorted(
            row["work_id"] for row in nondominated_complete
        ),
        "parallel_full_execution_work_ids": sorted(parallel_execution),
        "parallel_read_only_evidence_work_ids": sorted(parallel_evidence),
        "unresolved_full_execution_conflict_components": sorted(
            unresolved_execution_components
        ),
        "unresolved_evidence_conflict_components": sorted(
            unresolved_evidence_components
        ),
        "mutating_incomplete_vector_work_ids": mutating_incomplete,
        "selection_law": (
            "INTERVAL_ROBUST_PARETO_DOMINANCE_ONLY_WHEN_ALL_LOWER_AND_UPPER_VECTOR_BOUNDS_HAVE_EVIDENCE__"
            "NO_SCALAR_WEIGHTS_INVENTED__"
            "NONCONFLICTING_NONDOMINATED_COMPLETE_WORK_MAY_RUN_IN_PARALLEL__"
            "INCOMPLETE_VECTOR_WORK_IS_EVIDENCE_ONLY_AND_READ_ONLY_OR_FAILS_CLOSED__"
            "CONFLICTING_INCOMPARABLE_WORK_REQUIRES_MINIMUM_DISCRIMINATING_EVIDENCE"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
