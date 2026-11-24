"""Learn which parts of an observation are instance noise, from interventions on the reset.

Problem (measured in ENVIRONMENT_TRANSFER_IS_THE_ABSTRACTION_20261124_V1.md): a transition
table learned on one instance transfers to a new instance only if its state keys are
abstract. Raw keys carry instance facts (a tag, a file name) and never match again.

Mechanism (no model, no parameters):
  1. Intervene on the reset: run the same environment from several starts that differ only
     in instance identity (a tag, a name). Each start is one counterfactual.
  2. A token of an observation is INVARIANT if it occurs in every start. Tokens that vary
     with the start are nuisance. The invariant vocabulary is the learned abstraction.
  3. Abstract each observation by replacing every non-invariant token with "*".
  4. Accept the abstraction only if the abstract transition system is consistent:
       - deterministic: one (abstract state, action) has one abstract successor;
       - goal-consistent: every abstract state is entirely goal or entirely non-goal.
     If either fails, the abstraction is REFUSED (fail closed), not patched.

Observations are JSON-like: dict/list/str/int/bool/None. Only strings are tokenised.
"""
from __future__ import annotations

import json
import re
from collections import deque
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_ABSTRACTION_V1"
MASK = "*"
ACCEPTED = "ACCEPTED__ABSTRACTION_DETERMINISTIC_AND_GOAL_CONSISTENT"
REFUSED_NONDET = "REFUSED__ABSTRACTION_NONDETERMINISTIC"
REFUSED_GOAL = "REFUSED__ABSTRACTION_MIXES_GOAL_AND_NON_GOAL"


def _tokens(obs: Any, out: set[str]) -> None:
    if isinstance(obs, str):
        out.update(obs.split())
    elif isinstance(obs, Mapping):
        for k, v in obs.items():
            _tokens(k, out)
            _tokens(v, out)
    elif isinstance(obs, (list, tuple)):
        for v in obs:
            _tokens(v, out)


def token_set(observations: Iterable[Any]) -> set[str]:
    out: set[str] = set()
    for o in observations:
        _tokens(o, out)
    return out


def invariant_vocabulary(per_start: Sequence[Iterable[Any]]) -> frozenset[str]:
    """Tokens that occur in EVERY counterfactual start. Intersection = what survives the reset."""
    sets = [token_set(obs) for obs in per_start]
    if not sets:
        return frozenset()
    inter = set(sets[0])
    for s in sets[1:]:
        inter &= s
    return frozenset(inter)


def abstract(obs: Any, vocab: frozenset[str]) -> Any:
    """Mask every non-invariant token. Structure, numbers and booleans are kept as they are."""
    if isinstance(obs, str):
        # mask each token IN PLACE: whitespace layout is part of the state. Porcelain status
        # " M a.txt" (unstaged) and "M  a.txt" (staged) differ only in layout; joining the
        # split tokens merged them and produced a real nondeterministic abstraction.
        return re.sub(r"\S+", lambda m: m.group(0) if m.group(0) in vocab else MASK, obs)
    if isinstance(obs, Mapping):
        return {str(k): abstract(v, vocab) for k, v in sorted(obs.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obs, (list, tuple)):
        return [abstract(v, vocab) for v in obs]
    return obs


def akey(obs: Any) -> str:
    return json.dumps(obs, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_abstract_model(learned_list: Sequence[Mapping[str, Any]], vocab: frozenset[str],
                         is_goal: Callable[[Any], bool]) -> dict[str, Any]:
    """Fold every learned run into one abstract transition system, checking consistency.

    `learned_list` items are outputs of environment_learning_v1.learn_model.
    Traces give (before_key, action, after_key); `observations` maps keys to snapshots.
    """
    succ: dict[str, dict[str, str]] = {}
    goal_of: dict[str, set[bool]] = {}
    snap_of: dict[str, Any] = {}
    nondet: list[dict[str, str]] = []
    roots: list[str] = []

    for L in learned_list:
        obs = L["observations"]
        for key, snap in obs.items():
            ak = akey(abstract(snap, vocab))
            snap_of.setdefault(ak, abstract(snap, vocab))
            goal_of.setdefault(ak, set()).add(bool(is_goal(snap)))
        roots.append(akey(abstract(obs[L["root"]], vocab)))
        for t in L["traces"]:
            a_before = akey(abstract(obs[t["before"]], vocab))
            a_after = akey(abstract(obs[t["after"]], vocab))
            act = str(t["action"])
            prev = succ.setdefault(a_before, {}).get(act)
            if prev is None:
                succ[a_before][act] = a_after
            elif prev != a_after:
                nondet.append({"state": a_before, "action": act, "a": prev, "b": a_after})

    mixed = [k for k, v in goal_of.items() if len(v) > 1]
    if nondet:
        status = REFUSED_NONDET
    elif mixed:
        status = REFUSED_GOAL
    else:
        status = ACCEPTED
    goal_states = {k for k, v in goal_of.items() if v == {True}}
    return {
        "schema": SCHEMA, "status": status, "vocab_size": len(vocab),
        "vocab": sorted(vocab), "abstract_states": len(goal_of),
        "abstract_transitions": sum(len(v) for v in succ.values()),
        "nondeterministic_edges": len(nondet), "nondeterministic_examples": nondet[:3],
        "mixed_goal_states": len(mixed), "model": succ, "goal_states": sorted(goal_states),
        "roots": roots,
    }


def plan_in_abstraction(model: Mapping[str, Any], root_snapshot: Any, vocab: frozenset[str]
                        ) -> list[str] | None:
    """Shortest action sequence in the abstract model from the abstracted root to a goal state."""
    if model["status"] != ACCEPTED:
        return None
    root = akey(abstract(root_snapshot, vocab))
    goals = set(model["goal_states"])
    succ = model["model"]
    if root in goals:
        return []
    prev: dict[str, tuple[str, str]] = {}
    seen = {root}
    q = deque([root])
    while q:
        node = q.popleft()
        for act, nxt in sorted((succ.get(node) or {}).items()):
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = (node, act)
            if nxt in goals:
                out: list[str] = []
                cur = nxt
                while cur != root:
                    p, a = prev[cur]
                    out.append(a)
                    cur = p
                return list(reversed(out))
            q.append(nxt)
    return None
