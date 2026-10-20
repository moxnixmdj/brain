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
# Distinct from STUCK and from BOUND on purpose. "I could not move the number"
# and "I do not have enough of the world to know which way is fastest" are
# different failures and must not be reported as the same thing. The owner's
# requirement is that the machine says, by itself, "I don't have the data" --
# which it cannot do if the only vocabularies it has are pass and stuck.
INCOMPLETE_DATA = "OPEN__TARGET_CHASE_DATA_INCOMPLETE"
NOT_MEASURABLE = "FAIL_CLOSED__TARGET_NOT_MEASURABLE"

DIRECTIONS = ("maximize", "minimize")


class TargetChaseError(ValueError):
    pass


def _turn_flywheel(
    fly: Any,
    error_text: str,
    improved: bool,
    recorded: list[dict[str, Any]],
    state_path: str | None,
    procedure: str | None = None,
) -> None:
    """One datum per round, keyed on pathology -- never on the task.

    flywheel_v1.classify names the failure from the error alone, so the cell is
    (WHERE x WHY): "reading a file" x "no such file" recurs across every
    domain, while "how I fixed that one task" is worthless the moment the task
    changes. This system exists for tasks it has never seen.
    """
    try:
        where, why = fly.classify(error_text)
        kwargs = {"path": state_path} if state_path else {}
        fly.record(where, why, bool(improved), **kwargs)
        row = {"where": where, "why": why, "succeeded": bool(improved)}
        # A credited cell with no procedure attached is inert: primers() only
        # hands over cells that carry their resolution, and a fix that cannot be
        # handed over cannot be avoided next time. Avoiding a step is worth
        # strictly more than repairing one.
        if improved and procedure:
            cell = fly.cell_of(where, why)
            status = fly.status(cell, **(dict(kwargs)))
            if status.get("credited") and not status.get("procedure"):
                fly.teach(cell, str(procedure), **kwargs)
                row["taught"] = True
        recorded.append(row)
    except Exception:
        # Learning must never be able to break the chase.
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
    flywheel_state_path: str | None = None,
    options_provider: Callable[[Mapping[str, Any]], Any] | None = None,
    completeness_gate: Callable[[Mapping[str, Any]], Any] | None = None,
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
    recorded: list[dict[str, Any]] = []

    # Instant learning, with the timing that was measured to matter.
    # flywheel_v1.primers() must be consulted BEFORE the first action, not
    # after the first failure: consulted late, the store can only repair the
    # next step of this run and never prevents the next run's mistake. The
    # owner measured that ordering at a 0% improvement in mean steps.
    fly = None
    primers: list[dict[str, Any]] = []
    try:
        from canonical.runtime import flywheel_v1 as fly
        primers = list(fly.primers(
            **({"path": flywheel_state_path} if flywheel_state_path else {})
        ) or [])
    except Exception:
        fly = None

    # Options the actor has already been offered. Shares identity with every
    # round's context, so widening it mid-chase is visible to the next act().
    #
    # Seeded from context: the driver previously dropped caller-supplied
    # options entirely, which silently disabled the completeness gate -- the
    # set it was asked to judge was always empty, so it never blocked anything
    # and the chase acted on a single unverified source.
    options: list[dict[str, Any]] = [
        dict(o) for o in ((context or {}).get("options") or []) if isinstance(o, Mapping)
    ]

    base = {**(context or {}), "primers": primers, "options": options}
    rounds: list[dict[str, Any]] = []

    opening = measure()
    if opening is None:
        return _result(NOT_MEASURABLE, goal, target, direction, unit, [], None, opening, started, primers, recorded, options)
    best = float(opening)
    if _on_target(best, float(target), direction):
        return _result(MET, goal, target, direction, unit, rounds, best, opening, started, primers, recorded, options)

    stale = 0
    blocked_on_data = 0
    # gaps closed since the last stall, credited only if the number then moves
    pending_gaps: list[str] = []
    for index in range(max_rounds):
        before = best

        # COMPLETENESS GATE. No route may be acted on as "the fastest way"
        # unless the option set has a completeness basis behind it. Acting on an
        # incomplete set is precisely the failure the owner described: read one
        # paper saying "the fastest way is YouTube", rank YouTube first, and
        # call it done, when most of the opportunity space was never looked at.
        # The gate fails closed -- an error or an absent verdict blocks, never
        # permits -- because the cost of a false pass is acting on a conclusion
        # the machine had no right to draw.
        if completeness_gate is not None and options:
            try:
                verdict = completeness_gate({
                    "goal": goal, "round": index, "measured": before,
                    "target": float(target), "known_options": list(options),
                })
                complete = bool(verdict.get("complete")) if isinstance(verdict, Mapping) else bool(verdict)
                why = (verdict.get("reason") if isinstance(verdict, Mapping) else None) or "no completeness basis"
            except Exception as exc:
                complete, why = False, "gate_error:" + type(exc).__name__
            if not complete:
                blocked_on_data += 1
                rounds.append({"round": index, "blocked_on_data": True, "reason": why})
                # Being blocked is how the machine finds out what it does not
                # know. Recording the reason turns a refusal into a gap it can
                # later decide was worth closing -- which is what lets it learn
                # WHICH ignorance matters instead of treating every block alike.
                try:
                    from canonical.runtime import ignorance_ledger_v1 as led
                    gap_id = led.note(why, why=str(why), cost=1.0)
                    if gap_id:
                        pending_gaps.append(gap_id)
                    rounds[-1]["gap_id"] = gap_id
                    rounds[-1]["what_to_learn_next"] = [
                        g["what"] for g in led.rank(limit=3)
                    ]
                except Exception:
                    pass
                # Do not act. Spend the round getting data instead.
                if options_provider is not None:
                    try:
                        found = options_provider({
                            "goal": goal, "round": index, "measured": before,
                            "target": float(target), "known_options": list(options),
                        }) or []
                        for row in found:
                            if isinstance(row, Mapping) and dict(row) not in options:
                                options.append(dict(row))
                    except Exception:
                        pass
                if blocked_on_data >= patience:
                    return _result(INCOMPLETE_DATA, goal, target, direction, unit,
                                   rounds, best, opening, started, primers, recorded, options)
                continue

        try:
            action = act({**base, "round": index, "measured": before, "target": target})
        except Exception as exc:
            message = type(exc).__name__ + ":" + str(exc)[:200]
            rounds.append({"round": index, "error": message})
            if fly is not None:
                _turn_flywheel(fly, message, False, recorded, flywheel_state_path)
            stale += 1
            if stale >= patience:
                return _result(STUCK, goal, target, direction, unit, rounds, best, opening, started, primers, recorded, options)
            continue

        measured = measure()
        if measured is None:
            rounds.append({"round": index, "measure_error": "MEASURE_RETURNED_NONE"})
            if fly is not None:
                _turn_flywheel(fly, "MEASURE_RETURNED_NONE", False, recorded, flywheel_state_path)
            stale += 1
            if stale >= patience:
                return _result(STUCK, goal, target, direction, unit, rounds, best, opening, started, primers, recorded, options)
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
            return _result(MET, goal, target, direction, unit, rounds, best, opening, started, primers, recorded, options)

        improved = _improved(best, measured, direction)
        # Closing a gap is only worth anything if the number then moves. That
        # outcome is what teaches the ledger which ignorance actually blocked
        # the goal -- without it every gap stays worth the same 0.5 forever.
        if pending_gaps:
            try:
                from canonical.runtime import ignorance_ledger_v1 as led
                for gid in pending_gaps:
                    led.resolve(gid, helped=bool(improved), close=bool(improved))
            except Exception:
                pass
            if improved:
                pending_gaps = []
        if fly is not None:
            _turn_flywheel(
                fly,
                str((action or {}).get("error") or (action or {}).get("status") or ""),
                improved,
                recorded,
                flywheel_state_path,
                (action or {}).get("procedure"),
            )
        if improved:
            best = measured
            stale = 0
        else:
            # A round that failed to move the number is the signal that the
            # machine is missing something -- a route, a source, a datum it has
            # never seen. That is the moment to widen the option set, and only
            # that moment: asking every round would cost time and buy nothing.
            if options_provider is not None:
                try:
                    found = options_provider(
                        {
                            "goal": goal,
                            "round": index,
                            "measured": measured,
                            "target": float(target),
                            "known_options": list(options),
                        }
                    ) or []
                    for row in found:
                        if isinstance(row, Mapping) and dict(row) not in options:
                            options.append(dict(row))
                except Exception:
                    pass  # widening must never break the chase
            stale += 1
            if stale >= patience:
                return _result(STUCK, goal, target, direction, unit, rounds, best, opening, started, primers, recorded, options)

    return _result(BOUND, goal, target, direction, unit, rounds, best, opening, started, primers, recorded, options)


def _result(status, goal, target, direction, unit, rounds, best, opening, started,
            primers=None, recorded=None, options=None) -> dict[str, Any]:
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
        "learning": {
            "primers_handed_to_actor_before_round_0": list(primers or []),
            "pathologies_recorded": list(recorded or []),
            "options_discovered": list(options or []),
        },
        "goal_reached": met,
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
