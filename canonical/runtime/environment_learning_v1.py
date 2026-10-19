"""Learn any environment by acting in it, then plan the shortest way through it.

The machine could learn command-line programs -- but only those. That is one
shape of environment, and it is the reason the surface is all file conversion
and archive verification. Everywhere the machine has not been told how to
operate, it cannot act.

This is the general version. It assumes nothing about the environment except
that it can be acted on and observed:

    reset()      -- return to a known state
    act(action)  -- do something
    state()      -- report what is now true (anything hashable)

From that alone it builds a model of how actions change the world, and then
finds the SHORTEST sequence of actions to a goal. Not a guessed sequence: the
minimum, computed over a model it learned itself. "Calculate the fastest way
with minimal actions" is literally a shortest-path search once the model
exists.

Nothing here is told what anything means. The model is (state, action) ->
state, learned by doing. That is what makes it work on an environment nobody
wrote documentation for, which is most of them.

The three honest limits are respected rather than papered over:
  - no evidence means no model, and that is reported as such;
  - the number of trials bounds what can be learned, and is reported;
  - a model is a HYPOTHESIS until the plan it produced has been executed and
    the goal was observed to hold. Planning is not achieving.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from typing import Any, Callable, Hashable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_LEARNING_V1"

PASS = "PASS__ENVIRONMENT_LEARNED_AND_GOAL_REACHED"
OPEN_UNREACHED = "OPEN__ENVIRONMENT_LEARNED_GOAL_NOT_REACHED_IN_MODEL"
FAIL_NO_MODEL = "FAIL_CLOSED__ENVIRONMENT_LEARNED_NOTHING"
FAIL_NO_GOAL = "FAIL_CLOSED__GOAL_NEVER_OBSERVED"


# --------------------------------------------------------------------------- #
# observation
# --------------------------------------------------------------------------- #
def state_key(observation: Any) -> str:
    """A stable identity for a state. Anything hashable becomes a key."""
    try:
        if isinstance(observation, Hashable) and not isinstance(observation,
                                                                 (dict, list, set)):
            return str(observation)
    except TypeError:
        pass
    blob = json.dumps(observation, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class Trace:
    """One observed transition: from here, doing this, got there."""

    __slots__ = ("before", "action", "after", "reward")

    def __init__(self, before: str, action: Any, after: str, reward: float = 0.0):
        self.before = before
        self.action = action
        self.after = after
        self.reward = reward

    def as_dict(self) -> dict[str, Any]:
        return {"before": self.before, "action": self.action,
                "after": self.after, "reward": self.reward}


# --------------------------------------------------------------------------- #
# learning
# --------------------------------------------------------------------------- #
def learn_model(env: Any, actions: Sequence[Any], *, budget: int = 60,
                seed: int | None = None, max_depth: int = 6,
                reward: Callable[[Any, Any, Any], float] | None = None,
                heuristic: Callable[[Any], float] | None = None,
                prior: Mapping[str, Mapping[str, str]] | None = None
                ) -> dict[str, Any]:
    """Act, watch what changes, and record it. No model of the world is assumed.

    Each trial is a WALK, not a single action: reset, then take up to
    `walk_len` actions, recording every transition along the way. Replaying
    from reset to test one action costs O(depth) interactions each, so a
    budget of 400 trials would only ever walk 400 steps and a 1000-state
    environment stays unexplored. Walking records a whole trajectory per
    reset, which is what makes this fast enough to be called instant.
    """
    started = time.time()
    import random
    rng = random.Random(seed if seed is not None else 0)

    # A model carried over from a similar environment met before. Starting
    # from nothing every time is amnesiac: the same three-dial lock solved
    # yesterday would be re-learned from scratch today.
    model: dict[str, dict[str, str]] = (
        {k: dict(v) for k, v in (prior or {}).items()})
    observations: dict[str, Any] = {}
    traces: list[Trace] = []
    trials = 0
    steps = 0

    def observe() -> str:
        snapshot = env.state()
        key = state_key(snapshot)
        observations.setdefault(key, snapshot)
        return key

    order = list(actions)
    best: tuple[float, Any] | None = None
    while trials < budget:
        trials += 1
        env.reset()
        key = observe()
        model.setdefault(key, {})
        walk = rng.randint(1, max(1, max_depth))
        for _ in range(walk):
            action = _choose_action(env, order, rng, heuristic, epsilon=0.25)
            env.act(action)
            after = observe()
            steps += 1
            traces.append(Trace(key, action, after))
            model.setdefault(key, {})[action] = after
            key = after
            model.setdefault(key, {})

    return {
        "schema": SCHEMA,
        "model": model,
        "observations": observations,
        "guided": heuristic is not None,
        "prior_states": len(prior or {}),
        "traces": [t.as_dict() for t in traces],
        "states": sorted(model),
        "state_count": len(model),
        "transition_count": sum(len(v) for v in model.values()),
        "trials": trials,
        "steps": steps,
        "root": state_key(env.state()) if False else sorted(model)[0] if model else None,
        "duration_s": round(time.time() - started, 4),
    }


def _choose_action(env: Any, actions: Sequence[Any], rng: Any,
                   heuristic: Callable[[Any], float] | None,
                   epsilon: float = 0.25) -> str:
    """Pick an action, preferring ones that look like progress when we can tell.

    Random exploration almost never reaches a rare state: 18 precise
    increments out of 1000 possibilities is not found by walking. When the
    caller can say "this observation is closer than that one", the walk is
    pulled toward the goal instead of hoping to collide with it. `epsilon`
    keeps some wandering so a misleading sense of progress cannot trap it.
    """
    order = list(actions)
    if heuristic is None or rng.random() < epsilon:
        return str(rng.choice(order))
    # Looking ahead requires TRYING an action, which changes the world. Without
    # a way back, every probe leaves the environment somewhere else and the
    # ranking is computed over states that no longer hold -- which produced a
    # plan that was confidently wrong. If the environment cannot be snapshotted
    # we do not guess; we wander.
    can_undo = hasattr(env, "snapshot") and hasattr(env, "restore")
    if not can_undo:
        return str(rng.choice(order))

    scored: list[tuple[float, str]] = []
    for action in order:
        try:
            saved = env.snapshot()
            env.act(action)
            score = float(heuristic(env.state()))
            env.restore(saved)
        except Exception:
            score = float("inf")
        scored.append((score, str(action)))
    finite = [(s_, a) for s_, a in scored if s_ != float("inf")]
    if not finite:
        return str(rng.choice(order))
    best_score = min(s_ for s_, _ in finite)
    best_actions = [a for s_, a in finite if s_ == best_score]
    return str(rng.choice(best_actions))


def _path_to(model: Mapping[str, Mapping[str, str]], root: str,
             target: str) -> list[Any] | None:
    """Shortest known action sequence from root to target, or None."""
    if root == target:
        return []
    prev: dict[str, tuple[str, Any]] = {}
    seen = {root}
    queue = deque([root])
    while queue:
        node = queue.popleft()
        for action, nxt in (model.get(node) or {}).items():
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = (node, action)
            if nxt == target:
                out: list[Any] = []
                cur = target
                while cur != root:
                    parent, act = prev[cur]
                    out.append(act)
                    cur = parent
                return list(reversed(out))
            queue.append(nxt)
    return None


# --------------------------------------------------------------------------- #
# planning
# --------------------------------------------------------------------------- #
def shortest_plan(learned: Mapping[str, Any], is_goal: Callable[[str], bool],
                  start: str | None = None) -> list[Any] | None:
    """The minimum number of actions to a goal state, over the learned model.

    This is the 'fastest way with minimal actions' the owner asked for. It is
    minimal with respect to what has been learned, which is stated honestly.
    """
    model: Mapping[str, Mapping[str, str]] = learned.get("model") or {}
    if not model:
        return None
    root = start if start is not None else learned.get("root")
    if root is None:
        return None
    if is_goal(root):
        return []
    prev: dict[str, tuple[str, Any]] = {}
    seen = {root}
    queue = deque([root])
    while queue:
        node = queue.popleft()
        for action, nxt in (model.get(node) or {}).items():
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = (node, str(action))
            if is_goal(nxt):
                out: list[Any] = []
                cur = nxt
                while cur != root:
                    parent, act = prev[cur]
                    out.append(act)
                    cur = parent
                return list(reversed(out))
            queue.append(nxt)
    return None


# --------------------------------------------------------------------------- #
# drive: learn, plan, then prove it by doing it
# --------------------------------------------------------------------------- #
def drive(env: Any, actions: Sequence[Any], *,
          is_goal: Callable[[Any], bool],
          budget: int = 60, seed: int | None = None,
          max_depth: int = 6, verify: bool = True,
          heuristic: Callable[[Any], float] | None = None,
          prior: Mapping[str, Mapping[str, str]] | None = None) -> dict[str, Any]:
    """Learn an unknown environment and reach the goal in it. Or say why not.

    The plan is executed and the goal is CHECKED afterwards. A plan that was
    never run is a hypothesis, exactly as with capability composition.
    """
    started = time.time()
    learned = learn_model(env, actions, budget=budget, seed=seed,
                          max_depth=max_depth, heuristic=heuristic, prior=prior)
    if not learned["model"] or learned["transition_count"] == 0:
        return {"schema": SCHEMA, "status": FAIL_NO_MODEL, "pass": False,
                "learned": learned, "plan": None,
                "authority": "NO_MODEL_LEARNED",
                "duration_s": round(time.time() - started, 4)}

    # the goal is expressed over the environment's own observations, so the
    # planner tests it against recorded states
    goal_states: set[str] = set()

    def goal_key(key: str) -> bool:
        return key in goal_states

    plan: list[Any] | None = None
    if verify:
        # test the goal against what was OBSERVED, not by replaying. Replaying
        # to ask "is this the goal?" spends the trial budget asking questions
        # the model can already answer, and on a large environment it spends
        # all of it before learning anything.
        for key, snapshot in (learned.get("observations") or {}).items():
            try:
                if is_goal(snapshot):
                    goal_states.add(key)
            except Exception:
                continue
        if not goal_states:
            return {"schema": SCHEMA, "status": FAIL_NO_GOAL, "pass": False,
                    "learned": learned, "plan": None,
                    "authority": "GOAL_NEVER_OBSERVED_IN_LEARNED_MODEL",
                    "detail": "the goal was never seen in %d states; the "
                              "environment may be larger than the budget found"
                              % len(learned["states"]),
                    "duration_s": round(time.time() - started, 4)}
        plan = shortest_plan(learned, goal_key)

    if plan is None:
        return {"schema": SCHEMA, "status": OPEN_UNREACHED, "pass": False,
                "learned": learned, "plan": None,
                "authority": "MODEL_LEARNED_GOAL_UNREACHABLE",
                "duration_s": round(time.time() - started, 4)}

    # execute it
    env.reset()
    executed: list[Any] = []
    for action in plan:
        env.act(str(action))
        executed.append(str(action))

    reached = bool(is_goal(env.state()))
    return {
        "schema": SCHEMA,
        "status": PASS if reached else OPEN_UNREACHED,
        "pass": reached,
        "learned": learned,
        "plan": [str(a) for a in plan],
        "plan_length": len(plan),
        "executed": executed,
        "reached": reached,
        "authority": "MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED" if reached else
                     "MODEL_LEARNED_PLAN_EXECUTED_GOAL_NOT_OBSERVED",
        "duration_s": round(time.time() - started, 4),
    }
