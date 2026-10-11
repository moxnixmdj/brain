#!/usr/bin/env python3
"""Fail-closed benchmark/capability proof-lattice scheduler V2.

V2 preserves V1 admission rules, then ranks only explicitly proved proposition
closures. Benchmark-family projections remain scheduling hints and create zero
closure credit. When a complete proposition cover is available, the existing
exact proof-coverage compiler chooses the minimum admissible cover.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from canonical.runtime.benchmark_capability_dominance_scheduler_v1 import (
    _admit_candidate,
    summarize,
    validate_frontier,
)
from canonical.runtime.proof_coverage_compiler import evaluate as evaluate_cover

SCHEMA = "PROJECT_BRAIN_BENCHMARK_CAPABILITY_DOMINANCE_SCHEDULER_V2"

PROPOSITION_TYPES = {
    "CAPABILITY_RELATION",
    "EXACT_BENCHMARK_STATISTIC",
    "OWNERSHIP_PREDICATE",
}
CAPABILITY_RELATIONS = {
    "EXACT_EQUIVALENCE",
    "CONSERVATIVE_DOMINANCE",
    "OWNER_ACCEPTED_RELATION",
}
EXACT_STATISTIC_RELATIONS = {
    "NATIVE_OWNER_RECEIPT",
    "EXACT_STATISTIC_BRIDGE",
}
OWNERSHIP_RELATIONS = {"BRAIN_OWNERSHIP_CERTIFICATE"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _normalize_required(
    required_propositions: Iterable[str | Mapping[str, Any]] | None,
) -> list[str]:
    if required_propositions is None:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for row in required_propositions:
        pid = row if isinstance(row, str) else row.get("id")
        _require(isinstance(pid, str) and bool(pid), "PROPOSITION_ID_INVALID")
        _require(pid not in seen, "PROPOSITION_ID_DUPLICATE:" + pid)
        seen.add(pid)
        out.append(pid)
    return out


def _validate_edge(
    edge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    required: set[str],
) -> str:
    _require(isinstance(edge, Mapping), "PROPOSITION_EDGE_MUST_BE_MAPPING")
    pid = edge.get("proposition_id")
    ptype = edge.get("proposition_type")
    relation = edge.get("relation")

    _require(isinstance(pid, str) and bool(pid), "PROPOSITION_EDGE_ID_INVALID")
    if required:
        _require(pid in required, "PROPOSITION_EDGE_UNKNOWN:" + pid)
    _require(ptype in PROPOSITION_TYPES, "PROPOSITION_TYPE_INVALID:" + pid)
    _require(edge.get("entailment_proved") is True, "ENTAILMENT_NOT_PROVED:" + pid)
    _require(edge.get("scope_bound") is True, "PROPOSITION_SCOPE_UNBOUND:" + pid)
    _require(
        isinstance(edge.get("evidence_ref"), str) and bool(edge["evidence_ref"].strip()),
        "PROPOSITION_EVIDENCE_REF_MISSING:" + pid,
    )

    if ptype == "CAPABILITY_RELATION":
        _require(
            relation in CAPABILITY_RELATIONS,
            "CAPABILITY_RELATION_NOT_CREDITABLE:" + pid,
        )
    elif ptype == "EXACT_BENCHMARK_STATISTIC":
        _require(
            relation in EXACT_STATISTIC_RELATIONS,
            "EXACT_STATISTIC_RELATION_INVALID:" + pid,
        )
        if relation == "EXACT_STATISTIC_BRIDGE":
            _require(
                edge.get("frozen_scorer_state_bound") is True,
                "EXACT_STATISTIC_SCORER_UNBOUND:" + pid,
            )
    else:
        _require(
            relation in OWNERSHIP_RELATIONS,
            "OWNERSHIP_RELATION_INVALID:" + pid,
        )
        _require(
            candidate.get("brain_owned_operative_configuration") is True,
            "OWNERSHIP_CONFIGURATION_UNBOUND:" + pid,
        )
        _require(
            int(candidate.get("external_runtime_cognition", 0)) == 0,
            "OWNERSHIP_EXTERNAL_RUNTIME_COGNITION:" + pid,
        )

    return pid


def _proved_closure(
    candidate: Mapping[str, Any],
    required: set[str],
) -> tuple[list[str], list[str]]:
    edges = candidate.get("proposition_edges", [])
    if edges is None:
        edges = []
    _require(isinstance(edges, list), "PROPOSITION_EDGES_MUST_BE_LIST")

    proved: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for edge in edges:
        try:
            pid = _validate_edge(edge, candidate, required)
            _require(pid not in seen, "PROPOSITION_EDGE_DUPLICATE:" + pid)
            seen.add(pid)
            proved.append(pid)
        except ValueError as exc:
            errors.append(str(exc))
    return sorted(proved), sorted(set(errors))


def _cover_route(candidate: Mapping[str, Any], covers: list[str]) -> dict[str, Any]:
    return {
        "id": str(candidate.get("id") or ""),
        "covers": covers,
        "proof_mode": "FORMAL_PROOF",
        "zero_incremental_spend": True,
        "terminal_scope_authority": True,
        "prewave_admissible": True,
        "external_blocked": False,
        "new_reality_units": int(candidate.get("new_reality_units", 0)),
        "clean_case_spend": int(candidate.get("clean_case_spend", 0)),
        "evidence_cost": float(candidate.get("evidence_cost", 0.0)),
    }


def _candidate_rank(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    proved = candidate.get("proved_propositions", [])
    wall = int(candidate.get("wall_clock_rank", 10**9))
    return (
        -len(proved),
        -int(candidate.get("reusable_family_count", 0)),
        -int(candidate.get("projected_benchmark_row_count", 0)),
        wall,
        int(candidate.get("new_reality_units", 0)),
        float(candidate.get("evidence_cost", 0.0)),
        str(candidate.get("id") or ""),
    )


def plan(
    frontier: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    *,
    required_propositions: Iterable[str | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    validate_frontier(frontier)
    required_ids = _normalize_required(required_propositions)
    required = set(required_ids)
    row_state = {
        str(row["id"]): str(row["scheduler_state"])
        for row in frontier["benchmark_rows"]
    }

    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in candidates:
        candidate = dict(raw)
        ok, reason = _admit_candidate(candidate, row_state)
        if not ok:
            rejected.append({"id": candidate.get("id"), "reason": reason})
            continue

        try:
            proved, edge_errors = _proved_closure(candidate, required)
        except ValueError as exc:
            rejected.append({"id": candidate.get("id"), "reason": str(exc)})
            continue

        candidate["admission_reason"] = reason
        candidate["proved_propositions"] = proved
        candidate["proposition_edge_errors"] = edge_errors
        admitted.append(candidate)

    proof_cover = None
    selected_pool = admitted
    selection_mode = "V1_COMPATIBILITY_FALLBACK"

    if required_ids:
        routes = [
            _cover_route(candidate, candidate["proved_propositions"])
            for candidate in admitted
            if candidate["proved_propositions"]
            and not candidate["proposition_edge_errors"]
        ]
        proof_cover = evaluate_cover(
            {
                "required_obligations": required_ids,
                "routes": routes,
            }
        )
        if proof_cover["status"] == "EXACT_MINIMUM_COVER_FOUND":
            chosen = set(proof_cover["selected_route_ids"])
            selected_pool = [c for c in admitted if c.get("id") in chosen]
            selection_mode = "EXACT_MINIMUM_PROOF_COVER"
        else:
            selected_pool = [
                c
                for c in admitted
                if c["proved_propositions"] and not c["proposition_edge_errors"]
            ]
            selection_mode = "MAX_VERIFIED_MARGINAL_CLOSURE"

    selected_pool = sorted(selected_pool, key=_candidate_rank)
    selected = selected_pool[0] if selected_pool else None

    return {
        "schema": SCHEMA,
        "summary": summarize(frontier),
        "required_propositions": required_ids,
        "proof_cover": proof_cover,
        "selection_mode": selection_mode,
        "selected": selected,
        "admitted": sorted(admitted, key=_candidate_rank),
        "rejected": rejected,
        "rule": (
            "PROVED_PROPOSITION_CLOSURE_FIRST__EXACT_MINIMUM_PROOF_COVER_WHEN_AVAILABLE__"
            "HEURISTIC_BENCHMARK_PROJECTION_ZERO_CLOSURE_AUTHORITY"
        ),
        "hard_nonclaims": [
            "SCHEDULING_HEURISTIC_ONLY_RELATIONS_CREATE_ZERO_PROPOSITION_CLOSURE",
            "NO_BRANDED_SCORE_FROM_CAPABILITY_RELATION_WITHOUT_EXACT_STATISTIC_BRIDGE",
            "NO_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_SCHEDULER_SELECTION_ALONE",
            "NO_PRIVATE_TASK_OR_ANSWER_RECONSTRUCTION",
        ],
        "benchmark_score_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
