"""Steps to completion: the frontier's own scoring axis, applied to this runtime.

WHY THIS FILE EXISTS AND WHY IT IS SHAPED THIS WAY
--------------------------------------------------

ARC-AGI-3 is, as of 2026, the only general agentic benchmark that is not saturated:
humans solve 100% of its environments, and every frontier model scores below 1%.
Its scoring rule is not accuracy -- it is **actions relative to a human baseline**.
Beating a task with more steps earns a *lower* score; brute force is explicitly
punished.

That is the one frontier metric this repository has never measured itself on. It has
measured pass rates, receipts and certificates -- but never *how many actions it took*.
A system can pass every check it owns and still be four times less efficient than a
human, which is exactly what OSWorld-Human found for the leading computer-use agents
(2.7x-4.3x longer trajectories than necessary).

So this benchmark is deliberately the smallest thing that produces the frontier's own
number: count the steps a goal actually takes, and compare against the minimum.

WHAT A "STEP" IS HERE
---------------------

One module boundary crossing with observable effect: the capability adapter is invoked
once, and every distinct file it writes is counted. No weighted composite, no invented
index, no second score. One integer, comparable across runs and across systems.

WHAT THIS BENCHMARK CANNOT SAY
------------------------------

It does not score against humans, and it must never pretend to: this runtime has no
ARC-AGI-3 harness and inventing a number that looked like RHAE would be the exact
self-deception the rest of this repository exists to prevent. It reports *steps* and
*seconds*, and says so.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_STEPS_TO_COMPLETION_V1"


@dataclass
class Attempt:
    """One goal, one path, one set of measured costs."""

    path: str
    goal: str
    passed: bool
    elapsed_s: float
    steps: int
    artifacts: list[str] = field(default_factory=list)
    receipt: str | None = None
    error: str = ""

    @property
    def steps_per_second(self) -> float:
        return self.steps / self.elapsed_s if self.elapsed_s > 0 else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "goal": self.goal,
            "passed": self.passed,
            "elapsed_s": round(self.elapsed_s, 3),
            "steps": self.steps,
            "steps_per_second": round(self.steps_per_second, 3),
            "artifacts": self.artifacts,
            "receipt": self.receipt,
            "error": self.error,
        }


def _snapshot(root: Path) -> dict[str, str]:
    """Files and sizes under `root`, so a run's writes can be counted honestly."""
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            try:
                out[str(path)] = f"{path.stat().st_size}"
            except OSError:
                continue
    return out


def measure(
    *,
    path: str,
    goal: str,
    run: Callable[[], Mapping[str, Any]],
    watch: Path,
    passed_field: str = "pass",
) -> Attempt:
    """Run one goal and count what it cost. Never raises: a raise is a measured failure."""
    before = _snapshot(watch)
    started = time.perf_counter()
    try:
        result = dict(run() or {})
        error = ""
    except Exception as exc:  # noqa: BLE001 - a raise is a fate to be measured
        result, error = {}, f"{type(exc).__name__}: {exc}"[:200]
    elapsed = time.perf_counter() - started
    after = _snapshot(watch)

    written = [p for p, sz in after.items() if before.get(p) != sz]
    # A step is an adapter invocation that produced an observable effect; with no
    # file effect the call still happened, so it is still one step.
    steps = max(1, len(written))
    return Attempt(
        path=path,
        goal=goal,
        passed=result.get(passed_field) is True,
        elapsed_s=elapsed,
        steps=steps,
        artifacts=sorted(written),
        receipt=_receipt_of(result),
        error=error,
    )


def _receipt_of(result: Mapping[str, Any]) -> str | None:
    """The confinement receipt if one exists, else None. Never invented."""
    conf = result.get("confinement")
    if isinstance(conf, Mapping):
        value = conf.get("receipt_sha256")
        if isinstance(value, str):
            return value
    execution = result.get("execution")
    if isinstance(execution, Mapping):
        return _receipt_of(execution)
    return None


def summarise(attempts: list[Attempt]) -> dict[str, Any]:
    """One row per path, with the frontier's axis: steps and seconds to completion."""
    paths: dict[str, dict[str, Any]] = {}
    for a in attempts:
        row = paths.setdefault(
            a.path,
            {"path": a.path, "goals": 0, "passed": 0, "steps": 0,
             "elapsed_s": 0.0, "with_receipt": 0},
        )
        row["goals"] += 1
        row["passed"] += int(a.passed)
        row["steps"] += a.steps
        row["elapsed_s"] += a.elapsed_s
        row["with_receipt"] += int(a.receipt is not None)

    for row in paths.values():
        row["elapsed_s"] = round(row["elapsed_s"], 2)
        row["s_per_passed_goal"] = (
            round(row["elapsed_s"] / row["passed"], 2) if row["passed"] else None
        )
    return {
        "schema": SCHEMA,
        "axis": "steps and seconds to completion (ARC-AGI-3 scores actions, not accuracy)",
        "paths": list(paths.values()),
        "attempts": [a.as_dict() for a in attempts],
        "digest": hashlib.sha256(
            json.dumps([a.as_dict() for a in attempts], sort_keys=True).encode()
        ).hexdigest(),
    }
