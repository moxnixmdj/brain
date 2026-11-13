"""Reuse a learned environment model without spending the trials again -- and notice when it is stale.

THE MEASUREMENT THIS FIXES
--------------------------
`environment_learning_v1.drive()` accepts a `prior` model and merges it into exploration. Measured on
the repository's own three-dial lock (1000 states), over two consecutive visits:

    visit 1 (cold) : 1672 interactions, 245 states modelled, plan length 18
    visit 2 (prior): 1672 interactions, 245 states modelled, plan length 18

The second visit cost **exactly the same** as the first. Nothing was reused, because `drive()`
explores before it plans every time. Carrying the model changed nothing about the cost of a visit.

Separately, `shortest_plan()` never touches the environment -- by design, it plans over a recorded
model. Measured with a model learned on an environment whose dial 1 then moved BACKWARDS:

    stored plan executed on the drifted environment -> (7, 8, 9), goal was (7, 2, 9)

The plan was wrong, and no code in the reuse path was in a position to notice. That is the failure
mode "learn it once, then it is permanent" actually has: a remembered model is a claim about the
world, and the world is allowed to change.

WHAT THIS DOES
--------------
`replay_then_repair()` treats the prior as a HYPOTHESIS and checks it:

1. PLAN from the stored model -- zero interactions, this is where the saving comes from.
2. REPLAY the plan against the live environment, checking the goal after every step.
3. If the goal arrives, stop. Cost: len(plan) interactions, against (budget x walk length) for
   learning from scratch.
4. If it diverges, REPAIR: learn again from what actually happened, and report that the prior was
   stale rather than silently overwriting it.

It never reports a win it did not observe. The three outcomes are distinct:

    PASS__PRIOR_REPLAYED_GOAL_OBSERVED           prior was valid, cheap
    REPAIRED__PRIOR_STALE_RELEARNED_GOAL_OBSERVED prior was wrong, and we said so
    FAIL_CLOSED__PRIOR_STALE_REPAIR_FAILED        prior was wrong and repair did not reach the goal

Authority: measurement only. No weights, no model calls.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import environment_learning_v1 as el

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_REUSE_V1"

PASS_REPLAYED = "PASS__PRIOR_REPLAYED_GOAL_OBSERVED"
REPAIRED = "REPAIRED__PRIOR_STALE_RELEARNED_GOAL_OBSERVED"
FAIL_REPAIR = "FAIL_CLOSED__PRIOR_STALE_REPAIR_FAILED"
FAIL_NO_PRIOR = "FAIL_CLOSED__NO_USABLE_PRIOR"


def replay_then_repair(
    env: Any,
    actions: Sequence[Any],
    *,
    is_goal: Callable[[Any], bool],
    prior: Mapping[str, Any] | None,
    prior_schema: str | None = None,
    budget: int = 60,
    seed: int | None = None,
    max_depth: int = 6,
    heuristic: Callable[[Any], float] | None = None,
) -> dict[str, Any]:
    """Try the remembered plan first. Pay for learning only if the world disagrees."""
    started = time.time()
    actions = list(actions)

    # ---- 1. plan from memory, no interactions ---------------------------------
    model = (prior or {}).get("model") or {}
    if not model or prior_schema != (prior or {}).get("state_key_schema"):
        return {"schema": SCHEMA, "status": FAIL_NO_PRIOR, "pass": False,
                "interactions": 0, "authority": "NO_SCHEMA_MATCHED_PRIOR",
                "detail": "a prior is only reusable under the same observation identity",
                "duration_s": round(time.time() - started, 4)}

    env.reset()
    start_key = el.state_key(env.state())
    goal_states = {key for key, snap in ((prior or {}).get("observations") or {}).items()
                   if _safe_goal(is_goal, snap)}
    plan = el.shortest_plan({"model": model}, lambda k: k in goal_states, start=start_key)

    if plan is None:
        return {"schema": SCHEMA, "status": FAIL_NO_PRIOR, "pass": False,
                "interactions": 0, "authority": "NO_PLAN_IN_PRIOR_FOR_THIS_START",
                "detail": "the remembered model does not connect this start to the goal",
                "duration_s": round(time.time() - started, 4)}

    # ---- 2. replay it, checking the goal as we go -----------------------------
    env.reset()
    interactions = 0
    divergence_at: int | None = None
    for index, action in enumerate(plan):
        env.act(str(action))
        interactions += 1
        if _safe_goal(is_goal, env.state()):
            return {"schema": SCHEMA, "status": PASS_REPLAYED, "pass": True,
                    "plan": [str(a) for a in plan], "plan_length": len(plan),
                    "interactions": interactions, "prior_was_stale": False,
                    "authority": "PRIOR_PLAN_REPLAYED_GOAL_OBSERVED",
                    "duration_s": round(time.time() - started, 4)}
        # a step the model did not predict means the world is not the one we remember
        if index < len(plan) - 1:
            expected = (model.get(el.state_key(env.state())) or {})
            if str(action) not in expected and not expected:
                divergence_at = index
                break

    # ---- 3. the prior was wrong. learn from here, and say so ------------------
    learned = el.learn_model(env, actions, budget=budget, seed=seed,
                             max_depth=max_depth, heuristic=heuristic)
    repair = None
    new_goal = {key for key, snap in (learned.get("observations") or {}).items()
                if _safe_goal(is_goal, snap)}
    if new_goal:
        repair = el.shortest_plan(learned, lambda k: k in new_goal,
                                  start=el.state_key(env.state()))
    if repair:
        for action in repair:
            env.act(str(action))
            interactions += 1
        if _safe_goal(is_goal, env.state()):
            return {"schema": SCHEMA, "status": REPAIRED, "pass": True,
                    "plan": [str(a) for a in repair], "plan_length": len(repair),
                    "interactions": interactions, "prior_was_stale": True,
                    "divergence_at": divergence_at,
                    "authority": "PRIOR_PLAN_DIVERGED_RELEARNED_GOAL_OBSERVED",
                    "duration_s": round(time.time() - started, 4)}

    return {"schema": SCHEMA, "status": FAIL_REPAIR, "pass": False, "plan": None,
            "interactions": interactions, "prior_was_stale": True,
            "divergence_at": divergence_at,
            "authority": "PRIOR_PLAN_DIVERGED_REPAIR_DID_NOT_REACH_GOAL",
            "duration_s": round(time.time() - started, 4)}


def _safe_goal(is_goal: Callable[[Any], bool], snapshot: Any) -> bool:
    try:
        return bool(is_goal(snapshot))
    except Exception:
        return False
