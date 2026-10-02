"""Distribution-free matched statistical acceptance for open-ended terminal contracts.

This primitive implements one registered terminal proof mode:
PREDECLARED_MATCHED_STATISTICAL_COMPARISON_WITH_BRAIN_LOWER_BOUND_AT_OR_ABOVE_OPUS_5_5_ACCEPTANCE_BOUND

It uses Hoeffding's inequality for independent bounded [0,1] case scores.
No model-specific assumption, asymptotic normal approximation, or hidden tuning is used.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_MATCHED_STATISTICAL_ACCEPTANCE_V1"
PROOF_MODE = (
    "PREDECLARED_MATCHED_STATISTICAL_COMPARISON_WITH_BRAIN_LOWER_BOUND_"
    "AT_OR_ABOVE_OPUS_5_5_ACCEPTANCE_BOUND"
)


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if data.get("proof_mode") != PROOF_MODE:
        errors.append("PROOF_MODE_MISMATCH")

    scores = data.get("brain_case_scores")
    if not isinstance(scores, list) or not scores:
        errors.append("BRAIN_CASE_SCORES_REQUIRED")
        scores = []
    else:
        for i, x in enumerate(scores):
            if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(float(x)):
                errors.append(f"SCORE_INVALID:{i}")
            elif not (0.0 <= float(x) <= 1.0):
                errors.append(f"SCORE_OUT_OF_RANGE:{i}")

    target = data.get("frozen_opus_acceptance_bound")
    if not isinstance(target, (int, float)) or isinstance(target, bool) or not math.isfinite(float(target)):
        errors.append("FROZEN_OPUS_ACCEPTANCE_BOUND_INVALID")
    elif not (0.0 <= float(target) <= 1.0):
        errors.append("FROZEN_OPUS_ACCEPTANCE_BOUND_OUT_OF_RANGE")

    alpha = data.get("alpha")
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not math.isfinite(float(alpha)):
        errors.append("ALPHA_INVALID")
    elif not (0.0 < float(alpha) < 1.0):
        errors.append("ALPHA_OUT_OF_RANGE")

    for key in (
        "population_frozen_before_results",
        "selection_rule_frozen_before_results",
        "scorer_frozen_before_results",
        "candidate_frozen_before_results",
        "independent_acceptance",
        "case_scores_independent_conditionally_on_frozen_population",
        "zero_case_replacement",
        "zero_adaptive_selection",
        "zero_tuning_replay",
        "zero_incremental_spend",
    ):
        if data.get(key) is not True:
            errors.append(key.upper() + "_NOT_TRUE")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": sorted(set(errors)),
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    vals = [float(x) for x in scores]
    n = len(vals)
    mean = sum(vals) / n
    epsilon = math.sqrt(math.log(1.0 / float(alpha)) / (2.0 * n))
    lower = max(0.0, mean - epsilon)
    passed = lower >= float(target)

    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL_BOUND_NOT_MET",
        "pass": passed,
        "proof_mode": PROOF_MODE,
        "sample_count": n,
        "brain_mean_score": mean,
        "hoeffding_epsilon": epsilon,
        "brain_one_sided_lower_bound": lower,
        "frozen_opus_acceptance_bound": float(target),
        "alpha": float(alpha),
        "confidence": 1.0 - float(alpha),
        "errors": [],
        "rule": (
            "PASS_IFF_DISTRIBUTION_FREE_ONE_SIDED_BRAIN_LOWER_BOUND_"
            "GE_FROZEN_OPUS_5_5_ACCEPTANCE_BOUND"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
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
