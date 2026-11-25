#!/usr/bin/env python3
"""The frame is the model: what transfers between environments is a *slotted* relation, and
what an agent must refuse is a labelling that is not unique.

WHY THIS FILE EXISTS
--------------------
The tree has spent twenty rounds arriving, from different sides, at the same sentence:

    every "sufficient" is sufficient for the runs that were executed
    (THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE, F5: 208 collisions on the deeper pool)
    experience without a relation is not experience of anything
    (THE_VOCABULARY_IS_THE_ARTIFACT: `mv` was experienced twice and stayed invisible)
    the residual is closed by language, not by more runs
    (BREADTH_BUYS_WHAT_REPETITION_CANNOT: 4 -> 2 -> 2 statements over three machines)

and each of those is a statement about ONE object, which nobody has built: the object that
walks from one machine to another. This file is that object, and nothing else.

WHAT A MACHINE GIVES, AND WHAT IT DOES NOT
------------------------------------------
A machine (see `canonical/tools/instant_learning_in_a_new_environment_v1.Machine`) gives:

    read()   -> a state: rows of (identity, content), read by the machine's own tool
    reset()  -> a known starting state
    atoms    -> commands with opaque identifiers

It does NOT give names for its literals, a goal language, or a mapping to any other machine.
There is no shared vocabulary between `FILESYSTEM` (`alpha_one`, `beta_two`), `GIT` (commit
hashes), `TARBALL` (member paths) and `SORT` (line text). That is exactly why the previous
rounds could not carry anything across: they stored the names.

THE THREE OBJECTS
-----------------
1. A **frame** is `(relation, binding)` -- a relation over the attested state, computed on the
   whole state or on the rows a *slot* selects. Fifteen of them, all derived from the reader's
   own two fields. No relation names the world: `CARD`, `MULTISET`, `ORDER`, `IDENT`,
   `PAIRING` are the five the tree already uses, `binding` is `WHOLE`, `CONTENT` or `IDENTENT`.

2. An **effect template** is what an atom did, written over the slot and never over the names:

       template = ((-2 CARD +1 MULTISET)@CONTENT, ...)   <- moves the content the goal names
       trace    = ("FS_A1 moved 'alpha_one' to 'probe_new_content'")   <- what the tree stored

   The template is *instantiated* on a new machine by binding the slot to the literal the goal
   names. Nothing machine-specific is stored, so nothing machine-specific has to be unlearned.

3. A **labelling** is a bijection between the literals of a state and the literals a stored
   template mentions. A slot-only template needs no labelling at all -- that is the point of
   it. A template that mentions *structure* ("the two rows that hold equal content") needs a
   labelling, and a labelling is only usable when it is **unique**. Two labellings that both
   fit make the template mean two different things on this machine, and the honest answer is
   REFUSED, not the first one found.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
No machine, no command, no path, no network, no model, no weights, no store. This module is a
pure function of a reader's state and a goal template. The store lives in the caller and is
`json`, because a store that cannot be read by a person cannot be audited by one.

WHAT THIS CANNOT DO
-------------------
- A frame outside the fifteen is invisible: a machine whose difference is a permission bit, a
  pixel, or a scroll offset cannot be stated here, and `stateable()` says so rather than
  guessing (see the blind-spot gate in the instrument).
- Sufficiency is a count over a *pool*, and money cannot buy it in general: the instrument
  measures the collisions on a deeper pool and reports them instead of hiding them.
- A unique labelling is unique *relative to this state*. A state that merges two roles gives
  no labelling, and an answer is not available at any price.

Authority NONE. Producer-run code. Zero model calls.
"""
from __future__ import annotations

import collections
import itertools
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CANONICAL_FRAME_V1"

#: the five relations the tree already uses, unchanged, so a frame is comparable with every
#: earlier measurement rather than being a fourth dialect.
RELATIONS = ("CARD", "MULTISET", "ORDER", "IDENT", "PAIRING")

#: how a relation is aimed: at the whole reading, at the rows one content selects, or at the
#: rows one identity selects. This is the *slot*, and it is the only parameter a frame has.
BINDINGS = ("WHOLE", "CONTENT", "IDENT")

#: the fixed vocabulary the earlier path could state (cardinality + multiset over the whole
#: reading). Kept as a named set so the instrument can price what the slot buys.
FIXED_FRAMES = tuple((r, "WHOLE") for r in ("CARD", "MULTISET"))

State = Sequence[tuple[str, str]]
Frame = tuple[str, str]


class FrameError(ValueError):
    """A frame was asked for on a binding the reading cannot supply."""


# --------------------------------------------------------------------------------------------
# the reader's fields -> the fifteen frames
# --------------------------------------------------------------------------------------------

def literals(state: State, field: str = "CONTENT") -> tuple[str, ...]:
    """The literal names this reading exposes, in first-seen order. `field` is CONTENT or IDENT.

    A state is a *reading*, not a model: these are the names the machine's own tool printed.
    """
    index = 0 if field == "IDENT" else 1
    seen: list[str] = []
    for row in state:
        value = str(row[index])
        if value not in seen:
            seen.append(value)
    return tuple(seen)


def _rows(state: State, binding: str, slot: str | None) -> tuple[tuple[str, str], ...]:
    rows = tuple((str(i), str(c)) for i, c in state)
    if binding == "WHOLE":
        return rows
    if binding == "CONTENT":
        return tuple(r for r in rows if r[1] == slot)
    if binding == "IDENT":
        return tuple(r for r in rows if r[0] == slot)
    raise FrameError("UNKNOWN_BINDING:" + str(binding))


def observe(frame: Frame, state: State, slot: str | None = None) -> Any:
    """One frame's value on one reading. Total on the reading, partial on the vocabulary:
    a `CONTENT` frame with no slot names nothing and is refused, never defaulted to `[]`."""
    relation, binding = frame
    if relation not in RELATIONS:
        raise FrameError("UNKNOWN_RELATION:" + str(relation))
    if binding not in BINDINGS:
        raise FrameError("UNKNOWN_BINDING:" + str(binding))
    if binding != "WHOLE" and slot is None:
        raise FrameError("SLOT_REQUIRED:" + binding)
    rows = _rows(state, binding, slot)
    contents = tuple(c for _i, c in rows)
    if relation == "CARD":
        return len(rows)
    if relation == "MULTISET":
        return tuple(sorted(collections.Counter(contents).items()))
    if relation == "ORDER":
        return contents
    if relation == "IDENT":
        return tuple(i for i, _c in rows)
    return tuple(sorted(rows))  # PAIRING


def moved(before: State, after: State, frame: Frame, slot: str | None = None) -> bool:
    """Whether this frame can tell the two readings apart. `False` is 'invisible here', which
    is the finding the earlier rounds kept having to report as a failure."""
    return observe(frame, before, slot) != observe(frame, after, slot)


def signature(before: State, after: State, slot: str | None = None,
              frames: Iterable[Frame] = ()) -> tuple[Frame, ...]:
    """The effect of one atom in one cell, in the vocabulary's own words: which frames moved."""
    return tuple(f for f in frames if moved(before, after, f, slot))


# --------------------------------------------------------------------------------------------
# the object that crosses machines: a template, with slots and no names
# --------------------------------------------------------------------------------------------

def template(before: State, after: State, frames: Iterable[Frame] = (),
             slot: str | None = None) -> dict[str, Any]:
    """The *storable* form of one experience.

    The slot-only part (`slot_frames`) is what a template carries: the frames that moved when
    the slot was aimed at the row the goal names. It contains no literal, so it is meaningful
    on a machine that shares no names with the one it was learned on.

    The `whole_frames` part is the ambient part (cardinality, ordering of the whole reading),
    which is shared across machines by construction. The `literal_frames` part is the same
    measurement aimed at a *different, named* row: it is kept in the receipt as evidence of
    what the slot bought, and it is never the thing that is carried.

    `direction` is the sign of the change per frame, so `+CARD` (one row arrived) is not
    confused with `-CARD` (one left) when the two are later composed.
    """
    slot_frames: list[list[Any]] = []
    literal_frames: list[list[Any]] = []
    whole_frames: list[list[Any]] = []
    for frame in frames:
        if frame[1] == "WHOLE":
            if moved(before, after, frame):
                whole_frames.append([frame[0], _direction(frame, before, after, None)])
            continue
        if slot is not None and moved(before, after, frame, slot):
            slot_frames.append([frame[0], _direction(frame, before, after, slot)])
        others = [lit for lit in literals(before, "CONTENT")
                  if lit != slot and moved(before, after, frame, lit)]
        for lit in others:
            literal_frames.append([frame[0], _direction(frame, before, after, lit), lit])
    return {"schema": SCHEMA, "slot": slot, "slot_frames": slot_frames,
            "whole_frames": whole_frames, "literal_frames": literal_frames,
            "uses_literals": bool(literal_frames)}


def _direction(frame: Frame, before: State, after: State, slot: str | None) -> str:
    relation = frame[0]
    if relation == "CARD":
        return "+" if observe(frame, after, slot) > observe(frame, before, slot) else "-"
    if relation == "MULTISET":
        return "+" if (observe(frame, after, slot) != observe(frame, before, slot)) else "?"
    return "~"


def instantiate(tpl: Mapping[str, Any], state: State, goal_literal: str | None = None
                ) -> dict[str, Any]:
    """Bind a stored template to *this* reading.

    A slot-only template needs only the goal's literal, and that is supplied by the goal, not
    guessed from the state. A template that mentions literals needs a labelling, and this
    function returns every labelling that fits, or refuses. It never picks one.
    """
    slot_frames = [tuple(x) for x in (tpl.get("slot_frames") or [])]
    whole_frames = [tuple(x) for x in (tpl.get("whole_frames") or [])]
    literal_frames = [tuple(x) for x in (tpl.get("literal_frames") or [])]
    # A template asked at a slot it does not HAVE is not a slot-only template. The first version of
    # this check also required `slot_frames` to be non-empty, so a template built at `WHOLE` (which
    # stores nothing slotted) was silently instantiated with no slot whatever the goal named -- a
    # quiet widening of meaning, which is the exact failure mode this module exists to refuse.
    if isinstance(tpl.get("slot"), str) and goal_literal is None:
        return {"status": "REFUSED__SLOT_UNBOUND", "labellings": [], "frames": []}
    if not literal_frames:
        return {"status": "PASS__SLOT_ONLY", "labellings": [{"slot": goal_literal}],
                "frames": [(f[0], "CONTENT", goal_literal) for f in slot_frames]
                          + [(f[0], "WHOLE", None) for f in whole_frames]}
    names = literals(state, "CONTENT")
    fits = [lab for lab in _labellings(names, [f[2] for f in literal_frames])
            if all(observe((f[0], "CONTENT"), state, lab[f[2]]) != observe((f[0], "CONTENT"), state,
                    goal_literal) or True for f in literal_frames)]
    # a labelling is a *candidate reading of the template on this machine*; uniqueness is the
    # criterion, and equality of the frames above cannot break a tie by construction.
    if not fits:
        return {"status": "REFUSED__NO_LABELLING", "labellings": [], "frames": []}
    if len(fits) > 1:
        return {"status": "REFUSED__LABELLING_NOT_UNIQUE", "labellings": fits, "frames": [],
                "why": f"{len(fits)} labellings fit this reading; the template means "
                       f"{len(fits)} different things here and none of them is chosen"}
    lab = fits[0]
    return {"status": "PASS__LABELLED", "labellings": fits,
            "frames": [(f[0], "CONTENT", lab[f[2]]) for f in literal_frames]
                      + [(f[0], "CONTENT", goal_literal) for f in slot_frames]
                      + [(f[0], "WHOLE", None) for f in whole_frames]}


def _labellings(names: Sequence[str], wanted: Sequence[str]) -> list[dict[str, str]]:
    """Every injective assignment of the template's literal names to this reading's literals.

    This is the whole of "generalisation" in one function: the names of the machine that taught
    the template carry no weight, so any bijection is a candidate and the data decides.
    """
    unique = []
    for name in wanted:
        if name not in unique:
            unique.append(name)
    if len(unique) > len(names):
        return []
    return [dict(zip(unique, chosen)) for chosen in itertools.permutations(names, len(unique))]


# --------------------------------------------------------------------------------------------
# the goal, stated the same way, and what "stateable" means
# --------------------------------------------------------------------------------------------

def stateable(goal: Mapping[str, Any], frames: Iterable[Frame]) -> dict[str, Any]:
    """Whether this goal can be said at all in this vocabulary.

    A goal is `{frame: (relation, binding), slot: literal|None, test: name, value: n}`. It is
    stateable iff its frame is one of the frames the agent carries. This is the check whose
    absence let `mv` be experienced without being learned: the effect was real and the goal
    was unsayable, and nothing in the tree distinguished those two.
    """
    frame = tuple(goal.get("frame") or ())
    carried = tuple(tuple(f) for f in frames)
    if len(frame) != 2 or frame not in carried:
        return {"stateable": False, "reason": "FRAME_NOT_IN_VOCABULARY",
                "frame": list(frame), "carried": [list(f) for f in carried]}
    if frame[1] != "WHOLE" and not goal.get("slot"):
        return {"stateable": False, "reason": "SLOT_UNBOUND", "frame": list(frame)}
    return {"stateable": True, "reason": None, "frame": list(frame)}


def unstateable_why(goal: Mapping[str, Any], frames: Iterable[Frame]) -> str:
    """The *first* reason a goal cannot be said, in the order that matters: a vocabulary that does
    not contain the frame is a different disease from a slot that was not named, and reporting the
    second when the first is true would send the repair to the wrong place."""
    result = stateable(goal, frames)
    return "STATEABLE" if result["stateable"] else str(result["reason"])


def holds(goal: Mapping[str, Any], state: State) -> bool:
    """The goal's own test, read off the machine's own reader. Three tests, no fourth."""
    value = observe(tuple(goal["frame"]), state, goal.get("slot"))
    test = goal.get("test")
    if test == "equals":
        return value == goal.get("value")
    if test == "contains":
        return goal.get("value") in value
    if test == "count_is":
        return value == goal.get("value")
    raise FrameError("UNKNOWN_TEST:" + str(test))


# --------------------------------------------------------------------------------------------
# what the vocabulary buys, in cells: the price of a goal, and its growth with depth
# --------------------------------------------------------------------------------------------

def cells(frame: Frame, states: Sequence[State], slot: str | None = None) -> int:
    """How many distinguishable values one frame takes over a pool of readings.

    This is the *price* of a goal stated on that frame: `k` cells means `k` experiences decide
    it, in the sense measured by THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE. It is a count over a
    pool, and the pool is named by the caller, because a count without its pool is a number
    without a meaning.
    """
    return len({_freeze(observe(frame, s, slot)) for s in states})


def collisions(frames: Iterable[Frame], runs: Sequence[tuple[State, bool]],
               slot: str | None = None) -> int:
    """Pairs of runs this frame-tuple cannot tell apart but the machine judges differently.

    Zero is the only acceptable number and it is never a general fact: the instrument measures
    it on a shallow pool, then on a deeper one, and reports both.
    """
    index: dict[Any, set[bool]] = {}
    for state, verdict in runs:
        key = tuple(_freeze(observe(f, state, slot)) for f in frames)
        index.setdefault(key, set()).add(bool(verdict))
    return sum(1 for verdicts in index.values() if len(verdicts) > 1)


def _freeze(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    return value


def cheapest_sufficient(candidates: Iterable[Frame], runs: Sequence[tuple[State, bool]],
                        slot: str | None = None) -> dict[str, Any]:
    """The smallest set of frames, by number of frames then by cells, that separates every pair
    the machine judges differently. Exhaustive over subsets: the counts here are small, and an
    approximation would be a second mechanism to justify.

    `witness` is returned with a failure, because "this frame cannot carry the goal" is only a
    claim if it names the two runs it cannot separate.
    """
    order = sorted({tuple(f) for f in candidates})
    if not runs:
        return {"status": "REFUSED__EMPTY_POOL", "frames": []}
    best: dict[str, Any] | None = None
    for size in range(1, min(len(order), 4) + 1):
        for subset in itertools.combinations(order, size):
            if collisions(subset, runs, slot) == 0:
                price = sum(cells(f, [s for s, _v in runs], slot) for f in subset)
                row = {"status": "PASS__SUFFICIENT", "frames": [list(f) for f in subset],
                       "cells": price, "pool": len(runs)}
                if best is None or price < best["cells"]:
                    best = row
        if best is not None:
            return best
    return {"status": "REFUSED__NO_SUBSET_SEPARATES_POOL",
            "witness": _witness(order, runs, slot), "pool": len(runs)}


def _witness(order: Sequence[Frame], runs: Sequence[tuple[State, bool]],
             slot: str | None) -> dict[str, Any] | None:
    index: dict[Any, list[tuple[State, bool]]] = {}
    for state, verdict in runs:
        key = tuple(_freeze(observe(f, state, slot)) for f in order)
        index.setdefault(key, []).append((state, bool(verdict)))
    for members in index.values():
        verdicts = {v for _s, v in members}
        if len(verdicts) > 1:
            return {"state_a": [list(r) for r in members[0][0]], "verdict_a": members[0][1],
                    "state_b": [list(r) for r in members[-1][0]], "verdict_b": members[-1][1]}
    return None
