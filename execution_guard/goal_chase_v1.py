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


def global_options(
    goal: str,
    *,
    root: Path = ROOT,
    queries: list[str] | None = None,
    sources: list[Mapping[str, Any]] | None = None,
    limit: int = 8,
) -> Callable[[Mapping[str, Any]], list[dict[str, Any]]]:
    """Widen the option set from the global anti-blind-spot controller.

    This is the defence against the failure the owner described: read one paper
    saying "the fastest way is YouTube videos" and conclude YouTube, when the
    opportunity space is enormously larger and most of it is not written down
    anywhere obvious.

    The controller discounts CORRELATED channels rather than counting them as
    independent evidence -- ten sources repeating one claim are one source --
    and it ranks what to fetch by expected recovery per unit latency. It also
    never authorizes a claim of nonexistence: `a miss in an open world never
    authorizes nonexistence`. Nothing it returns is truth; every row is
    CANDIDATE_ONLY until independently verified.

    If the authority gate fails closed, this returns nothing rather than
    inventing options.
    """
    from canonical.runtime import global_retrieval_entrypoint_v4 as entry

    def provider(ctx: Mapping[str, Any]) -> list[dict[str, Any]]:
        known = {str(o) for o in ctx.get("known_options", [])}
        query_actions = [
            {"kind": "QUERY", "query": q, "source": "web"}
            for q in (queries or _queries_for(goal, ctx))
        ]
        try:
            out = entry.compile_authorized_plan(
                root=root,
                query_actions=query_actions,
                sources=list(sources or _DEFAULT_SOURCES),
                state=None,
            )
        except Exception:
            return []
        if out.get("status") != "PASS__AUTHORIZED_EMPIRICAL_PLAN_WITH_VERIFIED_RECOVERY_PORTFOLIO":
            return []
        plan = out.get("plan")
        if not isinstance(plan, Mapping):
            return []
        rows: list[dict[str, Any]] = []
        for action in plan.get("actions") or []:
            if not isinstance(action, Mapping):
                continue
            priority = action.get("retrieval_priority_v3") or {}
            row = {
                "kind": action.get("kind"),
                "query": action.get("query"),
                "source_id": action.get("source_id"),
                "expected_recovery_factor": priority.get("expected_recovery_factor"),
                "latency_seconds": priority.get("latency_seconds"),
                "mean_request_count": priority.get("mean_request_count"),
                "candidate_authority": action.get("candidate_authority"),
                "nonexistence_claim_authorized": action.get("nonexistence_claim_authorized"),
            }
            if str(row) in known:
                continue
            rows.append(row)
        # Best expected recovery per unit latency first: the fastest way to new
        # data is the whole requirement.
        rows.sort(
            key=lambda r: -(
                float(r["expected_recovery_factor"] or 0.0)
                / max(float(r["latency_seconds"] or 0.0), 1e-6)
            )
        )
        return rows[:limit]

    return provider


_DEFAULT_SOURCES = ({"source_id": "web", "kind": "EXTERNAL_INDEX", "enumeration_interface": False},)


# The trap is not having too few answers; it is asking the same question in one
# voice and treating agreement as confirmation. These framings probe DIFFERENT
# regions of the space, mechanically and with no model. Where independent
# sources genuinely agree the controller counts them once; where only one voice
# answers, that single voice is visible as one channel and not as the world.
_PROBE_FRAMINGS = (
    "ways to {goal}",
    "fastest way to {goal}",
    "unconventional or overlooked ways to {goal}",
    "alternatives to the most common way to {goal}",
    "what does not work when trying to {goal}",
    "hidden or non-obvious opportunities to {goal}",
    "measured evidence on how long it takes to {goal}",
)


def _queries_for(goal: str, ctx: Mapping[str, Any]) -> list[str]:
    """Probe what is NOT yet known, in several voices, never one."""
    text = str(goal).strip().rstrip(".")
    return [f.format(goal=text) for f in _PROBE_FRAMINGS]


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
    widen_options: bool = True,
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
        options_provider=(global_options(goal) if widen_options else None),
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
