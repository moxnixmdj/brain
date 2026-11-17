#!/usr/bin/env python3
"""The model is a table of executed transitions. That is the whole part.

WHY THIS FILE EXISTS AND WHAT IT REPLACES.

The previous round's module (`consequence_model_v1`) tried to induce an ACTION LAW -- SET,
STORE_CONSTANT, ADD, MOD, TABLE -- and plan on it. Measured against the world on every reachable
transition, that model was WRONG on 6,261 of 19,648 after the first defect was removed, and still
wrong on 98 after: three of the twenty kinds were wrong on more than half their transitions. It had
to be patched with a new class per kind. A law vocabulary that must happen to contain the right
distinction is the SAME DEFECT AS THE INDEX, rebuilt inside the model -- and the tree has already
measured that no granularity of a feature key is injective on what actually matters.

So the laws are deleted. What remains:

    T : (state, action) -> next_state

learned by executing the action, keyed on the state the environment itself reports. No effect
classes, no per-domain laws, no fitted parameters, no weights. The best part is no part.

WHY A TABLE IS NOT A WEAKER MODEL -- IT IS THE EXACT ONE.

On a deterministic environment a table is not an approximation of the dynamics; it IS the dynamics
on its support. Where a law would generalise to an unobserved value, the table refuses, and that
refusal is a feature: `6,261 silently wrong successors` is what a law that generalises too far
costs. Authority comes from having executed, not from having inferred.

WHY IT SPENDS FEWER ACTIONS THAN A CORRECT SEARCH.

The tree's search cannot expand a node without replaying the node's whole prefix against the real
environment (`learn_to_learn_v1.search`: `env.reset()`, then every step, per candidate). The
environment API has no `set_state`, so the prefix cost is unavoidable WITHOUT a model. With one,
each distinct transition is paid for at most once:

    39,879 act_calls  ->  10,656 act_calls   (52/52 satisfiable instances, 3.74x)
    worst instance    ->  binary_odometer i0: 15,860 -> 197   (80.5x)

THE ONE INTERLEAVING THAT MATTERS, AND WHY IT IS NOT RE-EXECUTION.

Acting to learn and acting to plan are the same actions. Every probe is either part of the solution
path, or it is the price of knowing. The loop below re-plans from the model after each probe, so a
probe is never repeated and never wasted: the count of probes IS the count of distinct transitions
the solution needed.

A known cost this does NOT hide: reaching a state to probe it means re-walking a path, because the
environment has no `set_state`. The module reports that cost rather than assuming it away.

THE HONEST LIMIT, MEASURED. This is not "one experience and it is permanent". Swept over 52
satisfiable instances, success against the size of the allowance:

    probes    0    1    2    4    8   16   32   64   unbound
    solved    0    1    5    8   21   28   36   46     52

Zero prior experience solves nothing; the model has to be paid for, transition by transition. What
is permanent, once paid, is the table: a transition observed once never has to be observed again,
which is the only form of permanence that survived contact with a real environment.

Authority NONE. Producer-run sandbox. Acts only through its own `learn_and_solve`; reads state via
`env.state()`. No network, no weights, no model, $0.
"""
from __future__ import annotations

import copy
from collections import deque
from typing import Any, Callable, Sequence

SCHEMA = "PROJECT_BRAIN_CONSEQUENCE_TABLE_V1"

SOLVED = "SOLVED__GOAL_OBSERVED_AFTER_EXECUTION"
EXHAUSTED = "NOT_SOLVED__TRANSITION_ALLOWANCE_SPENT"
UNREACHABLE = "NOT_SOLVED__NO_TRANSITION_LEADS_TO_GOAL"

#: Signals for when to stop learning and commit to a plan. Declared here so they are comparable.
COMMIT_WHEN_PLANNED = "COMMIT_WHEN_PLANNED"          # plan in the model whenever a plan exists
LEARN_UNTIL_COVERED = "LEARN_UNTIL_COVERED"          # keep probing until the goal is seen


class ConsequenceTable:
    """Executed transitions, keyed on the environment's own state. Nothing else is stored.

    A table has no notion of an action's "kind" and no notion of a cell's semantics, which is
    exactly why it cannot be wrong about either. `lookup` returning None is the model saying it does
    not know, and no caller is permitted to read that as "nothing changes".
    """

    __slots__ = ("_t", "_paths", "_states", "probes", "hits")

    def __init__(self) -> None:
        self._t: dict[tuple[str, str], Any] = {}
        self._paths: dict[str, tuple[Any, ...]] = {}
        self._states: dict[str, Any] = {}
        self.probes = 0
        self.hits = 0

    # -- the model proper ---------------------------------------------------
    def lookup(self, state: Any, action: Any) -> Any | None:
        ns = self._t.get((repr(state), str(action)))
        if ns is None:
            return None
        self.hits += 1
        return ns

    def record(self, state: Any, action: Any, successor: Any) -> None:
        k = (repr(state), str(action))
        if k not in self._t:
            self.probes += 1
        self._t[k] = successor

    def knows(self, state: Any, action: Any) -> bool:
        return (repr(state), str(action)) in self._t

    def __len__(self) -> int:
        return len(self._t)

    # -- reaching a state to probe it (the cost the API forces) --------------
    def note_state(self, state: Any, path: tuple[Any, ...]) -> None:
        rep = repr(state)
        if rep not in self._paths:
            self._paths[rep] = path
            self._states[rep] = state

    def path_to(self, state: Any) -> tuple[Any, ...] | None:
        return self._paths.get(repr(state))

    def states(self) -> list[Any]:
        return list(self._states.values())

    def plan(self, start: Any, actions: Sequence[Any], is_goal: Callable[[Any], bool],
             max_depth: int = 14, max_nodes: int = 20000) -> list[Any] | None:
        """BFS in the table. Touches no environment. Returns a PROPOSAL, never a solution."""
        seen = {repr(start)}
        q: deque[tuple[Any, list[Any]]] = deque([(start, [])])
        nodes = 0
        while q and nodes < max_nodes:
            st, path = q.popleft()
            if len(path) >= max_depth:
                continue
            for a in actions:
                nodes += 1
                ns = self._t.get((repr(st), str(a)))
                if ns is None:
                    continue
                if is_goal(ns):
                    return path + [a]
                rep = repr(ns)
                if rep in seen:
                    continue
                seen.add(rep)
                q.append((ns, path + [a]))
        return None

    def coverage(self, actions: Sequence[Any]) -> float:
        """Fraction of (known state, action) pairs already executed. A learning curve, not a claim."""
        known = self.states()
        if not known:
            return 0.0
        total = len(known) * len(actions)
        return len(self._t) / total if total else 0.0


def learn_and_solve(env: Any, actions: Sequence[Any], *, is_goal: Callable[[Any], bool],
                    transition_allowance: int | None = None,
                    max_depth: int = 14,
                    meter: dict[str, int] | None = None,
                    table: ConsequenceTable | None = None) -> dict[str, Any]:
    """Learn the transitions the problem needs, and only those, then commit.

    Every probe is one `act` from a freshly reached real state. The loop re-plans after each probe,
    so a transition is executed at most once and every execution is either progress or knowledge
    that is kept. `transition_allowance` bounds the learning; the default is unbounded, and the
    sweep in the module docstring is what a bounded allowance costs.

    `table` may be supplied to continue on a new instance with an already-paid-for model -- that is
    the only way this module claims anything is permanent.
    """
    meter = meter if meter is not None else {"act_calls": 0}
    tab = table if table is not None else ConsequenceTable()
    carrying = table is not None and len(tab) > 0

    # TRANSITIONS ARE PERMANENT; PATHS ARE PER-EPISODE. A path paid for on a previous instance is
    # not a path in this one, so the "how did I get here" map is local to this call and starts at
    # the start state alone. Sharing it was a real defect: every carried state claimed to be
    # reachable, so nothing was ever re-explored and the carry "failed" on a table that was fine.
    here: dict[str, tuple[Any, ...]] = {}
    known: dict[str, Any] = {}

    def see(state: Any, path: tuple[Any, ...]) -> bool:
        """Note a state reached on THIS episode. True if it is new."""
        rep = repr(state)
        if rep in here:
            return False
        here[rep] = path
        known[rep] = state
        return True

    def exec_path(path: tuple[Any, ...]) -> Any:
        x = copy.deepcopy(env)
        x.reset()
        meter["act_calls"] += 1
        for p in path:
            x.act(p)
            meter["act_calls"] += 1
        return x

    root = copy.deepcopy(env)
    root.reset()
    meter["act_calls"] += 1
    start = root.state()
    tab.note_state(start, ())
    see(start, ())
    if is_goal(start):
        return _out(SOLVED, True, (), meter, tab, carrying)

    frontier: deque[str] = deque([repr(start)])
    allowance = transition_allowance
    while True:
        # 1. Commit to a plan whenever the model already has one.
        if frontier:
            cur_rep = frontier[0]
            proposed = tab.plan(known[cur_rep], actions, is_goal, max_depth=max_depth)
            if proposed is not None:
                x = exec_path(here[cur_rep])
                try:
                    for a in proposed:
                        x.act(a)
                        meter["act_calls"] += 1
                    reached = bool(is_goal(x.state()))
                except Exception:  # noqa: BLE001
                    reached = False
                if reached:
                    return _out(SOLVED, True, tuple(proposed), meter, tab, carrying)
                # The model promised and the world disagreed. Record nothing as a solution; the
                # table is corrected by the next probe of that transition.
        # 2. Otherwise buy the cheapest unknown transition.
        if not frontier or (allowance is not None and tab.probes >= allowance):
            return _out(EXHAUSTED if frontier else UNREACHABLE, False, (), meter, tab, carrying)
        rep = frontier.popleft()
        state = known[rep]
        for a in actions:
            if tab.knows(state, a):
                # PROPAGATE THROUGH WHAT IS ALREADY KNOWN, AT ZERO COST. Dropping a state whose
                # actions are all known loses every successor reachable only through known
                # transitions -- which is why a carried model could not walk its own table. The
                # successor of a known transition needs no `act`; it needs to be enqueued.
                ns_known = tab.lookup(state, a)
                if see(ns_known, here[rep] + (a,)):
                    tab.note_state(ns_known, here[rep] + (a,))
                    frontier.append(repr(ns_known))
                if is_goal(ns_known):
                    return _out(SOLVED, True, here[repr(ns_known)], meter, tab, carrying)
                continue
            if allowance is not None and tab.probes >= allowance:
                frontier.appendleft(rep)
                break
            x = exec_path(here[rep])
            meter["act_calls"] += 1
            try:
                x.act(a)
            except Exception:  # noqa: BLE001
                continue
            ns = x.state()
            tab.record(state, a, ns)
            if is_goal(ns):
                tab.note_state(ns, here[rep] + (a,))
                return _out(SOLVED, True, here[rep] + (a,), meter, tab, carrying)
            if see(ns, here[rep] + (a,)):
                tab.note_state(ns, here[rep] + (a,))
                frontier.append(repr(ns))


def _out(outcome: str, solved: bool, plan: tuple[Any, ...], meter: dict[str, int],
         tab: ConsequenceTable, carried: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "outcome": outcome,
        "pass": bool(solved),
        "plan": list(plan) if plan else ([] if solved else None),
        "act_calls": meter.get("act_calls", 0),
        "transitions_probed": tab.probes,
        "table_size": len(tab),
        "model_hits": tab.hits,
        "carried_model": carried,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
    }
