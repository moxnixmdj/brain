"""Exact finite-sample proposal-probability estimator for H100 novelty stress tests.

This module does not reveal or execute hidden tasks. It consumes only already-produced,
pre-exposed, independently verified proposal outcomes and computes exact one-sided
Clopper-Pearson lower confidence bounds for the probability that one proposal yields
a useful candidate.

The result is finite-population evidence only. It must never be promoted into an
open-world generalization claim without separate authority.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

INPUT_SCHEMA = "PROJECT_BRAIN_H100_PROPOSAL_PROBABILITY_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_H100_PROPOSAL_PROBABILITY_OUTPUT_V1"
ALPHA = 0.05
HEX = set("0123456789abcdef")


class ProposalProbabilityError(ValueError):
    pass


def _is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and set(value.lower()) <= HEX


def _receipt(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value.get("path"))
        and _is_git_sha(value.get("git_blob_sha"))
    )


def _log_binomial_term(n: int, k: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * math.log(p)
        + (n - k) * math.log1p(-p)
    )


def _binomial_upper_tail(n: int, k: int, p: float) -> float:
    """P[X >= k] for X~Binomial(n,p), evaluated stably."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    logs = [_log_binomial_term(n, j, p) for j in range(k, n + 1)]
    m = max(logs)
    if m == -math.inf:
        return 0.0
    return math.exp(m) * sum(math.exp(x - m) for x in logs)


def clopper_pearson_lower(successes: int, trials: int, alpha: float = ALPHA) -> float:
    """Exact one-sided (1-alpha) Clopper-Pearson lower bound.

    The lower endpoint solves P_p[X >= successes] = alpha.
    """
    if not isinstance(successes, int) or isinstance(successes, bool):
        raise ProposalProbabilityError("SUCCESSES_INVALID")
    if not isinstance(trials, int) or isinstance(trials, bool) or trials <= 0:
        raise ProposalProbabilityError("TRIALS_INVALID")
    if successes < 0 or successes > trials:
        raise ProposalProbabilityError("SUCCESSES_OUT_OF_RANGE")
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not (0.0 < float(alpha) < 1.0):
        raise ProposalProbabilityError("ALPHA_INVALID")
    alpha = float(alpha)
    if successes == 0:
        return 0.0
    if successes == trials:
        return alpha ** (1.0 / trials)

    lo, hi = 0.0, successes / trials
    for _ in range(90):
        mid = (lo + hi) / 2.0
        tail = _binomial_upper_tail(trials, successes, mid)
        if tail < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def n95_from_lower_bound(p_lower: float) -> int | None:
    if not isinstance(p_lower, (int, float)) or isinstance(p_lower, bool):
        raise ProposalProbabilityError("P_LOWER_INVALID")
    p = float(p_lower)
    if p <= 0.0:
        return None
    if p >= 1.0:
        return 1
    return int(math.ceil(math.log(0.05) / math.log1p(-p)))


def _validate_task(row: Mapping[str, Any], index: int) -> tuple[str, int, int, str]:
    task_id = row.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise ProposalProbabilityError(f"TASK_ID_INVALID:{index}")
    if row.get("preexposed_before_outcomes") is not True:
        raise ProposalProbabilityError(f"TASK_NOT_PREEXPOSED:{task_id}")
    if not _receipt(row.get("task_preexposure_receipt")):
        raise ProposalProbabilityError(f"TASK_PREEXPOSURE_RECEIPT_INVALID:{task_id}")

    attempts = row.get("attempts")
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)) or not attempts:
        raise ProposalProbabilityError(f"ATTEMPTS_INVALID:{task_id}")

    successes = 0
    expected_index = 1
    for attempt in attempts:
        if not isinstance(attempt, Mapping):
            raise ProposalProbabilityError(f"ATTEMPT_NOT_OBJECT:{task_id}:{expected_index}")
        if attempt.get("proposal_index") != expected_index:
            raise ProposalProbabilityError(f"ATTEMPT_SEQUENCE_INVALID:{task_id}:{expected_index}")
        if not isinstance(attempt.get("useful_candidate"), bool):
            raise ProposalProbabilityError(f"ATTEMPT_OUTCOME_INVALID:{task_id}:{expected_index}")
        if attempt.get("outcome_verified") is not True:
            raise ProposalProbabilityError(f"ATTEMPT_OUTCOME_UNVERIFIED:{task_id}:{expected_index}")
        if not _receipt(attempt.get("verification_receipt")):
            raise ProposalProbabilityError(f"ATTEMPT_RECEIPT_INVALID:{task_id}:{expected_index}")
        successes += int(attempt["useful_candidate"])
        expected_index += 1

    return task_id, successes, len(attempts), (
        str(row["task_preexposure_receipt"]["path"])
        + "@"
        + str(row["task_preexposure_receipt"]["git_blob_sha"])
    )


def estimate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
        raise ProposalProbabilityError("SCHEMA_INVALID")
    if doc.get("confidence_alpha") != ALPHA:
        raise ProposalProbabilityError("ALPHA_MUST_BE_FROZEN_0_05")
    if doc.get("task_population_frozen_before_outcomes") is not True:
        raise ProposalProbabilityError("TASK_POPULATION_NOT_PREEXPOSED")
    if not _receipt(doc.get("population_preexposure_receipt")):
        raise ProposalProbabilityError("POPULATION_PREEXPOSURE_RECEIPT_INVALID")

    tasks = doc.get("tasks")
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)) or not tasks:
        raise ProposalProbabilityError("TASKS_INVALID")

    seen: set[str] = set()
    task_rows = []
    pooled_successes = 0
    pooled_trials = 0

    for i, raw in enumerate(tasks):
        if not isinstance(raw, Mapping):
            raise ProposalProbabilityError(f"TASK_NOT_OBJECT:{i}")
        task_id, successes, trials, preexposure = _validate_task(raw, i)
        if task_id in seen:
            raise ProposalProbabilityError(f"TASK_ID_DUPLICATE:{task_id}")
        seen.add(task_id)
        lower = clopper_pearson_lower(successes, trials, ALPHA)
        task_rows.append(
            {
                "task_id": task_id,
                "successes": successes,
                "trials": trials,
                "p_mle": successes / trials,
                "p_lower_95_one_sided": lower,
                "n95_from_p_lower": n95_from_lower_bound(lower),
                "task_preexposure_receipt": preexposure,
            }
        )
        pooled_successes += successes
        pooled_trials += trials

    pooled_lower = clopper_pearson_lower(pooled_successes, pooled_trials, ALPHA)
    worst_lower = min(row["p_lower_95_one_sided"] for row in task_rows)

    finite_gate_pass = worst_lower > 0.0
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "FINITE_PREEXPOSED_EVIDENCE" if finite_gate_pass else "INSUFFICIENT_FINITE_EVIDENCE",
        "finite_gate_pass": finite_gate_pass,
        "task_count": len(task_rows),
        "pooled_successes": pooled_successes,
        "pooled_trials": pooled_trials,
        "pooled_p_mle": pooled_successes / pooled_trials,
        "pooled_p_lower_95_one_sided": pooled_lower,
        "pooled_n95_from_p_lower": n95_from_lower_bound(pooled_lower),
        "worst_task_p_lower_95_one_sided": worst_lower,
        "worst_task_n95_from_p_lower": n95_from_lower_bound(worst_lower),
        "tasks": sorted(task_rows, key=lambda row: row["task_id"]),
        "hard_nonclaims": [
            "FINITE_TASK_EVIDENCE_IS_NOT_OPEN_WORLD_PROPOSAL_PROBABILITY",
            "NO_UNKNOWN_DOMAIN_ACCEPTANCE_CREDIT",
            "NO_H100_TERMINAL_CREDIT",
            "NO_EXECUTION_OR_FRESH_REALITY_AUTHORITY",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
