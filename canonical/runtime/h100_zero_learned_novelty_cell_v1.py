"""Point-of-use adapter for the frozen H100 zero-learned novelty census.

It changes no task, route, data, holdout, or threshold. It exposes exactly one
pre-exposed task x route cell as a process exit status so CI job conclusions form
a durable 12x3 result matrix even when log/artifact transport is unavailable.
"""
from __future__ import annotations

import argparse
import json

from canonical.runtime import h100_zero_learned_novelty_stress_v1 as stress


def run_cell(task_id: str, route_id: str) -> dict:
    pre = json.loads(stress.PREEXPOSURE.read_text())
    tasks = {row["id"]: row for row in pre["population"]["tasks"]}
    routes = {row["id"]: row for row in pre["frozen_routes"]}
    if task_id not in tasks:
        raise ValueError("TASK_ID_NOT_FROZEN:" + task_id)
    if route_id not in routes:
        raise ValueError("ROUTE_ID_NOT_FROZEN:" + route_id)
    task = tasks[task_id]
    train = stress._rows(task, pre, holdout=False)
    hold = stress._rows(task, pre, holdout=True)
    inputs = stress._inputs(task)
    if route_id == "ZERO_LEARNED_MONOMIAL_V1":
        result = stress._simple_attempt(train, hold, inputs)
    else:
        result = stress._expr_attempt(
            train, hold, inputs,
            route_id=route_id,
            config=routes[route_id]["config"],
        )
    if result["learned_bytes"] != 0:
        raise AssertionError("LEARNED_BYTES_NONZERO")
    if result["external_learned_calls"] != 0:
        raise AssertionError("EXTERNAL_LEARNED_CALLS_NONZERO")
    return {
        "task_id": task_id,
        "route_id": route_id,
        "operator_class": task["operator_class"],
        "useful_candidate": bool(result["useful_candidate"]),
        "holdout_nrmse": result["holdout_nrmse"],
        "internal_nrmse": result["internal_nrmse"],
        "candidate_count": result["candidate_count"],
        "generated_candidate_count": result["generated_candidate_count"],
        "learned_bytes": result["learned_bytes"],
        "external_learned_calls": result["external_learned_calls"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--route", required=True)
    parser.add_argument("--require-useful", action="store_true")
    args = parser.parse_args()
    out = run_cell(args.task, args.route)
    print(json.dumps(out, indent=2, sort_keys=True))
    if args.require_useful and not out["useful_candidate"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
