"""Deterministic reached-state escape kernel for Project Brain.

This module does not prove the open-ended mission is terminal. It evaluates one
actually reached finite decision region using only authenticated safe policy
adequacy and authenticated safe truthful complete discriminator maps.

For that reached state it returns exactly one constructive result:
1. TERMINALIZE_WITH_COMMON_POLICY
2. STRICT_PROGRESS_WITH_DISCRIMINATOR
3. UNSPLITTABLE_POLICY_CONFLICT with a content-addressed repair request.

The third result is not failure disguised as success. It preserves the exact
obstruction and asks for one of the only two mechanism-changing repairs:
a new truthful splitter or a common adequate policy.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_STATE_KERNEL_V1"
STATE_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_STATE_V1"
REPAIR_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_REPAIR_REQUEST_V1"
MAX_REGIONS = 4096
MAX_POLICIES = 4096
MAX_DISCRIMINATORS = 4096


class ReachedEscapeStateError(ValueError):
    pass


def _canon(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ReachedEscapeStateError("NON_CANONICAL_JSON_VALUE") from exc


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _rows(value: Any, *, label: str, maximum: int, nonempty: bool = False) -> list[Mapping[str, Any]]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > maximum
        or (nonempty and len(value) == 0)
    ):
        raise ReachedEscapeStateError(label + "_INVALID")
    rows: list[Mapping[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise ReachedEscapeStateError(label + "_ROW_INVALID")
        rows.append(row)
    return rows


def _id(raw: Any, *, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw.strip()) > 512:
        raise ReachedEscapeStateError(label + "_INVALID")
    return raw.strip()


def _normalize(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping) or state.get("schema") != STATE_SCHEMA:
        raise ReachedEscapeStateError("STATE_SCHEMA_INVALID")

    region_rows = _rows(
        state.get("regions"), label="REGIONS", maximum=MAX_REGIONS, nonempty=True
    )
    region_ids: list[str] = []
    region_seen: set[str] = set()
    for row in region_rows:
        rid = _id(row.get("region_id"), label="REGION_ID")
        if rid in region_seen:
            raise ReachedEscapeStateError("DUPLICATE_REGION_ID:" + rid)
        region_seen.add(rid)
        region_ids.append(rid)
    region_ids.sort()
    region_set = set(region_ids)

    policy_rows = _rows(
        state.get("policies", []), label="POLICIES", maximum=MAX_POLICIES
    )
    policies: list[dict[str, Any]] = []
    policy_seen: set[str] = set()
    for row in policy_rows:
        pid = _id(row.get("policy_id"), label="POLICY_ID")
        if pid in policy_seen:
            raise ReachedEscapeStateError("DUPLICATE_POLICY_ID:" + pid)
        policy_seen.add(pid)
        if row.get("authenticated") is not True or row.get("safe") is not True:
            raise ReachedEscapeStateError("POLICY_NOT_AUTHENTICATED_SAFE:" + pid)
        adequacy = row.get("adequate_region_ids")
        if (
            not isinstance(adequacy, Sequence)
            or isinstance(adequacy, (str, bytes, bytearray))
        ):
            raise ReachedEscapeStateError("POLICY_ADEQUACY_SET_INVALID:" + pid)
        normalized_adequacy: list[str] = []
        for raw in adequacy:
            rid = _id(raw, label="POLICY_ADEQUACY_REGION_ID")
            if rid not in region_set:
                raise ReachedEscapeStateError(
                    "POLICY_ADEQUACY_REGION_OUTSIDE_STATE:" + pid + ":" + rid
                )
            if rid not in normalized_adequacy:
                normalized_adequacy.append(rid)
        normalized_adequacy.sort()
        policies.append(
            {
                "policy_id": pid,
                "adequate_region_ids": normalized_adequacy,
                "authenticated": True,
                "safe": True,
            }
        )
    policies.sort(key=lambda row: row["policy_id"])

    discriminator_rows = _rows(
        state.get("discriminators", []),
        label="DISCRIMINATORS",
        maximum=MAX_DISCRIMINATORS,
    )
    discriminators: list[dict[str, Any]] = []
    discriminator_seen: set[str] = set()
    for row in discriminator_rows:
        did = _id(row.get("discriminator_id"), label="DISCRIMINATOR_ID")
        if did in discriminator_seen:
            raise ReachedEscapeStateError("DUPLICATE_DISCRIMINATOR_ID:" + did)
        discriminator_seen.add(did)
        if (
            row.get("authenticated") is not True
            or row.get("safe") is not True
            or row.get("truthful") is not True
            or row.get("complete") is not True
        ):
            raise ReachedEscapeStateError(
                "DISCRIMINATOR_NOT_AUTHENTICATED_SAFE_TRUTHFUL_COMPLETE:" + did
            )
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, Mapping):
            raise ReachedEscapeStateError("DISCRIMINATOR_OUTCOMES_INVALID:" + did)
        keys = {str(k) for k in outcomes}
        if keys != region_set:
            raise ReachedEscapeStateError(
                "DISCRIMINATOR_OUTCOME_DOMAIN_NOT_EXACT:" + did
            )
        normalized_outcomes: dict[str, Any] = {}
        for rid in region_ids:
            value = outcomes[rid]
            _canon(value)
            normalized_outcomes[rid] = value
        discriminators.append(
            {
                "discriminator_id": did,
                "outcomes": normalized_outcomes,
                "authenticated": True,
                "safe": True,
                "truthful": True,
                "complete": True,
            }
        )
    discriminators.sort(key=lambda row: row["discriminator_id"])

    normalized = {
        "schema": STATE_SCHEMA,
        "state_id": _id(state.get("state_id"), label="STATE_ID"),
        "regions": [{"region_id": rid} for rid in region_ids],
        "policies": policies,
        "discriminators": discriminators,
    }
    normalized["state_sha256"] = _digest(normalized)
    return normalized


def _common_policies(state: Mapping[str, Any]) -> list[str]:
    region_ids = {row["region_id"] for row in state["regions"]}
    out = [
        row["policy_id"]
        for row in state["policies"]
        if region_ids.issubset(set(row["adequate_region_ids"]))
    ]
    return sorted(out)


def _partition(discriminator: Mapping[str, Any], region_ids: Sequence[str]) -> list[dict[str, Any]]:
    groups: dict[str, tuple[Any, list[str]]] = {}
    for rid in region_ids:
        outcome = discriminator["outcomes"][rid]
        key = _canon(outcome)
        if key not in groups:
            groups[key] = (outcome, [])
        groups[key][1].append(rid)
    rows = [
        {"outcome": outcome, "region_ids": sorted(ids)}
        for _key, (outcome, ids) in sorted(groups.items())
    ]
    return rows


def _best_splitter(state: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[dict[str, Any]]] | None:
    region_ids = [row["region_id"] for row in state["regions"]]
    n = len(region_ids)
    candidates: list[tuple[tuple[Any, ...], Mapping[str, Any], list[dict[str, Any]]]] = []
    for row in state["discriminators"]:
        parts = _partition(row, region_ids)
        if len(parts) <= 1:
            continue
        sizes = sorted((len(part["region_ids"]) for part in parts), reverse=True)
        if any(size <= 0 or size >= n for size in sizes):
            raise ReachedEscapeStateError(
                "NONCONSTANT_DISCRIMINATOR_FAILED_STRICT_SHRINK:"
                + row["discriminator_id"]
            )
        score = (
            max(sizes),
            sum(size * size for size in sizes),
            len(parts) * -1,
            row["discriminator_id"],
        )
        candidates.append((score, row, parts))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    _score, row, parts = candidates[0]
    return row, parts


def evaluate(state: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one reached finite escape state without global completion claims."""
    try:
        normalized = _normalize(state)
    except ReachedEscapeStateError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": str(exc),
            "global_escape_progress_totality_proved": False,
            "open_ended_mission_terminal_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    state_sha = normalized["state_sha256"]
    region_ids = [row["region_id"] for row in normalized["regions"]]
    common = _common_policies(normalized)
    base = {
        "schema": SCHEMA,
        "pass": True,
        "state_id": normalized["state_id"],
        "state_sha256": state_sha,
        "region_count": len(region_ids),
        "global_escape_progress_totality_proved": False,
        "open_ended_mission_terminal_proved": False,
        "terminal_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }

    if common:
        return {
            **base,
            "status": "TERMINALIZE_WITH_COMMON_POLICY",
            "reached_state_progress_proved": True,
            "selected_policy_id": common[0],
            "common_adequate_policy_ids": common,
            "policy_selection_rule": "LEXICOGRAPHIC_MINIMUM_AUTHENTICATED_SAFE_COMMON_ADEQUATE_POLICY_ID",
            "next_action": {
                "kind": "RETURN_COMMON_ADEQUATE_POLICY",
                "policy_id": common[0],
                "requires_normal_execution_and_acceptance_authority": True,
            },
        }

    splitter = _best_splitter(normalized)
    if splitter is not None:
        row, parts = splitter
        max_branch = max(len(part["region_ids"]) for part in parts)
        return {
            **base,
            "status": "STRICT_PROGRESS_WITH_DISCRIMINATOR",
            "reached_state_progress_proved": True,
            "selected_discriminator_id": row["discriminator_id"],
            "outcome_partition": parts,
            "all_nonempty_branches_strict_subsets": True,
            "parent_region_count": len(region_ids),
            "maximum_branch_region_count": max_branch,
            "minimum_worst_case_region_elimination": len(region_ids) - max_branch,
            "selection_rule": "MINIMIZE_MAX_BRANCH_THEN_SUM_SQUARED_BRANCH_SIZES_THEN_MAXIMIZE_BRANCH_COUNT_THEN_DISCRIMINATOR_ID",
            "next_action": {
                "kind": "ACQUIRE_SELECTED_DISCRIMINATOR_OBSERVATION",
                "discriminator_id": row["discriminator_id"],
                "after_truthful_observation": "RESTRICT_TO_MATCHED_BRANCH_AND_REEVALUATE_KERNEL",
                "execution_authority": False,
            },
        }

    policy_sets = {
        rid: sorted(
            row["policy_id"]
            for row in normalized["policies"]
            if rid in row["adequate_region_ids"]
        )
        for rid in region_ids
    }
    obstruction = {
        "kind": "UNSPLITTABLE_POLICY_CONFLICT",
        "state_sha256": state_sha,
        "region_ids": region_ids,
        "policy_sets_by_region": policy_sets,
        "current_discriminator_ids": [
            row["discriminator_id"] for row in normalized["discriminators"]
        ],
        "common_adequate_policy_ids": [],
        "all_current_discriminators_constant_on_current_region": True,
    }
    obstruction_sha = _digest(obstruction)
    repair = {
        "schema": REPAIR_SCHEMA,
        "kind": "UNSPLITTABLE_POLICY_CONFLICT_REPAIR",
        "obstruction_sha256": obstruction_sha,
        "state_sha256": state_sha,
        "required_postcondition_any": [
            {
                "repair_class": "ACQUIRE_TRUTHFUL_DISTINGUISHING_OBSERVATION",
                "postcondition": "ADD_ONE_AUTHENTICATED_SAFE_TRUTHFUL_COMPLETE_DISCRIMINATOR_NONCONSTANT_ON_CURRENT_REGION_IDS",
                "preferred_existing_bridge": "R3_DISTINGUISHING_EVIDENCE_ACQUISITION",
            },
            {
                "repair_class": "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY",
                "postcondition": "ADD_ONE_AUTHENTICATED_SAFE_POLICY_ADEQUATE_FOR_EVERY_CURRENT_REGION_ID",
                "preferred_existing_bridge": "R2_POLICY_ADEQUACY_CAPABILITY_EXPANSION_OR_ROOT1_ACQUISITION",
            },
        ],
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "global_acquirability_claimed": False,
    }
    repair["request_sha256"] = _digest(repair)
    return {
        **base,
        "status": "UNSPLITTABLE_POLICY_CONFLICT",
        "reached_state_progress_proved": False,
        "obstruction": obstruction,
        "obstruction_sha256": obstruction_sha,
        "repair_request": repair,
        "hard_nonclaim": "NO_CLAIM_EITHER_REPAIR_CLASS_IS_GLOBALLY_ACQUIRABLE",
    }


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    return evaluate(args.get("state"))
