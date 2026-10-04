"""Pre-exposed zero-learned novelty stress census for H100.

This research harness uses only the frozen public synthetic task population in
H100_ZERO_LEARNED_NOVELTY_STRESS_PREEXPOSURE_V1.json.  Formula identifiers are
used only to generate training/holdout truth. Solver routes receive numeric rows
and input names only.

No hidden or terminal cases are used. Results create no acceptance credit.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as simple
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

ROOT = Path(__file__).resolve().parents[2]
PREEXPOSURE = ROOT / "canonical/governance/H100_ZERO_LEARNED_NOVELTY_STRESS_PREEXPOSURE_V1.json"
SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_NOVELTY_STRESS_RESULT_V1"
THRESHOLD = 1e-7


class NoveltyStressError(ValueError):
    pass


def sat(x: float) -> float:
    return x / (1.0 + abs(x))


def truth(formula_id: str, x: float, z: float | None = None) -> float:
    if formula_id == "AFFINE_2D":
        assert z is not None
        return 1.25 + 2.0 * x - 0.75 * z
    if formula_id == "POWER_RATIO":
        assert z is not None
        return 2.5 * (x * x) / (1.0 + abs(z))
    if formula_id == "RECIPROCAL_AFFINE":
        return 1.0 / (3.0 + 0.5 * x)
    if formula_id == "NESTED_SATURATION":
        return -0.4 + 1.7 * sat(sat(x))
    if formula_id == "LINEAR_PLUS_SATURATION":
        return 1.1 + 2.0 * x + 3.0 * sat(x)
    if formula_id == "CROSS_STABLE_RATIO":
        assert z is not None
        return 0.75 + 1.2 * x + 2.5 * (z / (1.0 + abs(x)))
    if formula_id == "DOUBLE_CROSS_STABLE_RATIO":
        assert z is not None
        return 2.0 * (x / (1.0 + abs(z))) + 3.0 * (z / (1.0 + abs(x)))
    if formula_id == "LOG1P_ABS":
        return -0.7 + 1.9 * math.log1p(abs(x))
    if formula_id == "RATIONAL_QUADRATIC":
        return 0.5 + 2.2 * (x / (1.0 + x * x))
    if formula_id == "PERIODIC_SINE":
        return 0.2 * x + math.sin(1.37 * x)
    if formula_id == "EXPONENTIAL":
        return math.exp(0.35 * abs(x))
    if formula_id == "SIGN_STEP":
        return -1.0 if x < 0.0 else 1.0
    raise NoveltyStressError("FORMULA_ID_UNKNOWN:" + formula_id)


def _nrmse(actual: list[float], predicted: list[float]) -> float:
    if len(actual) != len(predicted) or not actual:
        return math.inf
    mean = sum(actual) / len(actual)
    spread = math.sqrt(sum((x - mean) ** 2 for x in actual) / len(actual))
    scale = max(spread, max(abs(x) for x in actual) * 1e-9, 1e-12)
    return math.sqrt(sum((a-p) ** 2 for a,p in zip(actual,predicted)) / len(actual)) / scale


def _rows(task: Mapping[str, Any], pre: Mapping[str, Any], *, holdout: bool) -> list[dict[str, float]]:
    formula_id = str(task["formula_id"])
    if int(task["arity"]) == 1:
        key = "single_input_holdout_x" if holdout else "single_input_training_x"
        return [{"x": float(x), "y": truth(formula_id, float(x))} for x in pre["population"][key]]
    key = "two_input_holdout_pairs" if holdout else "two_input_training_pairs"
    return [
        {"x": float(x), "z": float(z), "y": truth(formula_id, float(x), float(z))}
        for x,z in pre["population"][key]
    ]


def _inputs(task: Mapping[str, Any]) -> list[str]:
    return ["x"] if int(task["arity"]) == 1 else ["x", "z"]


def _simple_attempt(train: list[dict[str,float]], hold: list[dict[str,float]], inputs: list[str]) -> dict[str, Any]:
    start = time.perf_counter()
    out = simple.discover(train, target="y", inputs=inputs, max_active_variables=3, top_k=16)
    best = None
    for candidate in out.get("candidates", []):
        try:
            pred = [simple.predict(candidate, row) for row in hold]
        except Exception:
            continue
        err = _nrmse([row["y"] for row in hold], pred)
        internal = max(float(candidate.get("nrmse", math.inf)), float(candidate.get("validation_nrmse", math.inf)))
        record = {"holdout_nrmse": err, "internal_nrmse": internal, "candidate": candidate}
        if best is None or (err, internal) < (best["holdout_nrmse"], best["internal_nrmse"]):
            best = record
    elapsed = time.perf_counter() - start
    useful = bool(best and best["holdout_nrmse"] <= THRESHOLD and best["internal_nrmse"] <= THRESHOLD)
    return {
        "route_id": "ZERO_LEARNED_MONOMIAL_V1",
        "useful_candidate": useful,
        "holdout_nrmse": None if best is None else best["holdout_nrmse"],
        "internal_nrmse": None if best is None else best["internal_nrmse"],
        "candidate_count": len(out.get("candidates", [])),
        "generated_candidate_count": int(out.get("grammar_candidates_considered", 0)),
        "wall_clock_seconds": elapsed,
        "learned_bytes": int(out.get("learned_parameter_bytes", 0)),
        "external_learned_calls": int(out.get("external_learned_capability_calls", 0)),
    }


def _expr_attempt(train: list[dict[str,float]], hold: list[dict[str,float]], inputs: list[str], *, route_id: str, config: Mapping[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    out = expr.discover(train, target="y", inputs=inputs, **dict(config))
    candidate = out.get("best_candidate")
    holdout_error = None
    internal = math.inf
    if candidate is not None:
        try:
            pred = [expr.predict(candidate, row) for row in hold]
            holdout_error = _nrmse([row["y"] for row in hold], pred)
            internal = max(float(candidate.get("nrmse", math.inf)), float(candidate.get("validation_nrmse", math.inf)))
        except Exception:
            holdout_error = None
    elapsed = time.perf_counter() - start
    useful = bool(holdout_error is not None and holdout_error <= THRESHOLD and internal <= 1e-8)
    return {
        "route_id": route_id,
        "useful_candidate": useful,
        "holdout_nrmse": holdout_error,
        "internal_nrmse": None if not math.isfinite(internal) else internal,
        "candidate_count": int(out.get("candidate_count", 0)),
        "generated_candidate_count": int(out.get("generated_tree_count", 0)),
        "wall_clock_seconds": elapsed,
        "learned_bytes": int(out.get("persistent_learned_bytes", 0)),
        "external_learned_calls": int(out.get("external_learned_capability_calls", 0)),
    }


def run() -> dict[str, Any]:
    pre = json.loads(PREEXPOSURE.read_text())
    if pre.get("status") != "FROZEN_BEFORE_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT":
        raise NoveltyStressError("PREEXPOSURE_NOT_FROZEN")
    tasks = pre["population"]["tasks"]
    routes = {row["id"]: row for row in pre["frozen_routes"]}
    expected_routes = ["ZERO_LEARNED_MONOMIAL_V1", "EXPRESSION_TREE_D2_W16", "EXPRESSION_TREE_D4_W32"]
    if list(routes) != expected_routes:
        raise NoveltyStressError("ROUTE_SET_DRIFT")

    rows = []
    false_exact_count = 0
    for task in tasks:
        train = _rows(task, pre, holdout=False)
        hold = _rows(task, pre, holdout=True)
        inputs = _inputs(task)
        attempts = [
            _simple_attempt(train, hold, inputs),
            _expr_attempt(train, hold, inputs, route_id="EXPRESSION_TREE_D2_W16", config=routes["EXPRESSION_TREE_D2_W16"]["config"]),
            _expr_attempt(train, hold, inputs, route_id="EXPRESSION_TREE_D4_W32", config=routes["EXPRESSION_TREE_D4_W32"]["config"]),
        ]
        task_solved = any(a["useful_candidate"] for a in attempts)
        for a in attempts:
            if a["internal_nrmse"] is not None and a["internal_nrmse"] <= 1e-8:
                if a["holdout_nrmse"] is None or a["holdout_nrmse"] > THRESHOLD:
                    false_exact_count += 1
        operator_class = str(task["operator_class"])
        if task_solved:
            classification = "SOLVED_BY_EXISTING_ZERO_LEARNED_ROUTE"
        elif operator_class == "WITHIN_CURRENT_OPERATOR_CLOSURE":
            classification = "SEARCH_OR_COMPOSITION_RESIDUAL"
        else:
            classification = "MISSING_PRIMITIVE_OR_GRAMMAR_RESIDUAL"
        rows.append({
            "task_id": task["id"],
            "operator_class": operator_class,
            "task_solved": task_solved,
            "classification": classification,
            "routes": attempts,
        })

    within = [r for r in rows if r["operator_class"] == "WITHIN_CURRENT_OPERATOR_CLOSURE"]
    outside = [r for r in rows if r["operator_class"] == "OUTSIDE_CURRENT_OPERATOR_SET"]
    learned_bytes = max(a["learned_bytes"] for r in rows for a in r["routes"])
    external_calls = sum(a["external_learned_calls"] for r in rows for a in r["routes"])
    return {
        "schema": SCHEMA,
        "preexposure_path": "canonical/governance/H100_ZERO_LEARNED_NOVELTY_STRESS_PREEXPOSURE_V1.json",
        "task_count": len(rows),
        "route_count": 3,
        "route_task_pair_count": len(rows) * 3,
        "tasks_solved": sum(r["task_solved"] for r in rows),
        "within_operator_tasks_solved": sum(r["task_solved"] for r in within),
        "within_operator_task_count": len(within),
        "outside_operator_tasks_solved": sum(r["task_solved"] for r in outside),
        "outside_operator_task_count": len(outside),
        "false_exact_count": false_exact_count,
        "max_persistent_learned_bytes": learned_bytes,
        "external_learned_capability_calls": external_calls,
        "tasks": rows,
        "hard_nonclaims": [
            "PUBLIC_SYNTHETIC_STRESS_IS_NOT_OPEN_WORLD_PROOF",
            "PUBLIC_SYNTHETIC_STRESS_IS_NOT_MYSTERYMECHANISM_OR_TERMINAL_EVIDENCE",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_terminal_reality_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
