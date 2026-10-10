"""Finite future-outcome totality certificate for one reached escape state.

This module proves a stronger, still bounded fact than the one-step reached-state
kernel: for one exact finite authenticated state, every possible sequence of the
kernel's selected truthful discriminator outcomes terminates in a cell with a
common authenticated safe adequate policy.

It does not prove global ESCAPE_PROGRESS_TOTALITY.  It proves totality only for
the exact supplied reached state under its exact current policy/discriminator
family.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime import reached_escape_state_kernel_v1 as kernel

SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_FINITE_TOTALITY_CERTIFICATE_V1"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "reached_state_future_outcome_totality_proved": False,
        "global_escape_progress_totality_proved": False,
        "open_ended_mission_terminal_proved": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _restrict(state: Mapping[str, Any], region_ids: Sequence[str]) -> dict[str, Any]:
    ids = sorted(set(region_ids))
    wanted = set(ids)
    return {
        "regions": [{"region_id": rid} for rid in ids],
        "policies": [
            {
                **deepcopy(dict(row)),
                "adequate_region_ids": [
                    rid for rid in row["adequate_region_ids"] if rid in wanted
                ],
            }
            for row in state["policies"]
        ],
        "discriminators": [
            {
                **deepcopy(dict(row)),
                "outcomes": {rid: deepcopy(row["outcomes"][rid]) for rid in ids},
            }
            for row in state["discriminators"]
        ],
    }


def _policy_sets(state: Mapping[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for region in state["regions"]:
        rid = region["region_id"]
        out[rid] = sorted(
            row["policy_id"]
            for row in state["policies"]
            if rid in row["adequate_region_ids"]
        )
    return out


def _equivalence_classes(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[str]] = {}
    discriminators = list(state["discriminators"])
    for region in state["regions"]:
        rid = region["region_id"]
        signature = tuple(
            kernel._canon(row["outcomes"][rid]) for row in discriminators
        )
        groups.setdefault(signature, []).append(rid)

    rows: list[dict[str, Any]] = []
    for signature, ids in sorted(groups.items(), key=lambda item: item[0]):
        sub = _restrict(state, ids)
        common = kernel._common_policies(sub)
        rows.append(
            {
                "region_ids": sorted(ids),
                "discriminator_signature": list(signature),
                "common_adequate_policy_ids": common,
            }
        )
    return rows


def _prove_tree(
    state: Mapping[str, Any],
    region_ids: Sequence[str],
    *,
    depth: int = 0,
) -> tuple[dict[str, Any], int]:
    sub = _restrict(state, region_ids)
    ids = [row["region_id"] for row in sub["regions"]]
    common = kernel._common_policies(sub)
    if common:
        return (
            {
                "kind": "COMMON_POLICY_LEAF",
                "region_ids": ids,
                "selected_policy_id": common[0],
                "common_adequate_policy_ids": common,
            },
            depth,
        )

    splitter = kernel._best_splitter(sub)
    if splitter is None:
        raise RuntimeError(
            "THEOREM_INCONSISTENCY__NO_COMMON_POLICY_AND_NO_STRICT_SPLITTER"
        )
    row, parts = splitter
    children = []
    max_depth = depth
    for part in parts:
        child, child_depth = _prove_tree(
            state,
            part["region_ids"],
            depth=depth + 1,
        )
        children.append(
            {
                "outcome": deepcopy(part["outcome"]),
                "region_ids": list(part["region_ids"]),
                "proof": child,
            }
        )
        max_depth = max(max_depth, child_depth)

    return (
        {
            "kind": "STRICT_SPLIT_NODE",
            "region_ids": ids,
            "selected_discriminator_id": row["discriminator_id"],
            "children": children,
        },
        max_depth,
    )


def certify(state: Mapping[str, Any]) -> dict[str, Any]:
    try:
        normalized = kernel._normalize(state)
    except Exception as exc:
        return _fail("REACHED_STATE_NORMALIZATION_FAILED:" + type(exc).__name__ + ":" + str(exc))

    region_ids = [row["region_id"] for row in normalized["regions"]]
    policy_sets = _policy_sets(normalized)
    uncovered = sorted(rid for rid, policies in policy_sets.items() if not policies)
    classes = _equivalence_classes(normalized)
    conflicting_classes = [
        deepcopy(row) for row in classes if not row["common_adequate_policy_ids"]
    ]

    base = {
        "schema": SCHEMA,
        "state_id": normalized["state_id"],
        "state_sha256": normalized["state_sha256"],
        "region_count": len(region_ids),
        "policy_count": len(normalized["policies"]),
        "discriminator_count": len(normalized["discriminators"]),
        "policy_sets_by_region": policy_sets,
        "discriminator_equivalence_classes": classes,
        "regionwise_policy_coverage_proved": not uncovered,
        "uncovered_region_ids": uncovered,
        "indistinguishable_class_common_policy_proved": not conflicting_classes,
        "indistinguishable_policy_conflict_classes": conflicting_classes,
        "global_escape_progress_totality_proved": False,
        "open_ended_mission_terminal_proved": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

    if uncovered:
        return {
            **base,
            "pass": False,
            "status": "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY",
            "reached_state_future_outcome_totality_proved": False,
        }

    if conflicting_classes:
        return {
            **base,
            "pass": False,
            "status": "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY",
            "reached_state_future_outcome_totality_proved": False,
        }

    try:
        proof_tree, max_depth = _prove_tree(normalized, region_ids)
    except Exception as exc:
        return _fail(
            "CONSTRUCTIVE_REPLAY_FAILED:" + type(exc).__name__ + ":" + str(exc),
            state_id=normalized["state_id"],
            state_sha256=normalized["state_sha256"],
        )

    upper = max(0, len(region_ids) - 1)
    if max_depth > upper:
        return _fail(
            "SPLIT_DEPTH_BOUND_VIOLATED",
            state_id=normalized["state_id"],
            state_sha256=normalized["state_sha256"],
            observed_max_split_depth=max_depth,
            theoretical_upper_bound=upper,
        )

    return {
        **base,
        "pass": True,
        "status": "PASS__ALL_DISCRIMINATOR_OUTCOME_PATHS_TERMINATE_IN_COMMON_POLICY_CELLS",
        "reached_state_future_outcome_totality_proved": True,
        "all_possible_selected_discriminator_outcomes_covered": True,
        "proof_tree": proof_tree,
        "max_selected_discriminator_depth": max_depth,
        "split_depth_upper_bound": upper,
        "proof_law": (
            "FINITE_REGION_COUNT_STRICTLY_DECREASES_ON_EVERY_NONTERMINAL_SPLIT;"
            "IF_ALL_CURRENT_DISCRIMINATORS_ARE_CONSTANT_ON_A_REACHED_CELL_THEN_THE_CELL_IS_"
            "CONTAINED_IN_ONE_GLOBAL_DISCRIMINATOR_EQUIVALENCE_CLASS;"
            "EVERY_SUCH_EQUIVALENCE_CLASS_HAS_A_COMMON_AUTHENTICATED_SAFE_ADEQUATE_POLICY;"
            "THEREFORE_THE_EXISTING_KERNEL_CANNOT_REACH_AN_UNSPLITTABLE_NONTERMINAL_CELL."
        ),
        "hard_nonclaims": [
            "NO_GLOBAL_ESCAPE_PROGRESS_TOTALITY",
            "NO_CLAIM_FUTURE_ACQUIRED_REGIONS_POLICIES_OR_DISCRIMINATORS_PRESERVE_THIS_CERTIFICATE",
            "NO_CLAIM_TRUTHFUL_DISCRIMINATOR_OBSERVATIONS_ARE_FREE_OR_INSTANT",
            "NO_OPEN_ENDED_MISSION_TERMINAL_CLAIM",
        ],
    }


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    return certify(args.get("state"))
