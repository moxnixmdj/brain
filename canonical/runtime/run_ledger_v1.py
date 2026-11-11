"""Remember every outcome, so no claim is ever a remembered total again.

WHY THIS EXISTS
---------------
r135 is the reason. A router change was measured at 27.5% before and 25.0% after.
The totals said "down one". They could not say WHICH task moved, and the transcript
had been truncated to its tail, so the regression was unnamable and the improvement
was indistinguishable from noise.

A run that reports only a total is not a measurement of a change. It is a
measurement of two different afternoons. The difference between those two things
is a per-task ledger on disk, diffed against the previous run.

WHAT IT RECORDS
---------------
One row per (policy, task) with the outcome, the action used, the reward, and a
fingerprint of the policy that produced it. Append-only, one JSON object per line,
so a crash mid-run cannot corrupt earlier rows and two runs can always be compared.

WHAT IT REFUSES TO DO
---------------------
It will not compute a "score" without the raw rows. A ledger that stores only
aggregates is the thing it was built to replace.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_RUN_LEDGER_V1"
DEFAULT_PATH = "canonical/governance/run_ledger_v1.jsonl"


def policy_fingerprint(source: str) -> str:
    """Short hash of the code that produced a run.

    Without this, two runs differ by a policy change and the diff cannot say
    whether the code or the world moved.
    """
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


def _path(path: str | None) -> str:
    return path or DEFAULT_PATH


def record(
    run_id: str,
    policy: str,
    task: str,
    success: bool,
    *,
    action: str | None = None,
    reward: float | None = None,
    seconds: float | None = None,
    path: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one (policy, task) outcome. Never rewrites history."""
    row = {
        "schema": SCHEMA,
        "run_id": run_id,
        "policy": policy,
        "task": task,
        "success": bool(success),
        "action": action,
        "reward": reward,
        "seconds": round(seconds, 3) if seconds is not None else None,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "extra": dict(extra) if extra else None,
    }
    target = _path(path)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def load(path: str | None = None) -> list[dict[str, Any]]:
    target = _path(path)
    if not os.path.exists(target):
        return []
    rows = []
    with open(target, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # A torn final line from a killed run must not destroy the ledger.
                continue
    return rows


def outcomes(rows: Iterable[Mapping[str, Any]], run_id: str) -> dict[str, bool]:
    return {r["task"]: bool(r["success"]) for r in rows if r.get("run_id") == run_id}


def diff(
    before: str,
    after: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """The only comparison that is honest: per-task, not per-total.

    A net-zero change can contain one fix and one break. A net-plus-one can contain
    two fixes and one break. Only the named sets tell you which you have.
    """
    rows = load(path)
    b = outcomes(rows, before)
    a = outcomes(rows, after)
    tasks = sorted(set(b) | set(a))
    fixed = [t for t in tasks if a.get(t) and not b.get(t)]
    broke = [t for t in tasks if b.get(t) and not a.get(t)]
    same_pass = [t for t in tasks if b.get(t) and a.get(t)]
    same_fail = [t for t in tasks if not b.get(t) and not a.get(t)]
    return {
        "schema": SCHEMA + "_DIFF",
        "before_run": before,
        "after_run": after,
        "n_before": len(b),
        "n_after": len(a),
        "score_before": sum(1 for v in b.values() if v),
        "score_after": sum(1 for v in a.values() if v),
        "net": sum(1 for v in a.values() if v) - sum(1 for v in b.values() if v),
        "fixed": fixed,
        "broke": broke,
        "unchanged_pass": same_pass,
        "unchanged_fail": same_fail,
        "verdict": (
            "PURE_GAIN" if fixed and not broke
            else "PURE_REGRESSION" if broke and not fixed
            else "MIXED" if fixed and broke
            else "NO_CHANGE"
        ),
    }


def summarise(run_id: str, *, path: str | None = None) -> dict[str, Any]:
    rows = [r for r in load(path) if r.get("run_id") == run_id]
    n = len(rows)
    passed = sum(1 for r in rows if r["success"])
    return {
        "schema": SCHEMA + "_SUMMARY",
        "run_id": run_id,
        "tasks": n,
        "passed": passed,
        "failed": n - passed,
        "reach": round(passed / n, 4) if n else 0.0,
        "policies": sorted({r.get("policy") for r in rows if r.get("policy")}),
    }
