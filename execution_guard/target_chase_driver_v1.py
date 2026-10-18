#!/usr/bin/env python3
"""Chase a number, not a request.

WHY THIS EXISTS
---------------
The machine's existing loops are request-solving loops. They close when every
unresolved edge in a request is resolved, which is the correct stop rule for
"answer this question" and the wrong stop rule for "make me a million dollars".

Those differ in exactly one place. A request loop asks: *is the request fully
resolved yet?* A goal chase asks: *has the number moved far enough yet, measured
by someone other than the thing doing the work?*

Everything else the chase needs already exists and is reused here, not rebuilt:

  act / re-plan / cycle-detect   general_adequate_decision_fixed_point_v2.run
  global, non-local options      global_retrieval_controller_v1
                                 ("correlated channels are discounted rather
                                  than counted as independent evidence"
                                  -> ten sources saying "YouTube" are ONE source)
  instant credit / suppression   experience_v1  (0.238 ms per observation)
  proof the goal was satisfied   _authenticate_goal_satisfaction_binding

THE THREE RULES (these are the entire point; everything else is plumbing)
-----------------------------------------------------------------------
1. MET is returned only when the MEASUREMENT is on the far side of the target.
   Never when the actor believes it is. The actor is not allowed to grade
   itself -- that is the law `VERIFICATION_IS_SOMEONE_ELSE`.
2. STUCK is returned only after `patience` consecutive rounds with zero
   improvement, and it is reported as failure, never as success.
3. ROUND_BOUND_EXHAUSTED is not success either. Running out of rounds is not
   reaching the goal.

There is deliberately no fourth outcome. A chase either arrives, or it says it
did not.

Authority: NONE. Credit: 0.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_TARGET_CHASE_DRIVER_V1"

MET = "PASS__TARGET_CHASE_MET"
STUCK = "OPEN__TARGET_CHASE_NO_MEASURED_PROGRESS"
BOUND = "OPEN__TARGET_CHASE_ROUND_BOUND_EXHAUSTED"
NOT_MEASURABLE = "FAIL_CLOSED__TARGET_NOT_MEASURABLE"

DIRECTIONS = ("maximize", "minimize")


class TargetChaseError(ValueError):
    pass


def _callee_identity(fn: Any) -> tuple[Any, Any]:
    """Who is really being called.

    `obj.method is obj.method` is FALSE -- every attribute access builds a fresh
    bound-method object. Identity alone therefore misses the ordinary case of
    handing the same bound method in as both actor and judge, which is exactly
    the mistake this guard exists to catch. Compare the underlying function and
    its instance instead.
    """
    return (getattr(fn, "__func__", fn), getattr(fn, "__self__", None))


def _same_callee(a: Any, b: Any) -> bool:
    left, right = _callee_identity(a), _callee_identity(b)
    return left[0] is right[0] and left[1] is right[1]


def _on_target(measured: float, target: float, direction: str) -> bool:
    """Has the number arrived?  >= for a floor, <= for a ceiling."""
    if direction == "maximize":
        return measured >= target
    return measured <= target


def _improved(best: float, measured: float, direction: str) -> bool:
    if direction == "maximize":
        return measured > best
    return measured < best


def run(
    *,
    goal: str,
    target: float,
    direction: str = "maximize",
    unit: str = "",
    measure: Callable[[], float | None],
    act: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    max_rounds: int = 16,
    patience: int = 3,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Act, measure, re-plan -- until the number arrives or progress dies.

    measure() must be independent of act(). If they are the same function, the
    machine is grading its own homework and this driver's whole guarantee is
    void. The caller is responsible for that separation; the driver records it.
    """
    if direction not in DIRECTIONS:
        raise TargetChaseError("CHASE_DIRECTION_INVALID:" + str(direction))
    if not isinstance(target, (int, float)) or isinstance(target, bool):
        raise TargetChaseError("CHASE_TARGET_NOT_A_NUMBER")
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 0:
        raise TargetChaseError("CHASE_MAX_ROUNDS_INVALID")
    if isinstance(patience, bool) or not isinstance(patience, int) or patience < 1:
        raise TargetChaseError("CHASE_PATIENCE_INVALID")
    if _same_callee(measure, act):
        raise TargetChaseError("CHASE_MEASURE_IS_ACT__ACTOR_CANNOT_GRADE_ITSELF")

    started = time.perf_counter()
    base = dict(context or {})
    rounds: list[dict[str, Any]] = []

    opening = measure()
    if opening is None:
        return _result(NOT_MEASURABLE, goal, target, direction, unit, [], None, opening, started)
    best = float(opening)
    if _on_target(best, float(target), direction):
        return _result(MET, goal, target, direction, unit, rounds, best, opening, started)

    stale = 0
    for index in range(max_rounds):
        before = best
        try:
            action = act({**base, "round": index, "measured": before, "target": target})
        except Exception as exc:
            rounds.append({"round": index, "error": type(exc).__name__ + ":" + str(exc)[:200]})
            stale += 1
            if stale >= patience:
                return _result(STUCK, goal, target, direction, unit, rounds, best, opening, started)
            continue

        measured = measure()
        if measured is None:
            rounds.append({"round": index, "measure_error": "MEASURE_RETURNED_NONE"})
            stale += 1
            if stale >= patience:
                return _result(STUCK, goal, target, direction, unit, rounds, best, opening, started)
            continue

        measured = float(measured)
        row = {
            "round": index,
            "before": before,
            "after": measured,
            "delta": round(measured - before, 6),
            "best_so_far": best,
        }
        if isinstance(action, Mapping):
            row["action_status"] = action.get("status")
        rounds.append(row)

        if _on_target(measured, float(target), direction):
            best = measured
            return _result(MET, goal, target, direction, unit, rounds, best, opening, started)

        if _improved(best, measured, direction):
            best = measured
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                return _result(STUCK, goal, target, direction, unit, rounds, best, opening, started)

    return _result(BOUND, goal, target, direction, unit, rounds, best, opening, started)


def _result(status, goal, target, direction, unit, rounds, best, opening, started) -> dict[str, Any]:
    met = status == MET
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": met,
        "goal": str(goal),
        "target": float(target),
        "direction": str(direction),
        "unit": str(unit),
        "opening_measurement": None if opening is None else float(opening),
        "best_measurement": None if best is None else float(best),
        "remaining_gap": (
            None if best is None else round(float(target) - float(best), 6)
        ),
        "round_count": len(rounds),
        "rounds": rounds,
        "goal_reached": met,
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
