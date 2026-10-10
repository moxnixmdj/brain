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
    """Canonical current-frontier planning entrypoint."""
    return plan_parallel_frontier(load_current_frontier())



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
