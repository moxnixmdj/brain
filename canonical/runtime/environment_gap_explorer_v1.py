"""Gap-directed, checkpointed exploration of an unseen environment with a learned abstract model.

Mechanism (no model call, no parameters):
  - The abstract model maps (abstract state, action) -> abstract successor. It comes from
    environment_abstraction_v1 (learned from counterfactual resets) and grows as the agent acts.
  - A plan is searched only over EDGES THAT WERE CONSISTENT: an edge seen with two different
    successors is marked unreliable and is never planned through.
  - When no plan exists, the explorer tries an action that has not been tried from the current
    abstract state (a gap), in a seeded order.
  - Before every action the environment is checkpointed. If the action violates the
    must-not-change predicate `keep`, the checkpoint is restored and (state, action) is recorded
    as unsafe. Restores are counted, not hidden.
  - Success is claimed ONLY when the real goal predicate holds on the real end state. A plan that
    the model predicted but the environment did not honour is counted as a mismatch.

Environment interface (duck-typed):
    state() -> snapshot, act(action), checkpoint() -> token, restore(token)
"""
from __future__ import annotations

import collections
import random
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_GAP_EXPLORER_V1"


class AbstractModel:
    """Abstract transition table with reliability marks (conflicting edges are not planned through)."""

    def __init__(self, succ: Mapping[str, Mapping[str, str]] | None = None,
                 goal_states: Sequence[str] = ()):
        self.succ: dict[str, dict[str, str]] = {k: dict(v) for k, v in (succ or {}).items()}
        self.goals: set[str] = set(goal_states)
        self.unreliable: set[tuple[str, str]] = set()
        self.mismatches = 0

    def observe(self, before: str, action: str, after: str, after_is_goal: bool) -> None:
        cur = self.succ.get(before, {}).get(action)
        if cur is not None and cur != after:
            self.unreliable.add((before, action))
            self.mismatches += 1
        self.succ.setdefault(before, {})[action] = after
        self.succ.setdefault(after, {})
        if after_is_goal:
            self.goals.add(after)

    def plan(self, start: str) -> list[str] | None:
        if start in self.goals:
            return []
        prev: dict[str, tuple[str, str] | None] = {start: None}
        q = collections.deque([start])
        while q:
            node = q.popleft()
            for act, nxt in sorted(self.succ.get(node, {}).items()):
                if (node, act) in self.unreliable or nxt in prev:
                    continue
                prev[nxt] = (node, act)
                if nxt in self.goals:
                    out: list[str] = []
                    cur = nxt
                    while prev[cur] is not None:
                        p, a = prev[cur]  # type: ignore[misc]
                        out.append(a)
                        cur = p
                    return list(reversed(out))
                q.append(nxt)
        return None


def explore(env: Any, actions: Sequence[str], model: AbstractModel, *,
            key: Callable[[Any], str], goal: Callable[[Any], bool],
            keep: Callable[[Any], bool], budget: int, seed: int,
            policy: str = "gap") -> dict[str, Any]:
    """policy='gap': plan if possible, else an untried action. policy='uniform': a random
    action each step, ignoring the model and what was tried (the control)."""
    rng = random.Random(seed)
    order = list(actions)
    rng.shuffle(order)
    tried: dict[str, set[str]] = collections.defaultdict(set)
    unsafe: set[tuple[str, str]] = set()
    spent = restores = 0
    snap = env.state()
    while True:
        if goal(snap):
            return _result(True, spent, restores, model, snap, keep)
        if spent >= budget:
            break
        cur = key(snap)
        if policy == "uniform":
            allowed = [a for a in actions if (cur, a) not in unsafe]
            if not allowed:
                break
            act = rng.choice(allowed)
            token = env.checkpoint()
            env.act(act); spent += 1
            after = env.state()
            if keep(snap) and not keep(after):
                env.restore(token); restores += 1; unsafe.add((cur, act)); continue
            model.observe(cur, act, key(after), goal(after))
            snap = after
            continue
        path = model.plan(cur)
        if path:
            act = path[0]
        else:
            cands = [a for a in order if a not in tried[cur] and (cur, a) not in unsafe]
            if not cands:
                break
            act = cands[0]
        tried[cur].add(act)
        token = env.checkpoint()
        env.act(act)
        spent += 1
        after = env.state()
        if keep(snap) and not keep(after):
            env.restore(token)
            restores += 1
            unsafe.add((cur, act))
            continue
        model.observe(cur, act, key(after), goal(after))
        snap = after
    return _result(False, spent, restores, model, snap, keep)


def _result(success: bool, spent: int, restores: int, model: AbstractModel,
            snap: Any, keep: Callable[[Any], bool]) -> dict[str, Any]:
    return {"schema": SCHEMA, "success": success, "actions": spent, "restores": restores,
            "mismatches": model.mismatches, "unreliable_edges": len(model.unreliable),
            "must_not_change_holds_at_end": bool(keep(snap)), "final": snap}
