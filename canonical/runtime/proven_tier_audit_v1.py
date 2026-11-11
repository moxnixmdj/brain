#!/usr/bin/env python3
"""Audit the PROVEN tier: do the claims point at things that exist and run?

THE HOLE THIS CLOSES
--------------------
The census priced 3,230 governance records and verified exactly none of them. "How valuable
it is" depends on whether the claim is true, so a census that never checks is half an
answer. This module checks the one thing that is cheap and decisive:

    a PROVEN record that cites canonical/<path>.py must cite a file that EXISTS, and
    a PROVEN record that cites canonical/tests/test_<x>.py must cite a test that RUNS GREEN.

WHAT THIS DOES AND DOES NOT PROVE
---------------------------------
It proves the evidence object behind a claim is present and passing. It does NOT prove the
claim's semantics -- a green test can test the wrong thing, and a module that exists can be
irrelevant to the sentence that cites it. Those are separate audits and this module says so
in its own output rather than implying more than it checked.

THE HONEST METRIC
-----------------
    cited_artifacts_missing   -- claimed evidence that is not there
    cited_tests_red           -- claimed evidence that fails
    cited_tests_green         -- claimed evidence that passes
    uncited_proven            -- PROVEN records with no checkable artefact at all

`uncited_proven` is not a failure of the record; many records assert a deduction rather
than an execution. It is reported so that the reader knows what fraction of PROVEN is
machine-checkable at all.

Usage
    python3 canonical/runtime/proven_tier_audit_v1.py
    python3 canonical/runtime/proven_tier_audit_v1.py --json --limit-tests 40
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.every_valuable_thing_measured_v1 import classify  # noqa: E402

SCHEMA = "brain.proven_tier_audit.v1"
GOV = ROOT / "canonical/governance"

MODULE_RE = re.compile(r"canonical/[A-Za-z0-9_/]+\.py")
TEST_RE = re.compile(r"canonical/tests/[A-Za-z0-9_]+\.py")


def _proven_records() -> list[tuple[str, dict]]:
    out = []
    for p in sorted(GOV.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(d, dict) and classify(str(d.get("status") or "")) == "PROVEN":
            out.append((p.stem, d))
    return out


def _run_test(rel: str, timeout: float = 240.0) -> tuple[str, int, int]:
    """Return (verdict, passed, failed) for one cited test file."""
    target = ROOT / rel
    if not target.is_file():
        return "MISSING", 0, 0
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", rel, "-q", "-p", "no:cacheprovider", "--tb=no"],
            cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        out = r.stdout + r.stderr
    except Exception as e:
        return f"ERROR:{type(e).__name__}", 0, 0
    p = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
    f = int(m.group(1)) if (m := re.search(r"(\d+) failed", out)) else 0
    if "error" in out.lower() and p == 0 and f == 0:
        return "COLLECTION_ERROR", 0, 0
    # An empty test file is NOT a failure and it is NOT a pass. Calling it RED would
    # overstate breakage; calling it GREEN would overstate coverage. It needs its own
    # verdict, because "0 passed 0 failed" means the cited evidence executes nothing.
    if p == 0 and f == 0:
        return "EMPTY", 0, 0
    return ("GREEN" if f == 0 and p > 0 else "RED"), p, f


def audit(limit_tests: int | None = None) -> dict:
    records = _proven_records()
    cited_modules: Counter = Counter()
    cited_tests: Counter = Counter()
    uncited = 0
    for _name, d in records:
        blob = json.dumps(d)
        mods = set(MODULE_RE.findall(blob))
        tests = set(TEST_RE.findall(blob))
        # a test path also matches the module regex; keep them separate
        mods = {m for m in mods if not m.startswith("canonical/tests/")}
        if not mods and not tests:
            uncited += 1
        cited_modules.update(mods)
        cited_tests.update(tests)

    missing_modules = sorted(m for m in cited_modules if not (ROOT / m).is_file())
    missing_tests = sorted(t for t in cited_tests if not (ROOT / t).is_file())

    runnable = sorted(t for t in cited_tests if (ROOT / t).is_file())
    to_run = runnable[:limit_tests] if limit_tests else runnable
    verdicts = {}
    for t in to_run:
        v, p, f = _run_test(t)
        verdicts[t] = {"verdict": v, "passed": p, "failed": f}

    tally = Counter(v["verdict"] for v in verdicts.values())
    return {
        "schema": SCHEMA,
        "proven_records": len(records),
        "distinct_cited_modules": len(cited_modules),
        "distinct_cited_tests": len(cited_tests),
        "cited_modules_missing": len(missing_modules),
        "cited_modules_missing_list": missing_modules[:25],
        "cited_tests_missing": len(missing_tests),
        "cited_tests_missing_list": missing_tests[:25],
        "cited_tests_run": len(to_run),
        "cited_test_verdicts": tally,
        "cited_tests_red": sorted(t for t, v in verdicts.items() if v["verdict"] == "RED")[:25],
        "uncited_proven_records": uncited,
        "uncited_pct": round(100.0 * uncited / max(1, len(records)), 1),
        "machine_checkable_pct": round(
            100.0 * (len(records) - uncited) / max(1, len(records)), 1),
        "what_this_proves": [
            "the evidence object a PROVEN record cites is present on disk",
            "the cited test file passes when executed",
        ],
        "what_this_does_NOT_prove": [
            "that the test measures the sentence the record asserts",
            "that a module which exists implements what the record says it implements",
            "anything about the uncited PROVEN records, which assert deductions rather than executions",
        ],
        "records": [{"name": n, "cited_modules": sorted(set(MODULE_RE.findall(json.dumps(d))))[:8]}
                    for n, d in records],
        "test_verdicts": verdicts,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit-tests", type=int, default=None)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    out = audit(limit_tests=args.limit_tests)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    if args.json:
        print(json.dumps({k: v for k, v in out.items()
                          if k not in ("records", "test_verdicts")}, indent=1))
        return 0

    print("=" * 78)
    print("PROVEN TIER AUDIT — do the claims point at things that exist and run?")
    print("=" * 78)
    print(f"  PROVEN records                {out['proven_records']}")
    print(f"  citing a canonical module     {out['proven_records'] - out['uncited_proven_records']}"
          f"  ({out['machine_checkable_pct']}% machine-checkable)")
    print(f"  uncited (deduction-only)      {out['uncited_proven_records']}"
          f"  ({out['uncited_pct']}%)")
    print()
    print(f"  distinct cited modules        {out['distinct_cited_modules']}")
    print(f"  cited modules MISSING         {out['cited_modules_missing']}")
    print(f"  distinct cited tests          {out['distinct_cited_tests']}")
    print(f"  cited tests MISSING           {out['cited_tests_missing']}")
    print(f"  cited tests RUN               {out['cited_tests_run']}")
    if out["cited_test_verdicts"]:
        for k, v in out["cited_test_verdicts"].most_common():
            print(f"      {k:18s} {v}")
    if out["cited_tests_red"]:
        print("  RED cited tests:")
        for t in out["cited_tests_red"]:
            print(f"      {t}")
    if out["cited_modules_missing_list"]:
        print("  MISSING cited modules:")
        for m in out["cited_modules_missing_list"][:10]:
            print(f"      {m}")
    print()
    print("  what this proves:    a cited evidence object is present, and a cited test passes")
    print("  what it does NOT:    that the test measures the sentence the record asserts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
