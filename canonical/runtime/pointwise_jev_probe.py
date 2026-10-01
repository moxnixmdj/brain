#!/usr/bin/env python3
"""Pointwise Jev-compatible decision probe for Project Brain.

Input JSONL fields per row:
  id, domain, primitive, state, question, gold
Optional:
  candidate

This runner intentionally evaluates bounded decision quality only. It does not
promote capabilities or infer whole-family ownership.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        required = {"id", "domain", "primitive", "state", "question", "gold"}
        missing = sorted(required - obj.keys())
        if missing:
            raise ValueError(f"{path}:{line_no}: missing fields {missing}")
        if not isinstance(obj["gold"], bool):
            raise ValueError(f"{path}:{line_no}: gold must be boolean")
        cases.append(obj)
    if not cases:
        raise ValueError("no cases loaded")
    return cases


def build_request(case: dict[str, Any], model: str) -> dict[str, Any]:
    instructions = str(case["question"]).strip()
    if case.get("candidate") is not None:
        instructions += f"\nCandidate: {case['candidate']}"
    return {
        "model": model,
        "state": case["state"],
        "questions": {
            "decision": {
                "type": "noul",
                "instructions": instructions,
            }
        },
    }


def call_endpoint(
    endpoint: str,
    payload: dict[str, Any],
    timeout_s: float,
    api_key: str | None,
) -> tuple[float, float]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    latency_ms = (time.perf_counter() - started) * 1000.0
    obj = json.loads(raw)
    try:
        score = float(obj["answers"]["decision"]["noul"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"malformed Jev-compatible response: {obj!r}") from exc
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise RuntimeError(f"invalid probability: {score!r}")
    return score, latency_ms


def expected_calibration_error(rows: list[dict[str, Any]], bins: int = 10) -> float:
    n = len(rows)
    total = 0.0
    for i in range(bins):
        lo = i / bins
        hi = (i + 1) / bins
        bucket = [
            r for r in rows
            if (lo <= r["confidence"] < hi) or (i == bins - 1 and r["confidence"] == 1.0)
        ]
        if not bucket:
            continue
        accuracy = sum(r["correct"] for r in bucket) / len(bucket)
        confidence = sum(r["confidence"] for r in bucket) / len(bucket)
        total += (len(bucket) / n) * abs(accuracy - confidence)
    return total


def summarize(rows: list[dict[str, Any]], confidence_gate: float) -> dict[str, Any]:
    n = len(rows)
    high = [r for r in rows if r["confidence"] >= confidence_gate]
    return {
        "cases": n,
        "accuracy": sum(r["correct"] for r in rows) / n,
        "brier": sum((r["score"] - r["gold_numeric"]) ** 2 for r in rows) / n,
        "ece_10bin": expected_calibration_error(rows),
        "mean_latency_ms": statistics.fmean(r["latency_ms"] for r in rows),
        "p50_latency_ms": statistics.median(r["latency_ms"] for r in rows),
        "high_confidence_gate": confidence_gate,
        "high_confidence_coverage": len(high) / n,
        "high_confidence_accuracy": (
            sum(r["correct"] for r in high) / len(high) if high else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8017/v1/systemone")
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--confidence-gate", type=float, default=0.80)
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--api-key-env", default="JEV_API_KEY")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    rows: list[dict[str, Any]] = []

    for case in cases:
        payload = build_request(case, args.model)
        score, latency_ms = call_endpoint(args.endpoint, payload, args.timeout, api_key)
        gold_numeric = 1.0 if case["gold"] else 0.0
        predicted = score >= 0.5
        confidence = max(score, 1.0 - score)
        rows.append({
            "id": case["id"],
            "domain": case["domain"],
            "primitive": case["primitive"],
            "score": score,
            "gold": case["gold"],
            "gold_numeric": gold_numeric,
            "predicted": predicted,
            "correct": predicted == case["gold"],
            "confidence": confidence,
            "latency_ms": latency_ms,
        })

    by_domain: dict[str, Any] = {}
    for domain in sorted({r["domain"] for r in rows}):
        by_domain[domain] = summarize([r for r in rows if r["domain"] == domain], args.confidence_gate)

    by_primitive: dict[str, Any] = {}
    for primitive in sorted({r["primitive"] for r in rows}):
        by_primitive[primitive] = summarize([r for r in rows if r["primitive"] == primitive], args.confidence_gate)

    result = {
        "schema": "PROJECT_BRAIN_POINTWISE_JEV_PROBE_RESULT_V1",
        "status": "MEASUREMENT_ONLY__ZERO_CAPABILITY_CREDIT",
        "endpoint": args.endpoint,
        "model": args.model,
        "overall": summarize(rows, args.confidence_gate),
        "by_domain": by_domain,
        "by_primitive": by_primitive,
        "rows": rows,
        "promotion_credit": 0,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["overall"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
