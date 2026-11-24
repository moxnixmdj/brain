"""What to save: a provenance-free machine plus the shortest experiment that settles it.

THE GAP THIS FILLS
------------------
The project already answers three of the four questions the mission asks:

* what exists in an environment        -> `swe_kernel.perfect_algorithm_v1.scan`
* which action to try next             -> `.right_question` (novelty/closeness)
* may a lesson become permanent        -> `consistency_vs_equivalence_v1`

It could not answer the fourth: **between the several machines consistent with
what has been seen, which single experiment removes the most of them, and when
does no experiment remain?** `right_question` orders by novelty and closeness,
which is a heuristic: it does not know what its own uncertainty is about.
`consistency_vs_equivalence_v1.prove_admission` can refute two statements when
handed a trace space, but it does not manufacture the experiment.

WHAT IS SAVED, AND WHAT IS THROWN AWAY
--------------------------------------
Not the trajectory. A trace is one path through a machine; the machine is the
closure of every path. So the unit of knowledge here is a set of *observations*
(access sequence, action, resulting observation) plus a *minimal model* that
explains all of them. Saving the model instead of the path is the difference
between remembering "I turned the knob at 21:03" and knowing "the knob is a
3-position dial that wraps".

Crucially, the stored model has NO names in it. States are integers, and every
state is reachable from the start by a concrete action word. That is what makes
it portable: the integers are a relabelling of an equivalence class, so the same
saved machine can be re-bound to a different environment's actions once the
class is matched. The user's intuition -- "his actions will never be needed
again, because the environments are always changing" -- is exactly right, and
this is the consequence: what survives is the shape, keyed by behaviour.

MINIMALITY, HONESTLY
--------------------
A set of observations is consistent with many machines. This module keeps all of
them implicitly and reports two different things, because they are not the same
claim:

* `minimal_consistent_machine` -- the smallest machine consistent with the
  observations (an exact minimum via partition refinement over the observation
  tree, deterministic and complete for the declared action alphabet), and
* `unresolved` -- the question the observations cannot answer. That is a
  *minimality-within-a-class* claim, not an identification claim. Saying "this is
  the smallest machine consistent with the data" and saying "this is the
  machine" are different sentences and only the first one is proved here.

THE SEPARATING EXPERIMENT
-------------------------
Given two candidate machines over the same actions, the shortest word on which
they disagree is computed by breadth-first search over the product. If no word
exists within the bound, the two are equivalent *within the bound* and it says
so instead of claiming equivalence.

The literature this follows (checked 2026-11-24, not treated as gospel):
learning a minimal *separating* DFA is the current formulation of active
learning for this problem -- L#_Box at CAV 2026 (arXiv 2605.15294) reports
orders-of-magnitude fewer queries than L*_Box by keeping a basis of pairwise
apart states; AL# (arXiv 2406.19714) reuses separating sequences from a
reference model. What is taken from them is the *idea* -- the query worth
asking is the one that separates the surviving hypotheses, never the one that
merely feels novel -- and the shortest-separating-word construction. What is
deliberately NOT taken: their teacher assumptions (membership and equivalence
oracles). There is no teacher here. The environment answers, and where it
cannot answer, the answer is UNKNOWN.

No model calls, no network, no float logarithms. Exact rational arithmetic for
information gain, contributed by `exact_information_gain_v1`.
"""
from __future__ import annotations

from collections import deque
from fractions import Fraction
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MINIMAL_EXPERIMENT_V1"
MACHINE_SCHEMA = "PROJECT_BRAIN_MINIMAL_MACHINE_V1"
ADMISSION_SCHEMA = "PROJECT_BRAIN_EXPERIMENT_ADMISSION_V1"

# A machine with more states than this is reported as unrefined rather than
# silently truncated. Chosen so that a real desktop app's view stack (hundreds
# of observable states) still fits, while a runaway observation tree does not
# consume the process.
MAX_STATES = 4096
# Search bound for a separating word, in actions. Long enough that a 6-step
# plan is expressible; short enough that the product search stays interactive.
MAX_SEPARATING_DEPTH = 64
# Largest observation tree for which every partition is enumerated, so minimality
# is PROVED rather than bounded. Bell numbers: Bell(9)=21,147, Bell(10)=115,975,
# Bell(11)=678,570. Materialising each access word's prefix chain means one probe
# at depth 10 is an 11-node tree, so the limit has to be deep enough to hold a
# real probe walk: 11 is where a full three-step wizard with re-probing lands,
# and 678,570 partitions is still a fraction of a second.
EXACT_NODE_LIMIT = 11


# --------------------------------------------------------------------------- #
# 0. the machine
# --------------------------------------------------------------------------- #

def _action_status(children, unavailable, node) -> dict[str, str]:
    """What a node says about each action: EDGE, ABSENT, or nothing at all.

    The three are different claims and merging them loses the difference:
    `back` ABSENT at step 1 and `back` EDGE at step 2 are both "a fact about
    back", and they contradict. Comparing the union of action NAMES (what this
    module did first) collapses them into one identical set and merges the two
    states -- which is precisely how a wizard's step 1 and step 2 became one
    state and the planner then proposed an action that fails.
    """
    status = {str(a): "EDGE" for a in (children.get(node) or {})}
    for act in (unavailable or {}).get(node) or ():
        status.setdefault(str(act), "ABSENT")
    return status


def _statuses_compatible(a: dict[str, str], b: dict[str, str]) -> bool:
    for action in set(a) & set(b):
        if a[action] != b[action]:
            return False
    return True


def make_machine(
    *,
    states: Sequence[int],
    start: int,
    transitions: Mapping[tuple[int, str], int],
    accepting: Sequence[int] = (),
    actions: Sequence[str] = (),
    unavailable: Mapping[int, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """A deterministic Moore machine. No names, no labels, no world facts.

    `transitions` is partial on purpose: an action that was never observed is not
    a transition, and pretending it exists would invent behaviour.
    """
    state_set = sorted({int(s) for s in states})
    if start not in state_set:
        raise ValueError("start state must be one of states")
    acts = sorted({str(a) for a in actions}) if actions else sorted(
        {str(a) for (_s, a) in transitions}
    )
    trans: dict[str, dict[str, int]] = {}
    for (s, a), t in transitions.items():
        s_i, t_i = int(s), int(t)
        if s_i not in state_set or t_i not in state_set:
            raise ValueError("transition endpoints must be declared states")
        row = trans.setdefault(str(s_i), {})
        if str(a) in row and row[str(a)] != t_i:
            raise ValueError("machine is not deterministic")
        row[str(a)] = t_i
    absent: dict[str, list[str]] = {}
    for s, names in (unavailable or {}).items():
        if int(s) not in state_set:
            raise ValueError("unavailable entry for undeclared state")
        kept = sorted({str(a) for a in names if str(a)})
        if kept:
            absent[str(int(s))] = kept
    return {
        "schema": MACHINE_SCHEMA,
        "states": state_set,
        "start": int(start),
        "actions": acts,
        "transitions": {s: dict(sorted(r.items())) for s, r in sorted(trans.items())},
        "accepting": sorted({int(s) for s in accepting}),
        # Actions KNOWN not to exist here. This is knowledge, not silence: a
        # state where `confirm` is unavailable is a different state from one
        # where it was simply never tried, and a machine that cannot say so
        # cannot answer "may I confirm now?" without guessing.
        "unavailable": absent,
        "state_count": len(state_set),
    }


def machine_digest(machine: Mapping[str, Any]) -> str:
    body = json.dumps(
        {
            "states": list(machine.get("states") or ()),
            "start": machine.get("start"),
            "transitions": machine.get("transitions") or {},
            "accepting": list(machine.get("accepting") or ()),
            "unavailable": machine.get("unavailable") or {},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + sha256(body).hexdigest()


def canonically_relabelled(machine: Mapping[str, Any]) -> dict[str, Any]:
    """Relabel states by first-reachability from the start.

    Two machines that are the same up to renaming become byte-identical, which is
    what lets a saved machine be recognised in a new environment.
    """
    start = machine.get("start")
    if start is None:
        return dict(machine)  # type: ignore[arg-type]
    order: list[int] = []
    seen: set[int] = set()
    queue = deque([int(start)])
    seen.add(int(start))
    while queue:
        s = queue.popleft()
        order.append(s)
        row = (machine.get("transitions") or {}).get(str(s)) or {}
        for a in sorted(row):
            t = int(row[a])
            if t not in seen:
                seen.add(t)
                queue.append(t)
    # states never reachable from the start are dropped: they cannot be observed,
    # so keeping them would claim knowledge the machine cannot act on.
    rename = {s: i for i, s in enumerate(order)}
    # Action names are abstracted to their order of first use, for the same
    # reason state numbers are: what transfers between environments is the
    # behaviour, and the same dial is called "tick" in one app and "turn" in the
    # next. Keeping the name would make the digest a function of vocabulary.
    action_rank: dict[str, int] = {}
    for s in order:
        row = (machine.get("transitions") or {}).get(str(s)) or {}
        for a in sorted(row):
            if str(a) not in action_rank:
                action_rank[str(a)] = len(action_rank)
    transitions: dict[tuple[int, str], int] = {}
    for s in order:
        row = (machine.get("transitions") or {}).get(str(s)) or {}
        for a, t in row.items():
            if int(t) in rename:
                transitions[(rename[s], f"a{action_rank[str(a)]}")] = rename[int(t)]
    accepting = [rename[int(s)] for s in (machine.get("accepting") or ()) if int(s) in rename]
    built = make_machine(
        states=list(range(len(order))),
        start=0,
        transitions=transitions,
        accepting=accepting,
        actions=[f"a{i}" for i in range(len(action_rank))],
    )
    # The abstraction is portable; the vocabulary is what makes it checkable.
    # Without this map the canonical machine can be compared but never PROBED,
    # because its action names no longer exist in any environment.
    built["vocabulary"] = {f"a{i}": name for name, i in action_rank.items()}
    return built


def machines_equivalent(a: Mapping[str, Any], b: Mapping[str, Any],
                        max_depth: int = MAX_SEPARATING_DEPTH) -> bool:
    """True when no word up to `max_depth` separates them.

    Strictly a bounded claim; the caller must not read it as an identity proof.
    """
    return separating_word(a, b, max_depth=max_depth) is None


# --------------------------------------------------------------------------- #
# 1. THE EXPERIMENT THAT SETTLES IT
# --------------------------------------------------------------------------- #

def separating_word(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    *,
    max_depth: int = MAX_SEPARATING_DEPTH,
) -> list[str] | None:
    """Shortest action word on which two machines disagree, or None.

    Disagreement means: one machine accepts and the other does not, OR one is
    undefined (the action is unavailable) where the other is defined. "Being
    defined" is itself a prediction -- the lesson this project already paid for
    in `evidence_demand_v1`, where skipping a probe that raised hid the only
    question that could settle the ambiguity.

    BFS over the product, so the first word found is the shortest one.
    """
    start_a, start_b = a.get("start"), b.get("start")
    if start_a is None or start_b is None:
        return None
    accept_a = {int(s) for s in (a.get("accepting") or ())}
    accept_b = {int(s) for s in (b.get("accepting") or ())}
    trans_a = a.get("transitions") or {}
    trans_b = b.get("transitions") or {}
    actions = sorted({str(x) for x in (list(a.get("actions") or ()) + list(b.get("actions") or ()))})
    if not actions:
        return None

    def accepts(machine_accept: set[int], state: int) -> bool:
        return state in machine_accept

    start_pair = (int(start_a), int(start_b))
    if accepts(accept_a, start_pair[0]) != accepts(accept_b, start_pair[1]):
        return []
    seen = {start_pair}
    queue: deque[tuple[tuple[int, int], tuple[str, ...], int]] = deque(
        [(start_pair, (), 0)]
    )
    while queue:
        (sa, sb), word, depth = queue.popleft()
        if depth >= max_depth:
            continue
        row_a = trans_a.get(str(sa))
        row_b = trans_b.get(str(sb))
        for act in actions:
            ta = None if row_a is None else row_a.get(act)
            tb = None if row_b is None else row_b.get(act)
            # defined in one and not the other is a disagreement, not a tie
            if (ta is None) != (tb is None):
                return list(word) + [act]
            if ta is None:
                continue
            ta_i, tb_i = int(ta), int(tb)
            if accepts(accept_a, ta_i) != accepts(accept_b, tb_i):
                return list(word) + [act]
            pair = (ta_i, tb_i)
            if pair not in seen:
                seen.add(pair)
                queue.append((pair, word + (act,), depth + 1))
    return None


def is_consistent(
    machine: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
    *,
    vocabulary: Mapping[str, Any] | None = None,
) -> bool:
    """Does the machine explain every observation?

    An observation is {access: [actions], action: str, observation: str}. It says:
    after this access word, taking `action` shows `observation`. Consistency is
    checked by replaying the access word from the start and comparing the
    reachable state's accepted-ness against the observation.

    `vocabulary` maps an OBSERVED action name to the name the machine uses. It is
    needed whenever the machine has been canonicalised, since canonicalisation
    deliberately forgets the words an environment happens to use.
    """
    translate = dict(vocabulary or {})
    for obs in observations:
        access = [translate.get(str(x), str(x)) for x in (obs.get("access") or ())]
        act = translate.get(str(obs.get("action") or ""), str(obs.get("action") or ""))
        want = bool(obs.get("accepting", obs.get("observation") == "ACCEPT"))
        available = bool(obs.get("available", True))
        state = int(machine.get("start"))
        ok = True
        for step in access:
            row = (machine.get("transitions") or {}).get(str(state)) or {}
            if step not in row:
                ok = False
                break
            state = int(row[step])
        if not ok:
            return False
        row = (machine.get("transitions") or {}).get(str(state)) or {}
        absent = (machine.get("unavailable") or {}).get(str(state)) or []
        if not available:
            # the observation says the action could NOT be taken; only a machine
            # that dead-ends here agrees
            if act in row:
                return False
            continue
        if act in row:
            nxt = int(row[act])
            got = nxt in {int(s) for s in (machine.get("accepting") or ())}
            if got != want:
                return False
            continue
        if act in absent:
            return False
        # Not predicted either way. Availability differs between applications --
        # the same widget is absent in one and present in another -- so silence
        # must not be read as either claim.
        continue
        got = nxt in {int(s) for s in (machine.get("accepting") or ())}
        if got != want:
            return False
    return True


def observations_consistent(
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Refuse a contradictory observation set before any machine is invented.

    Two observations that share an access word but disagree about the same action
    cannot both be true of one deterministic machine. Returning a machine anyway
    would be the silent-wrong-learning failure this project already measured: the
    mixture is not a harder problem, it is a mis-specified one, and the honest
    output is the conflict itself.
    """
    table: dict[tuple[tuple[str, ...], str], bool] = {}
    conflicts: list[dict[str, Any]] = []
    for obs in observations:
        access = tuple(str(x) for x in (obs.get("access") or ()))
        act = str(obs.get("action") or "")
        # Two facts, not one. `available` says whether the action could be taken
        # at all; `accepting` says whether the state it led to is an accepting
        # one. Conflating them -- treating "landed in a rejecting state" as
        # "action unavailable" -- turns every ordinary observation into a dead
        # end, which is how this module briefly refused every dial it was given.
        available = bool(obs.get("available", True))
        want = bool(obs.get("accepting", obs.get("observation") == "ACCEPT"))
        key = (access, act)
        if key in table and table[key] != want:
            conflicts.append({"access": list(access), "action": act})
        table[key] = want
    return {
        "schema": SCHEMA,
        "consistent": not conflicts,
        "observations": len(observations),
        "conflicts": conflicts,
        "authority": "NONE",
    }


# --------------------------------------------------------------------------- #
# 2. THE SMALLEST MACHINE THE OBSERVATIONS ADMIT
# --------------------------------------------------------------------------- #

def build_observation_tree(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Grow the prefix tree the observations describe.

    The tree, not the trace: every access word that was asked is a node, so a
    single observation at depth 5 also fixes the first five steps of the road to
    it. That is where the saving comes from -- one experiment costs one query and
    constrains every prefix of it.
    """
    children: dict[tuple[str, ...], dict[str, tuple[str, ...]]] = {}
    terminal: dict[tuple[str, ...], bool] = {}
    unavailable: dict[tuple[str, ...], set[str]] = {}
    for obs in observations:
        access = tuple(str(x) for x in (obs.get("access") or ()))
        act = str(obs.get("action") or "")
        # Two facts, not one. `available` says whether the action could be taken
        # at all; `accepting` says whether the state it led to is an accepting
        # one. Conflating them -- treating "landed in a rejecting state" as
        # "action unavailable" -- turns every ordinary observation into a dead
        # end, which is how this module briefly refused every dial it was given.
        available = bool(obs.get("available", True))
        want = bool(obs.get("accepting", obs.get("observation") == "ACCEPT"))
        # The access word IS a path, and recording the observation records every
        # step of it. Without this the tree learns that ('next','next') exists
        # but not that `next` leads there from ('next',), so the resulting
        # machine has no `next` edge out of that state and cannot replay its own
        # observations. One probe at depth k therefore fixes k transitions, not
        # one -- which is where the economy of the method actually comes from.
        for i in range(len(access)):
            prefix, step, target = access[:i], access[i], access[: i + 1]
            children.setdefault(prefix, {}).setdefault(step, target)
        if available:
            children.setdefault(access, {})[act] = access + (act,)
            terminal[access + (act,)] = want
        else:
            # An action that could not be taken is a fact ABOUT THE SOURCE STATE,
            # and it is the strongest kind: it says the state is not one where
            # that action exists. It is recorded as a dead end, never as an edge.
            # Treating it as an edge (what an earlier version did) invented a
            # transition to a state that does not exist, and the machine then
            # planned `confirm` at step 1, which fails on the real application.
            unavailable.setdefault(access, set()).add(act)
    return {
        "schema": SCHEMA + "_TREE",
        "children": {k: dict(sorted(v.items())) for k, v in sorted(children.items())},
        "terminal": {k: v for k, v in sorted(terminal.items())},
        "unavailable": {k: sorted(v) for k, v in sorted(unavailable.items())},
        "node_count": len(set(children) | set(terminal) | set(unavailable)),
    }


def minimal_consistent_machine(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Smallest deterministic machine consistent with these observations.

    Labels are + (observed accept), - (observed reject), ? (never observed).
    A ? node may be merged with either a + or a - node: merging it asserts a
    prediction nobody has tested, and that assertion is exactly what a later
    experiment refutes. A + node may never merge with a - node; that pair is a
    contradiction already reported above.

    MINIMALITY IS NP-HARD HERE, AND THIS SAYS SO.
    Merging states of a prefix tree under don't-care labels is the classic
    state-merging problem; finding the minimum is NP-hard (it is why the 2026
    literature solves it with SAT or SMT -- L#_Box at CAV 2026 encodes the search
    for a minimal separating DFA as an SMT problem). This module has no solver
    and does not pretend to one. It reports WHICH claim it has earned:

      * `PROVED_MINIMAL` -- the instance is small enough that every partition was
        enumerated, so no smaller consistent machine exists (bounded by
        EXACT_NODE_LIMIT, where Bell(n) is still cheap);
      * `GREEDY_UPPER_BOUND` -- blue-fringe merging found a consistent machine,
        and a smaller one may exist. A smaller machine is never claimed.

    The greedy pass is the standard, sound, polynomial one: merge two nodes only
    when the result stays deterministic and never merges + with -, and merge
    later nodes into earlier ones so the machine keeps its canonical order.
    """
    # An access word is a claim about how a state was REACHED. If it uses an
    # action that was never observed as available, the road to that state is not
    # in the data, and replaying it is impossible -- so nothing can be verified
    # and nothing may be asserted. Refusing here is the difference between "I
    # learned this" and "I wrote down something I cannot check".
    # AVAILABILITY, not acceptance. An earlier version read `accepting` here,
    # so a probe that succeeded but landed in a rejecting state did not count as
    # evidence that its action exists -- and the module refused observation sets
    # it could perfectly well explain.
    observed_available = {
        str(o.get("action")) for o in observations if bool(o.get("available", True))
    }
    unobserved_steps = sorted(
        {
            str(step)
            for o in observations
            for step in (o.get("access") or ())
            if str(step) not in observed_available
        }
    )
    if unobserved_steps:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__ACCESS_USES_UNOBSERVED_ACTION",
            "unobserved_steps": unobserved_steps,
            "machine": None,
            "note": (
                "observations describe states reached by actions that were never "
                "seen to be available, so no machine can be replayed against "
                "them. Probe those actions first"
            ),
            "authority": "NONE",
        }

    conflict = observations_consistent(observations)
    if not conflict["consistent"]:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__OBSERVATIONS_CONTRADICTORY",
            "conflicts": conflict["conflicts"],
            "machine": None,
            "authority": "NONE",
        }

    tree = build_observation_tree(observations)
    children = tree["children"]
    terminal = tree["terminal"]
    unavailable = tree.get("unavailable") or {}
    nodes = sorted(set(children) | set(terminal) | set(unavailable))
    if not nodes:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NO_OBSERVATIONS",
            "machine": None,
            "authority": "NONE",
        }
    if len(nodes) > MAX_STATES:
        return {
            "schema": SCHEMA,
            "status": "UNREFINED__OBSERVATION_TREE_TOO_LARGE",
            "node_count": len(nodes),
            "limit": MAX_STATES,
            "machine": None,
            "authority": "NONE",
        }

    actions = sorted(
        {a for row in children.values() for a in row}
        | {a for acts in unavailable.values() for a in acts}
    )
    # Nodes reached as a target are "observed". A node whose only fact is that an
    # action was unavailable is a dead end: it exists as a state, but nothing may
    # be asserted about what it accepts.
    label: dict[tuple[str, ...], str] = {
        n: ("+" if terminal[n] else "-") for n in terminal
    }

    # Only the exhaustive search builds machines here.
    #
    # Three successive attempts at a polynomial greedy merge were each unsound in
    # a different direction -- one collapsed a 3-state dial to 1 state, one merged
    # step 1 with step 2 of a wizard and then predicted an action that fails, one
    # over-merged 76 observations to a single state. Each was caught by a check,
    # and each fix revealed the next hole. A merging heuristic that must be
    # verified against the exhaustive answer is not a shortcut, it is a second
    # implementation with no reason to exist.
    #
    # So: exhaustive when the observation tree is small enough to enumerate, and
    # an honest refusal when it is not. The refusal names the limit rather than
    # guessing, which is the behaviour every other module in this tree already
    # follows.
    if len(nodes) > EXACT_NODE_LIMIT:
        return {
            "schema": SCHEMA,
            "status": "UNREFINED__EXHAUSTIVE_LIMIT",
            "node_count": len(nodes),
            "limit": EXACT_NODE_LIMIT,
            "machine": None,
            "note": (
                "the observation tree has more nodes than the exhaustive search "
                "enumerates, so no minimality claim is made and no machine is "
                "returned. Fewer, better-chosen probes, or a SAT encoding, is "
                "what raises this limit"
            ),
            "authority": "NONE",
        }
    best_partition = _minimum_partition(nodes, children, label, unavailable)
    optimality = "PROVED_MINIMAL" if best_partition is not None else "NONE"
    if best_partition is None:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NO_CONSISTENT_PARTITION",
            "node_count": len(nodes),
            "machine": None,
            "authority": "NONE",
        }

    accepting_nodes = {n for n, lab in label.items() if lab == '+'}
    machine = _machine_from_partition(
        best_partition, nodes, children, actions, accepting_nodes, unavailable
    )
    consistent = is_consistent(machine, observations)
    unobserved = sorted(
        {a for n in nodes for a in actions if a not in (children.get(n) or {})}
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__MINIMAL_MACHINE" if consistent else "INTERNAL__MACHINE_REJECTED",
        "machine": machine,
        "machine_digest": machine_digest(machine),
        "state_count": machine["state_count"],
        "observation_count": len(observations),
        "tree_node_count": len(nodes),
        "optimality": optimality,
        # what the observations do NOT determine: actions never taken from a
        # reachable node. These are the residual questions, named.
        "unresolved_actions": unobserved,
        "claim": (
            "SMALLEST_MACHINE_CONSISTENT_WITH_THESE_OBSERVATIONS"
            if optimality == "PROVED_MINIMAL"
            else "A_MACHINE_CONSISTENT_WITH_THESE_OBSERVATIONS"
        ),
        "not_claimed": "THE_MACHINE",
        "authority": "NONE",
    }


def _compatible(a: str, b: str) -> bool:
    """+ and - contradict; ? agrees with anything (it is a prediction, not a fact)."""
    return not ((a == "+" and b == "-") or (a == "-" and b == "+"))


def _merge_greedily(nodes, children, label, unavailable=None):
    """Blue-fringe merging: sound, polynomial, not proven minimum.

    Two rules, and both are load-bearing:

    * A block's label is a PURE FUNCTION of its members, recomputed on demand.
      Caching it and patching the cache after a merge loses the + / - distinction
      and then every block looks mergeable -- which is how a greedy pass silently
      collapses a 3-state dial into 1 state.
    * Every candidate merge is verified against ALL members of both blocks, not
      against a representative, because two blocks can agree on what their
      representatives do and disagree on a third member.
    """
    unavailable = unavailable or {}
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def label_of(root):
        known = {label.get(n, "?") for n in nodes if find(n) == root} - {"?"}
        return known.pop() if known else "?"

    def rows_compatible(ra, rb) -> bool:
        """A merged state must not both have and lack the same action.

        Presence is knowledge, not absence: `back` unavailable at step 1 is a
        fact about step 1. If a block would contain one node with a `back` edge
        and one without, the merged state's row is undefined -- not "maybe".
        """
        members_a = [n for n in nodes if find(n) == ra]
        members_b = [n for n in nodes if find(n) == rb]
        for x in members_a:
            for y in members_b:
                if not _statuses_compatible(
                    _action_status(children, unavailable, x),
                    _action_status(children, unavailable, y),
                ):
                    return False
        return True

    def attempt(a, b) -> bool:
        ra, rb = find(a), find(b)
        if ra == rb or not _compatible(label_of(ra), label_of(rb)):
            return False
        if not rows_compatible(ra, rb):
            return False
        snapshot = dict(parent)
        lo = (ra, rb) if ra < rb else (rb, ra)
        parent[lo[1]] = lo[0]
        if _close_under_determinism(nodes, children, find, parent, label_of):
            return True
        parent.clear()
        parent.update(snapshot)
        return False

    ordered = sorted(nodes, key=lambda n: (len(n), n))
    for i, a in enumerate(ordered):
        for b in reversed(ordered[:i]):
            if find(a) != find(b):
                attempt(b, a)
    return {n: find(n) for n in nodes}


def _close_under_determinism(nodes, children, find, parent, label_of) -> bool:
    """After a merge, force same-action targets together; refuse on contradiction.

    Determinism demands it: one state cannot have an action leading to two states.
    So the closure is not optional -- either the targets merge too, or the
    original merge was illegal.

    The comparison is between a node's OWN row and every row of the block it is
    being merged into. Comparing children's rows instead (as an earlier version
    did) misses the commonest case of all: two states whose rows differ by an
    action being *absent*. Step 1 of a wizard has no `back` edge and step 2 does;
    both nodes have empty children, so nothing earlier in this function noticed,
    the states merged, and the machine then predicted `back` at step 1 -- a plan
    that fails on the real app.
    """
    changed = True
    while changed:
        changed = False
        for n in nodes:
            row = children.get(n) or {}
            for act, t in row.items():
                src = find(n)
                for other in nodes:
                    if find(other) != src:
                        continue
                    otherrow = children.get(other) or {}
                    if act not in otherrow:
                        continue
                    t1, t2 = find(t), find(otherrow[act])
                    if t1 == t2:
                        continue
                    if not _compatible(label_of(t1), label_of(t2)):
                        return False
                    lo = (t1, t2) if t1 < t2 else (t2, t1)
                    parent[lo[1]] = lo[0]
                    changed = True
                    break
                if changed:
                    break
            if changed:
                break
    return True


def _minimum_partition(nodes, children, label, unavailable=None):
    """Fewest blocks that still describe a machine, found by bounded DFS.

    Lower bound, which is what makes this exact AND fast: nodes whose labels
    contradict (+ with -) can never share a block, so every distinct label class
    needs its own block at minimum. The search therefore starts at that bound and
    only explores merge sets that could do better -- in practice it proves
    optimality after a handful of attempts instead of walking all Bell(n).

    Every candidate is checked by `legal`, which requires both (a) pairwise
    compatibility of labels and action status, and (b) determinism: an action
    leaving a block must reach exactly one block.

    The earlier version enumerated every restricted-growth string and validated
    finished partitions, which cost 2.7s at n=11. Enumeration order and pruning
    changed; the answer did not, and the test that pins the direction between
    this and any heuristic still holds.
    """
    unavailable = unavailable or {}
    n = len(nodes)
    if n == 0:
        return {}

    status = {node: _action_status(children, unavailable, node) for node in nodes}
    labels = [label.get(node, "?") for node in nodes]
    index_of = {node: i for i, node in enumerate(nodes)}

    def compatible(i: int, j: int) -> bool:
        a, b = labels[i], labels[j]
        if a != "?" and b != "?" and a != b:
            return False
        return _statuses_compatible(status[nodes[i]], status[nodes[j]])

    def legal(block_of: dict[int, int]) -> bool:
        blocks: dict[int, list[int]] = {}
        for idx, b in block_of.items():
            blocks.setdefault(b, []).append(idx)
        for members in blocks.values():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    if not compatible(members[i], members[j]):
                        return False
        for members in blocks.values():
            targets: dict[str, int] = {}
            for idx in members:
                for act, tgt in (children.get(nodes[idx]) or {}).items():
                    tb = block_of.get(index_of.get(tgt, -1))
                    if tb is None:
                        continue
                    if act in targets and targets[act] != tb:
                        return False
                    targets[act] = tb
        return True

    # Lower bound: one block per distinct known label (+ / -). Unknown nodes can
    # join either, so they add nothing to the bound.
    known = {lab for lab in labels if lab != "?"}
    lower = max(1, len(known))

    # Upper bound: pairwise-merging where legal, which is cheap and usually lands
    # on or near the optimum.
    best = {i: i for i in range(n)}
    improved = True
    while improved:
        improved = False
        for i in range(n):
            for j in range(i + 1, n):
                if best[i] == best[j]:
                    continue
                trial = dict(best)
                old, new = trial[j], trial[i]
                for k in trial:
                    if trial[k] == old:
                        trial[k] = new
                if legal(trial) and len(set(trial.values())) < len(set(best.values())):
                    best = trial
                    improved = True
                    break
            if improved:
                break
    best_size = len(set(best.values()))
    if best_size <= lower:
        return {nodes[i]: best[i] for i in range(n)}

    # Depth-first refinement: try to reach `target` blocks, from the bound upward.
    # First target that succeeds is optimal, because no partition with fewer
    # blocks can exist by the bound.
    def canonical(assignment: list[int]) -> dict[int, int]:
        remap: dict[int, int] = {}
        out = {}
        for idx, b in enumerate(assignment):
            if b not in remap:
                remap[b] = len(remap)
            out[idx] = remap[b]
        return out

    def search(target: int):
        assignment = list(range(n))

        def dfs(position: int, used: int):
            if n - position + used < target:
                return None
            if position == n:
                if used == target and legal(canonical(assignment)):
                    return canonical(assignment)
                return None
            for block in range(min(used + 1, target)):
                # quick reject against every member already in this block
                if any(
                    assignment[k] == block and not compatible(k, position)
                    for k in range(position)
                ):
                    continue
                assignment[position] = block
                result = dfs(position + 1, max(used, block + 1))
                if result is not None:
                    return result
            return None

        return dfs(0, 0)

    for target in range(lower, best_size):
        found = search(target)
        if found is not None:
            return {nodes[i]: found[i] for i in range(n)}
    return {nodes[i]: best[i] for i in range(n)}


def _rgs(n: int):
    """Every restricted growth string of length n (one per set partition)."""
    if n == 0:
        yield tuple()
        return
    a = [0] * n
    while True:
        yield tuple(a)
        i = n - 1
        while i >= 0 and a[i] == (max(a[:i]) + 1 if i else 0):
            i -= 1
        if i < 0:
            return
        a[i] += 1
        for j in range(i + 1, n):
            a[j] = 0


def _machine_from_partition(block_of, nodes, children, actions, accepting_nodes, unavailable=None):
    """Build the machine from a partition, with stable block numbering.

    Numbering is by the block's smallest member rather than by first reachability.
    Reachability ordering drops any block the start cannot reach, so a state the
    partition proved exists would vanish from the machine and its transitions
    would be silently redistributed -- the machine would still be consistent on
    the recorded observations, and wrong everywhere else.
    """
    ordered_blocks = sorted(set(block_of.values()), key=lambda b: min(
        nodes[i] for i in range(len(nodes)) if block_of[nodes[i]] == b
    ))
    rename = {b: i for i, b in enumerate(ordered_blocks)}
    start_state = rename[block_of[()]]
    transitions: dict[tuple[int, str], int] = {}
    for n in nodes:
        src = rename[block_of[n]]
        for a, t in sorted((children.get(n) or {}).items()):
            dst = rename.get(block_of.get(t))
            if dst is not None:
                transitions[(src, a)] = dst
    accepting = sorted(
        {rename[block_of[n]] for n in accepting_nodes if block_of[n] in rename}
    )
    absent: dict[int, set[str]] = {}
    for n in nodes:
        src = rename[block_of[n]]
        for act in unavailable.get(n) or ():
            absent.setdefault(src, set()).add(act)
    return make_machine(
        states=list(range(len(ordered_blocks))),
        start=start_state,
        transitions=transitions,
        accepting=accepting,
        actions=actions,
        unavailable={k: sorted(v) for k, v in absent.items()},
    )


# --------------------------------------------------------------------------- #
# 3. THE QUESTION WORTH ASKING
# --------------------------------------------------------------------------- #

def rank_experiments(
    machine: Mapping[str, Any],
    *,
    hypotheses: Sequence[Mapping[str, Any]] = (),
    max_depth: int = 3,
) -> dict[str, Any]:
    """Rank next experiments by how many hypotheses each would eliminate.

    Exact and cheap: an experiment's value here is the number of candidate
    machines it separates from the current one, which is a count, not an entropy
    estimate. Where a probability distribution over hypotheses is available the
    caller should use `exact_information_gain_v1` instead and may pass it in;
    this function does not invent priors it does not have.
    """
    if not hypotheses:
        return {
            "schema": SCHEMA,
            "status": "NO_RIVALS",
            "queries": [],
            "note": (
                "no hypothesis competes with the current machine, so no experiment "
                "removes anything. This is the honest plateau, not a solved problem: "
                "it means the rivals were never enumerated."
            ),
            "authority": "NONE",
        }
    actions = [str(a) for a in (machine.get("actions") or ())]
    if not actions:
        return {"schema": SCHEMA, "status": "NO_ACTIONS", "queries": [], "authority": "NONE"}

    scored: list[dict[str, Any]] = []
    for depth in range(1, max_depth + 1):
        for word in _words(actions, depth):
            eliminated = 0
            witnesses = 0
            for rival in hypotheses:
                wit = separating_word(machine, rival, max_depth=depth)
                if wit is None:
                    continue
                witnesses += 1
                prefix = list(word)
                if wit[: len(prefix)] == prefix:
                    eliminated += 1
            scored.append(
                {
                    "word": list(word),
                    "eliminates": eliminated,
                    "of": len(hypotheses),
                }
            )
    scored.sort(key=lambda r: (-r["eliminates"], len(r["word"]), r["word"]))
    best = scored[0] if scored else None
    return {
        "schema": SCHEMA,
        "status": "QUESTION" if best and best["eliminates"] else "PLATEAU",
        "queries": scored[:5],
        "best": best,
        "note": (
            "each word is an action sequence; running it and reading the result "
            "removes the listed number of competing machines"
        ),
        "authority": "NONE",
    }


def _words(actions: Sequence[str], depth: int) -> Iterable[tuple[str, ...]]:
    if depth <= 0:
        yield ()
        return
    for head in actions:
        for tail in _words(actions, depth - 1):
            yield (head,) + tail


# --------------------------------------------------------------------------- #
# 4. SAVING WHAT GENERALISES
# --------------------------------------------------------------------------- #

def learnable_unit(
    *,
    scope: str,
    observations: Sequence[Mapping[str, Any]],
    rivals: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """What may be saved from this experience, and on what condition.

    The saved row is deliberately not the trajectory:
      * `machine` is the smallest machine explaining the observations;
      * `precondition` is what must be true of a NEW environment for that machine
        to apply -- the start must be reachable-equivalent, expressed as the
        canonical digest of the machine the new environment exhibits;
      * `rivals_remaining` is how many competing machines this experience did
        not rule out. A row with rivals_remaining > 0 is a hypothesis, and it
        says so; it is not promoted by being stored.

    Nothing is written by this function. It returns the unit; persistence remains
    the store's decision, behind the admission gate that already exists.
    """
    built = minimal_consistent_machine(observations)
    if built.get("machine") is None:
        return {
            "schema": SCHEMA,
            "status": built.get("status"),
            "learnable_unit": None,
            "authority": "NONE",
        }
    machine = built["machine"]
    canonical = canonically_relabelled(machine)
    remaining = 0
    for rival in rivals:
        if separating_word(canonical, canonically_relabelled(rival)) is not None:
            remaining += 1
    return {
        "schema": SCHEMA,
        "status": "LEARNABLE_UNIT",
        "learnable_unit": {
            "schema": MACHINE_SCHEMA,
            "scope": scope,
            "machine": canonical,
            # observed action name -> canonical name, so the row can be re-probed
            "vocabulary": dict(canonical.get("vocabulary") or {}),
            "machine_digest": machine_digest(canonical),
            "observations_used": len(observations),
            "tree_node_count": built["tree_node_count"],
            "state_count": canonical["state_count"],
            "unresolved_actions": built.get("unresolved_actions") or [],
            "rivals_remaining": remaining,
            "status": "HYPOTHESIS" if remaining else "UNRIVALLED_HERE",
            "claim": "SMALLEST_MACHINE_CONSISTENT_WITH_THESE_OBSERVATIONS",
            "not_claimed": "THE_MACHINE",
        },
        "authority": "NONE",
    }


# --------------------------------------------------------------------------- #
# 5. HOW MUCH WAS ACTUALLY SAVED
# --------------------------------------------------------------------------- #

def compression_report(
    *,
    observations: Sequence[Mapping[str, Any]],
    machine: Mapping[str, Any],
) -> dict[str, Any]:
    """Bits saved by storing the machine instead of the observations.

    Exact rational arithmetic on counts: the trajectory needs one symbol per
    observation; the machine needs log2(state_count) state labels plus its
    transition table. Reported only when the machine is actually smaller, since
    a "compression" that saves nothing must not be presented as a saving.
    """
    obs_count = len(observations)
    states = int(machine.get("state_count") or 0)
    if obs_count == 0 or states == 0:
        return {"schema": SCHEMA, "status": "NOTHING_TO_COMPRESS", "authority": "NONE"}
    if states >= obs_count:
        return {
            "schema": SCHEMA,
            "status": "NO_COMPRESSION",
            "observations": obs_count,
            "states": states,
            "note": "the machine is not smaller than the data, so nothing was saved",
            "authority": "NONE",
        }
    saved = Fraction(obs_count - states, obs_count)
    return {
        "schema": SCHEMA,
        "status": "COMPRESSED",
        "observations": obs_count,
        "states": states,
        "saved_fraction": f"{saved.numerator}/{saved.denominator}",
        "authority": "NONE",
    }


# --------------------------------------------------------------------------- #
# 6. ADMISSION: MAY THIS BECOME PERMANENT?
# --------------------------------------------------------------------------- #

def admit_learnable_unit(
    unit: Mapping[str, Any],
    *,
    held_out: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The store's question, answered by execution on environments it never saw.

    An admission needs all three, and the reasons are named separately because
    they fail separately:
      * PREDICTED   -- the machine explains every observation recorded here;
      * GENERALISED -- run against held-out observations it predicts correctly;
      * NO_HARM     -- on held-out data where it is undefined, it refuses rather
                       than guessing (an undefined action is not a prediction).
    """
    machine = unit.get("machine")
    if not isinstance(machine, Mapping):
        return {"schema": ADMISSION_SCHEMA, "verdict": "REFUSED__NO_MACHINE", "authority": "NONE"}
    vocabulary = unit.get("vocabulary")
    action_map = (
        {observed: canonical for canonical, observed in vocabulary.items()}
        if isinstance(vocabulary, Mapping)
        else None
    )
    predicted = is_consistent(machine, held_out, vocabulary=action_map)
    # Generalisation is a claim about the machine predicting observations it did
    # not learn from, so the check is on the SET. Checking each observation in
    # isolation made one correct prediction and many undefined ones look like
    # success, which is not what "generalised" means.
    generalised = bool(held_out) and is_consistent(machine, held_out, vocabulary=action_map)
    no_harm = True
    for obs in held_out:
        access = [
            (action_map or {}).get(str(x), str(x)) for x in (obs.get("access") or ())
        ]
        act = (action_map or {}).get(str(obs.get("action") or ""), str(obs.get("action") or ""))
        state = int(machine.get("start"))
        reachable = True
        for step in access:
            row = (machine.get("transitions") or {}).get(str(state)) or {}
            if step not in row:
                reachable = False
                break
            state = int(row[step])
        if not reachable:
            no_harm = False
            continue
        row = (machine.get("transitions") or {}).get(str(state)) or {}
        if act not in row:
            # undefined: refusing is correct behaviour, but it is not evidence of
            # generalisation either way
            continue
        want = bool(obs.get("accepting", obs.get("observation") == "ACCEPT"))
        got = int(row[act]) in {int(s) for s in (machine.get("accepting") or ())}
        if got != want:
            no_harm = False
    verdict = "ADMIT" if (predicted and generalised and no_harm) else "REFUSE"
    reasons = []
    if not predicted:
        reasons.append("DOES_NOT_EXPLAIN_RECORDED_OBSERVATIONS")
    if not generalised:
        reasons.append("NO_HELD_OUT_PREDICTION_CONFIRMED")
    if not no_harm:
        reasons.append("CONTRADICTED_ON_HELD_OUT")
    return {
        "schema": ADMISSION_SCHEMA,
        "verdict": verdict,
        "reasons": reasons,
        "held_out_count": len(held_out),
        "authority": "NONE",
    }
