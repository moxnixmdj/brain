#!/usr/bin/env python3
"""Reliability and speed of the tests that exercise each tested verified capability.

Scope: the verified bound capabilities that have at least one importing test file
(from capability_health.py). For each such test file, run it REPEAT times with
pytest and record pass/fail and wall-clock seconds.

This measures reliability and speed of the existing tests. It does NOT measure
capability power against a baseline, because the repo defines no task set or
no-capability baseline.
Writes out/bench_capabilities.csv and a summary JSON. Caches are disabled so the
repo tree is not modified.
"""
import csv
import collections
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]
PY = sys.executable
REPEAT = 3
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(canonical(?:\.[A-Za-z_]\w*)+)", re.M)


def main() -> None:
    with (OUT / "capability_health.csv").open() as fh:
        tested = [r for r in csv.DictReader(fh) if int(r["importing_test_files"]) > 0]

    test_files = {}
    for path in TREE.joinpath("canonical").rglob("test_*.py"):
        rel = path.relative_to(TREE).as_posix()
        test_files[rel] = set(IMPORT_RE.findall(path.read_text(errors="ignore")))

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    rows = []
    for cap in tested:
        dotted = cap["source_path"][:-3].replace("/", ".")
        files = sorted(f for f, mods in test_files.items() if dotted in mods)
        for f in files:
            for rep in range(1, REPEAT + 1):
                t0 = time.monotonic()
                proc = subprocess.run(
                    [PY, "-m", "pytest", "-q", f, "-p", "no:cacheprovider"],
                    cwd=TREE, env=env, capture_output=True, text=True, timeout=900,
                )
                secs = time.monotonic() - t0
                tail = (proc.stdout.strip().splitlines() or [""])[-1]
                rows.append({
                    "capability_id": cap["capability_id"],
                    "test_file": f,
                    "repeat": rep,
                    "exit_code": proc.returncode,
                    "passed": proc.returncode == 0,
                    "seconds": round(secs, 2),
                    "summary": tail[:200],
                })

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "bench_capabilities.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    per_cap = collections.defaultdict(list)
    for r in rows:
        per_cap[r["capability_id"]].append(r)
    summary = {
        "repeats_per_test_file": REPEAT,
        "capabilities": len(per_cap),
        "per_capability": {
            cid: {
                "runs": len(rs),
                "pass_rate": round(sum(r["passed"] for r in rs) / len(rs), 3),
                "median_seconds": round(statistics.median(r["seconds"] for r in rs), 2),
            }
            for cid, rs in per_cap.items()
        },
        "power_measured_against_baseline": False,
        "caveat": "reliability and speed of existing tests; no task set and no baseline in the repo",
    }
    (OUT / "bench_capabilities_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
