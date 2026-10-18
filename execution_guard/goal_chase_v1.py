#!/usr/bin/env python3
"""Plain sentence in, chase the number until it is measured as reached.

    "Make me a million dollars"  ->  bind  ->  act  ->  measure  ->  repeat

This is the composition of three things that already existed:

    goal_target_binding_v1    sentence -> {target, direction, unit}
    live_brain_route_admission_v1.solve
                              THE live entry: plain goal -> compiled capability
                              -> execution -> tool truth -> promised artifacts.
                              Deterministic, model-free, proven daily by the
                              heartbeat at ~150 fresh goals a run.
    target_chase_driver_v1    act / measure / re-plan, stopping only on a
                              measurement, learning inline every round.

THE ONE THING THE CALLER MUST SUPPLY: `measure`.

"Make me a million dollars" has no oracle in this repository. There is no bank
balance to read, no revenue ledger to query. The driver refuses to run without
a measurement, and this module refuses to invent one -- because a machine that
grades its own progress will eventually report a million dollars it never made.
That is the law VERIFICATION_IS_SOMEONE_ELSE, and it is the reason this file is
thin rather than clever.

If no measurement can be named, the honest answer is not a number. It is
FAIL_CLOSED, and the gap stays visible.

Authority: NONE. Credit: 0.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]

from execution_guard import goal_target_binding_v1 as binding  # noqa: E402
from execution_guard import target_chase_driver_v1 as chase  # noqa: E402

SCHEMA = "PROJECT_BRAIN_GOAL_CHASE_V1"


def live_act(goal: str, *, tag: str | None = None) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Return an `act` that drives the machine's one live entry.

    task ids must be unique: the live controller checkpoints per task id and
    refuses to re-run a finished one.
    """
    tag = tag or ("gc_" + hashlib.sha256(os.urandom(12)).hexdigest()[:10])

    def act(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
        from canonical.runtime import live_brain_route_admission_v1 as entry

        task_id = f"{tag}_{int(ctx.get('round', 0))}"
        try:
            out = entry.solve({"task_id": task_id, "goal": goal})
        except Exception as exc:
            return {
                "status": "LIVE_ENTRY_EXCEPTION",
                "error": type(exc).__name__ + ":" + str(exc)[:200],
            }
        if not isinstance(out, Mapping):
            return {"status": "LIVE_ENTRY_NON_OBJECT", "error": "not a mapping"}
        status = out.get("status")
        ok = out.get("pass") is True
        row: dict[str, Any] = {
            "status": status,
            "error": "" if ok else str(
                out.get("failure_class") or out.get("reason") or status or ""
            ),
            "capability_id": str(
                out.get("compiled_capability_id") or out.get("compiler_mode") or ""
            ),
        }
        # Only a passing run teaches anything worth reusing.
        if ok:
            row["procedure"] = str(row["capability_id"] or status or "")
        return row

    return act


def run(
    goal: str,
    *,
    measure: Callable[[], float | None],
    act: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    unit: str | None = None,
    target: float | None = None,
    direction: str | None = None,
    max_rounds: int = 16,
    patience: int = 3,
    flywheel_state_path: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind the sentence, then chase it. Or refuse, without inventing anything.

    `target`/`direction`/`unit` may be supplied to override a bad binding, but
    supplying them is a claim the caller is making, and it is recorded as such.
    """
    bound = binding.bind(goal)

    if not bound.get("pass"):
        if target is None or direction is None:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__GOAL_HAS_NO_MEASURABLE_TARGET",
                "pass": False,
                "goal": goal,
                "binding": bound,
                "detail": (
                    "no number could be bound from the goal, and no target was "
                    "supplied; a target is never invented"
                ),
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
        bound = {
            **bound,
            "pass": True,
            "target": float(target),
            "direction": direction,
            "unit": unit or "",
            "relation_source": "SUPPLIED_BY_CALLER__NOT_BOUND_FROM_GOAL",
            "evidence": {"note": "caller overrode the binding"},
        }

    if target is not None:
        bound = {**bound, "target": float(target)}
    if direction is not None:
        bound = {**bound, "direction": direction}
    if unit is not None:
        bound = {**bound, "unit": unit}

    result = chase.run(
        goal=goal,
        target=bound["target"],
        direction=bound["direction"],
        unit=bound.get("unit", ""),
        measure=measure,
        act=act if act is not None else live_act(goal),
        max_rounds=max_rounds,
        patience=patience,
        flywheel_state_path=flywheel_state_path,
        context=context,
    )
    return {
        "schema": SCHEMA,
        "goal": goal,
        "binding": bound,
        "chase": result,
        "status": result["status"],
        "pass": result["pass"],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
