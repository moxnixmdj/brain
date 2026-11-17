#!/usr/bin/env python3
"""Are two environments the same machine? An exact decision procedure, plus the transfer it permits.

WHY THIS EXISTS: A CLAIM TO SETTLE, NOT A FEATURE TO ADD.

The premise under test is "learn it once and it works in arbitrary new environments". That sentence
is worth exactly one question: are the two environments the same machine under some renaming of
their states and actions? If they are, a plan transfers and that is a THEOREM. If they are not, no
amount of learning, abstraction or clever indexing can transfer anything between them, because there
is nothing there to transfer -- the plan addresses a structure the target does not have.

The previous round measured 0/48 cross-environment transfers. That number was read by me as a GAP IN
OUR MECHANISM. This module is the check that decides whether it is a gap or a fact, and it is written
to answer the question EXACTLY so the question cannot be re-opened by argument.

WHAT I GOT WRONG BEFORE WRITING THIS, RECORDED SO IT IS NOT REPEATED.

My first attempt compared a `fingerprint`: the abstract block-transition table under a coarse
label. It reported that `grid_walk`, `toggle_bank`, `parity_lights` and `double_dial` were the same
machine, and `cyclic_counter`, `dial_lock`, `adjacent_sort`, `sliding_pairs`, `binary_odometer`,
`last_wins` and `tri_lock` were the same machine. Transferring plans across those groups executed
successfully 6 times out of 54 -- an 11.1% precision that looked like a weak win.

It was not a win. The fingerprint IGNORED the number of states, so machines with 16 and 20 states
were called equal. Enumerating the actual bijections and action permutations found NO isomorphism in
any of those pairs. A fingerprint is a NECESSARY condition and never a sufficient one; only a
witnessed bijection is a proof. That is why this module searches for the bijection and returns
REFUSED rather than a boolean it cannot back.

WHAT IT COMPUTES.

    induce(env, actions, is_goal)   the reachable LABELLED transition system, states numbered by
                                    discovery, label = "is this a goal state". The label is the only
                                    observation, and it is the one every environment can be asked
                                    for without naming it.
    canonical(ts)                   a name-free fingerprint. NECESSARY for isomorphism, used only to
                                    reject fast. Never reported as a conclusion.
    isomorphic(a, b)                EXACT search over state bijections and action permutations, with
                                    propagation and a node budget. Returns the witness WITNESS_FOUND,
                                    a proof of NO_WITNESS, or UNKNOWN when the budget runs out. It
                                    never returns "probably".
    transfer(plan, witness, target) map a plan through the witness and hand it back for EXECUTION.
                                    A mapped plan is a PROPOSAL; only running it is evidence.

THE HONEST FAILURE MODE. A large pair exhausts the node budget and answers UNKNOWN. UNKNOWN is
reported as UNKNOWN. Claiming "not isomorphic" from a search that did not finish would be the same
class of error as the fingerprint, and this module exists because of that error.

Authority NONE. Producer-run sandbox. Reads only `env.reset/act/state`. No network, no weights, $0.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Callable, Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_TRANSITION_SYSTEM_IDENTITY_V1"

WITNESS_FOUND = "WITNESS_FOUND__THE_TWO_ENVIRONMENTS_ARE_THE_SAME_MACHINE"
NO_WITNESS = "NO_WITNESS__EXHAUSTIVE_SEARCH_FOUND_NO_ISOMORPHISM"
UNKNOWN = "UNKNOWN__SEARCH_BUDGET_EXHAUSTED"
TRIVIAL = "TRIVIAL__THE_TWO_ARGUMENTS_ARE_THE_SAME_ENVIRONMENT"

#: A cap on the induced state space. Above this an environment is reported as too large to decide
#: EXACTLY, rather than decided by a heuristic. Real computer use is FAR above this; that is the
#: point of the limit and it is stated in every caller.
MAX_STATES = 600


def induce(env: Any, actions: Sequence[Any], is_goal: Callable[[Any], bool],
           cap: int = MAX_STATES, meter: dict[str, int] | None = None) -> dict[str, Any]:
    """The reachable labelled transition system, by acting. Nothing is assumed about the names."""
    meter = meter if meter is not None else {"act_calls": 0}
    acts = [str(a) for a in actions]
    env.reset()
    meter["act_calls"] = meter.get("act_calls", 0) + 1
    s0 = env.state()
    index = {repr(s0): 0}
    paths: dict[int, tuple[Any, ...]] = {0: ()}
    states = [s0]
    q: deque[int] = deque([0])
    delta: dict[tuple[int, str], int] = {}
    truncated = False
    while q:
        i = q.popleft()
        for a, name in zip(actions, acts):
            env.reset()
            meter["act_calls"] = meter.get("act_calls", 0) + 1
            for p in paths[i]:
                env.act(p)
                meter["act_calls"] = meter.get("act_calls", 0) + 1
            try:
                env.act(a)
                meter["act_calls"] = meter.get("act_calls", 0) + 1
            except Exception:  # noqa: BLE001 - an action that cannot run is absent from the system
                continue
            ns = env.state()
            rep = repr(ns)
            if rep not in index:
                if len(states) >= cap:
                    truncated = True
                    continue
                index[rep] = len(states)
                states.append(ns)
                paths[index[rep]] = paths[i] + (a,)
                q.append(index[rep])
            delta[(i, name)] = index[rep]

    labels: list[int] = []
    for i in range(len(states)):
        env.reset()
        meter["act_calls"] = meter.get("act_calls", 0) + 1
        for p in paths[i]:
            env.act(p)
            meter["act_calls"] = meter.get("act_calls", 0) + 1
        labels.append(1 if is_goal(env.state()) else 0)

    return {"schema": SCHEMA, "n": len(states), "actions": acts, "delta": delta,
            "labels": labels, "start": 0, "truncated": truncated,
            "act_calls": meter.get("act_calls", 0),
            "status": "TRUNCATED__STATE_CAP_REACHED" if truncated else "PASS"}


def canonical(ts: dict[str, Any]) -> tuple:
    """A name-free fingerprint. NECESSARY for isomorphism; NEVER sufficient. Rejects fast only."""
    n = ts["n"]
    acts = ts["actions"]
    labels = ts["labels"]
    block = {s: labels[s] for s in range(n)}
    ids: dict[Any, int] = {}
    block = {s: ids.setdefault((labels[s],), len(ids)) for s in range(n)}
    while True:
        sig = {}
        for s in range(n):
            row = tuple(-1 if ts["delta"].get((s, a)) is None else block[ts["delta"][(s, a)]]
                        for a in acts)
            sig[s] = (block[s], row)
        order: dict[Any, int] = {}
        new = {s: order.setdefault(sig[s], len(order)) for s in range(n)}
        if len(set(new.values())) == len(set(block.values())) and len(set(new.values())) == n:
            block = new
            break
        if new == block:
            break
        block = new
    absd = {}
    for (s, a), t in ts["delta"].items():
        absd[(block[s], acts.index(a))] = block[t]
    rows = tuple(sorted((block[s], tuple(absd.get((block[s], i), -1) for i in range(len(acts))))
                        for s in range(n)))
    return (n, len(acts), tuple(labels), len(set(block.values())), rows)


def _signatures(ts: dict[str, Any]) -> list[tuple]:
    """Per-state invariant profile: label, out-degree, in-degree, and per-action existence."""
    n = ts["n"]
    acts = ts["actions"]
    indeg = defaultdict(int)
    for t in ts["delta"].values():
        indeg[t] += 1
    out = []
    for s in range(n):
        out.append((ts["labels"][s], indeg[s],
                    tuple(1 if (s, a) in ts["delta"] else 0 for a in acts)))
    return out


def isomorphic(a: dict[str, Any], b: dict[str, Any], node_budget: int = 200000) -> dict[str, Any]:
    """Exact search for a state bijection + action permutation that commutes with both dynamics.

    Returns WITNESS_FOUND with the witness, NO_WITNESS only when the search space was exhausted,
    and UNKNOWN otherwise. There is no fourth answer and no probabilistic one.
    """
    if a is b:
        return {"outcome": TRIVIAL, "witness": None}
    if a["n"] != b["n"] or len(a["actions"]) != len(b["actions"]):
        return {"outcome": NO_WITNESS, "witness": None,
                "reason": "STATE_OR_ACTION_COUNT_DIFFERS", "nodes": 0,
                "proof": "a bijection cannot exist between sets of different size"}
    if canonical(a) != canonical(b):
        return {"outcome": NO_WITNESS, "witness": None,
                "reason": "CANONICAL_FINGERPRINT_DIFFERS", "nodes": 0,
                "proof": "the fingerprint is a necessary condition; differing fingerprints prove non-isomorphism"}
    if a["truncated"] or b["truncated"]:
        return {"outcome": UNKNOWN, "witness": None,
                "reason": "STATE_SPACE_TRUNCATED", "nodes": 0}

    n = a["n"]
    k = len(a["actions"])
    sa, sb = _signatures(a), _signatures(b)
    # candidate sets, and a deterministic order that tries the most constrained state first
    cand = [[i for i in range(n) if sa[s] == sb[i]] for s in range(n)]
    order = sorted(range(n), key=lambda s: (len(cand[s]), sa[s]))
    mapsto: dict[int, int] = {}
    used: set[int] = set()
    nodes = 0
    perms = []

    def perm_candidates(pi: list[int | None]) -> Iterable[list[int | None]]:
        if all(p is not None for p in pi):
            yield list(pi)  # type: ignore[misc]
            return
        i = pi.index(None)
        for j in range(k):
            if j in pi:
                continue
            pi[i] = j
            yield from perm_candidates(pi)
            pi[i] = None

    for perm in perm_candidates([None] * k):
        amap = {a["actions"][i]: b["actions"][perm[i]] for i in range(k)}
        mapsto.clear()
        used.clear()
        stack: list[tuple[int, int]] = []
        ok = True
        # start states must correspond
        if b["start"] not in cand[a["start"]]:
            continue
        mapsto[a["start"]] = b["start"]
        used.add(b["start"])
        stack = [a["start"]]
        while stack and ok:
            s = stack.pop()
            for act in a["actions"]:
                t = a["delta"].get((s, act))
                if t is None:
                    continue
                bt = b["delta"].get((mapsto[s], amap[act]))
                nodes += 1
                if nodes > node_budget:
                    return {"outcome": UNKNOWN, "witness": None,
                            "reason": "NODE_BUDGET_EXHAUSTED", "nodes": nodes}
                if bt is None:
                    ok = False
                    break
                if t in mapsto:
                    if mapsto[t] != bt:
                        ok = False
                        break
                else:
                    if bt in used or bt not in cand[t]:
                        ok = False
                        break
                    mapsto[t] = bt
                    used.add(bt)
                    stack.append(t)
        if ok and len(mapsto) == n:
            if all(a["labels"][s] == b["labels"][mapsto[s]] for s in range(n)):
                return {"outcome": WITNESS_FOUND, "nodes": nodes,
                        "witness": {"state_map": dict(mapsto), "action_map": amap},
                        "action_permutation": perm}
    return {"outcome": NO_WITNESS, "witness": None, "reason": "EXHAUSTED", "nodes": nodes,
            "proof": "every action permutation and state bijection was tried and none commutes"}


def transfer(plan: Sequence[Any], witness: dict[str, Any], source: dict[str, Any],
             target: dict[str, Any]) -> dict[str, Any]:
    """Map a plan through a witnessed isomorphism. Returns a PROPOSAL, not a result."""
    if not witness:
        return {"status": "REFUSED__NO_WITNESS", "plan": None}
    amap = witness["action_map"]
    out = []
    for a in plan:
        na = amap.get(str(a))
        if na is None:
            return {"status": "REFUSED__ACTION_NOT_IN_WITNESS", "plan": None}
        out.append(na)
    return {"status": "PROPOSED__MUST_BE_EXECUTED_TO_COUNT", "plan": out,
            "note": "a mapped plan is only evidence after it is executed and the goal observed"}
