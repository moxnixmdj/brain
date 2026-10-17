#!/usr/bin/env python3
"""CrossHair-backed mechanical contract oracle.

Why this exists.  TRUE_CAPABILITY_TEST_LAW_V1 requires at least two
independent oracles and a model_dependency_count of 0.  Until now the Python
repair cluster had no mechanical judge: the only evidence a repair worked was
the test suite, which is not independent of the repair process.

CrossHair symbolically executes a function and searches for inputs that break
its declared contract.  It is deterministic, driven by an SMT solver, and
contains no model -- so it is a legitimate independent oracle with a
completely different lineage from any generator we own.

Fail-closed.  If CrossHair is missing, or the run is inconclusive, the result
says so.  It never reports that contracts hold unless it actually checked them.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_CROSSHAIR_CONTRACT_ORACLE_V1"

VIOLATION_RE = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+):\s*error:\s*(?P<msg>.*)$")


def _safe_path(root: str, raw) -> pathlib.Path:
    root_p = pathlib.Path(root).resolve()
    raw_s = str(raw or "")
    p = pathlib.Path(raw_s)
    if not p.is_absolute():
        p = root_p / raw_s
    p = p.resolve()
    if root_p not in p.parents and p != root_p:
        raise ValueError("PATH_OUTSIDE_ROOT")
    return p


def run(args: dict, root: str) -> dict:
    args = dict(args or {})
    target = _safe_path(root, args.get("target_path"))
    out = _safe_path(root, args.get("output_path"))
    if not target.is_file():
        raise ValueError("ORACLE_TARGET_MISSING")

    timeout = float(args.get("timeout_s") or 300)
    proc = subprocess.run(
        [sys.executable, "-m", "crosshair", "check", str(target)],
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")

    violations = []
    for line in combined.splitlines():
        m = VIOLATION_RE.match(line.strip())
        if m:
            violations.append(
                {
                    "file": m.group("path"),
                    "line": int(m.group("line")),
                    "message": m.group("msg").strip(),
                }
            )

    if violations:
        status = "CONTRACT_VIOLATION_FOUND"
    elif proc.returncode == 0:
        status = "CONTRACTS_HOLD"
    else:
        status = "ORACLE_INCONCLUSIVE"

    result = {
        "schema": SCHEMA,
        "oracle": "crosshair",
        "model_dependency_count": 0,
        "target": str(target),
        "status": status,
        "violations": violations,
        "violation_count": len(violations),
        "returncode": proc.returncode,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["output_path"] = str(out)
    result["output_verified"] = status in ("CONTRACT_VIOLATION_FOUND", "CONTRACTS_HOLD")
    return result
