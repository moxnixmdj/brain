#!/usr/bin/env python3
"""Project Brain fail-closed pointwise cognitive decision kernel V1.

Scope:
- One bounded yes/no (noul) judgment.
- Jev-compatible /v1/systemone endpoint.
- Admit a decision only when confidence meets the configured threshold.
- Otherwise return ESCALATE.

This module does NOT promote capabilities and does NOT implement arbitrary
candidate ranking. Those remain unverified residuals.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionResult:
    status: str
    decision: bool | None
    probability_yes: float
    confidence: float
    threshold: float
    latency_ms: float
    model: str
    reason: str
    capability_credit_delta: int = 0


def _request(
    endpoint: str,
    model: str,
    state: Any,
    question: str,
    timeout_s: float,
    api_key: str | None,
) -> tuple[float, float]:
    payload = {
        "model": model,
        "state": state,
        "questions": {
            "decision": {
                "type": "noul",
                "instructions": question,
            }
        },
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"decision endpoint unavailable: {exc}") from exc

    latency_ms = (time.perf_counter() - started) * 1000.0
    obj = json.loads(raw)
    try:
        p_yes = float(obj["answers"]["decision"]["noul"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"malformed Jev-compatible response: {obj!r}") from exc
    if not math.isfinite(p_yes) or not 0.0 <= p_yes <= 1.0:
        raise RuntimeError(f"invalid decision probability: {p_yes!r}")
    return p_yes, latency_ms


def decide(
    *,
    endpoint: str,
    model: str,
    state: Any,
    question: str,
    threshold: float = 0.80,
    timeout_s: float = 30.0,
    api_key: str | None = None,
) -> DecisionResult:
    if not 0.5 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.5 and 1.0")
    if not str(question).strip():
        raise ValueError("question must be non-empty")

    p_yes, latency_ms = _request(
        endpoint=endpoint,
        model=model,
        state=state,
        question=str(question).strip(),
        timeout_s=timeout_s,
        api_key=api_key,
    )
    decision = p_yes >= 0.5
    confidence = max(p_yes, 1.0 - p_yes)

    if confidence < threshold:
        return DecisionResult(
            status="ESCALATE",
            decision=None,
            probability_yes=p_yes,
            confidence=confidence,
            threshold=threshold,
            latency_ms=latency_ms,
            model=model,
            reason="CONFIDENCE_BELOW_FAIL_CLOSED_THRESHOLD",
        )

    return DecisionResult(
        status="ADMIT",
        decision=decision,
        probability_yes=p_yes,
        confidence=confidence,
        threshold=threshold,
        latency_ms=latency_ms,
        model=model,
        reason="CONFIDENCE_MEETS_FAIL_CLOSED_THRESHOLD",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8017/v1/systemone")
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--state-json", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--api-key-env", default="JEV_API_KEY")
    args = parser.parse_args()

    state = json.loads(args.state_json)
    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    result = decide(
        endpoint=args.endpoint,
        model=args.model,
        state=state,
        question=args.question,
        threshold=args.threshold,
        timeout_s=args.timeout,
        api_key=api_key,
    )
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
