#!/usr/bin/env python3
"""Public Crowd-BT kernel for GDPval-AA v2.1.

Implements the publicly documented Crowd-BT comparison probability in Elo
rating units and a fixed-judge-quality anchored MLE. It deliberately does not
claim to reproduce Artificial Analysis' owner fit because the historical
judge-quality values and full owner epoch state are not public-bound here.
"""
from __future__ import annotations
import argparse, json, math, sys
from collections import defaultdict, deque
from typing import Any
import numpy as np
from scipy.optimize import minimize

ELO_SCALE = 400.0
LN10 = math.log(10.0)
DEFAULT_ANCHOR_MODEL = "DeepSeek V4.1 Flash (max)"
DEFAULT_ANCHOR_ELO = 1600.0
EPS = 1e-12

def bt_probability(rating_a: float, rating_b: float) -> float:
    z = (float(rating_a) - float(rating_b)) * LN10 / ELO_SCALE
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)

def crowd_bt_probability(rating_a: float, rating_b: float, judge_quality: float) -> float:
    eta = float(judge_quality)
    if not 0.0 <= eta <= 1.0:
        raise ValueError("judge_quality must be in [0,1]")
    p_true = bt_probability(rating_a, rating_b)
    return eta * p_true + (1.0 - eta) * (1.0 - p_true)

def _parse_comparisons(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, float]]:
    comparisons = payload.get("comparisons")
    qualities = payload.get("judge_quality")
    if not isinstance(comparisons, list) or not comparisons:
        raise ValueError("comparisons must be a non-empty list")
    if not isinstance(qualities, dict) or not qualities:
        raise ValueError("judge_quality must be a non-empty object")
    q: dict[str, float] = {}
    for judge, value in qualities.items():
        if not isinstance(judge, str) or not judge:
            raise ValueError("judge_quality keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"judge_quality[{judge!r}] must be numeric")
        eta = float(value)
        if not 0.0 <= eta <= 1.0:
            raise ValueError(f"judge_quality[{judge!r}] must be in [0,1]")
        q[judge] = eta
    parsed: list[dict[str, Any]] = []
    for idx, row in enumerate(comparisons):
        if not isinstance(row, dict):
            raise ValueError(f"comparisons[{idx}] must be an object")
        a, b, judge, outcome = row.get("a"), row.get("b"), row.get("judge"), row.get("outcome_a")
        if not all(isinstance(x, str) and x for x in (a, b, judge)):
            raise ValueError(f"comparisons[{idx}] requires non-empty a, b, judge")
        if a == b:
            raise ValueError(f"comparisons[{idx}] compares a model to itself")
        if judge not in q:
            raise ValueError(f"comparisons[{idx}] uses unbound judge_quality {judge!r}")
        if isinstance(outcome, bool) or not isinstance(outcome, (int, float)) or float(outcome) not in {0.0, 0.5, 1.0}:
            raise ValueError(f"comparisons[{idx}].outcome_a must be 0, 0.5, or 1")
        parsed.append({"a": a, "b": b, "judge": judge, "outcome_a": float(outcome)})
    return parsed, q

def _assert_effective_anchor_connectivity(
    comparisons: list[dict[str, Any]], qualities: dict[str, float], anchor: str
) -> list[str]:
    models = sorted({anchor} | {r["a"] for r in comparisons} | {r["b"] for r in comparisons})
    graph: dict[str, set[str]] = defaultdict(set)
    for row in comparisons:
        if abs(qualities[row["judge"]] - 0.5) <= 1e-12:
            continue
        graph[row["a"]].add(row["b"])
        graph[row["b"]].add(row["a"])
    seen = {anchor}
    queue = deque([anchor])
    while queue:
        x = queue.popleft()
        for y in graph[x]:
            if y not in seen:
                seen.add(y); queue.append(y)
    missing = sorted(set(models) - seen)
    if missing:
        raise ValueError(
            "ratings not identifiable from informative comparisons relative to anchor; "
            f"disconnected models: {missing}"
        )
    return models

def negative_log_likelihood(
    ratings: dict[str, float],
    comparisons: list[dict[str, Any]],
    judge_quality: dict[str, float],
) -> float:
    total = 0.0
    for row in comparisons:
        p = crowd_bt_probability(ratings[row["a"]], ratings[row["b"]], judge_quality[row["judge"]])
        p = min(1.0 - EPS, max(EPS, p))
        y = row["outcome_a"]
        total -= y * math.log(p) + (1.0 - y) * math.log(1.0 - p)
    return total

def fit_fixed_quality(payload: dict[str, Any]) -> dict[str, Any]:
    comparisons, qualities = _parse_comparisons(payload)
    anchor = payload.get("anchor_model", DEFAULT_ANCHOR_MODEL)
    if not isinstance(anchor, str) or not anchor:
        raise ValueError("anchor_model must be a non-empty string")
    anchor_elo = payload.get("anchor_elo", DEFAULT_ANCHOR_ELO)
    if isinstance(anchor_elo, bool) or not isinstance(anchor_elo, (int, float)):
        raise ValueError("anchor_elo must be numeric")
    anchor_elo = float(anchor_elo)
    models = _assert_effective_anchor_connectivity(comparisons, qualities, anchor)
    free = [m for m in models if m != anchor]
    initial = payload.get("initial_ratings", {})
    if not isinstance(initial, dict):
        raise ValueError("initial_ratings must be an object")
    x0 = np.array([float(initial.get(m, anchor_elo)) for m in free], dtype=float)
    def unpack(x: np.ndarray) -> dict[str, float]:
        ratings = {anchor: anchor_elo}
        ratings.update({m: float(v) for m, v in zip(free, x, strict=True)})
        return ratings
    def objective(x: np.ndarray) -> float:
        return negative_log_likelihood(unpack(x), comparisons, qualities)
    result = minimize(objective, x0, method="L-BFGS-B")
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError(f"MLE failed: {result.message}")
    fitted = unpack(result.x)
    return {
        "schema": "GDPVAL_AA_V21_PUBLIC_CROWD_BT_FIXED_QUALITY_FIT_V1",
        "status": "PASS",
        "ratings": dict(sorted(fitted.items(), key=lambda kv: (-kv[1], kv[0]))),
        "anchor_model": anchor,
        "anchor_elo": anchor_elo,
        "negative_log_likelihood": float(result.fun),
        "comparisons": len(comparisons),
        "judge_quality": qualities,
        "owner_exact_reproduction": False,
        "hard_nonclaims": [
            "Judge-quality values must be externally supplied; current AA historical fitted values are not embedded.",
            "This fit does not reproduce AA pairing/judge-assignment state or raw current-epoch graph.",
            "This fit does not implement AA's sandwich confidence interval because its exact clustering/fit-state convention is not bound.",
            "This fit does not claim the same regularization/optimizer details as the owner implementation.",
            "A PASS is not a Brain GDPval-AA owner Elo and is not terminal credit.",
        ],
    }

def self_test() -> dict[str, Any]:
    qualities = {"j1": 1.0, "j2": 0.9, "j3": 0.8}
    ratings = {"anchor": 1600.0, "strong": 1800.0, "weak": 1400.0}
    pairs = [("strong", "anchor"), ("anchor", "weak"), ("strong", "weak")]
    identity = (
        abs(crowd_bt_probability(1700, 1500, 1.0) - bt_probability(1700, 1500)) < 1e-12
        and abs(crowd_bt_probability(1700, 1500, 0.5) - 0.5) < 1e-12
        and abs(crowd_bt_probability(1700, 1500, 0.0) - (1.0 - bt_probability(1700, 1500))) < 1e-12
    )
    discrete = []
    for judge, eta in qualities.items():
        for a, b in pairs:
            p = crowd_bt_probability(ratings[a], ratings[b], eta)
            n = 200
            wins = round(n * p)
            discrete.extend([{"a": a, "b": b, "judge": judge, "outcome_a": 1}] * wins)
            discrete.extend([{"a": a, "b": b, "judge": judge, "outcome_a": 0}] * (n - wins))
    fit = fit_fixed_quality({
        "comparisons": discrete, "judge_quality": qualities,
        "anchor_model": "anchor", "anchor_elo": 1600,
    })
    fr = fit["ratings"]
    ranking_ok = fr["strong"] > fr["anchor"] > fr["weak"]
    recovery_ok = abs(fr["strong"] - 1800) < 5 and abs(fr["weak"] - 1400) < 5
    bad_disconnected = None
    try:
        fit_fixed_quality({
            "comparisons": [{"a": "x", "b": "y", "judge": "j", "outcome_a": 1}],
            "judge_quality": {"j": 1.0}, "anchor_model": "anchor", "anchor_elo": 1600,
        })
    except ValueError as exc:
        bad_disconnected = str(exc)
    passed = identity and ranking_ok and recovery_ok and bad_disconnected is not None
    return {
        "schema": "GDPVAL_AA_V21_PUBLIC_CROWD_BT_KERNEL_SELF_TEST_V1",
        "status": "PASS" if passed else "FAIL",
        "probability_identity_pass": identity,
        "ranking_recovery_pass": ranking_ok,
        "rating_recovery_within_5_elo_pass": recovery_ok,
        "disconnected_graph_fail_closed": bad_disconnected is not None,
        "fit": fit,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", help="JSON comparisons + judge-quality payload")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        out = self_test()
    else:
        if not args.input:
            parser.error("input required unless --self-test")
        with open(args.input, "r", encoding="utf-8") as f:
            payload = json.load(f)
        out = fit_fixed_quality(payload)
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if out["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
