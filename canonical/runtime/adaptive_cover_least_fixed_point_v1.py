"""Fail-closed least-fixed-point compiler for finite adaptive terminal/progress covers.

This runtime does not prove that the declared finite abstraction is scope-complete for S_TRACE.
It only computes the inductive closure and the entry-stage rank induced by authenticated
terminal and progress-edge premises supplied in the manifest.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_COVER_LEAST_FIXED_POINT_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "covered": False,
        "errors": list(errors),
        "terminal_authority": False,
        "u_empty_authority": False,
    }


def compute_cover(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_NOT_MAPPING")

    raw_states = manifest.get("states")
    if not isinstance(raw_states, list) or not raw_states:
        return _fail("STATES_REQUIRED")
    states = [str(x).strip() for x in raw_states]
    if any(not x for x in states) or len(states) != len(set(states)):
        return _fail("STATE_IDS_INVALID_OR_DUPLICATE")
    state_set = set(states)

    terminals_raw = manifest.get("terminal_states") or []
    if not isinstance(terminals_raw, list):
        return _fail("TERMINAL_STATES_NOT_LIST")
    terminals: set[str] = set()
    terminal_rows: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(terminals_raw):
        if not isinstance(row, Mapping):
            return _fail(f"TERMINAL_ROW_INVALID:{i}")
        sid = str(row.get("state_id") or "").strip()
        if sid not in state_set or sid in terminal_rows:
            return _fail(f"TERMINAL_STATE_INVALID:{i}")
        if row.get("adequacy_authenticated") is not True:
            continue
        if row.get("safety_authenticated") is not True:
            continue
        terminals.add(sid)
        terminal_rows[sid] = row

    edges_raw = manifest.get("progress_edges") or []
    if not isinstance(edges_raw, list):
        return _fail("PROGRESS_EDGES_NOT_LIST")

    edges_by_state: dict[str, list[dict[str, Any]]] = {s: [] for s in states}
    edge_ids: set[str] = set()
    for i, row in enumerate(edges_raw):
        if not isinstance(row, Mapping):
            return _fail(f"PROGRESS_EDGE_INVALID:{i}")
        eid = str(row.get("edge_id") or "").strip()
        sid = str(row.get("state_id") or "").strip()
        if not eid or eid in edge_ids or sid not in state_set:
            return _fail(f"PROGRESS_EDGE_ID_OR_STATE_INVALID:{i}")
        edge_ids.add(eid)

        outcomes = row.get("outcomes")
        if not isinstance(outcomes, list) or not outcomes:
            return _fail(f"OUTCOMES_REQUIRED:{eid}")
        succ: list[str] = []
        seen_outcomes: set[str] = set()
        for j, out in enumerate(outcomes):
            if not isinstance(out, Mapping):
                return _fail(f"OUTCOME_INVALID:{eid}:{j}")
            oid = str(out.get("outcome_id") or "").strip()
            nxt = str(out.get("successor_state_id") or "").strip()
            if not oid or oid in seen_outcomes or nxt not in state_set:
                return _fail(f"OUTCOME_ID_OR_SUCCESSOR_INVALID:{eid}:{j}")
            seen_outcomes.add(oid)
            succ.append(nxt)

        auth = all(
            row.get(k) is True
            for k in (
                "brain_owned",
                "safety_authenticated",
                "outcome_model_complete_authenticated",
                "true_world_preservation_authenticated",
                "resource_authenticated",
            )
        )
        edges_by_state[sid].append(
            {"edge_id": eid, "successors": tuple(succ), "authenticated": auth}
        )

    covered = set(terminals)
    stage: dict[str, int] = {s: 0 for s in terminals}
    witness: dict[str, dict[str, Any]] = {
        s: {"kind": "TERMINAL", "state_id": s} for s in terminals
    }

    next_stage = 1
    while True:
        additions: dict[str, dict[str, Any]] = {}
        for sid in states:
            if sid in covered:
                continue
            candidates = []
            for edge in edges_by_state[sid]:
                if not edge["authenticated"]:
                    continue
                if all(nxt in covered for nxt in edge["successors"]):
                    candidates.append(edge)
            if candidates:
                edge = sorted(candidates, key=lambda e: e["edge_id"])[0]
                additions[sid] = edge

        if not additions:
            break

        for sid, edge in additions.items():
            covered.add(sid)
            stage[sid] = next_stage
            witness[sid] = {
                "kind": "PROGRESS",
                "state_id": sid,
                "edge_id": edge["edge_id"],
                "successors": list(edge["successors"]),
            }
        next_stage += 1

    uncovered = [s for s in states if s not in covered]
    rank_edges_ok = True
    for sid, row in witness.items():
        if row["kind"] != "PROGRESS":
            continue
        if not all(stage[nxt] < stage[sid] for nxt in row["successors"]):
            rank_edges_ok = False
            break

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__DECLARED_FINITE_ABSTRACTION_TOTAL_TERMINAL_OR_PROGRESS_COVER"
            if not uncovered and rank_edges_ok
            else "PARTIAL__UNRESOLVED_DECLARED_ABSTRACT_STATES"
        ),
        "covered": not uncovered and rank_edges_ok,
        "state_count": len(states),
        "covered_state_count": len(covered),
        "uncovered_states": uncovered,
        "entry_stage_rank": {s: stage[s] for s in states if s in stage},
        "witnesses": {s: witness[s] for s in states if s in witness},
        "rank_strict_on_selected_progress_edges": rank_edges_ok,
        "scope_complete_for_s_trace_self_certified": False,
        "terminal_authority": False,
        "u_empty_authority": False,
        "hard_boundary": (
            "A_TOTAL_PASS_COVERS_ONLY_THE_DECLARED_FINITE_ABSTRACTION. "
            "SEPARATE_CONTENT_ADDRESSED_PROOF_MUST_BIND_TOTAL_SOUND_ALPHA_GAMMA "
            "FROM_THE_CLOSED_TRACE_SCOPE_BEFORE_GLOBAL_U_CREDIT."
        ),
    }
