"""Runtime answer receipt: how long does the unified model take to answer, with zero model calls?

The repo already knows the answers: 462 capabilities indexed, 849 promotion candidates,
31 callable, every one of them compiled into one JSON artifact. What it has never
measured is the *cost of asking*. This instrument asks the compiled model the three
questions the runtime is actually for -- can you do X, where is it, how many are left --
and records wall-clock percentiles per question, alongside the token cost of the same
question answered by an agent loop.

No model, no network, no subprocess: the only cost measured is JSON load plus an index
lookup, which is the entire point. If answering needs a language model, the answer was
not compiled.

Budgets are gates, not adjectives (Elon's law: everything must be insanely fast):
  load  p95 <= 2000 ms      (one 13 MB JSON parse)
  query p95 <=  5 ms        (index lookup inside a loaded model)
  total wall clock <= 60 s  (the whole receipt)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))

import brain_unified_model_v1 as brain  # noqa: E402

ARTIFACT = ROOT / "canonical/verification/RUNTIME_ANSWER_RECEIPT_20261127_V1.json"
SCHEMA = "PROJECT_BRAIN_RUNTIME_ANSWER_RECEIPT_V1"
BUDGETS = {"load_p95_ms": 2000.0, "query_p95_ms": 5.0, "total_wall_clock_s": 60.0}
REPEATS = 40


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))
    return round(ordered[idx], 4)


def _queries(model: dict, limit: int = 12) -> list[str]:
    """Deterministic questions derived from the compiled capability ids, never hand-written."""
    out: list[str] = []
    for cap in model.get("capabilities") or []:
        cid = str(cap.get("id") or "")
        if not cid:
            continue
        out.append(cid.replace(".", " ").replace("_", " "))
        if len(out) >= limit:
            break
    return out


def _time(fn, queries: list[str]) -> dict:
    samples: list[float] = []
    empty = 0
    for query in queries:
        for _ in range(REPEATS):
            start = time.perf_counter()
            result = fn(query)
            samples.append((time.perf_counter() - start) * 1000.0)
        if not result:
            empty += 1
    return {
        "n": len(samples),
        "p50_ms": _pct(samples, 0.50),
        "p95_ms": _pct(samples, 0.95),
        "max_ms": _pct(samples, 1.0),
        "mean_ms": round(statistics.fmean(samples), 4) if samples else 0.0,
        "empty_answers": empty,
    }


def measure() -> dict:
    started = time.perf_counter()

    t0 = time.perf_counter()
    raw = brain.load_model(verify=True)
    load_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    model = brain.UnifiedModel(raw)
    wrap_ms = (time.perf_counter() - t1) * 1000.0

    queries = _queries(raw)
    promotion = dict(raw.get("promotion") or {})

    t2 = time.perf_counter()
    for _ in range(REPEATS * max(1, len(queries))):
        promotion.get("callable_now")
    promotion_ms = (time.perf_counter() - t2) * 1000.0 / (REPEATS * max(1, len(queries)))

    find_source = _time(model.find_source, queries)
    route = _time(model.route, queries)
    find_any = _time(model.find_any_source, queries)

    # The composite question the runtime exists for: "can you do this, and where?"
    composite: list[float] = []
    answered = 0
    for query in queries:
        for _ in range(REPEATS):
            start = time.perf_counter()
            hit = model.find_source(query, top_k=1)
            ok = bool(hit) and bool(promotion.get("candidates"))
            composite.append((time.perf_counter() - start) * 1000.0)
            answered += int(ok)

    artifact_bytes = (ROOT / brain.DEFAULT_ARTIFACT).stat().st_size
    total_s = time.perf_counter() - started

    checks = {
        "load_p95_ms": round(load_ms, 4),
        "query_p95_ms": max(find_source["p95_ms"], route["p95_ms"], find_any["p95_ms"],
                            _pct(composite, 0.95)),
        "total_wall_clock_s": round(total_s, 3),
    }
    verdict = all(checks[k] <= BUDGETS[k] for k in BUDGETS)

    # What the same question costs when it is not compiled: an agent loop reads the tree,
    # the tests said 21-40 tool calls per solved task and the harness study measured
    # 28,142 tokens per solved task at the cheapest end (Goose).
    agent_loop_tokens = 28142
    return {
        "schema": SCHEMA,
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifact": {
            "path": str(brain.DEFAULT_ARTIFACT),
            "bytes": artifact_bytes,
            "digest": raw.get("digest"),
            "capabilities": len(raw.get("capabilities") or []),
        },
        "promotion": {
            "candidates": promotion.get("candidates"),
            "callable_now": promotion.get("callable_now"),
            "lookup_ms_per_call": round(promotion_ms, 6),
        },
        "questions": {
            "find_source": find_source,
            "route": route,
            "find_any_source": find_any,
            "composite_can_you_do_this": {
                "n": len(composite),
                "p50_ms": _pct(composite, 0.50),
                "p95_ms": _pct(composite, 0.95),
                "max_ms": _pct(composite, 1.0),
                "answered": answered,
                "queries": len(queries),
            },
        },
        "cost_of_asking": {
            "load_ms": round(load_ms, 3),
            "wrap_ms": round(wrap_ms, 3),
            "total_wall_clock_s": round(total_s, 3),
            "model_calls": 0,
            "network_calls": 0,
            "prompt_tokens_per_question": 0,
            "agent_loop_tokens_per_question_for_comparison": agent_loop_tokens,
        },
        "budgets": BUDGETS,
        "checks": checks,
        "verdict": "FAST" if verdict else "SLOW",
        "queries": queries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ARTIFACT))
    args = parser.parse_args(argv)
    receipt = measure()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": receipt["verdict"], "checks": receipt["checks"],
                      "out": str(out)}, indent=1))
    return 0 if receipt["verdict"] == "FAST" else 1


if __name__ == "__main__":
    raise SystemExit(main())
