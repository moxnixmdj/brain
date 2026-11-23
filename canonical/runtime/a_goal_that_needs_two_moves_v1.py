"""A goal that needs TWO moves, planned over the CLASS of each move.

THE BOTTLENECK THIS ANSWERS
---------------------------
Round 4 shipped a join that answers *which door does this ONE move*. Its own receipt
names the wall: a goal needing several moves IN ORDER is unanswered. The obvious plan
-- call the search the project already has -- is wrong for a reason that is measured,
not stylistic, and this module exists because that reason was confirmed by running it.

WHY THE EXISTING PLANNER CANNOT BE USED AS IS
---------------------------------------------
`capability_planner.plan_capabilities` is a correct A* over precondition/effect pairs,
and twenty modules in this tree already use it. But its transition is ADD-ONLY:

    new_facts = frozenset(set(facts) | set(cap.provides))

No capability can TAKE ANYTHING AWAY. On the file tree that is not a detail, because
the moves that matter most are exactly the ones that destroy things. Handed

    initial  plain:a
    gzip     requires plain:a  provides archived:a
    cp       requires plain:a  provides copy:a
    goal      archived:a AND copy:a

it returns `['gzip', 'cp']` -- and running that for real fails, because `gzip` consumed
`in.txt` and `cp` then has nothing to copy:

    gzip -q a.txt      -> a.txt GONE
    cp a.txt copy.txt  -> cp: cannot stat 'a.txt': No such file or directory

The plan is not merely suboptimal; it is impossible. A planner without a delete list
cannot see that a step destroyed a precondition of a later step.

The other planner in the tree, `consequence_table_v1.learn_and_solve`, is correct and
has no such trouble -- it plans over whole states. It is also forced to PROBE, and
reports the honest consequence: with zero prior experience it solves 0 of 52. Whole
states do not transfer to a world that has different filenames in it, which is the
user's standing objection ("environments always change") stated as a measurement.

So neither existing piece does the round-5 job, and the gap between them is this file.

THE UNIT: A CLASS OF MOVE, NOT A STATE AND NOT A TOOL
----------------------------------------------------
Round 4 already established the right unit for ONE move: a relation signature over the
project's five relations plus LOT, measured by running the door. That row contains no
path, no argv, no tool name as a lookup key, and no example -- it is a class.

The omission that made it insufficient for SEQUENCES: the signature is a *delta*, and a
delta does not say what a state was. `{'IDENT': CHANGED}` is true of `mv in.txt x` and
of `mv y in.txt`. Sequencing deltas is therefore not well defined -- the first move's
result is what the second move's precondition must be checked against.

What makes sequencing possible without giving up the class unit is that each measured
signature carries its own PRE-STATE, as a value: `LOT: RETAINED` says the content can
still be read afterwards. So the signature is a small set of conditions on a state, and
it is a class because the condition is about *some* content, never a named one.

    rm        LOT PARTIAL, CARD DECREASED   -> needs readable content; loses ONE of them
    cp        CARD INCREASED                -> needs readable content; adds a name
    mv        IDENT CHANGED, LOT RETAINED   -> needs readable content; keeps the count
    gzip      CARD SAME, LOT RETAINED       -> needs readable content; keeps it one layer down

Every one of those requires "there is readable content", and none of them names it.

THE TRANSITION IS DERIVED, NOT FITTED
-------------------------------------
The state a plan carries is a relation VECTOR, not a file list:

    counts   how many names           (CARD)
    idents   how many distinct names  (IDENT)
    payable  how many contents a reader can recover (LOT)

Each move's effect on the vector is computed from its measured signature by one rule
per relation, and every rule is a statement about the relation:

    LOT LOST     -> every readable content is destroyed   payable := 0
    LOT PARTIAL  -> exactly one is destroyed              payable -= 1
    CARD INCREASED / DECREASED                        counts  += / -= 1
    IDENT CHANGED with CARD SAME                      idents  unchanged
    IDENT CHANGED with CARD INCREASED                 idents  += 1

A relation that does not appear in the signature did not move, so it does not change --
`moved()` already drops SAME, and the planner reads only what moved. Nothing here is a
coefficient fitted to data; each line can be checked against what the relation means.

THE GOAL IS A RELATION VECTOR TOO, SO NOTHING HAS TO BE OBSERVED
----------------------------------------------------------------
`perfect_algorithm_v1.plan` returns `REFUSED__GOAL_NEVER_OBSERVED` because reaching a
goal state requires recognising it, and recognising it requires having stood in it. A
goal stated as a vector needs no such thing: "hold at least one of content you can
read, under two names, having destroyed none" is checkable in any world, and so is the
state a plan predicts. That is what makes a 2-move answer possible at all -- the plan
is refuted by its own predictions before anything is executed.

WHAT IS REFUSED, AND WHY THAT IS THE POINT
------------------------------------------
An unreachable goal is refused with the fact that is missing, not with a plausible
sequence. `rm` then `cp` cannot retain a content: after the delete there is nothing to
copy, and the search says `UNREACHABLE` and names `PAYABLE >= 1` as what no remaining
move can provide. Refusing is the honest output; a planner that always returns a plan
has not been tested.

ZERO MODEL CALLS, ZERO PARAMETERS
---------------------------------
No network, no weights, no model, $0. The only numbers are the relation counts read off
a measured signature by the rules above. The search is a breadth-first enumeration over
unit-cost moves, so the first plan found is a shortest one, which is what "the fewest
moves that does it" means.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Mapping, Sequence

from canonical.runtime.goal_to_door_v1 import (
    CARD,
    IDENT,
    LOT,
    LOST,
    PARTIAL,
    RETAINED,
    INCREASED,
    DECREASED,
    SAME,
    CHANGED,
)

SCHEMA = "PROJECT_BRAIN_A_GOAL_THAT_NEEDS_TWO_MOVES_V1"

#: The four dimensions a plan carries, and why each is one of them.
#:
#: NAMES     (CARD)     how many names the world holds
#: READABLE             how many of those names a reader can recover content from
#: CONTENTS             how many DISTINCT contents are recoverable
#: REMOVED              how many times the name count has FALLEN
#:
#: READABLE exists because CARD alone cannot separate a copy from an empty file:
#: `cp in.txt out.txt` and `touch out.txt` both raise CARD by one, and only one of
#: them leaves a readable second name. That is not a hypothetical -- it is the first
#: thing that broke this model, and it is why CARD is not the state.
#:
#: CONTENTS exists because a copy does not create content: after `cp` there are two
#: readable names holding ONE distinct content, and a goal stated over READABLE alone
#: would think the world gained a content.
#:
#: REMOVED exists because a goal may be about HISTORY, not just the final state --
#: "clean up the original but keep the content" is exactly that goal, and without
#: this dimension `cp x y; rm x` and the starting world are indistinguishable.
NAMES, READABLE, CONTENTS, REMOVED = "NAMES", "READABLE", "CONTENTS", "REMOVED"
DIMENSIONS = (NAMES, READABLE, CONTENTS, REMOVED)

SOLVED = "SOLVED__A_SEQUENCE_REACHES_THE_GOAL"
UNREACHABLE = "REFUSED__NO_SEQUENCE_OF_MEASURED_MOVES_REACHES_THE_GOAL"
UNKNOWN_MOVE = "REFUSED__A_MOVE_WITH_NO_MEASURED_EFFECT_WAS_OFFERED"


class Move:
    """One class of move: what it needs of a world, and what it leaves behind."""

    __slots__ = ("id", "tool", "signature", "_needs", "_delta", "_absolute")

    def __init__(self, id: str, tool: str, signature: Mapping[str, str]) -> None:
        self.id = str(id)
        self.tool = str(tool)
        self.signature = dict(signature)
        self._needs, self._delta, self._absolute = _from_signature(self.signature)

    def requires(self, state: Mapping[str, int]) -> bool:
        return all(state[name] >= 1 for name in self._needs)

    def apply(self, state: Mapping[str, int]) -> dict[str, int]:
        if not self.requires(state):
            raise ValueError("MOVE_APPLIED_TO_A_WORLD_IT_REQUIRES_NOTHING_OF")
        out = {name: state[name] + self._delta.get(name, 0) for name in DIMENSIONS}
        out.update(self._absolute)
        for name in DIMENSIONS:
            out[name] = max(0, out[name])
        # a copy cannot be readable if there is no name to hold it, and there cannot
        # be more distinct contents than there are readable names
        out[READABLE] = min(out[READABLE], out[NAMES])
        out[CONTENTS] = min(out[CONTENTS], out[READABLE])
        return out

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "tool": self.tool, "signature": dict(self.signature),
                "needs": sorted(self._needs),
                "delta": {k: self._delta[k] for k in sorted(self._delta)},
                "sets": {k: self._absolute[k] for k in sorted(self._absolute)}}

    def __repr__(self) -> str:  # pragma: no cover
        return f"Move({self.id!r}, {self.signature!r})"


def _from_signature(signature: Mapping[str, str]):
    """(needs, delta, absolute) for one move, from the relations its signature moved.

    Needs the FULL six-relation signature, not the `moved()` subset. The subset was
    the first input and it silently deleted the precondition: `mv`'s moved subset is
    `{IDENT, PAIRING}`, because `LOT: RETAINED` counts as unchanged, so a planner fed
    the subset believed a rename could be applied to a world with nothing in it.
    `LOT: RETAINED` is noise when CHOOSING a door and a precondition when SEQUENCING
    one -- the same value, two jobs, and only the second needs it kept.
    """
    if LOT not in signature:
        raise ValueError("A_SIGNATURE_WITHOUT_LOT_IS_THE_MOVED_SUBSET_PASS_THE_FULL_ONE")

    lot = signature.get(LOT)
    card = signature.get(CARD)
    ident = signature.get(IDENT)
    needs: set[str] = set()
    delta: dict[str, int] = {}
    absolute: dict[str, int] = {}

    if lot == RETAINED:
        # content survived the step, so content existed going in. This one line is
        # what makes `cp`, `mv` and `gzip` have a precondition at all.
        needs.add(READABLE)
    elif lot in (LOST, PARTIAL):
        needs.add(READABLE)
        delta[READABLE] = -1
        if lot == LOST:
            # LOST is defined as "nothing readable survives", which is a statement
            # about the RESULT rather than about how much was destroyed, so it is a
            # set rather than a decrement. Using a decrement made a LOST move in a
            # three-content world leave two contents behind, which is not LOST.
            absolute[READABLE] = 0
        # CONTENTS is deliberately NOT touched here. It is clamped to READABLE in
        # `apply`, which derives the right answer in both cases without knowing the
        # multiplicity a signature cannot express: deleting one of two readable names
        # leaves CONTENTS where it was, and deleting the last one takes it to zero
        # because there is no longer a readable name for it to live in. Subtracting
        # here instead made `cp a b; rm a` report zero contents while the content was
        # sitting readable in `b`.

    if card == INCREASED:
        delta[NAMES] = 1
        delta[READABLE] = 1
        # CONTENTS deliberately unchanged: a copy adds a NAME holding a content that
        # was already there. Known falsifier, tested: an operation that raises CARD
        # while writing nothing readable (`touch`) satisfies this signature and is
        # therefore mis-modelled as a copy. No signature over these six relations can
        # separate them -- `touch` and `cp` both leave LOT RETAINED -- so the limit is
        # stated rather than papered over with a tool name.
    elif card == DECREASED:
        # NAMES and REMOVED only. The loss of READABLE and CONTENTS for a delete is
        # already stated by its LOT value, and taking it twice was a real bug: `rm`
        # came out with READABLE -2 in a one-name world, so a COPY followed by a
        # DELETE looked like it had destroyed everything. One relation owns one
        # dimension: LOT owns readability, CARD owns the name count.
        delta[NAMES] = -1
        delta[REMOVED] = 1
    elif card == SAME and ident == CHANGED:
        # a rename or a repack: the number of names did not move. `mv` removes a name
        # and creates one, and it is NOT counted as a removal -- REMOVED counts the
        # times the name COUNT fell, which is the fact that "a delete happened".
        delta[NAMES] = 0

    if not needs and not delta and not absolute:
        raise ValueError("SIGNATURE_MOVED_NOTHING_SO_IT_IS_NOT_A_MOVE")
    return frozenset(needs), delta, absolute


def move_of(row: Mapping[str, Any], *, signature: Mapping[str, str] | None = None) -> Move:
    """A `Move` from a measured row: a census row, or a round-4 saved row."""
    sig = signature if signature is not None else row.get("signature")
    if not isinstance(sig, Mapping):
        raise ValueError("A_ROW_WITHOUT_A_SIGNATURE_IS_NOT_A_MEASURED_MOVE")
    tool = str(row.get("tool") or row.get("machine") or "")
    rid = str(row.get("id") or row.get("door")
              or f"{tool}:{'+'.join(sorted(sig))}")
    return Move(rid, tool, sig)


class Goal:
    """Conditions on the four dimensions, checkable in a world nobody has observed."""

    __slots__ = ("at_least", "at_most", "desc")

    def __init__(self, *, at_least: Mapping[str, int] | None = None,
                 at_most: Mapping[str, int] | None = None, desc: str = "") -> None:
        unknown = set(at_least or {}) | set(at_most or {})
        unknown -= set(DIMENSIONS)
        if unknown:
            raise ValueError(f"GOAL_NAMES_A_DIMENSION_THE_STATE_DOES_NOT_HAVE:{sorted(unknown)}")
        self.at_least = {k: max(0, int(v)) for k, v in (at_least or {}).items()}
        self.at_most = {k: int(v) for k, v in (at_most or {}).items()}
        self.desc = desc

    def holds(self, state: Mapping[str, int]) -> bool:
        return not self.unmet(state)

    def unmet(self, state: Mapping[str, int]) -> list[str]:
        out = []
        for name in DIMENSIONS:
            if name in self.at_least and state[name] < self.at_least[name]:
                out.append(f"{name} >= {self.at_least[name]} (is {state[name]})")
            if name in self.at_most and state[name] > self.at_most[name]:
                out.append(f"{name} <= {self.at_most[name]} (is {state[name]})")
        return out

    def as_dict(self) -> dict[str, Any]:
        return {"desc": self.desc, "at_least": dict(self.at_least),
                "at_most": dict(self.at_most)}


def world(*, names: int, readable: int | None = None, contents: int | None = None,
          removed: int = 0) -> dict[str, int]:
    """The four dimensions of a world, with the invariants applied.

    `readable` defaults to `names` because the ordinary world is one where every name
    can be read. It is a separate argument because the interesting worlds are the ones
    where that is false.
    """
    n = max(0, int(names))
    r = n if readable is None else min(n, max(0, int(readable)))
    c = r if contents is None else min(r, max(0, int(contents)))
    return {NAMES: n, READABLE: r, CONTENTS: c, REMOVED: max(0, int(removed))}


class Refusal(Exception):
    """No plan. Carries the fact that is missing, because that is the useful part."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}")


def _key(state: Mapping[str, int]) -> tuple[int, ...]:
    return tuple(state[name] for name in DIMENSIONS)


def plan(start: Mapping[str, int], goal: Goal, moves: Sequence[Move],
         *, max_depth: int = 8) -> list[str]:
    """The fewest moves that reach the goal. Or a refusal naming what is missing.

    Breadth-first over unit-cost moves, so the first plan found is a shortest one.
    Depth is bounded: an unbounded search for an unreachable goal is a hang, not an
    answer.
    """
    if not moves:
        raise Refusal(UNKNOWN_MOVE, "no measured move was offered")
    if len({m.id for m in moves}) != len(moves):
        raise Refusal(UNKNOWN_MOVE, "two moves share an id, so a plan would be ambiguous")
    if goal.holds(start):
        return []

    seen = {_key(start)}
    queue: deque[tuple[dict[str, int], list[str]]] = deque([(dict(start), [])])
    closest, closest_gap = dict(start), len(goal.unmet(start))
    while queue:
        state, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for move in moves:
            if not move.requires(state):
                continue
            nxt = move.apply(state)
            k = _key(nxt)
            if k in seen:
                continue
            seen.add(k)
            found = [*path, move.id]
            if goal.holds(nxt):
                return found
            gap = len(goal.unmet(nxt))
            if gap < closest_gap:
                closest, closest_gap = nxt, gap
            queue.append((nxt, found))
    raise Refusal(UNREACHABLE, "; ".join(goal.unmet(closest)) or "no move applies")


def _try(order: Sequence[Move], start: Mapping[str, int], goal: Goal) -> dict[str, Any]:
    state, applied = dict(start), []
    for move in order:
        if not move.requires(state):
            return {"holds": False, "applied": applied, "state": dict(state),
                    "refused_because": f"{move.tool} needs {sorted(move._needs)} "
                                       f"and the world has "
                                       f"{ {n: state[n] for n in move._needs} }"}
        state = move.apply(state)
        applied.append(move.tool)
    return {"holds": goal.holds(state), "applied": applied, "state": dict(state),
            "refused_because": None}


def why_order_matters(moves: Sequence[Move], start: Mapping[str, int]) -> dict[str, Any]:
    """Two steps, both orders, and the difference -- which is what a sequence IS.

    The measurement this round turns on: a COPY then a DELETE keeps the content
    readable, and the DELETE then the COPY cannot even run, because the delete left
    nothing to copy.

    The two steps are chosen by CLASS -- the move that raises NAMES, and the move that
    falls it -- and never by tool name. A version that looked up `"cp"` and `"rm"` here
    would have made the experiment a statement about this machine's coreutils rather
    than about kinds of move, which is the user's standing objection to the whole idea.
    """
    adder = next((m for m in moves if m._delta.get(NAMES, 0) > 0), None)
    remover = next((m for m in moves if m._delta.get(REMOVED, 0) > 0), None)
    if adder is None or remover is None:
        return {"measured": False,
                "reason": ("both a class that ADDS a name and a class that FALLS the "
                           "name count are needed; measured "
                           f"{[m.id for m in moves]}")}
    goal = Goal(at_least={REMOVED: 1, READABLE: 1, NAMES: start[NAMES]},
                desc="a name was removed and nothing readable was lost")
    forward = _try([adder, remover], start, goal)
    reverse = _try([remover, adder], start, goal)
    return {"measured": True, "goal": goal.as_dict(),
            "adder": adder.id, "remover": remover.id,
            "copy_then_delete": forward, "delete_then_copy": reverse,
            "order_decides": forward["holds"] != reverse["holds"]}


def one_move_answers(goal: Goal, moves: Sequence[Move], start: Mapping[str, int]) -> list[str]:
    """Which single doors satisfy the goal outright. Empty is the point of the round."""
    return [m.id for m in moves if m.requires(start) and goal.holds(m.apply(start))]
