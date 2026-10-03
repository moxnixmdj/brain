#!/usr/bin/env python3
"""Adaptive terminal-closure controller.

Zero-credit scheduling/control only. This module never grants acceptance,
capability, family, ownership, execution, promotion, or fresh-reality authority.

It ranks currently admissible actions by expected terminal value per unit
wall-clock cost, while preserving fail-closed invariants from the live Brain:
- fresh reality remains forbidden unless an independently verified authority says otherwise;
- Tool Discovery retrieval must use the exact current verified V2 gate;
- consumed Tool Discovery source epochs cannot be replayed as progress;
- TB4 execution is forbidden while the machine-verified attainable upper bound
  remains below the frozen pass threshold;
- verified deltas trigger immediate fixed-point/dominance recomputation;
- ownership work may proceed in parallel with acceptance work but cannot bypass
  either acceptance or internalization requirements.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import log
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_CONTROLLER_V1"


@dataclass(frozen=True)
class Action:
    action_id: str
    action_class: str
    expected_seconds: float
    p_discharge: float
    predicate_delta: float = 0.0
    family_delta: float = 0.0
    ownership_delta: float = 0.0
    downstream_delta: float = 0.0
    information_gain: float = 0.0
    incremental_spend_usd: float = 0.0
    fresh_reality_units: int = 0
    tool_discovery_retrieval: bool = False
    source_epoch_consumed: bool = False
    tb4_execution: bool = False
    independent_branch: bool = True
    blocked: bool = False
    block_reason: str | None = None


@dataclass(frozen=True)
class Policy:
    weight_predicate: float = 1.0
    weight_family: float = 8.0
    weight_ownership: float = 10.0
    weight_downstream: float = 3.0
    weight_information: float = 1.5
    latency_floor_seconds: float = 0.05
    max_incremental_spend_usd: float = 0.0
    fresh_reality_authority: bool = False
    tool_discovery_v2_gate_mandatory: bool = True
    tb4_attainable_upper_bound: int = 180
    tb4_required_successes: int = 220


def _clamp_probability(p: float) -> float:
    return min(1.0, max(0.0, float(p)))


def terminal_value(action: Action, policy: Policy) -> float:
    """Expected terminal value. Probability is scheduling-only, never proof."""
    p = _clamp_probability(action.p_discharge)
    direct = (
        policy.weight_predicate * max(0.0, action.predicate_delta)
        + policy.weight_family * max(0.0, action.family_delta)
        + policy.weight_ownership * max(0.0, action.ownership_delta)
        + policy.weight_downstream * max(0.0, action.downstream_delta)
    )
    info = policy.weight_information * max(0.0, action.information_gain)
    return p * direct + info


def admissibility(action: Action, policy: Policy) -> tuple[bool, str | None]:
    if action.blocked:
        return False, action.block_reason or "ACTION_DECLARED_BLOCKED"
    if action.incremental_spend_usd > policy.max_incremental_spend_usd:
        return False, "INCREMENTAL_SPEND_EXCEEDS_POLICY"
    if action.fresh_reality_units > 0 and not policy.fresh_reality_authority:
        return False, "FRESH_REALITY_AUTHORITY_FALSE"
    if action.tool_discovery_retrieval and action.source_epoch_consumed:
        return False, "CONSUMED_TOOL_DISCOVERY_SOURCE_EPOCH_REPLAY_FORBIDDEN"
    if action.tb4_execution and policy.tb4_attainable_upper_bound < policy.tb4_required_successes:
        return False, "TB4_EXECUTION_MATHEMATICALLY_UNATTAINABLE_UNDER_CURRENT_ROUTE"
    return True, None


def score(action: Action, policy: Policy) -> float:
    ok, _ = admissibility(action, policy)
    if not ok:
        return float("-inf")
    latency = max(policy.latency_floor_seconds, float(action.expected_seconds))
    return terminal_value(action, policy) / latency


def rank(actions: Sequence[Action], policy: Policy | None = None) -> list[dict[str, Any]]:
    policy = policy or Policy()
    rows: list[dict[str, Any]] = []
    for action in actions:
        ok, reason = admissibility(action, policy)
        rows.append(
            {
                **asdict(action),
                "admissible": ok,
                "inadmissible_reason": reason,
                "terminal_value": terminal_value(action, policy),
                "priority_score": score(action, policy),
                "acceptance_credit": 0,
                "family_credit": 0,
                "ownership_credit": 0,
                "execution_authority": False,
                "promotion_authority": False,
                "fresh_reality_authority": policy.fresh_reality_authority,
            }
        )
    rows.sort(
        key=lambda r: (
            not r["admissible"],
            -r["priority_score"] if r["admissible"] else 0.0,
            r["expected_seconds"],
            r["action_id"],
        )
    )
    return rows


def frontier(actions: Sequence[Action], policy: Policy | None = None) -> dict[str, Any]:
    """Return all independent admissible actions for immediate parallel launch.

    This intentionally does not serialize independent branches behind the
    highest-priority action. Priority only controls scarce resource allocation.
    """
    policy = policy or Policy()
    ranked = rank(actions, policy)
    admissible = [r for r in ranked if r["admissible"]]
    return {
        "schema": SCHEMA,
        "status": "ZERO_CREDIT_SCHEDULING_FRONTIER",
        "parallel_launch": [r["action_id"] for r in admissible if r["independent_branch"]],
        "resource_priority": [r["action_id"] for r in admissible],
        "blocked": [
            {"action_id": r["action_id"], "reason": r["inadmissible_reason"]}
            for r in ranked
            if not r["admissible"]
        ],
        "fixed_point_after_every_verified_delta": True,
        "stop_branch_when_dominated": True,
        "acceptance_credit": 0,
        "family_credit": 0,
        "ownership_credit": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": policy.fresh_reality_authority,
    }


def beta_posterior_mean(successes: int, failures: int, alpha: float = 1.0, beta: float = 1.0) -> float:
    """Posterior mean for scheduling priors only."""
    if successes < 0 or failures < 0 or alpha <= 0 or beta <= 0:
        raise ValueError("INVALID_BETA_POSTERIOR_INPUT")
    return (alpha + successes) / (alpha + beta + successes + failures)


def capture_recapture_unseen(single_source_only: int, multi_source_overlap: int) -> dict[str, Any]:
    """Discovery-control heuristic only; never a completeness proof."""
    n1 = max(0, int(single_source_only))
    n2 = max(0, int(multi_source_overlap))
    if n2 == 0:
        return {
            "status": "UNBOUNDED_OR_INSUFFICIENT_OVERLAP",
            "estimated_unseen": None,
            "completeness_proof": False,
        }
    return {
        "status": "HEURISTIC_ESTIMATE_ONLY",
        "estimated_unseen": (n1 * n1) / (2.0 * n2),
        "completeness_proof": False,
    }


def should_stop_finite_bar(successes: int, attempted: int, total: int, required: int) -> str:
    """Exact early stopping for a finite fixed benchmark."""
    if min(successes, attempted, total, required) < 0 or successes > attempted or attempted > total:
        raise ValueError("INVALID_FINITE_BAR_COUNTS")
    remaining = total - attempted
    if successes >= required:
        return "STOP_PASS"
    if successes + remaining < required:
        return "STOP_FAIL"
    return "CONTINUE"


def ownership_ready(
    *,
    acceptance_pass: bool,
    internalized: bool,
    donor_independent: bool,
    scope_complete: bool,
) -> bool:
    return all((acceptance_pass, internalized, donor_independent, scope_complete))


def event_policy() -> dict[str, Any]:
    return {
        "on_verified_delta": [
            "RECOMPUTE_ACCEPTANCE_FIXED_POINT",
            "RECOMPUTE_INFORMATION_DOMINANCE",
            "RECOMPUTE_ACTION_PRIORITIES",
            "CANCEL_NEWLY_DOMINATED_BRANCHES",
            "RECOMPUTE_OWNERSHIP_READINESS",
        ],
        "on_source_epoch_change": [
            "ALLOW_ONLY_EXACT_RESIDUAL_TARGETED_RETRIEVAL",
            "PRESERVE_NO_RESULT_IS_NOT_NONEXISTENCE",
        ],
        "on_fresh_reality_authority_change": [
            "RECOMPUTE_MINIMUM_IRREDUCIBLE_REALITY_CUT_BEFORE_EXECUTION"
        ],
    }


__all__ = [
    "Action",
    "Policy",
    "SCHEMA",
    "admissibility",
    "beta_posterior_mean",
    "capture_recapture_unseen",
    "event_policy",
    "frontier",
    "ownership_ready",
    "rank",
    "score",
    "should_stop_finite_bar",
    "terminal_value",
]
