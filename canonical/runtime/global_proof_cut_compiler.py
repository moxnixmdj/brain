"""Exact global proof-cut compiler over a frozen finite action universe.

An "exact global minimum" is undefined over an open-ended action space. This
compiler makes exactness truthful by requiring:
1. a complete open terminal-obligation inventory,
2. evidence saturation before freeze,
3. a finite candidate action universe frozen by hash,
4. automatic invalidation if that universe changes.

Objective order:
  1) minimize longest dependency depth,
  2) minimize frozen-model new reality units,
  3) minimize parallel critical-path wall-clock units,
  4) minimize selected action count,
  5) deterministic lexical tie-break.

Candidate actions are self-contained proof bundles. Their declared
dependency_depth already includes internal prerequisites.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GLOBAL_PROOF_CUT_INPUT_V1"
FREEZE_SCHEMA = "PROJECT_BRAIN_FROZEN_PROOF_ACTION_UNIVERSE_V1"
MAX_OPEN_OBLIGATIONS = 24
MAX_CANDIDATE_ACTIONS = 64


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _finite_nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _normalize_obligations(rows: Any) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(rows, list):
        return [], ["OBLIGATIONS_NOT_LIST"]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"OBLIGATION_INVALID:{i}")
            continue
        oid = row.get("id")
        status = row.get("status")
        if not isinstance(oid, str) or not oid.strip():
            errors.append(f"OBLIGATION_ID_INVALID:{i}")
            continue
        if oid in seen:
            errors.append(f"OBLIGATION_ID_DUPLICATE:{oid}")
            continue
        seen.add(oid)
        if status not in {"OPEN", "CLOSED"}:
            errors.append(f"OBLIGATION_STATUS_INVALID:{oid}")
            continue
        terminal_necessary = row.get("terminal_necessary")
        if terminal_necessary is not True and terminal_necessary is not False:
            errors.append(f"OBLIGATION_TERMINAL_NECESSITY_INVALID:{oid}")
            continue
        out.append(
            {
                "id": oid,
                "status": status,
                "terminal_necessary": terminal_necessary,
            }
        )
    return sorted(out, key=lambda x: x["id"]), errors


def _normalize_actions(
    rows: Any, known_obligations: set[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(rows, list):
        return [], ["CANDIDATE_ACTIONS_NOT_LIST"]
    if len(rows) > MAX_CANDIDATE_ACTIONS:
        errors.append("CANDIDATE_ACTION_LIMIT_EXCEEDED")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"ACTION_INVALID:{i}")
            continue
        aid = row.get("id")
        if not isinstance(aid, str) or not aid.strip():
            errors.append(f"ACTION_ID_INVALID:{i}")
            continue
        if aid in seen:
            errors.append(f"ACTION_ID_DUPLICATE:{aid}")
            continue
        seen.add(aid)
        covers = row.get("covers")
        if not isinstance(covers, list) or not covers or any(
            not isinstance(x, str) or not x for x in covers
        ):
            errors.append(f"ACTION_COVERAGE_INVALID:{aid}")
            continue
        if not set(covers) <= known_obligations:
            errors.append(f"ACTION_COVERS_UNKNOWN_OBLIGATION:{aid}")
        bits = row.get("new_reality_units")
        depth = row.get("dependency_depth")
        wall = row.get("critical_path_wall_clock_units")
        if not _finite_nonnegative(bits):
            errors.append(f"ACTION_REALITY_COST_INVALID:{aid}")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
            errors.append(f"ACTION_DEPENDENCY_DEPTH_INVALID:{aid}")
        if not _finite_nonnegative(wall):
            errors.append(f"ACTION_WALL_CLOCK_INVALID:{aid}")
        if row.get("admissible") is not True:
            errors.append(f"ACTION_NOT_ADMISSIBLE:{aid}")
        if row.get("bundle_complete") is not True:
            errors.append(f"ACTION_BUNDLE_NOT_COMPLETE:{aid}")
        out.append(
            {
                "id": aid,
                "covers": sorted(set(covers)),
                "new_reality_units": float(bits) if _finite_nonnegative(bits) else 0.0,
                "dependency_depth": depth if isinstance(depth, int) and not isinstance(depth, bool) else 0,
                "critical_path_wall_clock_units": float(wall) if _finite_nonnegative(wall) else 0.0,
                "admissible": row.get("admissible") is True,
                "bundle_complete": row.get("bundle_complete") is True,
            }
        )
    return sorted(out, key=lambda x: x["id"]), errors


def _dominance_delete(
    actions: list[dict[str, Any]], open_ids: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    kept: list[dict[str, Any]] = []
    deletions: list[dict[str, str]] = []
    for b in actions:
        bcover = set(b["covers"]) & open_ids
        dominator = None
        for a in actions:
            if a["id"] == b["id"]:
                continue
            acover = set(a["covers"]) & open_ids
            no_worse = (
                acover >= bcover
                and a["dependency_depth"] <= b["dependency_depth"]
                and a["new_reality_units"] <= b["new_reality_units"]
                and a["critical_path_wall_clock_units"] <= b["critical_path_wall_clock_units"]
            )
            strict = (
                acover > bcover
                or a["dependency_depth"] < b["dependency_depth"]
                or a["new_reality_units"] < b["new_reality_units"]
                or a["critical_path_wall_clock_units"] < b["critical_path_wall_clock_units"]
            )
            exact_tie_better_id = (
                acover == bcover
                and a["dependency_depth"] == b["dependency_depth"]
                and a["new_reality_units"] == b["new_reality_units"]
                and a["critical_path_wall_clock_units"] == b["critical_path_wall_clock_units"]
                and a["id"] < b["id"]
            )
            if no_worse and (strict or exact_tie_better_id):
                dominator = a["id"]
                break
        if dominator is None:
            kept.append(b)
        else:
            deletions.append({"deleted": b["id"], "dominated_by": dominator})
    return kept, sorted(deletions, key=lambda x: x["deleted"])


def _solve_at_depth(
    actions: list[dict[str, Any]], open_ids: list[str], max_depth: int
) -> dict[str, Any] | None:
    index = {oid: i for i, oid in enumerate(open_ids)}
    target = (1 << len(open_ids)) - 1
    eligible = [a for a in actions if a["dependency_depth"] <= max_depth]
    best: dict[int, tuple[float, float, int, tuple[str, ...]]] = {
        0: (0.0, 0.0, 0, ())
    }
    for action in eligible:
        mask = 0
        for oid in action["covers"]:
            if oid in index:
                mask |= 1 << index[oid]
        if not mask:
            continue
        snapshot = list(best.items())
        for covered, state in snapshot:
            nmask = covered | mask
            ids = tuple(sorted(state[3] + (action["id"],)))
            cand = (
                state[0] + action["new_reality_units"],
                max(state[1], action["critical_path_wall_clock_units"]),
                state[2] + 1,
                ids,
            )
            prior = best.get(nmask)
            if prior is None or cand < prior:
                best[nmask] = cand
    if target not in best:
        return None
    bits, wall, count, ids = best[target]
    return {
        "max_dependency_depth": max_depth,
        "total_new_reality_units": bits,
        "parallel_critical_path_wall_clock_units": wall,
        "action_count": count,
        "selected_actions": list(ids),
    }


def compile_cut(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {"status": "INVALID", "errors": ["INPUT_NOT_OBJECT"], "exact": False}
    if payload.get("schema") != SCHEMA:
        errors.append("SCHEMA_INVALID")

    obligations, obligation_errors = _normalize_obligations(payload.get("obligations"))
    errors.extend(obligation_errors)
    known = {x["id"] for x in obligations}
    actions, action_errors = _normalize_actions(payload.get("candidate_actions"), known)
    errors.extend(action_errors)

    freeze = payload.get("freeze")
    if not isinstance(freeze, Mapping):
        errors.append("FREEZE_MISSING")
        freeze = {}
    else:
        if freeze.get("schema") != FREEZE_SCHEMA:
            errors.append("FREEZE_SCHEMA_INVALID")
        if freeze.get("status") != "FROZEN":
            errors.append("CANDIDATE_UNIVERSE_NOT_FROZEN")
        if freeze.get("evidence_saturation_complete") is not True:
            errors.append("EVIDENCE_SATURATION_INCOMPLETE")
        if freeze.get("discovery_frontier_frozen") is not True:
            errors.append("DISCOVERY_FRONTIER_NOT_FROZEN")
        if freeze.get("candidate_universe_complete_relative_to_freeze") is not True:
            errors.append("CANDIDATE_UNIVERSE_NOT_COMPLETE_RELATIVE_TO_FREEZE")
        if freeze.get("invalidated_by_new_candidate") is not False:
            errors.append("FROZEN_UNIVERSE_INVALIDATED_BY_NEW_CANDIDATE")

    obligation_hash = canonical_hash(obligations)
    action_hash = canonical_hash(actions)
    if freeze.get("obligation_graph_sha256") != obligation_hash:
        errors.append("OBLIGATION_GRAPH_HASH_MISMATCH")
    if freeze.get("candidate_universe_sha256") != action_hash:
        errors.append("CANDIDATE_UNIVERSE_HASH_MISMATCH")
    sat_hash = freeze.get("evidence_saturation_receipt_sha256")
    if not isinstance(sat_hash, str) or len(sat_hash) != 64 or any(
        c not in "0123456789abcdef" for c in sat_hash
    ):
        errors.append("EVIDENCE_SATURATION_RECEIPT_HASH_INVALID")

    cost_model = payload.get("cost_model")
    if not isinstance(cost_model, Mapping):
        errors.append("COST_MODEL_MISSING")
        cost_model = {}
    else:
        if cost_model.get("status") != "FROZEN":
            errors.append("COST_MODEL_NOT_FROZEN")
        if cost_model.get("information_unit") != "PREDECLARED_NEW_TERMINAL_DISTINCTION_UNIT":
            errors.append("COST_MODEL_INFORMATION_UNIT_INVALID")
        if cost_model.get("parallel_wall_clock_aggregation") != "MAX_CRITICAL_PATH":
            errors.append("COST_MODEL_PARALLEL_WALL_CLOCK_INVALID")
        if cost_model.get("bundle_internal_dependencies_included") is not True:
            errors.append("COST_MODEL_BUNDLE_DEPENDENCIES_NOT_INCLUDED")
    cost_model_hash = canonical_hash(cost_model) if isinstance(cost_model, Mapping) else ""
    if freeze.get("cost_model_sha256") != cost_model_hash:
        errors.append("COST_MODEL_HASH_MISMATCH")

    open_ids = sorted(
        x["id"]
        for x in obligations
        if x["status"] == "OPEN" and x["terminal_necessary"] is True
    )
    if len(open_ids) > MAX_OPEN_OBLIGATIONS:
        errors.append("OPEN_OBLIGATION_LIMIT_EXCEEDED")

    if errors:
        return {
            "schema": "PROJECT_BRAIN_GLOBAL_PROOF_CUT_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "exact": False,
            "exactness_scope": "FROZEN_DECLARED_CANDIDATE_UNIVERSE_AND_COST_MODEL",
            "errors": sorted(set(errors)),
            "obligation_graph_sha256": obligation_hash,
            "candidate_universe_sha256": action_hash,
            "cost_model_sha256": cost_model_hash,
        }

    if not open_ids:
        return {
            "schema": "PROJECT_BRAIN_GLOBAL_PROOF_CUT_VERDICT_V1",
            "status": "EXACT_CUT",
            "exact": True,
            "exactness_scope": "FROZEN_DECLARED_CANDIDATE_UNIVERSE_AND_COST_MODEL",
            "open_obligations": [],
            "selected_actions": [],
            "max_dependency_depth": 0,
            "total_new_reality_units": 0.0,
            "parallel_critical_path_wall_clock_units": 0.0,
            "action_count": 0,
            "dominance_deletions": [],
            "obligation_graph_sha256": obligation_hash,
            "candidate_universe_sha256": action_hash,
            "cost_model_sha256": cost_model_hash,
        }

    open_set = set(open_ids)
    coverage = set()
    for action in actions:
        coverage.update(set(action["covers"]) & open_set)
    missing = sorted(open_set - coverage)
    if missing:
        return {
            "schema": "PROJECT_BRAIN_GLOBAL_PROOF_CUT_VERDICT_V1",
            "status": "GRAPH_INCOMPLETE",
            "exact": False,
            "exactness_scope": "FROZEN_DECLARED_CANDIDATE_UNIVERSE_AND_COST_MODEL",
            "missing_obligations": missing,
            "obligation_graph_sha256": obligation_hash,
            "candidate_universe_sha256": action_hash,
            "cost_model_sha256": cost_model_hash,
        }

    reduced, deletions = _dominance_delete(actions, open_set)
    depths = sorted({a["dependency_depth"] for a in reduced})
    solution = None
    for depth in depths:
        solution = _solve_at_depth(reduced, open_ids, depth)
        if solution is not None:
            break
    if solution is None:
        return {
            "schema": "PROJECT_BRAIN_GLOBAL_PROOF_CUT_VERDICT_V1",
            "status": "UNRESOLVABLE_WITH_FROZEN_UNIVERSE",
            "exact": False,
            "exactness_scope": "FROZEN_DECLARED_CANDIDATE_UNIVERSE_AND_COST_MODEL",
            "obligation_graph_sha256": obligation_hash,
            "candidate_universe_sha256": action_hash,
            "cost_model_sha256": cost_model_hash,
        }

    return {
        "schema": "PROJECT_BRAIN_GLOBAL_PROOF_CUT_VERDICT_V1",
        "status": "EXACT_CUT",
        "exact": True,
        "exactness_scope": "FROZEN_DECLARED_CANDIDATE_UNIVERSE_AND_COST_MODEL",
        "objective_order": [
            "MINIMIZE_LONGEST_DEPENDENCY_DEPTH",
            "MINIMIZE_NEW_REALITY_UNITS",
            "MINIMIZE_PARALLEL_CRITICAL_PATH_WALL_CLOCK_UNITS",
            "MINIMIZE_ACTION_COUNT",
            "LEXICOGRAPHIC_ACTION_IDS",
        ],
        "open_obligations": open_ids,
        **solution,
        "dominance_deletions": deletions,
        "obligation_graph_sha256": obligation_hash,
        "candidate_universe_sha256": action_hash,
        "cost_model_sha256": cost_model_hash,
        "recompute_rule": "ANY_NEW_CANDIDATE_OR_OBLIGATION_INVALIDATES_FREEZE_AND_REQUIRES_RECOMPUTATION",
    }
