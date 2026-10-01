#!/usr/bin/env python3
"""Brain Cognitive Basis Probe V1: zero-credit shared-decision diagnostic."""
from __future__ import annotations
import argparse, json, math, pathlib, time, urllib.request
from collections import defaultdict

def post_json(url, payload, timeout=60):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def discover_model(endpoint):
    with urllib.request.urlopen(endpoint.rstrip("/") + "/v1/models", timeout=30) as r:
        payload = json.load(r)
    data = payload.get("data", [])
    if not data or "id" not in data[0]:
        raise RuntimeError("No model id returned by /v1/models")
    return data[0]["id"]

def endpoint_decider(endpoint, model, delay):
    model = discover_model(endpoint) if model == "auto" else model
    url = endpoint.rstrip("/") + "/v1/classifier"
    first = True
    def decide(case):
        nonlocal first
        if not first and delay:
            time.sleep(delay)
        first = False
        out = post_json(url, {
            "model": model,
            "state": case["state"],
            "questions": {"decision": {
                "type": "choice",
                "instructions": case["instructions"],
                "criteria": case["criteria"]
            }}
        })
        return out["answers"]["decision"]
    return decide

def oracle_decider(case):
    return {
        "choice": case["expected"],
        "confidence": 1.0,
        "probabilities": {k: 1.0 if k == case["expected"] else 0.0 for k in case["criteria"]}
    }

def evaluate(cases, decide):
    rows = []
    for case in cases:
        ans = decide(case)
        pred = ans["choice"]
        probs = ans.get("probabilities", {})
        p = max(float(probs.get(case["expected"], 0.0)), 1e-12)
        rows.append({
            "id": case["id"], "primitive": case["primitive"], "domain": case["domain"],
            "expected": case["expected"], "predicted": pred,
            "correct": pred == case["expected"],
            "confidence": float(ans.get("confidence", 0.0)),
            "nll": -math.log(p)
        })
    groups = {}
    for field in ("primitive", "domain"):
        buckets = defaultdict(list)
        for row in rows:
            buckets[row[field]].append(row)
        groups[field] = {
            k: {
                "n": len(v),
                "accuracy": sum(x["correct"] for x in v) / len(v),
                "mean_nll": sum(x["nll"] for x in v) / len(v)
            }
            for k, v in sorted(buckets.items())
        }
    return {
        "n": len(rows),
        "accuracy": sum(r["correct"] for r in rows) / len(rows) if rows else 0.0,
        "mean_nll": sum(r["nll"] for r in rows) / len(rows) if rows else 0.0,
        "groups": groups,
        "rows": rows
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--endpoint", default="https://simple-jev-demo-api.featherless.ai")
    ap.add_argument("--model", default="auto")
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--out")
    ap.add_argument("--oracle-self-test", action="store_true")
    args = ap.parse_args()

    cases = json.loads(pathlib.Path(args.cases).read_text())
    required = {"id", "primitive", "domain", "state", "instructions", "criteria", "expected"}
    for case in cases:
        missing = required - set(case)
        if missing:
            raise SystemExit(f"{case.get('id', '?')}: missing {sorted(missing)}")
        if case["expected"] not in case["criteria"]:
            raise SystemExit(f"{case['id']}: expected choice absent from criteria")

    decide = oracle_decider if args.oracle_self_test else endpoint_decider(args.endpoint, args.model, args.delay)
    report = evaluate(cases, decide)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        pathlib.Path(args.out).write_text(rendered + "\n")
    print(rendered)
    if args.oracle_self_test and report["accuracy"] != 1.0:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
