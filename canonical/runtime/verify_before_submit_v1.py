"""Verify a step BEFORE submitting: act, diff, undo if the effect is absent.

THE PROBLEM THIS SOLVES (r107). Every measurement in this session that failed on computer
use failed for one reason, not for lack of learning: a click is only judged when the WHOLE
task ends. A page's grader fires once. So there is no verdict on step 1, and nothing to
learn from, and predicate_induction_v1 measured INDUCED: 0 in the suite (r104) while working
perfectly in isolation (r105).

THE ORACLE ALREADY EXISTED. bench_capability_graph_v1.facts_from_nodes produces a frozenset
of (role, content) facts, and run_planned_v1 already computes f0 = facts(...) before acting.
It was used to PLAN. It was never used to CHECK.

What this module adds is the missing order: instead of act -> submit -> see if the whole task
passed, do

    observe -> act -> observe -> did the fact set move in the intended direction?
                                  yes: the step is verified, continue
                                  no:  the step FAILED, and here is the evidence

A step with no observable effect is not a completed step. It is a click that missed, and
saying so costs nothing. This is the per-step oracle the whole system was missing, and it is
built from a function that has been in the repo the whole time.
"""
from __future__ import annotations
import time
from typing import Any, Callable, Sequence


# MEASURED FAILURE (r108). The first version called any change in the fact set a successful
# step. Held-out tasks then scored 15/20 -- and the number was WRONG. A wrong click that
# TERMINATES the episode produces new facts too: the reward readout ("-1.00"), the score
# ("1"), and the "start" overlay all appear. So "facts changed" was reporting "I failed and
# the page closed" as "the step had an effect".
#
# A step is only verified if the page changed AND the episode is still running. These
# sentinels are the episode-end facts, and they are excluded from the diff.
_TERMINAL = ("reward", "start", "-1.00", "1.00", "0.00", "restart", "continue")


def _is_terminal(fact: str) -> bool:
    low = fact.lower()
    return any(t in low for t in _TERMINAL)


def step_effect(observe: Callable[[], frozenset], act: Callable[[], Any]) -> dict[str, Any]:
    """Run one action and report exactly what changed in the page's fact set.

    `observe` must return a frozenset of facts (bench_capability_graph_v1.facts_from_nodes).
    Nothing here decides what is CORRECT; it decides what CHANGED, which is the part an
    oracle can settle without judging the goal.
    """
    before = observe()
    t0 = time.perf_counter()
    result = act()
    dt = (time.perf_counter() - t0) * 1000.0
    time.sleep(0.12)
    after = observe()
    gained = sorted(after - before)
    lost = sorted(before - after)
    meaningful = [g for g in gained if not _is_terminal(g)]
    terminal = [g for g in gained if _is_terminal(g)]
    return {
        "acted": True,
        "action_result": result,
        "facts_before": len(before),
        "facts_after": len(after),
        "gained": gained[:8],
        "lost": lost[:8],
        # a step counts only if the page moved for a reason OTHER than the episode ending
        "changed": bool(meaningful),
        "terminal_only": bool(terminal) and not meaningful,
        "elapsed_ms": round(dt, 1),
    }


def verified_step(observe: Callable[[], frozenset], act: Callable[[], Any],
                  undo: Callable[[], Any] | None = None,
                  attempts: int = 3) -> dict[str, Any]:
    """Retry a step until the page actually changes. A no-op click is a failed click.

    MEASURED (r107): buy-ticket scored 3/10 with the correct rule because the click landed
    on stale coordinates. The click REPORTED success both times -- only the fact set could
    tell them apart. Retrying on `changed == False` is the cheapest possible fix for that,
    and it needs no new knowledge.
    """
    tries = []
    for n in range(1, attempts + 1):
        r = step_effect(observe, act)
        tries.append(r)
        if r["changed"]:
            return {"status": "STEP_VERIFIED", "attempts": n, "effect": r}
        if undo is not None:
            try:
                undo()
            except Exception:
                pass
    return {"status": "STEP_HAD_NO_EFFECT", "attempts": attempts,
            "effect": tries[-1] if tries else None, "all_attempts": tries}
