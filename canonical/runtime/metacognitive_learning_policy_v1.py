"""Fail-closed metacognitive learning-policy compiler.

A strategy may be preferred only from verified matched episodes and only when it
is Pareto-noninferior on task success/safety and no worse on all measured cost
dimensions, with at least one strict improvement. No universal superiority claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

SCHEMA = "PROJECT_BRAIN_METACOGNITIVE_LEARNING_POLICY_V1"


class MetaPolicyError(ValueError):
    pass


def _f(value):
    return value if isinstance(value, Fraction) else Fraction(value)


@dataclass(frozen=True)
class VerifiedEpisode:
    task_id: str
    strategy_id: str
    verified: bool
    success: bool
    safety_violation: bool = False
    wall_clock: Fraction | int | str = 0
    reality_calls: int = 0
    information_actions: int = 0


def _index(episodes: Sequence[VerifiedEpisode], strategy_id: str) -> dict[str, VerifiedEpisode]:
    out = {}
    for episode in episodes:
        if episode.strategy_id != strategy_id:
            continue
        if not episode.verified:
            raise MetaPolicyError("UNVERIFIED_EPISODE_FORBIDDEN:" + episode.task_id)
        if episode.task_id in out:
            raise MetaPolicyError("DUPLICATE_TASK_FOR_STRATEGY:" + episode.task_id)
        out[episode.task_id] = episode
    return out


def compare_strategies(*, episodes: Sequence[VerifiedEpisode],
                       incumbent: str, candidate: str) -> dict:
    base = _index(episodes, incumbent)
    cand = _index(episodes, candidate)
    if not base or not cand:
        raise MetaPolicyError("BOTH_STRATEGIES_REQUIRE_VERIFIED_EPISODES")
    if set(base) != set(cand):
        raise MetaPolicyError("MATCHED_TASK_SET_REQUIRED")

    task_ids = sorted(base)
    success_noninferior = True
    safety_noninferior = True
    strict = False
    base_wall = cand_wall = Fraction(0)
    base_reality = cand_reality = 0
    base_info = cand_info = 0

    for task_id in task_ids:
        b, c = base[task_id], cand[task_id]
        if b.success and not c.success:
            success_noninferior = False
        if (not b.safety_violation) and c.safety_violation:
            safety_noninferior = False
        base_wall += _f(b.wall_clock)
        cand_wall += _f(c.wall_clock)
        base_reality += b.reality_calls
        cand_reality += c.reality_calls
        base_info += b.information_actions
        cand_info += c.information_actions
        if (c.success and not b.success) or (b.safety_violation and not c.safety_violation):
            strict = True

    cost_noninferior = (
        cand_wall <= base_wall
        and cand_reality <= base_reality
        and cand_info <= base_info
    )
    if cand_wall < base_wall or cand_reality < base_reality or cand_info < base_info:
        strict = True

    promoted = success_noninferior and safety_noninferior and cost_noninferior and strict
    return {
        "schema": SCHEMA,
        "matched_task_ids": task_ids,
        "success_noninferior_on_matched_set": success_noninferior,
        "safety_noninferior_on_matched_set": safety_noninferior,
        "cost_noninferior_on_matched_set": cost_noninferior,
        "strict_improvement_exists": strict,
        "incumbent_totals": {
            "wall_clock": str(base_wall),
            "reality_calls": base_reality,
            "information_actions": base_info,
        },
        "candidate_totals": {
            "wall_clock": str(cand_wall),
            "reality_calls": cand_reality,
            "information_actions": cand_info,
        },
        "promotion_allowed_for_environment_class": promoted,
        "universal_superiority_claimed": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def compile_environment_policy(*, environment_class: str, comparison: dict,
                               candidate_strategy: str,
                               evidence_receipts: Sequence[str]) -> dict:
    cls = str(environment_class).strip()
    receipts = [str(x).strip() for x in evidence_receipts if str(x).strip()]
    if not cls or not receipts:
        raise MetaPolicyError("ENVIRONMENT_CLASS_AND_EVIDENCE_REQUIRED")
    if comparison.get("promotion_allowed_for_environment_class") is not True:
        raise MetaPolicyError("STRATEGY_NOT_PROVED_NONINFERIOR_ON_MATCHED_SET")
    return {
        "schema": SCHEMA,
        "environment_class": cls,
        "preferred_learning_strategy": str(candidate_strategy),
        "state": "VERIFIED_MATCHED_POLICY_PREFERENCE",
        "evidence_receipts": receipts,
        "scope": "MATCHED_VERIFIED_EPISODE_CLASS_ONLY",
        "fallback": "UNIVERSAL_LEARNING_V2_DECISION_ROUTER",
        "universal_superiority_claimed": False,
    }
