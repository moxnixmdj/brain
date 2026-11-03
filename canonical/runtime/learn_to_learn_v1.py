"""Learning to learn: can the searcher improve its own SEARCH, not just its facts?

THE QUESTION, AND WHY IT IS THE ONE THAT MATTERS
------------------------------------------------
Measured 2026-11-03 (`canonical/tools/cross_kind_compounding_benchmark_v1.py`): ten
never-before-seen kinds solved cold and solved after nine prior kinds came out **byte-identical,
10/10, net saving 0**. The transition model is keyed per kind, so it cannot compound by
construction. That is a fact about the mechanism, not about the world.

A creature that gets better at new problems has something the transition model does not: its
PROCEDURE changes. It does not remember "here is the answer"; it remembers "that approach was
worse than this one, on a problem shaped like this". That is a different object, and this module
is the smallest honest version of it:

    * a small set of SEARCH POLICIES, each a different way to choose what to try next;
    * a FEATURE view of a problem that does not name its kind (depth, branching shape, whether a
      reward appears gradually or all at once) -- so a lesson can travel between kinds;
    * credit recorded against (features, policy), so the searcher can choose a better policy for a
      problem it has never seen;
    * the SAME verifier discipline as `transfer_learning_v1`: nothing counts unless the goal was
      observed, and a policy is only credited when it actually solved the instance.

WHAT THIS WOULD AND WOULD NOT MEAN IF IT WORKED
-----------------------------------------------
It would mean the system's search improves with experience on unseen problems -- the first real
form of compounding in this repository. It would NOT mean sentience, and it would NOT mean the
policies are discovered by the system: they are written here, by me, as a fixed vocabulary. The
learning is over WHICH TO WRITE POLICY TO USE, which is a genuine but narrow kind of
learning-to-learn. Stated plainly because the alternative -- claiming the mechanism invented its
own strategies -- would be false.

WHAT WOULD FALSIFY IT
---------------------
If, on kinds it has never seen, the learned policy choice performs no better than choosing at
random, then the features do not generalise and this is noise with a story attached. That is the
measurement in `cross_kind_learning_to_learn_benchmark_v1.py`, and it includes the random arm on
purpose.

Authority: NONE. Small constructed state spaces with a hashable `state()`.
"""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_LEARN_TO_LEARN_V1"
STATE_PATH = os.environ.get("BRAIN_LEARN_TO_LEARN_STATE")
POLICY_LEDGER = "policy_credit_v1.json"
DEFAULT_POLICY_MAX = 512


# --------------------------------------------------------------------------- #
# The policy vocabulary. Each returns the order in which to try actions from a
# node: a plan, not a fact. None of them can see the goal state directly; they
# see the actions and a distance-to-goal reading the environment supplies.
# --------------------------------------------------------------------------- #
def _p_bfs_lex(actions: Sequence[Any], _depth: int, _shape: Mapping[str, Any]) -> list[Any]:
    """Breadth-first, trying actions alphabetically. The safe, boring baseline."""
    return list(actions)


def _p_dfs_reversed(actions: Sequence[Any], depth: int, _shape: Mapping[str, Any]) -> list[Any]:
    """Depth-first: plunge. Better when one long chain is needed, worse when branching is wide."""
    return list(reversed(actions)) if depth % 2 == 0 else list(actions)


def _p_repeat_last(actions: Sequence[Any], _depth: int, shape: Mapping[str, Any]) -> list[Any]:
    """Prefer the action that moved last time. Strong in monotone problems (append, count)."""
    last = shape.get("last_action")
    return ([last] + [a for a in actions if a != last]) if last in actions else list(actions)


def _p_never_last(actions: Sequence[Any], _depth: int, shape: Mapping[str, Any]) -> list[Any]:
    """Avoid the action that moved last time. Strong when the state must cycle back."""
    last = shape.get("last_action")
    return [a for a in actions if a != last] + ([last] if last in actions else [])


def _p_rarest(actions: Sequence[Any], _depth: int, shape: Mapping[str, Any]) -> list[Any]:
    """Prefer actions that have been used least in this episode. Spreads exploration."""
    used = shape.get("used") or {}
    return sorted(actions, key=lambda a: (used.get(str(a), 0), str(a)))


POLICIES: dict[str, Callable[..., list[Any]]] = {
    "bfs_lex": _p_bfs_lex,
    "dfs_reversed": _p_dfs_reversed,
    "repeat_last": _p_repeat_last,
    "never_last": _p_never_last,
    "rarest": _p_rarest,
}


# --------------------------------------------------------------------------- #
# Features: what the searcher can know about a problem WITHOUT naming its kind.
# --------------------------------------------------------------------------- #
def features(env: Any, actions: Sequence[Any], is_goal: Callable[[Any], bool],
             horizon: int = 8) -> dict[str, Any]:
    """A kind-blind description of the problem, taken by acting a little.

    Deliberately few and coarse. A rich feature vector would let the choice overfit to kinds it
    has seen, which is the failure this measurement is looking for.
    """
    try:
        env.reset()
    except Exception:  # noqa: BLE001
        pass
    start = env.state()
    states = {str(start)}
    changed_by_action = 0
    try:
        for action in list(actions)[:horizon]:
            env.reset()
            before = env.state()
            env.act(action)
            if str(env.state()) != str(before):
                changed_by_action += 1
            states.add(str(env.state()))
    except Exception:  # noqa: BLE001
        pass
    try:
        env.reset()
    except Exception:  # noqa: BLE001
        pass
    # A SECOND, DEEPER READING: do actions DECOMPOSE the problem, or merely PERMUTE it?
    #
    # The first version of this view reported only branching and moved_fraction. Measured
    # 2026-11-03, that collapsed six distinct training kinds into ONE feature key, every policy
    # solving all of them -- so the ledger had nothing to learn and the benchmark could only say
    # no. The missing distinction is structural and kind-blind:
    #
    #   readout-like   (append a letter, turn a dial, count) the state carries its own progress
    #   permuting-like (rotate, swap)                       the state is CONSERVED
    #
    # Measured without knowing the kind: compare the number of distinct states reachable in ONE
    # action with the number in TWO. A product space of independent readouts grows by the
    # branching factor; a permutation group saturates at its order. This is exactly the
    # difference that makes one search policy right and another wrong, and it is available to a
    # searcher that has never seen the kind before.
    one: set[str] = set()
    two: set[str] = set()
    try:
        for action in list(actions)[:horizon]:
            env.reset()
            env.act(action)
            one.add(str(env.state()))
        for a in list(actions)[:horizon]:
            for b in list(actions)[:horizon]:
                env.reset()
                env.act(a)
                env.act(b)
                two.add(str(env.state()))
    except Exception:  # noqa: BLE001
        one, two = set(), set()
    try:
        env.reset()
    except Exception:  # noqa: BLE001
        pass
    growth = (len(two) / max(1, len(one))) if one else 0.0
    return {
        "branching": len(actions),
        "moved_fraction": round(changed_by_action / max(1, len(list(actions)[:horizon])), 2),
        "start_reaches_goal_already": bool(is_goal(start)),
        "reachable_growth": round(growth, 2),
    }


def _bucket(value: Any, edges: Sequence[float]) -> int:
    for i, edge in enumerate(edges):
        if value <= edge:
            return i
    return len(edges)


def feature_key(feat: Mapping[str, Any]) -> str:
    """A coarse, transferable key. Coarse on purpose: a fine key cannot generalise."""
    return "b%s_m%s_r%s_g%s" % (
        _bucket(int(feat.get("branching") or 0), (2, 4, 6)),
        _bucket(float(feat.get("moved_fraction") or 0.0), (0.45, 0.8)),
        _bucket(float(feat.get("reachable_growth") or 0.0), (1.5, 3.0)),
        int(bool(feat.get("start_reaches_goal_already"))),
    )


# --------------------------------------------------------------------------- #
# The ledger: which policy has worked, on problems that LOOK like this one.
# --------------------------------------------------------------------------- #
def _path() -> str:
    override = os.environ.get("BRAIN_LEARN_TO_LEARN_STATE")
    if override:
        return override
    if STATE_PATH:
        return STATE_PATH
    return str(Path(tempfile.gettempdir()) / "brain_l2l" / POLICY_LEDGER)


def _load() -> dict[str, Any]:
    try:
        with open(_path()) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data: Mapping[str, Any]) -> bool:
    try:
        Path(_path()).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(_path() + ".tmp")
        tmp.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
        tmp.replace(_path())
        return True
    except OSError:
        return False


def credit(fkey: str, policy: str, *, trials: int, solved: bool) -> None:
    """Record what a policy cost on a problem with this feature key.

    Only a SOLVED run is credited as evidence of solving; an unsolved run still records its
    trials, because "this cost 120 trials and failed" is real evidence too. Nothing is credited
    from a run whose goal was never observed by the verifier.
    """
    data = _load()
    rows = data.setdefault("rows", {})
    row = rows.setdefault(fkey, {})
    cell = row.setdefault(policy, {"runs": 0, "solved": 0, "trial_total": 0})
    cell["runs"] = int(cell.get("runs", 0)) + 1
    cell["trial_total"] = int(cell.get("trial_total", 0)) + max(0, int(trials))
    if solved:
        cell["solved"] = int(cell.get("solved", 0)) + 1
    if len(rows) > DEFAULT_POLICY_MAX:
        for stale in list(rows)[:len(rows) - DEFAULT_POLICY_MAX]:
            rows.pop(stale, None)
    _save(data)


def choose(fkey: str, *, rng_seed: int | None = None) -> tuple[str, dict[str, Any]]:
    """The policy to use on a problem with this feature key, and why.

    Unseen feature key -> the boring baseline, and the reason says so. That matters: a chooser
    that silently guesses on an unseen shape looks confident and has no evidence.
    """
    rows = (_load().get("rows") or {}).get(fkey) or {}
    scored = []
    for name, cell in rows.items():
        if name not in POLICIES:
            continue
        runs = max(1, int(cell.get("runs", 0)))
        solved_rate = int(cell.get("solved", 0)) / runs
        mean_trials = int(cell.get("trial_total", 0)) / runs
        # A policy that never solved anything cannot win by being cheap.
        scored.append((solved_rate, -mean_trials, name))
    if not scored:
        return "bfs_lex", {"why": "UNSEEN_FEATURE_KEY", "evidence": 0}
    scored.sort(reverse=True)
    best = scored[0][2]
    return best, {"why": "BEST_OBSERVED_ON_THIS_FEATURE_KEY", "evidence": int(rows[best].get("runs", 0)),
                  "candidates": {name: round(s[0], 2) for s, name in zip(scored, [x[2] for x in scored])}}


def search(env: Any, actions: Sequence[Any], *, is_goal: Callable[[Any], bool],
           policy: str = "bfs_lex", max_depth: int = 10, node_budget: int = 3000,
           meter: dict[str, int] | None = None) -> dict[str, Any]:
    """Depth-limited search whose ORDER is decided by `policy`. Verifier-checked throughout.

    Every node is expanded against the real environment from a real reset, so a plan is only
    returned if the goal was observed after executing it. Counting is through `meter` so the
    caller measures act calls including the expansion work.
    """
    meter = meter if meter is not None else {"act_calls": 0}
    order = POLICIES.get(policy) or POLICIES["bfs_lex"]
    used: dict[str, int] = {}
    last: dict[int, Any] = {}

    def run_plan(plan: Sequence[Any]) -> bool:
        env.reset()
        meter["act_calls"] = meter.get("act_calls", 0) + 1
        for a in plan:
            env.act(a)
            meter["act_calls"] = meter.get("act_calls", 0) + 1
        return bool(is_goal(env.state()))

    # A plan-free check first: the problem may already be solved at the start.
    try:
        env.reset()
        meter["act_calls"] = meter.get("act_calls", 0) + 1
        if is_goal(env.state()):
            return {"schema": SCHEMA, "pass": True, "plan": [], "policy": policy,
                    "nodes": 0, "act_calls": meter["act_calls"]}
    except Exception:  # noqa: BLE001
        pass

    frontier: list[list[Any]] = [[]]
    nodes = 0
    while frontier and nodes < node_budget:
        plan = frontier.pop(0)
        nodes += 1
        shape = {"last_action": last.get(len(plan)), "used": dict(used)}
        for action in order(list(actions), len(plan), shape):
            candidate = plan + [action]
            used[str(action)] = used.get(str(action), 0) + 1
            last[len(candidate)] = action
            try:
                env.reset()
                meter["act_calls"] = meter.get("act_calls", 0) + 1
                for step in candidate:
                    env.act(step)
                    meter["act_calls"] = meter.get("act_calls", 0) + 1
                reached = bool(is_goal(env.state()))
            except Exception:  # noqa: BLE001
                reached = False
            if reached:
                return {"schema": SCHEMA, "pass": True, "plan": candidate, "policy": policy,
                        "nodes": nodes, "act_calls": meter["act_calls"]}
            if len(candidate) < max_depth:
                frontier.insert(0 if policy == "dfs_reversed" else len(frontier), candidate)
    return {"schema": SCHEMA, "pass": False, "plan": None, "policy": policy,
            "nodes": nodes, "act_calls": meter["act_calls"]}
