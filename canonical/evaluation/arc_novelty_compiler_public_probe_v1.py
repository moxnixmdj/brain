"""Public ARC-AGI probe for arc_novelty_compiler_v1.

This evaluator is deliberately development-only: point it at a public ARC training
corpus, never a hidden/private evaluation set. It measures two distinct quantities:

1. two_attempt_task_solve_rate: the compiler's first two stable hypotheses are used
   as the two allowed attempts for every test input;
2. grammar_oracle_task_coverage: whether any emitted hypothesis would solve every
   test input, regardless of ranking.

The second metric is an upper bound on the current grammar, not an achieved score.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from canonical.runtime.arc_novelty_compiler_v1 import compile_hypotheses, predict

SCHEMA = "PROJECT_BRAIN_ARC_NOVELTY_COMPILER_PUBLIC_PROBE_V1"


def _matches(hypothesis: dict[str, Any], test_case: dict[str, Any]) -> bool:
    out = predict(hypothesis, test_case["input"])
    return out.get("status") == "PREDICTED" and out.get("prediction") == test_case["output"]


def evaluate_task(task: dict[str, Any]) -> dict[str, Any]:
    train = task.get("train")
    test = task.get("test")
    if not isinstance(train, list) or not train or not isinstance(test, list) or not test:
        return {"status": "INVALID_TASK"}
    if any("output" not in x for x in test if isinstance(x, dict)):
        return {"status": "UNSCORABLE_NO_TEST_OUTPUT"}

    compiled = compile_hypotheses(train)
    if compiled.get("status") == "FAIL_CLOSED":
        return {"status": "COMPILER_FAIL_CLOSED", "reason": compiled.get("reason")}

    hypotheses = compiled.get("hypotheses", [])
    first_two = hypotheses[:2]
    two_attempt = bool(first_two) and all(any(_matches(h, case) for h in first_two) for case in test)
    oracle = bool(hypotheses) and any(all(_matches(h, case) for case in test) for h in hypotheses)

    return {
        "status": "SCORED",
        "hypothesis_count": len(hypotheses),
        "two_attempt_solved": two_attempt,
        "grammar_oracle_solved": oracle,
    }


def evaluate_directory(data_dir: Path) -> dict[str, Any]:
    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise SystemExit("NO_TASK_FILES")

    scored = 0
    two_attempt = 0
    oracle = 0
    invalid = 0
    no_hypothesis = 0
    per_task: list[dict[str, Any]] = []

    for path in files:
        try:
            task = json.loads(path.read_text())
            result = evaluate_task(task)
        except Exception as exc:
            result = {"status": "EVALUATOR_EXCEPTION", "reason": type(exc).__name__ + ":" + str(exc)}

        row = {"task_id": path.stem, **result}
        per_task.append(row)
        if result.get("status") != "SCORED":
            invalid += 1
            continue
        scored += 1
        if result.get("hypothesis_count") == 0:
            no_hypothesis += 1
        two_attempt += int(result.get("two_attempt_solved") is True)
        oracle += int(result.get("grammar_oracle_solved") is True)

    return {
        "schema": SCHEMA,
        "task_files": len(files),
        "scored_tasks": scored,
        "invalid_or_unscored_tasks": invalid,
        "tasks_with_no_hypothesis": no_hypothesis,
        "two_attempt_tasks_solved": two_attempt,
        "two_attempt_task_solve_rate": (two_attempt / scored if scored else 0.0),
        "grammar_oracle_tasks_solved": oracle,
        "grammar_oracle_task_coverage": (oracle / scored if scored else 0.0),
        "metric_semantics": {
            "two_attempt_task_solve_rate": "ACHIEVED_BY_STABLE_FIRST_TWO_HYPOTHESES_ON_PUBLIC_DEVELOPMENT_CORPUS",
            "grammar_oracle_task_coverage": "UPPER_BOUND_ONLY__ANY_EMITTED_HYPOTHESIS_MAY_WIN",
        },
        "private_or_hidden_score_claimed": False,
        "per_task": per_task,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = evaluate_directory(args.data_dir)
    body = json.dumps(result, indent=2, sort_keys=True)
    print(body)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body + "\n")


if __name__ == "__main__":
    main()
