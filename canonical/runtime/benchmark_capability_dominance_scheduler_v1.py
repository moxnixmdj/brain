#!/usr/bin/env python3
"""Fail-closed benchmark/capability dominance scheduler V1."""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_BENCHMARK_CAPABILITY_DOMINANCE_SCHEDULER_V1"
CREDIT_RELATIONS = {
    "EXACT_EQUIVALENCE",
    "CONSERVATIVE_DOMINANCE",
    "OWNER_ACCEPTED_RELATION",
}
ALL_RELATIONS = CREDIT_RELATIONS | {"SCHEDULING_HEURISTIC_ONLY"}
ROW_STATES = {"RUNNABLE", "WAKE_GATED", "PARKED"}
CANDIDATE_TYPES = {"BENCHMARK_SPECIFIC", "CAPABILITY", "RESOURCE_PARETO"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_frontier(frontier: Mapping[str, Any]) -> None:
    rows = frontier.get("benchmark_rows")
    _require(isinstance(rows, list) and rows, "BENCHMARK_ROWS_REQUIRED")
    seen: set[str] = set()
    for row in rows:
        _require(isinstance(row, Mapping), "ROW_MUST_BE_MAPPING")
        row_id = str(row.get("id") or "")
        _require(row_id and row_id not in seen, "ROW_ID_EMPTY_OR_DUPLICATE")
        seen.add(row_id)
        _require(row.get("scheduler_state") in ROW_STATES, "INVALID_ROW_STATE")
        rel = row.get("capability_projection", {}).get("relation")
        _require(rel in ALL_RELATIONS, "INVALID_CAPABILITY_RELATION")
        fams = row.get("capability_projection", {}).get("families", [])
        _require(isinstance(fams, list), "FAMILIES_MUST_BE_LIST")


def capability_projection_can_grant_credit(row: Mapping[str, Any]) -> bool:
    return row.get("capability_projection", {}).get("relation") in CREDIT_RELATIONS


def branded_score_can_close(
    *,
    exact_owner_receipt_bound: bool = False,
    explicit_score_entailment_bound: bool = False,
) -> bool:
    return bool(exact_owner_receipt_bound or explicit_score_entailment_bound)


def family_incidence(frontier: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_frontier(frontier)
    counts: Counter[str] = Counter()
    wake_counts: Counter[str] = Counter()
    for row in frontier["benchmark_rows"]:
        fams = row["capability_projection"].get("families", [])
        counts.update(fams)
        if row["scheduler_state"] != "RUNNABLE":
            wake_counts.update(fams)
    return [
        {
            "family": family,
            "projected_row_count": count,
            "nonrunnable_row_count": wake_counts[family],
            "credit_authority_from_projection": False,
        }
        for family, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def summarize(frontier: Mapping[str, Any]) -> dict[str, Any]:
    validate_frontier(frontier)
    rows = frontier["benchmark_rows"]
    states = Counter(str(row["scheduler_state"]) for row in rows)
    return {
        "schema": SCHEMA,
        "benchmark_row_count": len(rows),
        "runnable_benchmark_row_count": states["RUNNABLE"],
        "wake_gated_benchmark_row_count": states["WAKE_GATED"],
        "parked_benchmark_row_count": states["PARKED"],
        "family_incidence": family_incidence(frontier),
        "branded_score_credit_delta": 0,
        "capability_credit_delta_from_heuristic_projection": 0,
    }


def _admit_candidate(
    candidate: Mapping[str, Any],
    row_state: Mapping[str, str],
) -> tuple[bool, str]:
    ctype = candidate.get("type")
    if ctype not in CANDIDATE_TYPES:
        return False, "INVALID_CANDIDATE_TYPE"
    if int(candidate.get("external_runtime_cognition", 0)) != 0:
        return False, "EXTERNAL_RUNTIME_COGNITION_FORBIDDEN"
    if float(candidate.get("incremental_spend_usd", 0)) != 0:
        return False, "HARD_ZERO_INCREMENTAL_SPEND"
    if bool(candidate.get("waits_for_external_event", False)):
        return False, "EXTERNAL_WAIT_NOT_EXECUTABLE_NOW"

    if ctype == "BENCHMARK_SPECIFIC":
        row_id = str(candidate.get("benchmark_row_id") or "")
        if row_state.get(row_id) != "RUNNABLE":
            return False, "BENCHMARK_ROW_NOT_RUNNABLE"
        if not bool(candidate.get("new_policy_changing_evidence", False)):
            return False, "SAME_INFORMATION_BENCHMARK_RETRY_FORBIDDEN"
        return True, "ADMITTED_BENCHMARK_SPECIFIC"

    if ctype == "CAPABILITY":
        if not (
            bool(candidate.get("proved_live_defect", False))
            or bool(candidate.get("verified_counterexample", False))
            or bool(candidate.get("authorized_discriminating_experiment", False))
        ):
            return False, "NO_LIVE_CAPABILITY_DEFECT_OR_DISCRIMINATOR"
        return True, "ADMITTED_CAPABILITY_WORK"

    if not bool(candidate.get("proof_preserving", False)):
        return False, "RESOURCE_PARETO_NOT_PROOF_PRESERVING"
    return True, "ADMITTED_RESOURCE_PARETO"


def plan(
    frontier: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_frontier(frontier)
    row_state = {
        str(row["id"]): str(row["scheduler_state"])
        for row in frontier["benchmark_rows"]
    }
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in candidates:
        candidate = dict(raw)
        ok, reason = _admit_candidate(candidate, row_state)
        record = {"id": candidate.get("id"), "reason": reason}
        if ok:
            admitted.append(candidate | {"admission_reason": reason})
        else:
            rejected.append(record)

    admitted.sort(
        key=lambda c: (
            -int(c.get("reusable_family_count", 0)),
            -int(c.get("projected_benchmark_row_count", 0)),
            int(c.get("wall_clock_rank", 10**9)),
            str(c.get("id") or ""),
        )
    )
    return {
        "schema": SCHEMA,
        "summary": summarize(frontier),
        "selected": admitted[0] if admitted else None,
        "admitted": admitted,
        "rejected": rejected,
        "rule": "CAPABILITY_FIRST__BENCHMARK_AUDIT_ONLY_UNLESS_RUNNABLE_AND_NONDOMINATED",
    }
