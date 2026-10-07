"""Observable policy-cover totality gate V1.

For one *complete finite policy-relevant state model*, this gate removes recursive
"prove progress at every state" bookkeeping.

It computes an exact finite observation policy over the supplied truthful,
safe discriminators. A node is terminal as soon as one independently certified
Brain-owned policy is adequate for every world still possible at that node.
Otherwise only a discriminator that strictly partitions the current world set
may be selected.

Positive result:
  every execution path reaches a common adequate policy in finite cost, so the
  bound state has terminal-or-strict-refinement totality.

Negative result:
  the returned unresolved observational classes are unresolved *relative to the
  supplied discriminator library*. They are an information-theoretic
  impossibility witness only if a separate authority proves that library
  complete. This module never grants U-empty or terminal authority.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OBSERVABLE_POLICY_COVER_TOTALITY_GATE_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "bound_state_totality_proved": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _auth_receipt(
    value: Any,
    *,
    required: Mapping[str, Any],
    label: str,
) -> tuple[bool, str | None]:
    if not isinstance(value, Mapping):
        return False, label + "_RECEIPT_REQUIRED"
    common = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
    }
    for key, expected in {**common, **dict(required)}.items():
        if value.get(key) != expected:
            return False, label + "_RECEIPT_INVALID:" + key
    return True, None


def evaluate(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_MAPPING_REQUIRED")

    state_id = problem.get("state_id")
    if not isinstance(state_id, str) or not state_id:
        return _fail("STATE_ID_REQUIRED")

    worlds = problem.get("worlds")
    if (
        not isinstance(worlds, Sequence)
        or isinstance(worlds, (str, bytes))
        or not worlds
    ):
        return _fail("WORLDS_REQUIRED")

    world_ids: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(worlds):
        if not isinstance(row, Mapping):
            return _fail("WORLD_INVALID", index=i)
        wid = row.get("world_id")
        if not isinstance(wid, str) or not wid or wid in seen:
            return _fail("WORLD_ID_INVALID", index=i)
        seen.add(wid)
        world_ids.append(wid)
    universe = frozenset(world_ids)

    ok, reason = _auth_receipt(
        problem.get("world_set_completeness_receipt"),
        required={"policy_relevant_world_set_complete": True, "state_id": state_id},
        label="WORLD_SET_COMPLETENESS",
    )
    if not ok:
        return _fail(str(reason))

    policies = problem.get("policies")
    if (
        not isinstance(policies, Sequence)
        or isinstance(policies, (str, bytes))
        or not policies
    ):
        return _fail("POLICIES_REQUIRED")

    policy_regions: dict[str, frozenset[str]] = {}
    policy_costs: dict[str, float] = {}
    for i, row in enumerate(policies):
        if not isinstance(row, Mapping):
            return _fail("POLICY_INVALID", index=i)
        pid = row.get("policy_id")
        members = row.get("adequate_world_ids")
        cost = row.get("cost_units")
        if not isinstance(pid, str) or not pid or pid in policy_regions:
            return _fail("POLICY_ID_INVALID", index=i)
        if (
            not isinstance(members, Sequence)
            or isinstance(members, (str, bytes))
            or not members
            or any(not isinstance(x, str) or not x for x in members)
        ):
            return _fail("POLICY_REGION_INVALID", policy_id=pid)
        member_set = frozenset(members)
        if not member_set.issubset(universe):
            return _fail("POLICY_REGION_OUTSIDE_WORLD_SET", policy_id=pid)
        if (
            not isinstance(cost, (int, float))
            or isinstance(cost, bool)
            or cost < 0
        ):
            return _fail("POLICY_COST_INVALID", policy_id=pid)
        ok, reason = _auth_receipt(
            row.get("adequacy_receipt"),
            required={
                "policy_id": pid,
                "policy_adequate_on_every_listed_world": True,
                "brain_owned": True,
                "deployed_exact": True,
                "resource_bound_proved": True,
            },
            label="POLICY_ADEQUACY",
        )
        if not ok:
            return _fail(str(reason), policy_id=pid)
        policy_regions[pid] = member_set
        policy_costs[pid] = float(cost)

    observations = problem.get("discriminators", [])
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        return _fail("DISCRIMINATORS_INVALID")

    obs: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(observations):
        if not isinstance(row, Mapping):
            return _fail("DISCRIMINATOR_INVALID", index=i)
        did = row.get("discriminator_id")
        outcomes = row.get("outcomes")
        cost = row.get("cost_units")
        if not isinstance(did, str) or not did or did in obs:
            return _fail("DISCRIMINATOR_ID_INVALID", index=i)
        if not isinstance(outcomes, Mapping) or set(outcomes) != set(universe):
            return _fail("DISCRIMINATOR_OUTCOME_MAP_INCOMPLETE", discriminator_id=did)
        if (
            not isinstance(cost, (int, float))
            or isinstance(cost, bool)
            or cost < 0
        ):
            return _fail("DISCRIMINATOR_COST_INVALID", discriminator_id=did)
        ok, reason = _auth_receipt(
            row.get("truth_safety_receipt"),
            required={
                "discriminator_id": did,
                "outcome_map_complete": True,
                "truth_preserving": True,
                "safe_on_entire_state": True,
                "resource_bound_proved": True,
            },
            label="DISCRIMINATOR",
        )
        if not ok:
            return _fail(str(reason), discriminator_id=did)
        # repr gives a deterministic equality key for JSON-like outcome values.
        obs[did] = {
            "cost": float(cost),
            "outcomes": {wid: repr(outcomes[wid]) for wid in world_ids},
        }

    def common_policies(state: frozenset[str]) -> tuple[str, ...]:
        return tuple(
            sorted(pid for pid, region in policy_regions.items() if state.issubset(region))
        )

    def partition(state: frozenset[str], did: str) -> tuple[frozenset[str], ...]:
        buckets: dict[str, set[str]] = {}
        for wid in state:
            buckets.setdefault(obs[did]["outcomes"][wid], set()).add(wid)
        return tuple(
            frozenset(v)
            for _, v in sorted(buckets.items(), key=lambda item: item[0])
        )

    @lru_cache(maxsize=None)
    def solve(state: frozenset[str]):
        covers = common_policies(state)
        if covers:
            best_policy = min(covers, key=lambda pid: (policy_costs[pid], pid))
            return {
                "possible": True,
                "worst_cost": policy_costs[best_policy],
                "policy_id": best_policy,
                "discriminator_id": None,
                "children": (),
            }

        best = None
        for did in sorted(obs):
            parts = partition(state, did)
            if len(parts) <= 1:
                continue
            children = [solve(part) for part in parts]
            if not all(child["possible"] for child in children):
                continue
            worst = obs[did]["cost"] + max(child["worst_cost"] for child in children)
            candidate = {
                "possible": True,
                "worst_cost": worst,
                "policy_id": None,
                "discriminator_id": did,
                "children": tuple((tuple(sorted(part)), child) for part, child in zip(parts, children)),
            }
            if best is None or (candidate["worst_cost"], did) < (
                best["worst_cost"],
                str(best["discriminator_id"]),
            ):
                best = candidate
        if best is not None:
            return best
        return {
            "possible": False,
            "worst_cost": float("inf"),
            "policy_id": None,
            "discriminator_id": None,
            "children": (),
        }

    root = solve(universe)

    # Full observational equivalence classes under the supplied library. These
    # are diagnostic on failure and exact for this declared discriminator set.
    signatures: dict[tuple[tuple[str, str], ...], list[str]] = {}
    for wid in world_ids:
        sig = tuple((did, obs[did]["outcomes"][wid]) for did in sorted(obs))
        signatures.setdefault(sig, []).append(wid)
    unresolved_classes = []
    for members in signatures.values():
        state = frozenset(members)
        if not common_policies(state):
            unresolved_classes.append(sorted(members))
    unresolved_classes.sort()

    if not root["possible"]:
        library_complete = False
        if problem.get("discriminator_library_scope_complete") is True:
            library_ok, _ = _auth_receipt(
                problem.get("discriminator_library_completeness_receipt"),
                required={
                    "discriminator_library_scope_complete": True,
                    "state_id": state_id,
                },
                label="DISCRIMINATOR_LIBRARY_COMPLETENESS",
            )
            library_complete = library_ok
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNRESOLVED__NO_ADAPTIVE_COMMON_POLICY_COVER_FROM_DECLARED_DISCRIMINATORS",
            "state_id": state_id,
            "world_count": len(universe),
            "policy_count": len(policy_regions),
            "discriminator_count": len(obs),
            "unresolved_observational_classes": unresolved_classes,
            "negative_impossibility_authorized": library_complete,
            "bound_state_totality_proved": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "FAILURE_IS_RELATIVE_TO_DECLARED_DISCRIMINATORS_UNLESS_A_SEPARATE_"
                "SCOPE_COMPLETE_LIBRARY_RECEIPT_PROVES_NO_OTHER_AUTHORIZED_SEPARATOR_EXISTS"
            ),
        }

    def serialize(node: Mapping[str, Any]) -> dict[str, Any]:
        if node["policy_id"] is not None:
            return {
                "terminal_policy_id": node["policy_id"],
                "worst_case_remaining_cost_units": node["worst_cost"],
            }
        return {
            "discriminator_id": node["discriminator_id"],
            "worst_case_remaining_cost_units": node["worst_cost"],
            "outcome_partitions": [
                {"world_ids": list(part), "next": serialize(child)}
                for part, child in node["children"]
            ],
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__BOUND_STATE_TERMINAL_OR_STRICT_REFINEMENT_TOTALITY",
        "state_id": state_id,
        "world_count": len(universe),
        "policy_count": len(policy_regions),
        "discriminator_count": len(obs),
        "minimum_worst_case_resource_bound_units": root["worst_cost"],
        "decision_tree": serialize(root),
        "unresolved_observational_classes": [],
        "bound_state_totality_proved": True,
        "strict_refinement_by_construction": True,
        "finite_termination_by_finite_partition_descent": True,
        "complete_raw_semantic_world_model_required": False,
        "complete_discriminator_library_required_for_positive_proof": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "proof_rule": (
            "COMPLETE_BOUND_POLICY_RELEVANT_WORLD_SET__SOUND_POSITIVE_POLICY_REGIONS__"
            "TRUTHFUL_SAFE_COMPLETE_OUTCOME_MAPS_FOR_USED_DISCRIMINATORS__"
            "EVERY_NONTERMINAL_NODE_STRICTLY_PARTITIONS__EVERY_LEAF_HAS_ONE_COMMON_"
            "ADEQUATE_BRAIN_POLICY__THEREFORE_BOUND_STATE_TOTALITY"
        ),
    }
