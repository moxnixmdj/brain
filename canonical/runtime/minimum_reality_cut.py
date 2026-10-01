#!/usr/bin/env python3
"""Exact minimum-reality-cut solver for Project Brain.

Input JSON:
{
  "distinctions": ["D1", "D2", ...],
  "already_resolved": ["D1", ...],
  "observations": [
    {"id": "O1", "covers": ["D2"], "cost": 1.0},
    ...
  ]
}

The solver returns an exact minimum-cost cover for unresolved distinctions.
It fails closed rather than labeling an approximation as a minimum.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

MAX_EXACT_DISTINCTIONS = 24
MAX_OBSERVATIONS = 64


def _validate(data: dict[str, Any]) -> tuple[list[str], set[str], list[dict[str, Any]]]:
    distinctions = data.get("distinctions")
    resolved = data.get("already_resolved", [])
    observations = data.get("observations")

    if not isinstance(distinctions, list) or not all(isinstance(x, str) and x for x in distinctions):
        raise ValueError("distinctions must be a nonempty-string list")
    if len(distinctions) != len(set(distinctions)):
        raise ValueError("duplicate distinction")
    if not isinstance(resolved, list) or not all(isinstance(x, str) for x in resolved):
        raise ValueError("already_resolved must be a string list")
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")

    universe = set(distinctions)
    resolved_set = set(resolved)
    if not resolved_set <= universe:
        raise ValueError("already_resolved contains unknown distinction")

    clean: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("observation must be object")
        oid = row.get("id")
        covers = row.get("covers")
        cost = row.get("cost")
        if not isinstance(oid, str) or not oid or oid in seen_ids:
            raise ValueError("observation id invalid or duplicate")
        seen_ids.add(oid)
        if not isinstance(covers, list) or not all(isinstance(x, str) for x in covers):
            raise ValueError(f"{oid}: covers must be string list")
        cover_set = set(covers)
        if not cover_set <= universe:
            raise ValueError(f"{oid}: covers unknown distinction")
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or not math.isfinite(float(cost)) or float(cost) < 0:
            raise ValueError(f"{oid}: cost must be finite nonnegative number")
        clean.append({"id": oid, "covers": cover_set, "cost": float(cost)})
    return distinctions, resolved_set, clean


def solve(data: dict[str, Any]) -> dict[str, Any]:
    distinctions, resolved, observations = _validate(data)
    unresolved = [d for d in distinctions if d not in resolved]

    if not unresolved:
        return {
            "schema": "PROJECT_BRAIN_MINIMUM_REALITY_CUT_VERDICT_V1",
            "status": "EXACT_MINIMUM",
            "exact_minimum": True,
            "unresolved_distinctions": [],
            "selected_observations": [],
            "total_cost": 0.0,
            "rule": "NO_REALITY_QUERY_REQUIRED"
        }

    if len(unresolved) > MAX_EXACT_DISTINCTIONS:
        return {
            "schema": "PROJECT_BRAIN_MINIMUM_REALITY_CUT_VERDICT_V1",
            "status": "DECOMPOSE_REQUIRED",
            "exact_minimum": False,
            "reason": "TOO_MANY_UNRESOLVED_DISTINCTIONS_FOR_EXACT_SOLVER",
            "unresolved_count": len(unresolved),
            "limit": MAX_EXACT_DISTINCTIONS
        }
    if len(observations) > MAX_OBSERVATIONS:
        return {
            "schema": "PROJECT_BRAIN_MINIMUM_REALITY_CUT_VERDICT_V1",
            "status": "DECOMPOSE_REQUIRED",
            "exact_minimum": False,
            "reason": "TOO_MANY_CANDIDATE_OBSERVATIONS_FOR_EXACT_SOLVER",
            "observation_count": len(observations),
            "limit": MAX_OBSERVATIONS
        }

    index = {d: i for i, d in enumerate(unresolved)}
    target = (1 << len(unresolved)) - 1
    candidates: list[tuple[str, int, float]] = []
    cover_union = 0
    for row in observations:
        mask = 0
        for d in row["covers"]:
            if d in index:
                mask |= 1 << index[d]
        if mask:
            candidates.append((row["id"], mask, row["cost"]))
            cover_union |= mask

    if cover_union != target:
        missing = [d for d, i in index.items() if not (cover_union & (1 << i))]
        return {
            "schema": "PROJECT_BRAIN_MINIMUM_REALITY_CUT_VERDICT_V1",
            "status": "UNRESOLVABLE_WITH_DECLARED_OBSERVATIONS",
            "exact_minimum": False,
            "missing_distinctions": sorted(missing)
        }

    # Exact dynamic programming over covered-distinction masks.
    # Value is (total_cost, observation_count, tuple(sorted(ids))).
    best: dict[int, tuple[float, int, tuple[str, ...]]] = {0: (0.0, 0, ())}
    for oid, omask, cost in sorted(candidates):
        snapshot = list(best.items())
        for mask, state in snapshot:
            nmask = mask | omask
            ids = tuple(sorted(state[2] + (oid,)))
            cand = (state[0] + cost, state[1] + 1, ids)
            prev = best.get(nmask)
            if prev is None or cand < prev:
                best[nmask] = cand

    if target not in best:
        raise RuntimeError("exact solver internal error: target unexpectedly unreachable")

    total_cost, count, ids = best[target]
    return {
        "schema": "PROJECT_BRAIN_MINIMUM_REALITY_CUT_VERDICT_V1",
        "status": "EXACT_MINIMUM",
        "exact_minimum": True,
        "unresolved_distinctions": unresolved,
        "selected_observations": list(ids),
        "observation_count": count,
        "total_cost": total_cost,
        "rule": "MINIMUM_COST__THEN_MINIMUM_COUNT__THEN_LEXICOGRAPHIC_ID"
    }


def self_test() -> None:
    r = solve({
        "distinctions": ["A", "B", "C"],
        "already_resolved": [],
        "observations": [
            {"id": "ab", "covers": ["A", "B"], "cost": 1},
            {"id": "c", "covers": ["C"], "cost": 1},
            {"id": "abc_expensive", "covers": ["A", "B", "C"], "cost": 3}
        ]
    })
    assert r["exact_minimum"] is True
    assert r["selected_observations"] == ["ab", "c"]
    assert r["total_cost"] == 2.0

    r2 = solve({
        "distinctions": ["A"],
        "already_resolved": ["A"],
        "observations": []
    })
    assert r2["selected_observations"] == []
    assert r2["total_cost"] == 0.0

    r3 = solve({
        "distinctions": ["A", "B"],
        "already_resolved": [],
        "observations": [{"id": "a", "covers": ["A"], "cost": 1}]
    })
    assert r3["status"] == "UNRESOLVABLE_WITH_DECLARED_OBSERVATIONS"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"status": "SELF_TEST_PASS"}, sort_keys=True))
        return 0
    if args.input is None:
        ap.error("input is required unless --self-test is used")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    out = solve(data)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("exact_minimum") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
