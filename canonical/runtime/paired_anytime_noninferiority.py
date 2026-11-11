"""Anytime-valid paired noninferiority test for scarce exact-comparator calls.

For predeclared checkpoints k=1,2,... allocate
    alpha_k = alpha * 6 / (pi^2 * k^2)
so sum_k alpha_k <= alpha.

For paired case scores B_i,O_i in [0,1], D_i=B_i-O_i is in [-1,1].
Hoeffding gives
    P(E[D] < mean(D)-eps_k) <= alpha_k
with
    eps_k = sqrt(2*log(1/alpha_k)/n_k).

By the union bound, all checkpoint lower bounds are simultaneously valid
with probability at least 1-alpha. Therefore stopping at the first
predeclared checkpoint whose lower bound is >= 0 preserves the declared
error guarantee. This module does not select cases, score outputs, call a
comparator, or grant terminal credit.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_PAIRED_ANYTIME_NONINFERIORITY_V1"
PROOF_MODE = "PREDECLARED_PAIRED_ANYTIME_HOEFFDING_NONINFERIORITY_AGAINST_OPUS_5_5"

_REQUIRED_TRUE = (
    "population_frozen_before_results",
    "selection_rule_frozen_before_results",
    "case_order_frozen_before_results",
    "scorer_frozen_before_results",
    "brain_candidate_frozen_before_results",
    "opus_model_configuration_frozen_before_results",
    "checkpoint_schedule_frozen_before_results",
    "independent_acceptance",
    "case_pairs_independent_conditionally_on_frozen_population",
    "same_case_pairing",
    "zero_case_replacement",
    "zero_adaptive_case_selection",
    "zero_tuning_replay",
    "zero_incremental_spend",
)


def _valid_score_list(value: Any, label: str, errors: list[str]) -> list[float]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label}_REQUIRED")
        return []
    out: list[float] = []
    for i, x in enumerate(value):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)):
            errors.append(f"{label}_INVALID:{i}")
            continue
        xf = float(x)
        if not 0.0 <= xf <= 1.0:
            errors.append(f"{label}_OUT_OF_RANGE:{i}")
        out.append(xf)
    return out


def _valid_checkpoints(value: Any, errors: list[str]) -> list[int]:
    if not isinstance(value, list) or not value:
        errors.append("CHECKPOINT_SCHEDULE_REQUIRED")
        return []
    out: list[int] = []
    prev = 0
    for i, x in enumerate(value):
        if isinstance(x, bool) or not isinstance(x, int) or x <= 0:
            errors.append(f"CHECKPOINT_INVALID:{i}")
            continue
        if x <= prev:
            errors.append(f"CHECKPOINT_NOT_STRICTLY_INCREASING:{i}")
        out.append(x)
        prev = x
    return out


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if data.get("proof_mode") != PROOF_MODE:
        errors.append("PROOF_MODE_MISMATCH")

    brain = _valid_score_list(data.get("brain_case_scores"), "BRAIN_CASE_SCORES", errors)
    opus = _valid_score_list(data.get("opus_case_scores"), "OPUS_CASE_SCORES", errors)
    if len(brain) != len(opus):
        errors.append("PAIRED_SCORE_LENGTH_MISMATCH")

    alpha = data.get("alpha")
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(float(alpha)):
        errors.append("ALPHA_INVALID")
    elif not 0.0 < float(alpha) < 1.0:
        errors.append("ALPHA_OUT_OF_RANGE")

    checkpoints = _valid_checkpoints(data.get("checkpoint_schedule"), errors)

    for key in _REQUIRED_TRUE:
        if data.get(key) is not True:
            errors.append(key.upper() + "_NOT_TRUE")

    n = len(brain)
    checkpoint_index: int | None = None
    if checkpoints and n:
        try:
            checkpoint_index = checkpoints.index(n) + 1
        except ValueError:
            errors.append("CURRENT_SAMPLE_COUNT_NOT_PREDECLARED_CHECKPOINT")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": sorted(set(errors)),
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

    assert checkpoint_index is not None
    total_alpha = float(alpha)
    checkpoint_alpha = total_alpha * 6.0 / (math.pi**2 * checkpoint_index**2)
    differences = [b - o for b, o in zip(brain, opus)]
    mean_difference = sum(differences) / n

    # D_i is bounded in [-1,1], so (b-a)^2 = 4.
    epsilon = math.sqrt(2.0 * math.log(1.0 / checkpoint_alpha) / n)
    lower = mean_difference - epsilon
    passed = lower >= 0.0

    cumulative_alpha_spend = sum(
        total_alpha * 6.0 / (math.pi**2 * j**2)
        for j in range(1, checkpoint_index + 1)
    )

    return {
        "schema": SCHEMA,
        "status": "PASS_NONINFERIOR" if passed else "NO_PASS_YET",
        "pass": passed,
        "proof_mode": PROOF_MODE,
        "sample_count": n,
        "checkpoint_index": checkpoint_index,
        "checkpoint_sample_count": checkpoints[checkpoint_index - 1],
        "total_alpha": total_alpha,
        "checkpoint_alpha": checkpoint_alpha,
        "cumulative_alpha_spend": cumulative_alpha_spend,
        "paired_mean_advantage": mean_difference,
        "hoeffding_epsilon": epsilon,
        "paired_advantage_one_sided_lower_bound": lower,
        "decision_rule": "PASS_IFF_ANYTIME_VALID_PAIRED_ADVANTAGE_LOWER_BOUND_GE_ZERO",
        "stopping_rule": "STOP_ON_FIRST_PREDECLARED_CHECKPOINT_WITH_PASS_TRUE",
        "guarantee": "UNION_BOUND_OVER_PREDECLARED_ALPHA_SPENDING_SCHEDULE_LE_TOTAL_ALPHA",
        "errors": [],
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    args = ap.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("input must be a JSON object")
    out = evaluate(data)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
