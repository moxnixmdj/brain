"""Scope-complete U depletion orchestrator.

This module fuses the two already-owned structural moves used by the terminal
authority:
  1. close a whole residual region with one certified adequate policy; else
  2. compute the minimum truthful observation policy needed to partition the
     region into cells that admit certified adequate policies.

It never grants terminal/family/capability credit by itself. U subtraction is
authorized only when scope completeness and adequacy evidence are explicitly
bound in the input.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.finite_minimax_decision_region_v1 import solve as solve_minimax

SCHEMA = "PROJECT_BRAIN_U_SCOPE_COMPLETE_DEPLETION_ORCHESTRATOR_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "u_subtraction_authorized": False,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_REQUIRED")

    region_id = problem.get("region_id")
    if not isinstance(region_id, str) or not region_id:
        return _fail("REGION_ID_REQUIRED")

    if problem.get("scope_complete") is not True:
        return _fail("SCOPE_COMPLETENESS_UNPROVED", region_id=region_id)

    cells = problem.get("cells")
    if not isinstance(cells, Sequence) or isinstance(cells, (str, bytes)) or not cells:
        return _fail("CELLS_REQUIRED", region_id=region_id)

    world_ids: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(cells):
        if not isinstance(row, Mapping):
            return _fail(f"CELL_INVALID:{i}")
        wid = row.get("world_id")
        if not isinstance(wid, str) or not wid or wid in seen:
            return _fail(f"WORLD_ID_INVALID:{i}")
        if row.get("membership_proved") is not True:
            return _fail(f"CELL_MEMBERSHIP_UNPROVED:{wid}")
        seen.add(wid)
        world_ids.append(wid)

    policies = problem.get("policy_regions")
    if not isinstance(policies, Sequence) or isinstance(policies, (str, bytes)) or not policies:
        return _fail("POLICY_REGIONS_REQUIRED")

    normalized_regions: list[dict[str, Any]] = []
    common: list[str] = []
    universe = set(world_ids)
    for i, row in enumerate(policies):
        if not isinstance(row, Mapping):
            return _fail(f"POLICY_REGION_INVALID:{i}")
        pid = row.get("policy_id")
        members = row.get("world_ids")
        if not isinstance(pid, str) or not pid:
            return _fail(f"POLICY_ID_INVALID:{i}")
        if row.get("adequacy_proved") is not True:
            return _fail(f"POLICY_ADEQUACY_UNPROVED:{pid}")
        if row.get("independent_or_objective") is not True:
            return _fail(f"POLICY_ADEQUACY_NOT_INDEPENDENT_OR_OBJECTIVE:{pid}")
        if not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
            return _fail(f"POLICY_MEMBERS_INVALID:{pid}")
        member_set = set(members)
        if any(not isinstance(x, str) or not x for x in members) or not member_set.issubset(universe):
            return _fail(f"POLICY_MEMBERS_INVALID:{pid}")
        normalized_regions.append({
            "policy_id": pid,
            "world_ids": list(members),
            "region_complete": True,
        })
        if universe.issubset(member_set):
            common.append(pid)

    if common:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__WHOLE_REGION_COMMON_POLICY_CLOSED",
            "region_id": region_id,
            "scope_complete": True,
            "world_count": len(world_ids),
            "common_policy_ids": sorted(common),
            "minimum_truthful_discriminator_required": False,
            "u_subtraction_authorized": True,
            "u_subtraction_scope": region_id,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "rule": "ONE_SCOPE_COMPLETE_CERTIFIED_ADEQUATE_POLICY_COVERS_THE_WHOLE_RESIDUAL_REGION",
        }

    observations = problem.get("observations")
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        return _fail("OBSERVATIONS_REQUIRED_WHEN_NO_COMMON_POLICY")

    minimax_problem = {
        "hypothesis_set_complete": True,
        "worlds": [{"world_id": wid} for wid in world_ids],
        "policy_regions": normalized_regions,
        "observations": list(observations),
    }
    result = solve_minimax(minimax_problem)

    if result.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "OPEN__NO_SOUND_DECLARED_DISCRIMINATOR_CLOSURE",
            "region_id": region_id,
            "scope_complete": True,
            "minimax": result,
            "u_subtraction_authorized": False,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    if result.get("status") == "PASS__COMMON_POLICY_ALREADY_COVERS_VERSION_SPACE":
        # Defensive: this should normally have been caught above.
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__WHOLE_REGION_COMMON_POLICY_CLOSED",
            "region_id": region_id,
            "scope_complete": True,
            "common_policy_ids": result.get("common_policy_ids", []),
            "minimum_truthful_discriminator_required": False,
            "u_subtraction_authorized": True,
            "u_subtraction_scope": region_id,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__MINIMUM_TRUTHFUL_DISCRIMINATOR_PLAN",
        "region_id": region_id,
        "scope_complete": True,
        "minimum_truthful_discriminator_required": True,
        "first_observation_id": result.get("first_observation_id"),
        "minimum_worst_case_cost_units": result.get("minimum_worst_case_cost_units"),
        "partitions": result.get("first_observation_partitions", []),
        "u_subtraction_authorized": False,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": (
            "DO_NOT_RECONSTRUCT_THE_WORLD__ACQUIRE_ONLY_THE_MINIMUM_TRUTHFUL_"
            "POLICY_CHANGING_OBSERVATION_THEN_RECURSE_ON_RESULTING_SCOPE_COMPLETE_CELLS"
        ),
    }
