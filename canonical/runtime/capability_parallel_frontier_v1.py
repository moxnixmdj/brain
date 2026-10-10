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


SCHEMA = "PROJECT_BRAIN_CAPABILITY_PARALLEL_FRONTIER_V1"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_FRONTIER_PATH = ROOT / "canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json"
CURRENT_PROFESSIONAL_PATH = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
CURRENT_ASSURANCE_PATH = ROOT / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
ASSURANCE_SOURCE_REL = "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
ASSURANCE_WORK_ID = "ASSURANCE_UVCK_V2_PROMOTION_GATES"
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

BENEFIT_FIELDS = (
    "expected_capability_gain_lcb",
    "expected_efficiency_gain_lcb",
    "expected_reliability_gain_lcb",
    "reuse_breadth_lcb",
    "generalization_lcb",
    "success_probability_lcb",
)
COST_FIELDS = (
    "wall_clock_cost_ub",
    "compute_cost_ub",
    "memory_cost_ub",
    "complexity_cost_ub",
)
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


def _load_mapping(path: Path, code: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ParallelFrontierError(code) from exc
    if not isinstance(raw, dict):
        raise ParallelFrontierError(code)
    return raw


def _validate_assurance_professional_mirror(
    assurance: Mapping[str, Any],
    professional: Mapping[str, Any],
    professional_blob_sha: str,
) -> dict[str, Any]:
    if assurance.get("live_default") is not False or assurance.get("terminal_authority") is not False:
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROMOTION_STATE_CHANGED")

    prof_frontier = professional.get("same_subject_root_binding_frontier")
    if not isinstance(prof_frontier, Mapping):
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_FRONTIER_MISSING")
    verified = prof_frontier.get("verified_root_subject_binding_count")
    root_count = prof_frontier.get("root_count")
    if (
        isinstance(verified, bool)
        or not isinstance(verified, int)
        or isinstance(root_count, bool)
        or not isinstance(root_count, int)
        or verified < 0
        or root_count != 12
        or verified > root_count
    ):
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_VERIFIED_COUNT_INVALID")

    next_index, next_name = _current_professional_next_root(professional)
    mirror = assurance.get("professional_quality_same_subject_frontier")
    if not isinstance(mirror, Mapping):
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROFESSIONAL_MIRROR_MISSING")
    if _s(mirror.get("current_professional_execution_path")) != PROFESSIONAL_SOURCE_REL:
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROFESSIONAL_PATH_DRIFT")
    if _s(mirror.get("current_professional_execution_git_blob_sha")) != professional_blob_sha:
        raise ParallelFrontierError("CURRENT_ASSURANCE_PROFESSIONAL_BLOB_STALE")

    worklist = mirror.get("root_binding_worklist")
    if not isinstance(worklist, Mapping):
        raise ParallelFrontierError("CURRENT_ASSURANCE_WORKLIST_MISSING")
    expected_worklist_path = _s(prof_frontier.get("path"))
    expected_worklist_sha = _s(prof_frontier.get("git_blob_sha"))
    if (
        _s(worklist.get("path")) != expected_worklist_path
        or _s(worklist.get("git_blob_sha")) != expected_worklist_sha
        or worklist.get("required_root_count") != root_count
        or worklist.get("verified_root_subject_binding_count") != verified
        or worklist.get("composition_admissible") is not (
            prof_frontier.get("composition_admissible") is True
        )
    ):
        raise ParallelFrontierError("CURRENT_ASSURANCE_WORKLIST_DRIFT")

    if (
        mirror.get("verified_root_subject_binding_count") != verified
        or mirror.get("root_count") != root_count
        or mirror.get("composition_admissible") is not (
            prof_frontier.get("composition_admissible") is True
        )
    ):
        raise ParallelFrontierError("CURRENT_ASSURANCE_FRONTIER_COUNT_DRIFT")

    expected_next = "COMPLETE" if next_index == 13 else f"R{next_index}_{next_name}"
    if _s(mirror.get("next")) != expected_next:
        raise ParallelFrontierError("CURRENT_ASSURANCE_NEXT_ROOT_DRIFT")

    bindings = mirror.get("current_verified_root_bindings")
    if not isinstance(bindings, Mapping):
        raise ParallelFrontierError("CURRENT_ASSURANCE_VERIFIED_BINDINGS_MISSING")
    expected_keys = {
        f"R{i}_{PROFESSIONAL_ROOT_NAMES[i]}" for i in range(1, verified + 1)
    }
    if set(bindings) != expected_keys:
        raise ParallelFrontierError("CURRENT_ASSURANCE_VERIFIED_BINDING_SET_DRIFT")
    for i in range(1, verified + 1):
        key = f"R{i}_{PROFESSIONAL_ROOT_NAMES[i]}"
        mirror_row = bindings.get(key)
        source_row = professional.get(f"r{i}_root_subject_binding")
        if not isinstance(mirror_row, Mapping) or not isinstance(source_row, Mapping):
            raise ParallelFrontierError("CURRENT_ASSURANCE_VERIFIED_BINDING_INVALID:" + key)
        for field in (
            "binding_path",
            "binding_git_blob_sha",
            "verification_path",
            "verification_git_blob_sha",
        ):
            if _s(mirror_row.get(field)) != _s(source_row.get(field)):
                raise ParallelFrontierError(
                    "CURRENT_ASSURANCE_VERIFIED_BINDING_DRIFT:" + key + ":" + field
                )

    status = _s(assurance.get("status"))
    if f"__{verified}_OF_{root_count}_CURRENT_ROOT_SUBJECT_BINDINGS" not in status:
        raise ParallelFrontierError("CURRENT_ASSURANCE_TOP_LEVEL_COUNT_DRIFT")
    if next_index != 13:
        next_marker = f"__R{next_index}"
        marker_pos = status.find(next_marker)
        if marker_pos < 0 or "_NEXT" not in status[marker_pos:]:
            raise ParallelFrontierError("CURRENT_ASSURANCE_TOP_LEVEL_NEXT_DRIFT")

    return {
        "verified_root_subject_binding_count": verified,
        "required_root_count": root_count,
        "next_root": expected_next,
        "composition_admissible": prof_frontier.get("composition_admissible") is True,
    }


def refresh_supported_dynamic_sources(
    frontier: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Refresh explicitly supported moving current-pointer families.

    Professional same-subject work is mechanically sequential. Assurance is a
    derived mirror of that same subject and may follow only when every mirrored
    root binding, worklist binding, count, next edge, and non-promotion state
    agrees with the authoritative professional pointer. Any other source drift
    still fails closed.
    """
    out = json.loads(json.dumps(frontier))
    source_set = out.get("scope", {}).get("source_set")
    if not isinstance(source_set, list):
        raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_SET_MISSING")

    professional_rows = [
        row for row in source_set
        if isinstance(row, Mapping) and _s(row.get("path")) == PROFESSIONAL_SOURCE_REL
    ]
    if len(professional_rows) != 1:
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_SOURCE_BINDING_MISSING")
    professional_source_row = professional_rows[0]

    professional_path = root / PROFESSIONAL_SOURCE_REL
    if not professional_path.is_file():
        raise ParallelFrontierError("CURRENT_PROFESSIONAL_SOURCE_UNAVAILABLE")
    professional = _load_mapping(
        professional_path, "CURRENT_PROFESSIONAL_SOURCE_INVALID"
    )
    actual_prof_sha = _git_blob_sha(professional_path)
    next_index, next_name = _current_professional_next_root(professional)

    if _s(professional_source_row.get("git_blob_sha")) != actual_prof_sha:
        professional_source_row["git_blob_sha"] = actual_prof_sha
        candidates = out.get("candidates")
        if not isinstance(candidates, list):
            raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATES_INVALID")
        positions = [
            i for i, row in enumerate(candidates)
            if isinstance(row, Mapping)
            and _s(row.get("work_id")).startswith("PROFESSIONAL_QUALITY_V7_R")
        ]
        if len(positions) != 1:
            raise ParallelFrontierError("CURRENT_PROFESSIONAL_CANDIDATE_CARDINALITY_INVALID")
        i = positions[0]
        if next_index == 13:
            candidates[i] = {
                **dict(candidates[i]),
                "work_id": "PROFESSIONAL_QUALITY_V7_SAME_SUBJECT_BINDINGS_COMPLETE",
                "scheduler_state": "BLOCKED",
                "prerequisites_satisfied": False,
                "readiness": "ALL_12_ROOT_BINDINGS_COMPLETE__COMPOSITION_GATE_NEXT_OUTSIDE_THIS_DYNAMIC_ADAPTER",
                "vector_evidence_state": "UNBOUND",
                "vector_evidence": {},
            }
        else:
            row = dict(candidates[i])
            row["work_id"] = f"PROFESSIONAL_QUALITY_V7_R{next_index}_{next_name}_BINDING"
            row["causal_role"] = (
                f"NEXT_EXACT_SAME_SUBJECT_BINDING_EDGE__R{next_index}_"
                f"{next_name}__UPSTREAM_OF_REMAINING_COMPOSITION_AND_DOMAIN_EVIDENCE"
            )
            row["readiness"] = (
                f"ACTIONABLE_ON_CURRENT_V7_SUBJECT_AFTER_R1_R{next_index - 1}_VERIFIED"
            )
            row["scheduler_state"] = "READY_EXECUTION"
            row["prerequisites_satisfied"] = True
            row["vector_evidence_state"] = "PARTIAL"
            row["vector_evidence"] = {}
            evidence = dict(row.get("read_only_evidence") or {})
            evidence.update(
                {
                    "source": PROFESSIONAL_SOURCE_REL,
                    "source_git_blob_sha": actual_prof_sha,
                    "verified_root_subject_binding_count": next_index - 1,
                    "required_root_count": 12,
                    "next_root": f"R{next_index}_{next_name}",
                    "vector_bounds_complete": False,
                    "dynamic_current_pointer_follow": True,
                }
            )
            row["read_only_evidence"] = evidence
            candidates[i] = row

        findings = out.get("currentness_findings")
        if isinstance(findings, list):
            for finding in findings:
                if isinstance(finding, dict) and finding.get("id") == "PROFESSIONAL_CURRENT":
                    finding["truth"] = (
                        "R1_R12_V7_BINDINGS_VERIFIED__12_OF_12__COMPOSITION_NEXT"
                        if next_index == 13
                        else f"R1_R{next_index - 1}_V7_BINDINGS_VERIFIED__{next_index - 1}_OF_12__R{next_index}_NEXT"
                    )
                    finding["source"] = PROFESSIONAL_SOURCE_REL
                    finding["dynamic_current_pointer_follow"] = True

    assurance_rows = [
        row for row in source_set
        if isinstance(row, Mapping) and _s(row.get("path")) == ASSURANCE_SOURCE_REL
    ]
    assurance_followed = False
    assurance_sha = None
    if assurance_rows:
        if len(assurance_rows) != 1:
            raise ParallelFrontierError("CURRENT_ASSURANCE_SOURCE_BINDING_INVALID")
        assurance_path = root / ASSURANCE_SOURCE_REL
        if not assurance_path.is_file():
            raise ParallelFrontierError("CURRENT_ASSURANCE_SOURCE_UNAVAILABLE")
        assurance = _load_mapping(
            assurance_path, "CURRENT_ASSURANCE_SOURCE_INVALID"
        )
        assurance_sha = _git_blob_sha(assurance_path)
        assurance_snapshot = _validate_assurance_professional_mirror(
            assurance, professional, actual_prof_sha
        )
        assurance_row = assurance_rows[0]
        if _s(assurance_row.get("git_blob_sha")) != assurance_sha:
            assurance_row["git_blob_sha"] = assurance_sha
            assurance_followed = True
            candidates = out.get("candidates")
            if not isinstance(candidates, list):
                raise ParallelFrontierError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATES_INVALID")
            positions = [
                i for i, row in enumerate(candidates)
                if isinstance(row, Mapping) and _s(row.get("work_id")) == ASSURANCE_WORK_ID
            ]
            if len(positions) != 1:
                raise ParallelFrontierError("CURRENT_ASSURANCE_CANDIDATE_CARDINALITY_INVALID")
            row = dict(candidates[positions[0]])
            evidence = dict(row.get("read_only_evidence") or {})
            evidence.update(
                {
                    "source": ASSURANCE_SOURCE_REL,
                    "source_git_blob_sha": assurance_sha,
                    "embedded_professional_snapshot_lags_live_frontier": False,
                    "verified_root_subject_binding_count": assurance_snapshot[
                        "verified_root_subject_binding_count"
                    ],
                    "required_root_count": assurance_snapshot["required_root_count"],
                    "next_professional_root": assurance_snapshot["next_root"],
                    "vector_bounds_complete": False,
                    "dynamic_current_pointer_follow": True,
                }
            )
            row["read_only_evidence"] = evidence
            candidates[positions[0]] = row

            findings = out.get("currentness_findings")
            if isinstance(findings, list):
                for finding in findings:
                    if isinstance(finding, dict) and finding.get("id") == "ASSURANCE_CURRENT_PATH":
                        finding["truth"] = (
                            "UVCK_V2_CURRENT_POINTER_PRESENT__EMBEDDED_PROFESSIONAL_"
                            "SNAPSHOT_MATCHES_LIVE_PROFESSIONAL_FRONTIER__"
                            "BLOCKED_PROMOTION_REMAINS_BLOCKED"
                        )
                        finding["source"] = ASSURANCE_SOURCE_REL
                        finding["dynamic_current_pointer_follow"] = True

    out["dynamic_currentness"] = {
        "professional_current_pointer_follow": True,
        "professional_current_git_blob_sha": actual_prof_sha,
        "professional_next_root": (
            "COMPLETE" if next_index == 13 else f"R{next_index}_{next_name}"
        ),
        "assurance_current_pointer_follow": bool(assurance_rows),
        "assurance_current_git_blob_sha": assurance_sha,
        "assurance_source_was_refreshed": assurance_followed,
        "other_source_families_dynamic_follow": False,
    }
    return out

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
    success = _f(raw["success_probability_lcb"], "success_probability_lcb")
    if success > 1:
        raise ParallelFrontierError("SUCCESS_PROBABILITY_LCB_GT_ONE")
    return True


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    if not (_vector_complete(a) and _vector_complete(b)):
        return False
    weak = all(_f(a[k], k) >= _f(b[k], k) for k in BENEFIT_FIELDS) and all(
        _f(a[k], k) <= _f(b[k], k) for k in COST_FIELDS
    )
    strict = any(_f(a[k], k) > _f(b[k], k) for k in BENEFIT_FIELDS) or any(
        _f(a[k], k) < _f(b[k], k) for k in COST_FIELDS
    )
    return weak and strict


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
            "PARETO_DOMINANCE_ONLY_WHEN_ALL_VECTOR_FIELDS_HAVE_EVIDENCE__"
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
