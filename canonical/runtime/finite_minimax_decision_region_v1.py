"""Exact minimax decision-region determination for finite deterministic models.

Unlike terminal-equivalence identification, decision regions may overlap:
one world may admit several adequate Brain policies. Resolution occurs as soon
as at least one policy region contains every surviving world.

This solver is structural only. It assumes the supplied finite hypothesis set,
policy regions, and observation outcome maps are complete and sound for the
declared cell. It has no terminal authority.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_FINITE_MINIMAX_DECISION_REGION_V1"


def solve(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "PROBLEM_REQUIRED"}
    if problem.get("hypothesis_set_complete") is not True:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "HYPOTHESIS_SET_COMPLETENESS_UNPROVED"}

    worlds = problem.get("worlds")
    regions = problem.get("policy_regions")
    observations = problem.get("observations")

    if not isinstance(worlds, Sequence) or isinstance(worlds, (str, bytes)) or not worlds:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "WORLDS_REQUIRED"}
    ids: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(worlds):
        if not isinstance(row, Mapping):
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"WORLD_INVALID:{i}"}
        wid = row.get("world_id")
        if not isinstance(wid, str) or not wid or wid in seen:
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"WORLD_ID_INVALID:{i}"}
        seen.add(wid)
        ids.append(wid)
    universe = set(ids)

    if not isinstance(regions, Sequence) or isinstance(regions, (str, bytes)) or not regions:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "POLICY_REGIONS_REQUIRED"}
    region_map: dict[str, frozenset[str]] = {}
    for i, row in enumerate(regions):
        if not isinstance(row, Mapping):
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"POLICY_REGION_INVALID:{i}"}
        pid = row.get("policy_id")
        members = row.get("world_ids")
        if not isinstance(pid, str) or not pid or pid in region_map:
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"POLICY_ID_INVALID:{i}"}
        if row.get("region_complete") is not True:
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"POLICY_REGION_COMPLETENESS_UNPROVED:{pid}"}
        if not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"POLICY_REGION_MEMBERS_INVALID:{pid}"}
        member_set = set(members)
        if any(not isinstance(x, str) or not x for x in members) or not member_set.issubset(universe):
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"POLICY_REGION_MEMBERS_INVALID:{pid}"}
        region_map[pid] = frozenset(member_set)

    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "OBSERVATIONS_REQUIRED"}
    obs: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(observations):
        if not isinstance(row, Mapping):
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"OBSERVATION_INVALID:{i}"}
        oid = row.get("observation_id")
        outcomes = row.get("outcomes")
        cost = row.get("cost_units")
        if not isinstance(oid, str) or not oid or oid in obs:
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"OBSERVATION_ID_INVALID:{i}"}
        if row.get("outcome_map_complete") is not True or not isinstance(outcomes, Mapping) or set(outcomes) != universe:
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"OBSERVATION_OUTCOME_MAP_INCOMPLETE:{oid}"}
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": f"OBSERVATION_COST_INVALID:{oid}"}
        obs[oid] = {
            "cost": float(cost),
            "outcomes": {wid: repr(outcomes[wid]) for wid in ids},
        }

    def covering_policies(state: frozenset[str]) -> tuple[str, ...]:
        return tuple(sorted(pid for pid, members in region_map.items() if state.issubset(members)))

    def partition(state: frozenset[str], oid: str) -> tuple[frozenset[str], ...]:
        buckets: dict[str, set[str]] = {}
        for wid in state:
            buckets.setdefault(obs[oid]["outcomes"][wid], set()).add(wid)
        return tuple(
            frozenset(v)
            for _, v in sorted(buckets.items(), key=lambda item: item[0])
        )

    @lru_cache(maxsize=None)
    def dp(state: frozenset[str]):
        covers = covering_policies(state)
        if covers:
            return (0.0, None, (), covers)

        best = None
        for oid in sorted(obs):
            parts = partition(state, oid)
            if len(parts) <= 1:
                continue
            child_rows = []
            worst = 0.0
            impossible = False
            for part in parts:
                child = dp(part)
                if child[0] == float("inf"):
                    impossible = True
                    break
                worst = max(worst, child[0])
                child_rows.append((tuple(sorted(part)), child[0], child[3]))
            if impossible:
                continue
            total = obs[oid]["cost"] + worst
            candidate = (total, oid, tuple(child_rows), ())
            if best is None or (candidate[0], candidate[1]) < (best[0], best[1]):
                best = candidate

        return best if best is not None else (float("inf"), None, (), ())

    initial = frozenset(ids)
    total, first, children, initial_covers = dp(initial)

    if initial_covers:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__COMMON_POLICY_ALREADY_COVERS_VERSION_SPACE",
            "world_count": len(ids),
            "common_policy_ids": list(initial_covers),
            "minimum_worst_case_cost_units": 0.0,
            "first_observation_id": None,
            "terminal_authority": False,
            "capability_credit_delta": 0,
        }

    if total == float("inf"):
        conflicts = []
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pair = frozenset({a, b})
                if not covering_policies(pair):
                    indistinguishable = all(
                        obs[oid]["outcomes"][a] == obs[oid]["outcomes"][b]
                        for oid in obs
                    )
                    if indistinguishable:
                        conflicts.append([a, b])
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__NO_DECLARED_OBSERVATION_POLICY_CAN_REACH_A_COMMON_DECISION_REGION",
            "unresolved_pair_witnesses": conflicts,
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__EXACT_MINIMAX_DECISION_REGION_POLICY",
        "world_count": len(ids),
        "policy_region_count": len(region_map),
        "minimum_worst_case_cost_units": total,
        "first_observation_id": first,
        "first_observation_partitions": [
            {
                "world_ids": list(worlds_in_part),
                "remaining_optimal_cost": remaining,
                "common_policy_ids_if_resolved": list(covers),
            }
            for worlds_in_part, remaining, covers in children
        ],
        "decision_regions_may_overlap": True,
        "stops_on_common_policy_not_world_identification": True,
        "theorem_boundary": (
            "EXACT_ONLY_FOR_THE_DECLARED_COMPLETE_FINITE_HYPOTHESIS_SET_COMPLETE_SOUND_POLICY_REGIONS"
            "_AND_COMPLETE_TRUTHFUL_OBSERVATION_OUTCOME_MAPS"
        ),
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
