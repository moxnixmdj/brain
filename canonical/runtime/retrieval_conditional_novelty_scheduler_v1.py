"""Conditional-novelty scheduler for Retrieval V6.

Ranks actions by expected *marginal* discovery value, not source fame or raw hit
count. Scores are scheduling heuristics, never calibrated probability claims.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_RETRIEVAL_CONDITIONAL_NOVELTY_SCHEDULER_V1"


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def rank_actions(
    actions: Sequence[Mapping[str, Any]],
    observations: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    closure_value: float = 1.0,
) -> dict[str, Any]:
    if closure_value <= 0:
        raise ValueError("CLOSURE_VALUE_MUST_BE_POSITIVE")
    observations = observations or {}
    global_seen: set[str] = set()
    by_action: dict[str, set[str]] = {}
    for aid, obs in observations.items():
        ids = {str(x) for x in (obs.get("candidate_ids") or []) if str(x)}
        by_action[str(aid)] = ids
        global_seen |= ids

    rows: list[dict[str, Any]] = []
    seen_action_ids: set[str] = set()
    for raw in actions:
        if not isinstance(raw, Mapping):
            raise ValueError("ACTION_MAPPING_REQUIRED")
        aid = _canon(raw.get("action_id"))
        if not aid or aid in seen_action_ids:
            raise ValueError("ACTION_ID_REQUIRED_UNIQUE")
        seen_action_ids.add(aid)
        source_group = _canon(raw.get("source_group")) or "UNKNOWN"
        latency = max(1.0, float(raw.get("latency_cost", 1.0)))
        requests = max(0.0, float(raw.get("request_cost", 1.0)))
        risk = max(0.0, float(raw.get("reliability_risk", 0.0)))
        obs = observations.get(aid) or {}
        attempts = max(0, int(obs.get("attempts", 0)))
        own = by_action.get(aid, set())
        others = global_seen - own
        marginal_ids = own - others
        marginal_successes = max(0, min(attempts, int(obs.get("marginal_successes", len(marginal_ids) > 0))))
        novelty_rate = (marginal_successes + 1.0) / (attempts + 2.0)
        overlap = (len(own & others) / len(own)) if own else 0.0
        independence = max(0.05, 1.0 - overlap)
        structural_bonus = 1.25 if raw.get("orthogonal_channel") is True else 1.0
        denominator = latency + requests + 2.0 * risk
        score = closure_value * novelty_rate * independence * structural_bonus / denominator
        rows.append({
            "action_id": aid,
            "source_group": source_group,
            "priority_score": score,
            "posterior_marginal_yield_heuristic": novelty_rate,
            "observed_overlap_fraction": overlap,
            "independence_factor": independence,
            "structural_bonus": structural_bonus,
            "attempts": attempts,
            "candidate_count": len(own),
            "marginal_candidate_count": len(marginal_ids),
            "score_is_calibrated_probability": False,
        })

    rows.sort(key=lambda x: (-x["priority_score"], x["action_id"]))
    return {
        "schema": SCHEMA,
        "status": "RANKED",
        "actions": rows,
        "selected_action_id": rows[0]["action_id"] if rows else None,
        "hard_rules": [
            "RANK_BY_MARGINAL_NOVELTY_NOT_RAW_HIT_COUNT",
            "ORTHOGONAL_CHANNELS_RECEIVE_STRUCTURAL_DIVERSITY_BONUS",
            "HEURISTIC_SCORE_IS_NOT_A_CALIBRATED_PROBABILITY",
            "RANKING_CANNOT_DELETE_MONOTONIC_LEDGER_CANDIDATES",
        ],
        "acceptance_credit_delta": 0,
    }
