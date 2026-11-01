#!/usr/bin/env python3
"""Fail the build when a capability's declared verification stops being able to fail.

`canonical/runtime/expect_discrimination_v1.py` measures how many capabilities declare an
`expect` that is a constant their own adapter assigns -- a check that observes nothing. Measured
2026-11-01: 155 capabilities, 59 constant (dead) expects, 8 dead and uncovered, 94.8%
discrimination. The module existed and no workflow ran it, so the number could only drift down.

This is a ratchet, not a target: it compares today's measurement to `--baseline` and fails if any
number got worse. Fixing capabilities lowers the bar permanently; nobody can raise it to pass.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = "canonical/runtime/expect_discrimination_v1.py"
FIELDS = {
    "capabilities": r"capabilities\s*:\s*(\d+)",
    "constant_expects": r"constant \(dead\) expects\s*:\s*(\d+)",
    "dead_and_uncovered": r"dead and uncovered\s*:\s*(\d+)",
    "discrimination_pct": r"discrimination\s*:\s*([\d.]+)",
}


def measure() -> dict[str, float]:
    out = subprocess.run(
        [sys.executable, MODULE], cwd=ROOT, text=True, capture_output=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
    )
    # The measuring module exits non-zero when it finds dead expects; that is its verdict, not a
    # failure to measure, so the numbers are read either way.
    if not out.stdout.strip():
        raise SystemExit(f"measurement produced no report:\n{out.stderr}")
    values = {}
    for name, pattern in FIELDS.items():
        hit = re.search(pattern, out.stdout)
        if not hit:
            raise SystemExit(f"could not read {name} from the report")
        values[name] = float(hit.group(1))
    return values


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="canonical/verification/EXPECT_DISCRIMINATION_BASELINE_20261101_V1.json")
    ns = ap.parse_args()
    base = json.loads((ROOT / ns.baseline).read_text())
    live = measure()
    print(json.dumps({"baseline": base, "live": live}, indent=1))
    worse = []
    for name in ("constant_expects", "dead_and_uncovered"):
        if live[name] > base[name]:
            worse.append(f"{name} rose {base[name]} -> {live[name]}")
    if live["discrimination_pct"] < base["discrimination_pct"]:
        worse.append(f"discrimination fell {base['discrimination_pct']} -> {live['discrimination_pct']}")
    if live["capabilities"] < base["capabilities"]:
        worse.append(f"capabilities fell {base['capabilities']} -> {live['capabilities']}")
    if worse:
        print("EXPECT_DISCRIMINATION_REGRESSION")
        for row in worse:
            print(" - " + row)
        return 1
    print("EXPECT_DISCRIMINATION_RATCHET_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
