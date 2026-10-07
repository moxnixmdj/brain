"""Bridge monotone semantic abstraction to exact finite minimax DRD.

The current semantic state is a sound over-approximation over a bounded Boolean
decision basis. Every satisfying valuation becomes an abstract world. Policy
adequacy formulas induce overlapping decision regions. Authorized Boolean
observations induce complete deterministic outcome maps. The exact minimax DRD
solver then selects the minimum worst-case observation policy.

All exactness is relative to the abstract model and the supplied soundness
certificates. Spurious abstract worlds may cause extra queries or abstention,
but must not create an unsafe policy proof. This module has no terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence
import json

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    compile_state,
    _eval,
    _models,
    _validate_formula,
)
from canonical.runtime.finite_minimax_decision_region_v1 import solve as solve_drd

SCHEMA = "BRAIN_MONOTONE_SEMANTIC_DRD_BRIDGE_V1"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _world_id(valuation: Mapping[str, bool]) -> str:
    return "AW-" + sha256(_canon(valuation).encode("utf-8")).hexdigest()[:16]


def solve(
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    *,
    formal_source_constraints: Sequence[Mapping[str, Any]] = (),
    proposed_refinements: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    compiled = compile_state(
        decision_basis,
        formal_source_constraints=formal_source_constraints,
        proposed_refinements=proposed_refinements,
    )
    if compiled.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_STATE_FAIL_CLOSED",
            "semantic_state": compiled,
            "terminal_authority": False,
        }

    basis = list(compiled["decision_basis"])
    basis_set = set(basis)
    errors: list[str] = []
    normalized_policies: dict[str, dict[str, Any]] = {}

    if not isinstance(policy_conditions, Mapping) or not policy_conditions:
        errors.append("POLICY_CONDITIONS_INVALID_OR_EMPTY")
    else:
        for pid, row in policy_conditions.items():
            if not isinstance(pid, str) or not pid or not isinstance(row, Mapping):
                errors.append("POLICY_CONDITION_INVALID")
                continue
            formula = row.get("condition")
            cert = row.get("adequacy_certificate_id")
            if not isinstance(cert, str) or not cert:
                errors.append(f"POLICY_ADEQUACY_CERTIFICATE_ID_MISSING:{pid}")
            for err in _validate_formula(formula, basis_set):
                errors.append(f"POLICY_{pid}:{err}")
            normalized_policies[pid] = {"condition": formula, "adequacy_certificate_id": cert}

    normalized_obs: list[dict[str, Any]] = []
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        errors.append("OBSERVATIONS_INVALID")
    else:
        seen_obs: set[str] = set()
        for i, row in enumerate(observations):
            if not isinstance(row, Mapping):
                errors.append(f"OBSERVATION_INVALID:{i}")
                continue
            oid = row.get("observation_id")
            formula = row.get("formula")
            cert = row.get("truthfulness_certificate_id")
            cost = row.get("cost_units")
            if not isinstance(oid, str) or not oid or oid in seen_obs:
                errors.append(f"OBSERVATION_ID_INVALID:{i}")
                continue
            seen_obs.add(oid)
            if not isinstance(cert, str) or not cert:
                errors.append(f"OBSERVATION_TRUTHFULNESS_CERTIFICATE_ID_MISSING:{oid}")
            if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
                errors.append(f"OBSERVATION_COST_INVALID:{oid}")
            for err in _validate_formula(formula, basis_set):
                errors.append(f"OBSERVATION_{oid}:{err}")
            normalized_obs.append({
                "observation_id": oid,
                "formula": formula,
                "truthfulness_certificate_id": cert,
                "cost_units": cost,
            })

    if errors:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    valuations = _models(basis, compiled["state"])
    if not valuations:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "NO_ABSTRACT_WORLDS",
            "terminal_authority": False,
        }

    worlds = []
    id_to_val: dict[str, dict[str, bool]] = {}
    for valuation in valuations:
        wid = _world_id(valuation)
        id_to_val[wid] = valuation
        worlds.append({"world_id": wid})

    regions = []
    for pid, row in sorted(normalized_policies.items()):
        members = sorted(
            wid for wid, valuation in id_to_val.items()
            if _eval(row["condition"], valuation)
        )
        regions.append({
            "policy_id": pid,
            "world_ids": members,
            "region_complete": True,
            "adequacy_certificate_id": row["adequacy_certificate_id"],
        })

    obs_rows = []
    for row in normalized_obs:
        outcomes = {
            wid: ("TRUE" if _eval(row["formula"], valuation) else "FALSE")
            for wid, valuation in id_to_val.items()
        }
        obs_rows.append({
            "observation_id": row["observation_id"],
            "cost_units": row["cost_units"],
            "outcome_map_complete": True,
            "outcomes": outcomes,
            "truthfulness_certificate_id": row["truthfulness_certificate_id"],
        })

    drd = solve_drd({
        "hypothesis_set_complete": True,
        "worlds": worlds,
        "policy_regions": regions,
        "observations": obs_rows,
    })

    return {
        "schema": SCHEMA,
        "pass": bool(drd.get("pass")),
        "status": drd.get("status"),
        "semantic_state": compiled,
        "abstract_world_count": len(worlds),
        "abstract_worlds_complete_relative_to_state_formula": True,
        "policy_regions": regions,
        "observation_models": obs_rows,
        "decision_region_result": drd,
        "common_policy_ids": drd.get("common_policy_ids", []),
        "first_observation_id": drd.get("first_observation_id"),
        "minimum_worst_case_cost_units": drd.get("minimum_worst_case_cost_units"),
        "terminal_authority": False,
        "soundness_boundary": (
            "EXACT_MINIMAX_ONLY_RELATIVE_TO_THE_SOUND_ABSTRACT_STATE_DECLARED_POLICY_ADEQUACY_FORMULAS"
            "_AND_TRUTHFUL_OBSERVATION_SEMANTICS__CERTIFICATE_IDS_ARE_REFERENCES_NOT_SELF_VERIFICATION"
        ),
    }
