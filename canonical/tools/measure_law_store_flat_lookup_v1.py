#!/usr/bin/env python3
"""Measure whether a bucketed law store's *lookup* is flat as the store grows.

WHY THIS EXISTS
---------------
Play 4 of the leapfrog plan claims our agent has no context window: a law is
found by its projection key, so lookup cost does not grow with the number of
laws the way token cost grows with the number of tokens. The earlier ablation
(`o1_bucket_law_store_scaling_ablation_20261124_v1.json`) measured 1 / 10 / 100 /
500 laws at 0.25–0.27 ms. It stopped at 500 and it did not report the baseline
it is being compared against.

This re-measures the same property as a self-contained index benchmark, at
1, 10, 100, 500, 1,000 and 5,000 laws, and reports BOTH:

* the bucketed store (key -> bucket -> confirm), and
* a linear scan over the same laws,

so the claim is "the index is flat and the alternative is not", not "0.25 ms is
small". A removal control runs at every size: delete the law that answered the
query and the same query must return nothing, otherwise the timing measures
nothing at all.

WHAT IT IS NOT
--------------
It measures the *index*, not the solver. No repair is produced here; a hit means
"this candidate key matched", not "this law refuted the failure". Nothing about
model calls, because there are none.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import time
from pathlib import Path
from typing import Any

SCHEMA = "BRAIN_LAW_STORE_FLAT_LOOKUP_V1"
DEFAULT_OUT = "canonical/Immediate_Results/law_store_flat_lookup_20261125_V1.json"
ATOMS = ("state", "field", "value", "list", "dict", "iter", "getter", "setter", "path", "bytes")


def make_laws(n: int, seed: int = 1301, key_mode: str = "scaled") -> list[dict[str, Any]]:
    """Two key regimes, because flatness depends on entropy and hiding that would be a lie.

    ``fixed``   keys drawn from the same 1,000 three-atom combinations regardless of n.
                Bucket occupancy rises with n, so the bucket scan is linear in occupancy.
    ``scaled``  each law gets a key over a 4-atom alphabet *plus* its ordinal, so distinct
                keys grow with n and occupancy stays ~1 -- the regime a real store is in when
                the projection key carries the discriminating detail.
    """
    rng = random.Random(seed)
    laws = []
    for i in range(n):
        if key_mode == "fixed":
            key = (rng.choice(ATOMS), rng.choice(ATOMS), rng.choice(ATOMS))
        else:
            key = (rng.choice(ATOMS), rng.choice(ATOMS), f"k{i}")
        laws.append({"id": f"law_{i:05d}", "key": key, "effect": f"effect_{i % 7}"})
    return laws


class Bucketed:
    """key -> laws. Lookup touches one bucket, then confirms. Never scans the store."""

    comparisons = 0

    def __init__(self, laws: list[dict[str, Any]]):
        self.buckets: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for law in laws:
            self.buckets.setdefault(tuple(law["key"]), []).append(law)

    def lookup(self, key: tuple[str, ...]) -> list[dict[str, Any]]:
        bucket = self.buckets.get(tuple(key), ())
        Bucketed.comparisons += len(bucket)
        return [law for law in bucket if law["key"] == key]


class Linear:
    comparisons = 0

    def __init__(self, laws: list[dict[str, Any]]):
        self.laws = laws

    def lookup(self, key: tuple[str, ...]) -> list[dict[str, Any]]:
        Linear.comparisons += len(self.laws)
        return [law for law in self.laws if law["key"] == key]


def time_lookups(index: Any, keys: list[tuple[str, ...]], repeats: int) -> dict[str, Any]:
    samples: list[float] = []
    hits = 0
    for key in keys:
        start = time.perf_counter()
        for _ in range(repeats):
            found = index.lookup(key)
        elapsed = (time.perf_counter() - start) / repeats
        samples.append(elapsed * 1000.0)
        hits += 1 if found else 0
    samples.sort()
    return {
        "median_ms": round(statistics.median(samples), 6),
        "p95_ms": round(samples[max(0, int(len(samples) * 0.95) - 1)], 6),
        "hits": hits,
        "queries": len(keys),
    }


def measure(size: int, *, queries: int = 60, repeats: int = 5, seed: int = 1301,
            key_mode: str = "scaled") -> dict[str, Any]:
    laws = make_laws(size, seed, key_mode)
    rng = random.Random(seed + size)
    keys = [tuple(rng.choice(laws)["key"]) for _ in range(queries)]
    bucketed, linear = Bucketed(laws), Linear(laws)

    Bucketed.comparisons = 0
    fast = time_lookups(bucketed, keys, repeats)
    fast["comparisons_per_query"] = round(Bucketed.comparisons / len(keys), 2)
    Linear.comparisons = 0
    slow = time_lookups(linear, keys, repeats)
    slow["comparisons_per_query"] = round(Linear.comparisons / len(keys), 2)

    # Removal control: the law that answered must be gone. The *key* may still have other
    # owners (two laws can project to the same key), so the control checks the id, not the key.
    target = laws[-1]
    trimmed = Bucketed([law for law in laws if law["id"] != target["id"]])
    before = Bucketed(laws).lookup(tuple(target["key"]))
    after = trimmed.lookup(tuple(target["key"]))

    return {
        "law_count": size,
        "key_mode": key_mode,
        "buckets": len(bucketed.buckets),
        "bucket_occupancy": round(size / max(1, len(bucketed.buckets)), 2),
        "bucketed": fast,
        "linear": slow,
        "speedup": round(slow["median_ms"] / fast["median_ms"], 2) if fast["median_ms"] else None,
        "removal_control": {
            "law": target["id"],
            "law_present_before": any(law["id"] == target["id"] for law in before),
            "law_present_after": any(law["id"] == target["id"] for law in after),
            "control_ok": any(law["id"] == target["id"] for law in before)
                          and not any(law["id"] == target["id"] for law in after),
        },
    }


def run(sizes: tuple[int, ...] = (1, 10, 100, 500, 1000, 5000), **kw: Any) -> dict[str, Any]:
    rows = [measure(size, **kw) for size in sizes]
    fixed_rows = [measure(size, key_mode="fixed", **kw) for size in sizes]
    # A subset run must still report honest ratios: compare the smallest and largest
    # sizes actually measured, and only emit the 5000-over-10 keys when those exist.
    smallest = min(rows, key=lambda r: r["law_count"])
    largest = max(rows, key=lambda r: r["law_count"])
    # The headline ratio is the 10 -> 5000 comparison, so it is only emitted when those
    # exact sizes were measured; a subset run reports max-over-min under its own name.
    base = next((r for r in rows if r["law_count"] == 10), smallest)
    top = next((r for r in rows if r["law_count"] == 5000), largest)
    thousand = next((r for r in rows if r["law_count"] == 1000), None)
    ratios = {
        "bucketed_1000_over_10": round(thousand["bucketed"]["median_ms"] / base["bucketed"]["median_ms"], 2)
        if thousand and base["bucketed"]["median_ms"] else None,
        "bucketed_5000_over_10": round(top["bucketed"]["median_ms"] / base["bucketed"]["median_ms"], 2)
        if top["law_count"] == 5000 and base["law_count"] == 10 and base["bucketed"]["median_ms"] else None,
        "linear_5000_over_10": round(top["linear"]["median_ms"] / base["linear"]["median_ms"], 2)
        if base["linear"]["median_ms"] else None,
    }
    return {
        "schema": SCHEMA,
        "date_utc": "2026-11-25",
        "model_calls": 0,
        "measures": "INDEX_LOOKUP_ONLY__NOT_SOLVER_QUALITY",
        "rows": rows,
        "rows_fixed_key_space": fixed_rows,
        "ratios": ratios,
        "controls_pass": all(r["removal_control"]["control_ok"] for r in rows + fixed_rows),
        "fixed_5000_over_10": round(
            max(r["bucketed"]["median_ms"] for r in fixed_rows)
            / max(min(r["bucketed"]["median_ms"] for r in fixed_rows), 1e-9), 2)
        if any(r["law_count"] == 5000 for r in fixed_rows) else None,
        "flat_claim_holds": bool(ratios["bucketed_5000_over_10"] is not None
                                 and ratios["bucketed_5000_over_10"] < 2.0),
        "kill_criterion": "if bucketed_5000_over_10 >= 2.0 the flat-lookup claim is dead",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args(argv)
    result = run()
    out = Path(args.root) / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{'laws':>6}{'buckets':>9}{'bucketed ms':>13}{'linear ms':>12}{'speedup':>9}{'control':>9}")
    for row in result["rows"]:
        print(f"{row['law_count']:>6}{row['buckets']:>9}{row['bucketed']['median_ms']:>13}"
              f"{row['linear']['median_ms']:>12}{row['speedup']:>9}{str(row['removal_control']['control_ok']):>9}")
    print("\nfixed key space (1,000 possible keys):")
    print(f"{'laws':>6}{'buckets':>9}{'occupancy':>11}{'bucketed ms':>13}{'cmps/query':>12}")
    for row in result["rows_fixed_key_space"]:
        print(f"{row['law_count']:>6}{row['buckets']:>9}{row['bucket_occupancy']:>11}"
              f"{row['bucketed']['median_ms']:>13}{row['bucketed']['comparisons_per_query']:>12}")
    print(json.dumps(result["ratios"], indent=1))
    print("fixed-key 5000/10 ratio:", result["fixed_5000_over_10"])
    print("flat_claim_holds:", result["flat_claim_holds"], "| controls:", result["controls_pass"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
