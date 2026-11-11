"""An unknown environment is a graph nobody has drawn yet. Draw it without paying twice.

Why this file exists
--------------------
`environment_learning_v1.learn_model` is the machine's first contact with a place it has
never seen, and it explores by RANDOM WALKS FROM RESET: reset, take 1..max_depth random
actions, repeat. Three consequences follow from that mechanism, not from any environment:

  1. a goal deeper than `max_depth` is unreachable by construction;
  2. the cost of reaching depth d by chance grows like |A|**d, so the first solve of a new
     kind is expensive (measured 2026-11-03: 22.4 trials mean, a 3-dial lock 24..200);
  3. it can never say "the goal is not there". Spending the budget and proving absence are
     reported identically.

"Learn once, replay forever" pays for the SECOND solve. This file is about the FIRST one,
which is the only one a memory cannot help with.

What it does
------------
The same tabular model as `environment_learning_v1` -- (state, action) -> state, learned by
acting -- but the next action is never a guess:

    at a state with an untried action      take it (that is new information)
    otherwise                              walk the KNOWN model to the nearest state that
                                           still has one, or reset if that is cheaper
    nothing reachable is untried           stop: the reachable space is EXHAUSTED

So no (state, action) pair is ever paid for twice as an experiment. The only repeated
actions are travel through transitions already known, and each travelled step is checked
against the model: a step that lands somewhere else is a SURPRISE, the model is corrected,
and too many of them end the run as NOT_REPEATABLE instead of pretending to have a map.

"Nearest" is a choice with a price, and the price is stated rather than hidden:

    order="nearest"     experiment wherever you already are. Least travel, cheapest first
                        solve -- but the first route found is A route, not the shortest.
    order="shallowest"  always experiment at the untried state closest to the START. More
                        travel, but every state nearer than the goal has been fully tried
                        before the goal is first seen, so in a repeatable environment the
                        first route found is a SHORTEST one.

Which untried action to take first is the one place a prior can enter. `effect_prior=True`
keeps a running count, per action CLASS, of how often trying it changed the state, and
schedules untried actions in proportion to that rate (deterministically; no random numbers
anywhere in this file). An action that has done nothing every time it was tried is tried
less, in every state, including states never seen before. That is the smallest piece of a
world model that generalises beyond the states it was measured in.

What it is not
--------------
  * It is still a TABLE. It predicts nothing about a state it has not visited, so nothing
    learned in one level, instance or kind makes the next one cheaper. That limit is the
    subject of `canonical/tools/arc_agi_3_public_exploration_measure_v1.py`.
  * It needs a state key under which the environment repeats. A clock in the corner of
    the screen makes every state new and every action untried; the run then degenerates
    into a non-repeating walk and reports its revisit rate so that this is visible.
  * It assumes nothing about what the goal looks like. It finds a goal only by reaching it.

No model, no weights, no network, no randomness. `K3 = 0`, `$0`.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SYSTEMATIC_EXPLORATION_V1"

PASS = "PASS__GOAL_OBSERVED_DURING_SYSTEMATIC_EXPLORATION"
PASS_VERIFIED = "PASS__GOAL_REACHED_AGAIN_BY_REPLAYING_THE_PLAN"
OPEN_BUDGET = "OPEN__ACTION_BUDGET_EXHAUSTED_GOAL_NOT_OBSERVED"
OPEN_UNSTABLE = "OPEN__ENVIRONMENT_NOT_REPEATABLE_UNDER_THIS_STATE_KEY"
FAIL_EXHAUSTED = "FAIL_CLOSED__REACHABLE_SPACE_EXHAUSTED_GOAL_ABSENT"
FAIL_NOT_REPRODUCIBLE = "FAIL__GOAL_OBSERVED_ONCE_BUT_NO_PLAN_REPLAYS_TO_IT"

AUTHORITY_OBSERVED = "GOAL_OBSERVED_ONCE_DURING_EXPLORATION_NOT_REPLAYED"
AUTHORITY_REPLAYED = "PLAN_REPLAYED_FROM_RESET_GOAL_OBSERVED_AGAIN"

# A table is only a map if the place holds still. Past this many contradictions the run is
# reported as not repeatable rather than continued on a model that keeps being wrong.
MIN_SURPRISE_ALLOWANCE = 8
SURPRISE_FRACTION = 0.25


def _default_key(observation: Any) -> str:
    """Same identity `environment_learning_v1` uses, so both learners fill one kind of model."""
    from canonical.runtime.environment_learning_v1 import state_key

    return state_key(observation)


def _shortest_path(model: Mapping[str, Mapping[str, str]], start: str,
                   accept: Callable[[str], bool]) -> list[str] | None:
    """Fewest known actions from `start` to the nearest state `accept` approves, or None."""
    if accept(start):
        return []
    previous: dict[str, tuple[str, str]] = {}
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for action, nxt in (model.get(node) or {}).items():
            if nxt in seen:
                continue
            seen.add(nxt)
            previous[nxt] = (node, action)
            if accept(nxt):
                out: list[str] = []
                cursor = nxt
                while cursor != start:
                    parent, taken = previous[cursor]
                    out.append(taken)
                    cursor = parent
                out.reverse()
                return out
            queue.append(nxt)
    return None


class _EffectSchedule:
    """Deterministic proportional scheduling of action classes by how often they changed anything.

    Every class starts optimistic (one imagined change in two imagined tries), so nothing is
    starved before it has been tried. Each pick, every candidate class earns credit equal to
    its current rate and the richest class is chosen and charged one unit: classes are
    therefore tried in proportion to their measured effect rate, a class that never does
    anything still gets a shrinking share, and the same history always yields the same pick.
    """

    def __init__(self) -> None:
        self.tries: dict[str, int] = {}
        self.changes: dict[str, int] = {}
        self.credit: dict[str, float] = {}

    def rate(self, cls: str) -> float:
        return (self.changes.get(cls, 0) + 1.0) / (self.tries.get(cls, 0) + 2.0)

    def pick(self, classes: Sequence[str]) -> str:
        best = None
        for cls in classes:  # declared order breaks ties, so the choice is reproducible
            self.credit[cls] = self.credit.get(cls, 0.0) + self.rate(cls)
            if best is None or self.credit[cls] > self.credit[best] + 1e-12:
                best = cls
        assert best is not None
        self.credit[best] -= 1.0
        return best

    def record(self, cls: str, changed: bool) -> None:
        self.tries[cls] = self.tries.get(cls, 0) + 1
        if changed:
            self.changes[cls] = self.changes.get(cls, 0) + 1

    def table(self) -> dict[str, dict[str, int]]:
        return {cls: {"tries": n, "changes": self.changes.get(cls, 0)}
                for cls, n in sorted(self.tries.items())}


def explore_to_goal(env: Any, actions: Sequence[Any], *,
                    is_goal: Callable[[Any], bool],
                    action_budget: int,
                    actions_of: Callable[[Any], Iterable[Any]] | None = None,
                    is_dead: Callable[[Any], bool] | None = None,
                    key_of: Callable[[Any], str] | None = None,
                    action_class: Callable[[str], str] | None = None,
                    effect_prior: bool = False,
                    order: str = "nearest",
                    prior: Mapping[str, Mapping[str, str]] | None = None,
                    reset_cost: int = 1,
                    include_model: bool = True) -> dict[str, Any]:
    """Explore until the goal is OBSERVED, the budget is spent, or nothing is left to try.

    env            reset() / act(action) / state(), exactly as `environment_learning_v1`.
    actions        the actions available everywhere, unless `actions_of` says otherwise.
    actions_of     observation -> the actions available THERE (a screen offers what it shows).
    is_dead        observation -> True when only a reset leaves this state.
    key_of         observation -> identity of the state. Defaults to the shared `state_key`.
    action_class   action -> the class its effect statistics are pooled under.
    effect_prior   schedule untried actions by measured effect rate instead of declared order.
    order          "nearest" (cheapest first solve) or "shallowest" (first route is a shortest one).
    prior          a model carried from elsewhere; it is travelled, checked, and corrected.
    reset_cost     what a reset is worth in actions. It decides between walking and resetting,
                   and every reset after the first is charged against `action_budget` at this
                   price -- some environments count a reset as an action, and one that does
                   must not be explored as if starting over were free.

    Returns what was learned and how it ended. `plan_walked` is the exact action sequence
    since the last reset that ended on the goal, so it replays from reset by construction;
    `plan_shortest` is the shortest route to the same state in the learned model.
    """
    if order not in ("nearest", "shallowest"):
        raise ValueError("EXPLORATION_ORDER_INVALID")
    started = time.time()
    key = key_of or _default_key
    budget = max(0, int(action_budget))
    static_actions = tuple(str(a) for a in actions)
    classify = action_class or (lambda a: a)

    model: dict[str, dict[str, str]] = {str(k): {str(a): str(n) for a, n in v.items()}
                                        for k, v in (prior or {}).items()}
    available: dict[str, tuple[str, ...]] = {}
    dead: set[str] = set()
    schedule = _EffectSchedule() if effect_prior else None

    counters = {"acts": 0, "resets": 0, "travel_acts": 0, "experiment_acts": 0,
                "surprises": 0, "revisits": 0, "self_loops": 0}
    price = max(0, int(reset_cost))

    def spent() -> int:
        return counters["acts"] + price * max(0, counters["resets"] - 1)
    since_reset: list[str] = []
    seen_this_run: set[str] = set()

    def observe() -> tuple[Any, str]:
        observation = env.state()
        k = str(key(observation))
        if k in seen_this_run:
            counters["revisits"] += 1
        seen_this_run.add(k)
        if k not in available:
            offered = actions_of(observation) if actions_of is not None else static_actions
            available[k] = tuple(dict.fromkeys(str(a) for a in offered))
        if is_dead is not None and is_dead(observation):
            dead.add(k)
        model.setdefault(k, {})
        return observation, k

    def untried(k: str) -> list[str]:
        if k in dead:
            return []
        offered = available.get(k)
        if offered is None:
            # Known only from a carried model: its actions are learned on arrival.
            return ["?"]
        known = model.get(k) or {}
        return [a for a in offered if a not in known]

    def has_untried(k: str) -> bool:
        return bool(untried(k))

    def finish(status: str, goal_key: str | None, **extra: Any) -> dict[str, Any]:
        reached = goal_key is not None
        out: dict[str, Any] = {
            "schema": SCHEMA, "status": status, "pass": reached, "reached": reached,
            "authority": AUTHORITY_OBSERVED if reached else "NO_GOAL_OBSERVED",
            "root": root, "goal_key": goal_key,
            "action_budget": budget, "budget_spent": spent(), "reset_cost": price,
            "state_count": len(model),
            "transition_count": sum(len(v) for v in model.values()),
            "dead_state_count": len(dead),
            "exhausted": status == FAIL_EXHAUSTED,
            "revisit_rate": round(counters["revisits"] / max(1, counters["acts"]), 4),
            "effect_prior": bool(effect_prior),
            "order": order,
            "prior_states": len(prior or {}),
            "duration_s": round(time.time() - started, 4),
        }
        out.update(counters)
        if reached:
            out["plan_walked"] = list(since_reset)
            shortest = _shortest_path(model, root, lambda k: k == goal_key)
            out["plan_shortest"] = shortest if shortest is not None else list(since_reset)
            # "Shortest" is shortest IN WHAT WAS LEARNED. It is the true minimum only when
            # everything nearer than the goal was fully tried first and the place held still.
            out["plan_minimality"] = (
                "SHORTEST_GIVEN_REPEATABLE_ENVIRONMENT"
                if order == "shallowest" and not counters["surprises"] and not prior
                else "NOT_PROVEN_SHORTEST")
        if schedule is not None:
            out["effect_table"] = schedule.table()
        if include_model:
            out["model"] = model
        out.update(extra)
        return out

    env.reset()
    counters["resets"] += 1
    observation, current = observe()
    root = current
    if is_goal(observation):
        return finish(PASS, current)

    def step(action: str, *, travelling: bool) -> tuple[Any, str, bool]:
        """Do one action. Returns (observation, new key, surprised)."""
        nonlocal current
        before = current
        predicted = (model.get(before) or {}).get(action)
        env.act(action)
        counters["acts"] += 1
        counters["travel_acts" if travelling else "experiment_acts"] += 1
        since_reset.append(action)
        obs, after = observe()
        surprised = predicted is not None and predicted != after
        if surprised:
            counters["surprises"] += 1
        model.setdefault(before, {})[action] = after
        if after == before:
            counters["self_loops"] += 1
        if schedule is not None and not travelling:
            schedule.record(classify(action), after != before)
        current = after
        return obs, after, surprised

    def too_surprised() -> bool:
        allowed = max(MIN_SURPRISE_ALLOWANCE, int(SURPRISE_FRACTION * counters["acts"]))
        return counters["surprises"] > allowed

    def experiment_here() -> Any:
        candidates = untried(current)
        if schedule is None:
            action = candidates[0]
        else:
            by_class: dict[str, str] = {}
            for a in candidates:
                by_class.setdefault(classify(a), a)
            action = by_class[schedule.pick(list(by_class))]
        obs, _, _ = step(action, travelling=False)
        return obs

    def end_of(path: Sequence[str], start: str) -> str:
        node = start
        for action in path:
            node = model[node][action]
        return node

    while True:
        if spent() >= budget:
            return finish(OPEN_BUDGET, None)
        if too_surprised():
            return finish(OPEN_UNSTABLE, None)

        here = untried(current)
        can_experiment_here = bool(here) and here != ["?"]
        if order == "nearest" and can_experiment_here:
            # No search at all on this path: on a large table the common case must stay O(1).
            observation = experiment_here()
            if is_goal(observation):
                return finish(PASS, current)
            continue
        from_root = _shortest_path(model, root, has_untried)

        if order == "nearest" or from_root is None:
            if can_experiment_here:
                observation = experiment_here()
                if is_goal(observation):
                    return finish(PASS, current)
                continue
            local = None if current in dead else _shortest_path(model, current, has_untried)
        else:
            # Breadth first: the untried state closest to the start is the only place an
            # experiment is allowed, so nothing deeper is tried while something shallower is not.
            target = end_of(from_root, root)
            if target == current and can_experiment_here:
                observation = experiment_here()
                if is_goal(observation):
                    return finish(PASS, current)
                continue
            local = (None if current in dead
                     else _shortest_path(model, current, lambda k: k == target))

        if local is None and (from_root is None or current == root):
            status = OPEN_UNSTABLE if counters["surprises"] else FAIL_EXHAUSTED
            return finish(status, None)

        use_reset = current != root and from_root is not None and (
            local is None or price + len(from_root) < len(local))
        if use_reset:
            if spent() + price > budget:
                return finish(OPEN_BUDGET, None)
            env.reset()
            counters["resets"] += 1
            since_reset.clear()
            observation, current = observe()
            if current != root:
                # Reset does not return to one place. The table still holds; the root moves.
                counters["surprises"] += 1
                root = current
            if is_goal(observation):
                return finish(PASS, current)
            continue

        assert local is not None
        for action in local:
            if spent() >= budget:
                return finish(OPEN_BUDGET, None)
            observation, _, surprised = step(action, travelling=True)
            if is_goal(observation):
                return finish(PASS, current)
            if surprised:
                break  # the map was wrong here; plan again from where we actually are


def _replay(env: Any, plan: Sequence[str], is_goal: Callable[[Any], bool]) -> tuple[bool, int]:
    env.reset()
    done = 0
    for action in plan:
        env.act(action)
        done += 1
    try:
        return bool(is_goal(env.state())), done
    except Exception:  # a goal predicate that cannot be evaluated has not been met
        return False, done


def drive(env: Any, actions: Sequence[Any], *,
          is_goal: Callable[[Any], bool],
          action_budget: int,
          goal_key: str | None = None,
          use_memory: bool = True,
          verify: bool = True,
          **explore_options: Any) -> dict[str, Any]:
    """Recall first, explore systematically second, and prove either by doing it again.

    Shares the episode store of `transfer_learning_v1`: a plan found here is recalled there
    and the other way round, so this is a different first solve, not a second memory.
    `goal_key` names the goal for that store; without one nothing is recalled or remembered,
    because two different goals must never be filed under one name.
    """
    started = time.time()
    counters = {"act_calls": 0, "reset_calls": 0}

    class Metered:
        def __getattr__(self, name: str) -> Any:
            return getattr(env, name)

        def act(self, action: Any) -> Any:
            counters["act_calls"] += 1
            return env.act(action)

        def reset(self) -> Any:
            counters["reset_calls"] += 1
            return env.reset()

    metered = Metered()
    remember = recall = fingerprint = replayable = None
    fp = None
    memory_on = bool(use_memory and goal_key)
    if memory_on:
        from canonical.runtime import transfer_learning_v1 as tl

        remember, recall, fingerprint, replayable = (
            tl.remember, tl.recall, tl.fingerprint, tl.replayable)
        fp = fingerprint(metered, actions)
        offered = [str(a) for a in actions]
        for candidate in recall(fp, goal_key):
            plan = [str(a) for a in (candidate.get("plan") or [])]
            if not replayable(plan, offered):
                continue
            reached, _ = _replay(metered, plan, is_goal)
            remember(fp, goal_key, plan, reached=reached)
            if reached:
                return {"schema": SCHEMA, "status": PASS_VERIFIED, "pass": True,
                        "reached": True, "transferred": True, "plan": plan,
                        "plan_length": len(plan), "authority": "RECALLED_PLAN_EXECUTED_GOAL_OBSERVED",
                        "interactions": dict(counters), "explored": None,
                        "duration_s": round(time.time() - started, 4)}

    explored = explore_to_goal(metered, actions, is_goal=is_goal,
                               action_budget=action_budget, **explore_options)
    result: dict[str, Any] = {
        "schema": SCHEMA, "status": explored["status"], "pass": False, "reached": False,
        "transferred": False, "plan": None, "authority": explored["authority"],
        "explored": {k: v for k, v in explored.items() if k != "model"},
    }
    if explored["reached"]:
        plans = [explored["plan_shortest"]]
        if explored["plan_walked"] != explored["plan_shortest"]:
            plans.append(explored["plan_walked"])
        if not verify:
            result.update({"status": PASS, "pass": True, "reached": True,
                           "plan": plans[0], "plan_length": len(plans[0])})
        else:
            result["status"] = FAIL_NOT_REPRODUCIBLE
            result["authority"] = "GOAL_OBSERVED_ONCE_NO_PLAN_REPLAYED_TO_IT"
            for plan in plans:
                reached, _ = _replay(metered, plan, is_goal)
                if reached:
                    result.update({"status": PASS_VERIFIED, "pass": True, "reached": True,
                                   "plan": list(plan), "plan_length": len(plan),
                                   "authority": AUTHORITY_REPLAYED})
                    break
        if result["pass"] and memory_on and remember is not None:
            kept = remember(fp, goal_key, result["plan"], reached=True,
                            model=explored.get("model"))
            result["episode_persisted"] = bool(kept.get("persisted"))
    result["interactions"] = dict(counters)
    result["duration_s"] = round(time.time() - started, 4)
    return result
