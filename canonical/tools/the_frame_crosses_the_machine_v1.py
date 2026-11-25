#!/usr/bin/env python3
"""What crosses a machine boundary: the relation, or nothing. Measured on seven real machines.

THE OWNER'S QUESTION, TAKEN WHOLE
---------------------------------
"All he should do is go into any new environment, ask the right question, and know the things he
should know from instant knowledge. What should he SAVE, what should he GENERALIZE, and is he
goal-directed or exhaustive?"

Twenty rounds of this tree have priced the pieces:

  * one verified experience adds an action permanently          (30/30, real machine)
  * an action *list* transfers nothing                          (0/20 held-out)
  * `mv` was experienced twice and stayed unusable               (its relation was invisible)
  * more repetition is worth exactly zero bits                   (0/200 identified)
  * breadth halves the ambiguity and then saturates              (4 -> 2 -> 2 sentences)
  * a "sufficient" statistic collided 208 times at a deeper pool (F5)

Every one of those is a statement about ONE object: **the thing that is carried**. Nobody has
carried anything between two machines that share no name. That crossing is this instrument, and
nothing else in it is new.

THE SEVEN MACHINES
------------------
Four are reused verbatim from `instant_learning_in_a_new_environment_v1` (FILESYSTEM, GIT,
TARBALL, SQLITE); three are added by `frames_that_cross_machines_v1` (GIT2, ARCHIVE2, LIST). All
seven are real tools over real state and each has its own reader. They share no literal at all:
`probe_seed_content`, `alpha_one`, a commit hash, a member path and a line of text have nothing in
common except that a tool printed them.

THE FOUR LEDGERS, EACH OF WHICH CAN SAY NO
------------------------------------------
L1  STATEABILITY. Every atom of every machine is executed in two cells and the *frames* that moved
    are recorded. A goal can only be stated on a frame the agent carries; a frame that is not in
    `{CARD, MULTISET} @ WHOLE` is a goal the old vocabulary could not even name. Counted per
    machine, with the atoms whose real effect was invisible to the old vocabulary named.

L2  IDENTIFICATION. The user's *sentence* is not available; the user's *judgement on runs* is.
    Given accepted and rejected readings and nothing else, how many judgements before one frame
    survives, and is the survivor the goal's own frame or only its equivalent? Measured with a
    canonical hypothesis order and with a cross-machine prior, leave-one-machine-out, so
    "does experience elsewhere make this machine cheaper" is a number and not a story.

L3  CROSSING, WHICH IS THE POINT. A frame is learned on machine A from A's judged runs. Nothing
    else is carried: no atom identifier, no literal, no command. On machine B, in a different
    family, the agent reads B's own atoms, executes each once (that cost is counted, because it
    is real), and picks the atom whose measured effect moves the carried frame toward what the
    user accepted. Then it executes for real and the *machine's own reader* judges.
    Two controls run on the identical goal and budget:
      EXEMPLAR  reproduce the accepted reading exactly, no frame inferred
      REPLAY    re-use the atom identifier that worked on A
    A win for the frame that costs more than the controls is not a win, and both are reported.

L4  DEPTH. The frame that separates every judged pair at depth 2 can collide at depth 3. This is
    F5 of `THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE` (208 collisions) asked again in a new currency and
    on real machines, so the failure is measured here rather than inherited from a document.

A BLIND SPOT BUILT ON PURPOSE
-----------------------------
`chmod 600 -> 755` is a real change to real state that none of the fifteen frames can see. The
vocabulary must refuse to state it and say why. A vocabulary that answered here would be guessing,
and the refusal is the result.

WHAT THIS IS NOT
----------------
Not a benchmark score, not a capability, not independent verification, and not GUI: there is no
display in this sandbox. `OSWorld 2.0` (arXiv 2606.29537) puts the frontier at 20.6% binary on 108
long-horizon desktop tasks and its own diagnosis is hidden state and missing verification -- the
same law these seven machines exhibit -- but a bitmap's frames (pixels, permission bits, scroll
offsets) are outside this vocabulary, and the blind spot says so with a measurement.

Zero model calls. Zero stored parameters. Zero network at run time. $0.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import itertools
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402
from canonical.swe_kernel import canonical_frame_v1 as cf  # noqa: E402

SCHEMA = "BRAIN_THE_FRAME_CROSSES_THE_MACHINE_V1"
State = tuple[tuple[str, str], ...]

FIXED = tuple(cf.FIXED_FRAMES)
ALL_FRAMES = tuple((r, b) for r in cf.RELATIONS for b in cf.BINDINGS)


def execute(atom: Any, machine: Any, args: dict[str, str]) -> dict[str, Any]:
    return room.base.execute(atom, machine, args)


def slots_of(state: Sequence[tuple[str, str]], frame: tuple[str, str]) -> list[str | None]:
    if frame[1] == "WHOLE":
        return [None]
    if frame[1] == "CONTENT":
        return list(cf.literals(state, "CONTENT"))
    return list(cf.literals(state, "IDENT"))


def read(machine: Any) -> State:
    return tuple(map(tuple, machine.read()))


# =============================================================================================
# the cells: every atom of every machine, executed in two state classes, on real state
# =============================================================================================

@dataclasses.dataclass(frozen=True)
class Cell:
    machine: str
    atom: str
    state_class: str
    before: State
    after: State
    args: dict[str, str]
    exit: int

    def moved_frames(self) -> list[tuple[tuple[str, str], str | None]]:
        out = []
        for frame in ALL_FRAMES:
            for slot in slots_of(self.before, frame):
                try:
                    if cf.moved(self.before, self.after, frame, slot):
                        out.append((frame, slot))
                except cf.FrameError:
                    continue
        return out


def probe_cells(builds: dict[str, Any], root: pathlib.Path) -> tuple[list[Cell], dict[str, Any]]:
    cells: list[Cell] = []
    notes: dict[str, Any] = {}
    for name in sorted(builds):
        machine = builds[name](root / name)
        machine.reset()
        changed = 0
        invisible_to_fixed = 0
        invisible_to_everything = 0
        for atom in machine.atoms:
            for state_class in ("TARGET_ABSENT", "TARGET_EXISTS"):
                machine.reset()
                before = read(machine)
                args = room.cell_args(list(before), state_class)
                result = execute(atom, machine, args)
                after = read(machine)
                cell = Cell(name, atom.ident, state_class, before, after, dict(args),
                            result["exit"])
                cells.append(cell)
                if before != after:
                    changed += 1
                if not any(cf.moved(before, after, f) for f in FIXED):
                    invisible_to_fixed += 1
                if not cell.moved_frames():
                    invisible_to_everything += 1
        machine.reset()
        notes[name] = {
            "atoms": len(machine.atoms),
            "cells": 2 * len(machine.atoms),
            "readings_that_changed": changed,
            "changed_but_invisible_to_the_old_vocabulary": invisible_to_fixed,
            "changed_but_invisible_to_every_frame_here": invisible_to_everything,
            "rows_at_reset": len(machine.read()),
            "literals_at_reset": list(cf.literals(machine.read(), "CONTENT")),
        }
    return cells, notes


def run_pool(machine: Any, depth: int) -> list[State]:
    """Every sequence of DISTINCT atoms up to `depth`, executed from reset. Real state."""
    idents = [atom.ident for atom in machine.atoms]
    states: list[State] = []
    for size in range(1, depth + 1):
        for sequence in itertools.permutations(idents, size):
            machine.reset()
            for ident in sequence:
                atom = next(a for a in machine.atoms if a.ident == ident)
                execute(atom, machine, room.cell_args(machine.read(), "TARGET_ABSENT"))
            states.append(read(machine))
    machine.reset()
    return states


# =============================================================================================
# L1: stateability, and which frame each real effect needed
# =============================================================================================

def stateability(cells: Sequence[Cell], notes: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for name in sorted(notes):
        machine_cells = [c for c in cells if c.machine == name and c.before != c.after]
        fixed = [c for c in machine_cells if any(cf.moved(c.before, c.after, f) for f in FIXED)]
        needed = collections.Counter()
        invisible = []
        for cell in machine_cells:
            frames = cell.moved_frames()
            if not frames:
                invisible.append(cell.atom)
                continue
            if not any(f in FIXED for f, _s in frames):
                for frame, _slot in frames:
                    needed[f"{frame[0]}@{frame[1]}"] += 1
        rows[name] = {
            "effects_that_changed_the_reading": len(machine_cells),
            "effects_stateable_under_the_old_vocabulary": len(fixed),
            "effects_NOT_stateable_under_the_old_vocabulary": len(machine_cells) - len(fixed),
            "frames_the_old_vocabulary_could_not_name": dict(needed),
            "atoms_whose_real_effect_is_invisible_to_every_frame": sorted(set(invisible)),
        }
    return rows


# =============================================================================================
# goals: a frame, a slot, and a value. Derived from judged runs, never from a name
# =============================================================================================

@dataclasses.dataclass(frozen=True)
class Goal:
    """A goal as the user states it: *which* thing, and *what* must be true of it.

    `slot` is the literal the user NAMES (a file they point at, a member they mention). `value`
    is the outcome they want to see for it. Both are the user's, not the agent's, and the value
    is an OBJECT the user hands over -- a single datum, of the shape the frame produces -- which
    is exactly as much as "one more copy of THIS" tells a person.
    """
    machine: str
    name: str
    frame: tuple[str, str]
    slot: str | None
    value: Any
    atom: str

    def holds(self, state: Sequence[tuple[str, str]]) -> bool:
        try:
            return cf.observe(self.frame, state, self.slot) == self.value
        except cf.FrameError:
            return False

    def not_already_true(self, state: Sequence[tuple[str, str]]) -> bool:
        """A goal the world already satisfies is not a task. This predicate exists because the
        first version of this instrument scored 5 "REACHED" verdicts that were the reset state.
        A goal whose outcome already holds is counted as a defect of the instrument, printed,
        and excluded -- not as a win."""
        return not self.holds(state)


def holds(goal: Goal, state: Sequence[tuple[str, str]]) -> bool:
    return goal.holds(state)


def goals_of(machine: str, cells: Sequence[Cell]) -> list[Goal]:
    """One goal per cell per frame that moved: the *outcome* the atom produced, stated on each
    frame that can see it. Several frames seeing one change is not redundancy -- it is the
    ambiguity L2 has to resolve, and hiding it would make L2 look easier than it is."""
    out: list[Goal] = []
    for cell in cells:
        if cell.machine != machine or cell.state_class != "TARGET_ABSENT":
            continue
        for frame, slot in cell.moved_frames():
            value = cf.observe(frame, cell.after, slot)
            if value == cf.observe(frame, cell.before, slot):
                continue
            out.append(Goal(machine, f"{cell.atom}:{frame[0]}@{frame[1]}", frame, slot, value,
                            cell.atom))
    return out


def goals_for_machine(name: str, machine: Any, atoms: Sequence[Any],
                      depth2: Sequence[State]) -> list[Goal]:
    """Goals derived from what THIS machine's atoms actually achieve, at run time.

    The first version derived goals from the other file's cell table, which is a shared artifact;
    a shared artifact is a leak, and it made one machine's goal depend on another machine's
    probes. This version derives each goal from a real execution on this machine, in this run,
    and does not look at any table the other machines contributed to.
    """
    out: list[Goal] = []
    for atom in atoms:
        machine.reset()
        before = read(machine)
        execute(atom, machine, room.cell_args(list(before), "TARGET_ABSENT"))
        after = read(machine)
        machine.reset()
        for candidate in ALL_FRAMES:
            for slot in slots_of(before, candidate):
                try:
                    if not cf.moved(before, after, candidate, slot):
                        continue
                    value = cf.observe(candidate, after, slot)
                except cf.FrameError:
                    continue
                out.append(Goal(name, f"{atom.ident}:{candidate[0]}@{candidate[1]}",
                                candidate, slot, value, atom.ident))
                break
    machine.reset()
    return out


def never_true_at_reset(goal: Goal, machine: Any) -> bool:
    machine.reset()
    state = read(machine)
    machine.reset()
    return goal.not_already_true(state) and any(goal.holds(s) for s in [state]) is False


# =============================================================================================
# L2: identification from judged pairs, with and without a prior from other machines
# =============================================================================================

def hypothesis_space(state: State) -> list[tuple]:
    return [(frame, slot) for frame in ALL_FRAMES for slot in slots_of(state, frame)]


def agrees(hypothesis: tuple, goal: Goal, runs: Sequence[State]) -> bool:
    """Whether this hypothesis judges every run in the pool exactly as the goal does.

    This is the criterion that matters, and it is weaker than naming: a frame need not be the
    frame the goal was *written* on, it must *behave* the same on everything the world can show.
    Both are reported separately, because counting the weaker one as a discovery is how a useful
    mechanism gets sold as an insight.
    """
    frame, slot = hypothesis
    for state in runs:
        try:
            if (cf.observe(frame, state, slot) == goal.value) != holds(goal, state):
                return False
        except cf.FrameError:
            return False
    return True


def labelled_runs(goal: Goal, runs: Sequence[State]) -> list[tuple[State, bool]]:
    """The user's supervision: `this end state is what I meant`, per run, in pool order.

    This is the weakest kind of judgement a user can give and it is the one the interface has:
    a person points at the result they wanted. The order is the pool's, never the agent's -- the
    active-vs-arrival question is already settled in this tree (0.6987 vs 0.7038) and re-running
    it here would be a second experiment wearing the first one's clothes.
    """
    return [(state, holds(goal, state)) for state in runs]


def consistent(hypothesis: tuple, evidence: Sequence[tuple[State, bool]]) -> bool:
    frame, slot = hypothesis
    for state, accepted in evidence:
        try:
            if (cf.observe(frame, state, slot) == state_value(frame, slot, state)) and False:
                return False
            if (cf.observe(frame, state, slot) == _reference(frame, slot, evidence)) != accepted:
                return False
        except cf.FrameError:
            return False
    return True


def state_value(frame: tuple, slot: str | None, state: State) -> Any:
    return cf.observe(frame, state, slot)


def _reference(frame: tuple, slot: str | None, evidence: Sequence[tuple[State, bool]]) -> Any:
    """The value this hypothesis would predict for an accepted run: the value it takes on the
    first accepted run. A frame that cannot be aimed at this reading predicts nothing."""
    for state, accepted in evidence:
        if accepted:
            return cf.observe(frame, state, slot)
    return object()


def identify(order: Sequence[tuple], goal: Goal, evidence: Sequence[tuple[State, bool]],
             pool: Sequence[State], deep: Sequence[State]) -> dict[str, Any]:
    """How many labelled runs before one hypothesis is left, and what the survivor is worth.

    Two answers per count, because they are different claims:
      `names_the_goals_frame`  the survivor is the frame the goal was written on
      `behaves_like_the_goal`  the survivor judges every run of the DEEPER pool as the goal does
    A mechanism that gets the second and not the first is still a mechanism; a mechanism that
    gets the first and not the second is a coincidence.
    """
    reference = None
    for state, accepted in evidence:
        if accepted:
            reference = cf.observe(goal.frame, state, goal.slot)
            break
    if reference is None:
        return {"runs": 0, "identified": False, "why": "NO_ACCEPTED_RUN_IN_THE_POOL"}

    surviving = list(order)
    for count in range(1, len(evidence) + 1):
        seen = evidence[:count]
        surviving = [h for h in surviving
                     if all((cf.observe(h[0], s, h[1]) == reference) == acc for s, acc in seen)]
        if len(surviving) == 1:
            hyp = surviving[0]
            return {"runs": count, "identified": True, "hypothesis": [list(hyp[0]), hyp[1]],
                    "names_the_goals_frame": hyp == (goal.frame, goal.slot),
                    "behaves_like_the_goal": agrees(hyp, goal, deep),
                    "cells": cf.cells(hyp[0], list(pool), hyp[1])}
        if not surviving:
            return {"runs": count, "identified": False, "why": "NO_HYPOTHESIS_SURVIVES",
                    "after_one_run": count == 1}
    equiv = [h for h in surviving if agrees(h, goal, deep)]
    return {"runs": len(evidence), "identified": False,
            "why": "POOL_EXHAUSTED__SOME_HYPOTHESIS_IS_INDISTINGUISHABLE_HERE",
            "survivors": len(surviving),
            "survivors_that_behave_like_the_goal_on_the_deeper_pool": len(equiv),
            "cheapest_equivalent_cells": min((cf.cells(h[0], list(pool), h[1])
                                              for h in equiv), default=None)}


def what_a_prior_buys(order: Sequence[tuple], goal: Goal, evidence: Sequence[tuple[State, bool]],
                      deep: Sequence[State]) -> dict[str, Any]:
    """What the ORDER buys: the accuracy of the top-ranked consistent hypothesis, before and
    after k labelled runs. A prior cannot change how many runs identify the truth; it changes how
    right the agent is while it waits, which is the only thing an agent can act on."""
    reference = next((cf.observe(goal.frame, s, goal.slot) for s, a in evidence if a), None)
    rows = {}
    for count in (0, 1, 2, 3):
        seen = evidence[:count]
        consistent_here = [h for h in order
                           if all((cf.observe(h[0], s, h[1]) == reference) == acc
                                  for s, acc in seen)]
        top = consistent_here[0] if consistent_here else None
        rows[f"after_{count}"] = {
            "survivors": len(consistent_here),
            "top_names_the_goals_frame": top == (goal.frame, goal.slot),
            "top_behaves_like_the_goal": bool(top) and agrees(top, goal, deep),
        }
    return rows


def canonical_order(space: Sequence[tuple]) -> list[tuple]:
    """Fewest relations first, then the frames the tree already had. Deliberately untuned: an
    order tuned on the test machine is the answer leaking back into the question."""
    return sorted(space, key=lambda h: (len(h[0]), ALL_FRAMES.index(h[0]) or 0))


def prior_order(trained: Sequence[tuple[str, str]], space: Sequence[tuple]) -> list[tuple]:
    """Order by how often each FRAME was the answer on the other machines, leave-one-out.

    Only the frame can cross: the slots are this machine's literals and say nothing about another
    machine. Ties keep the canonical order, so a prior that knows nothing costs nothing.
    """
    counts = collections.Counter(trained)
    index = {h: i for i, h in enumerate(space)}
    return sorted(space, key=lambda h: (-counts.get(h[0], 0), index[h]))


# =============================================================================================
# L3: the crossing. Learn the frame on A, answer on B, judge with B's own reader.
# =============================================================================================

def _target_goal(frame: tuple[str, str], target: str, *, machine: Any,
                 atoms: Sequence[Any]) -> tuple[Goal | None, str]:
    """The same goal, stated on the target machine by the user of that machine.

    A goal is a frame and an outcome a person wants -- "the lines are in ascending order", "one
    more copy of this content". It is NOT a value carried from another machine: two machines'
    values are not comparable, and pretending they are is the mistake this instrument exists to
    avoid. So the target's goal is the same FRAME, aimed at one of the target's own literals,
    with the value the target can reach -- and, by construction, one the target does NOT already
    satisfy, because a goal the world already meets is not a task.

    Returns (goal, why-not) so a refusal is a value with a name and not an absence.
    """
    machine.reset()
    state = read(machine)
    machine.reset()
    for slot in slots_of(state, frame):
        for atom in atoms:
            machine.reset()
            before = read(machine)
            args = room.cell_args(list(before), "TARGET_ABSENT")
            execute(atom, machine, args)
            after = read(machine)
            machine.reset()
            try:
                if not cf.moved(before, after, frame, slot):
                    continue
                value = cf.observe(frame, after, slot)
                goal = Goal(target, f"same-frame:{frame[0]}@{frame[1]}", frame, slot, value,
                            atom.ident)
            except cf.FrameError:
                continue
            if goal.not_already_true(state):
                return goal, ""
    return None, "NO_UNSATISFIED_GOAL_ON_THIS_FRAME_WITH_THIS_MACHINES_ATOMS"


def learn_frame(goal: Goal, runs_a: Sequence[State], space_a: Sequence[tuple]) -> dict[str, Any]:
    """What is carried: one frame and one slot KIND, and no literal, no atom, no command.

    The slot *kind* (`WHOLE` / `CONTENT` / `IDENT`) crosses, because it says which component of
    the reading the goal is about. The slot *value* does not cross, and must not: it is one of the
    source machine's names.
    """
    evidence = labelled_runs(goal, runs_a)
    result = identify(canonical_order(space_a), goal, evidence, runs_a, runs_a)
    carried = {"schema": cf.SCHEMA, "frame": list(goal.frame),
               "learned_on": goal.machine, "identified_from": result["runs"],
               "identified_exactly": result["identified"],
               "names_the_goals_own_frame": result.get("names_the_goals_frame")}
    return {"carried": carried, "identification": result}


def answer_on_target(goal: Goal, carried: dict[str, Any], machine: Any, atoms: Sequence[Any],
                     *, blind: bool = False) -> dict[str, Any]:
    """Answer on a machine that shares no name with the one the frame came from.

    The agent knows ONE FRAME and nothing else: no literal, no atom, no command, and -- this is
    the whole design -- no goal value it can test a candidate against. It reads this machine,
    executes each atom once in one cell (that is the counted adaptation cost), and picks the atom
    whose measured effect on this reading moves the carried frame. Only then does it execute, and
    only then does the machine's own reader judge.

    `blind=True` is the control: the same loop, the same probes, the same counted cost, but the
    atom is chosen because it changed the reading AT ALL, with the frame ignored. The difference
    between the two columns is the entire value of carrying a relation, and if the difference is
    zero then the frame is not worth its bytes -- which this instrument will say.
    """
    frame = tuple(carried["frame"])
    if frame not in ALL_FRAMES:
        return {"verdict": "REFUSED__CARRIED_FRAME_UNKNOWN", "atom": None}
    machine.reset()
    probes: list[dict[str, Any]] = []
    for atom in atoms:                                  # the counted adaptation cost
        machine.reset()
        before = read(machine)
        args = room.cell_args(list(before), "TARGET_ABSENT")
        execute(atom, machine, args)
        after = read(machine)
        moves_frame = False
        for slot in slots_of(before, frame):
            try:
                if cf.moved(before, after, frame, slot):
                    moves_frame = True
                    break
            except cf.FrameError:
                continue
        probes.append({"atom": atom.ident, "changed": before != after,
                       "moves_the_carried_frame": moves_frame})
    machine.reset()
    pool = [row for row in probes if (row["changed"] if blind else row["moves_the_carried_frame"])]
    if not pool:
        return {"verdict": "REFUSED__NO_ATOM_MOVES_THE_CARRIED_FRAME_ON_THIS_MACHINE",
                "atom": None, "probes": len(probes)}
    chosen = pool[0]
    machine.reset()
    execute(next(a for a in atoms if a.ident == chosen["atom"]), machine,
            room.cell_args(machine.read(), "TARGET_ABSENT"))
    reached = goal.holds(read(machine))
    machine.reset()
    return {"verdict": "REACHED" if reached else "NOT_REACHED", "atom": chosen["atom"],
            "candidates": len(pool), "probes": len(probes),
            "picked_the_atom_the_goal_was_generated_from": chosen["atom"] == goal.atom}


def holds_via(frame: tuple, slot: str | None, value: Any, state: State) -> bool:
    try:
        return cf.observe(frame, state, slot) == value
    except cf.FrameError:
        return False


def _shape_head(value: Any) -> str:
    if isinstance(value, (tuple, list)):
        return f"seq[{len(value)}]"
    return type(value).__name__


def _brief(value: Any) -> Any:
    text = repr(value)
    return value if len(text) < 120 else text[:117] + "..."


def exemplar_control(exemplar: State, atoms: Sequence[Any], machine: Any) -> dict[str, Any]:
    """The control with no inference at all: reproduce the accepted reading exactly.

    This is the strongest *frame-free* baseline, because it needs no vocabulary and no prior --
    it needs only the user's accepted end state. It fails on exactly the thing a frame throws
    away: identities and literals that differ between the machine that produced the exemplar and
    the machine answering now.
    """
    machine.reset()
    for atom in atoms:
        machine.reset()
        execute(atom, machine, room.cell_args(machine.read(), "TARGET_ABSENT"))
        if read(machine) == exemplar:
            machine.reset()
            return {"verdict": "REACHED", "atom": atom.ident, "probes": 1}
    machine.reset()
    return {"verdict": "NOT_REACHED__NO_SINGLE_ATOM_REPRODUCES_THE_ACCEPTED_READING",
            "atom": None, "probes": len(atoms)}


def replay_control(foreign_atom: str | None, atoms: Sequence[Any]) -> dict[str, Any]:
    """The control that stores the experience as it came: an atom identifier from another
    machine. Identifiers are opaque and machine-local, so this either refuses or guesses."""
    if foreign_atom is None:
        return {"verdict": "REFUSED__NOTHING_TO_REPLAY", "atom": None}
    if any(atom.ident == foreign_atom for atom in atoms):
        return {"verdict": "ADMISSIBLE_BY_ACCIDENT", "atom": foreign_atom}
    return {"verdict": "REFUSED__ATOM_IDENTIFIER_DOES_NOT_EXIST_ON_THIS_MACHINE",
            "atom": None, "replayed": foreign_atom}


# =============================================================================================
# L4: a frame sufficient on a shallow pool, and what it does on a deeper one
# =============================================================================================
#
# The first version of this section was TAUTOLOGICAL and it is kept here as a warning rather
# than deleted: its "goal" was `frame == value`, so the verdict was a function of the frame key
# by construction and no pair of runs could ever collide. It reported zero collisions on 39 rows
# and was measuring nothing.
#
# A collision is only possible when the user's judgement is stated INDEPENDENTLY of the frame
# under test. So the goal here is not a frame at all: it is a statement about the machine's
# contents, which is what a person looks at -- "this content appears exactly twice", "this
# content is the last line". The frame then has a job: be a statistic whose value determines that
# judgement. Depth is the variable that breaks it, because a deeper run can reach a reading the
# shallow pool never contained.

@dataclasses.dataclass(frozen=True)
class UserGoal:
    """A judgement a person makes by looking at the reading, with no frame in it at all."""
    machine: str
    name: str
    literal: str
    kind: str          # "count_is" | "is_last"
    k: int

    def holds(self, state: Sequence[tuple[str, str]]) -> bool:
        contents = [c for _i, c in state]
        if self.kind == "count_is":
            return contents.count(self.literal) == self.k
        if self.kind == "is_last":
            return bool(contents) and contents[-1] == self.literal
        raise cf.FrameError("UNKNOWN_USER_TEST:" + self.kind)


def user_goals(machine: str, machine_obj: Any, atoms: Sequence[Any]) -> list[UserGoal]:
    """Frame-free goals, derived from what this machine's atoms can actually produce."""
    machine_obj.reset()
    literals = list(cf.literals(read(machine_obj), "CONTENT"))
    machine_obj.reset()
    goals: list[UserGoal] = []
    for atom in atoms:
        machine_obj.reset()
        before = read(machine_obj)
        execute(atom, machine_obj, room.cell_args(list(before), "TARGET_ABSENT"))
        after = read(machine_obj)
        machine_obj.reset()
        if before == after:
            continue
        counts = collections.Counter(c for _i, c in after)
        for literal in literals:
            if counts[literal] != collections.Counter(c for _i, c in before)[literal]:
                goals.append(UserGoal(machine, f"{atom.ident}:count({literal})", literal,
                                      "count_is", counts[literal]))
        if after:
            goals.append(UserGoal(machine, f"{atom.ident}:last({after[-1][1]})", after[-1][1],
                                  "is_last", 1))
    return goals


def sufficient_frame(goal: UserGoal, pool: Sequence[State]) -> dict[str, Any]:
    """The cheapest frame whose value determines this judgement on THIS pool.

    Candidates are the whole-reading frames plus the content-bound frames aimed at the user's own
    literal. The literal is the user's, not the agent's: a person pointing at "this file" has
    named a slot, and pretending otherwise would hide the rebinding step that has to happen.
    """
    candidates = [(r, "WHOLE") for r in cf.RELATIONS] + [(r, "CONTENT") for r in cf.RELATIONS]
    runs = [(state, goal.holds(state)) for state in pool]
    best: dict[str, Any] | None = None
    for frame in candidates:
        slot = goal.literal if frame[1] == "CONTENT" else None
        try:
            if collisions_of(frame, slot, runs):
                continue
            price = cf.cells(frame, list(pool), slot)
        except cf.FrameError:
            continue
        if best is None or price < best["cells"]:
            best = {"frame": list(frame), "slot": slot, "cells": price}
    if best is None:
        return {"status": "REFUSED__NO_FRAME_IN_THIS_VOCABULARY_CARRIES_THE_GOAL"}
    return {"status": "PASS__SUFFICIENT_ON_THIS_POOL", **best}


def collisions_of(frame: tuple[str, str], slot: str | None,
                  runs: Sequence[tuple[State, bool]]) -> int:
    seen: dict[Any, set[bool]] = {}
    for state, accepted in runs:
        key = cf.observe(frame, state, slot)
        seen.setdefault(key, set()).add(bool(accepted))
    return sum(1 for verdicts in seen.values() if len(verdicts) > 1)


def witness_pair(frame: tuple[str, str], slot: str | None,
                 runs: Sequence[tuple[State, bool]]) -> dict[str, Any] | None:
    """The two runs a frame cannot separate and the user judges differently. A claim that a frame
    is insufficient is only a claim if it names them."""
    seen: dict[Any, list[tuple[State, bool]]] = {}
    for state, accepted in runs:
        seen.setdefault(cf.observe(frame, state, slot), []).append((state, bool(accepted)))
    for members in seen.values():
        if len({a for _s, a in members}) > 1:
            accepted = next(m for m in members if m[1])
            rejected = next(m for m in members if not m[1])
            return {"the_user_accepts": _brief(accepted[0]),
                    "the_user_rejects": _brief(rejected[0]),
                    "and_the_frame_gives_both_the_same_value":
                        _brief(cf.observe(frame, accepted[0], slot))}
    return None


# =============================================================================================
# L5: composition -- two frames that no single atom can move, and what a prior over actions buys
# =============================================================================================
#
# The tree measured that two individually-correct skills compose to a NO-OP (SKILLS_DONT_COMPOSE,
# 2026-11-12) and named the fix: reduce the effective branching factor, because the budget needed
# grows as b^depth and the willingness to spend grows linearly. This ledger is that fix, priced.
#
# A goal is a CONJUNCTION of two frame tests. On the machine chosen, no single atom can move both
# -- so the answer is a sequence, and the sequence has to be found. Two planners, same budget:
#
#   BLIND   every atom is a candidate at every step, in identifier order
#   PRUNE   only atoms that move a frame the goal is stated on, at the root
#   ORDER   every atom is still a candidate, but the ones that move a stated frame are tried
#           first, at every step
#
# All three verify a sequence by executing it and reading the machine, and every execution is
# counted, because that is the currency the previous rounds measured in.
#
# PRUNE IS MEASURED HERE BECAUSE IT FAILED, AND IT IS KEPT SO IT CANNOT QUIETLY RETURN. On the
# first run it cut executions 314 -> 233 and root candidates 57 -> 35, and it *lost four plans
# that BLIND found*: a conjunctive goal's second clause often only becomes reachable after the
# first action, so an atom that moves no wanted frame at reset is still the atom step two needs.
# Goal-directed pruning of the action set is therefore UNSOUND for conjunctive goals, and the
# sound version of the same idea is ORDER, which prunes nothing and only re-ranks.

@dataclasses.dataclass(frozen=True)
class Conjunction:
    machine: str
    name: str
    parts: tuple[tuple[tuple[str, str], str | None, Any], ...]

    def holds(self, state: Sequence[tuple[str, str]]) -> bool:
        for frame, slot, value in self.parts:
            try:
                if cf.observe(frame, state, slot) != value:
                    return False
            except cf.FrameError:
                return False
        return True


def conjunction_goals(machine: str, machine_obj: Any, atoms: Sequence[Any]) -> list[Conjunction]:
    """Two-frame goals this machine's own atoms can produce, one frame at a time.

    Step A: execute each atom and record which frames moved. Step B: pick the pairs of frames no
    single atom moved together. Those are the goals that *require* a sequence, which is the whole
    point -- a conjunction one atom satisfies is a one-step goal wearing two clauses.
    """
    machine_obj.reset()
    start = read(machine_obj)
    per_atom: dict[str, list[tuple[tuple[str, str], str | None, Any]]] = {}
    for atom in atoms:
        machine_obj.reset()
        before = read(machine_obj)
        execute(atom, machine_obj, room.cell_args(list(before), "TARGET_ABSENT"))
        after = read(machine_obj)
        machine_obj.reset()
        moved = []
        for frame in ALL_FRAMES:
            for slot in slots_of(before, frame):
                try:
                    if cf.moved(before, after, frame, slot):
                        moved.append((frame, slot, cf.observe(frame, after, slot)))
                        break
                except cf.FrameError:
                    continue
        per_atom[atom.ident] = moved
    goals: list[Conjunction] = []
    seen: set[tuple] = set()
    for one, two in itertools.combinations(sorted(per_atom), 2):
        for a in per_atom[one]:
            for b in per_atom[two]:
                if a[0] == b[0]:
                    continue
                key = (a[0], b[0])
                if key in seen:
                    continue
                target = Conjunction(machine, f"{a[0][0]}@{a[0][1]}+{b[0][0]}@{b[0][1]}",
                                     (a, b))
                if not target.holds(start):
                    seen.add(key)
                    goals.append(target)
    return goals


def solve_sequence(goal: Conjunction, machine: Any, atoms: Sequence[Any], *,
                   depth: int = 2, mode: str = "blind") -> dict[str, Any]:
    """Find a sequence that makes the conjunction hold, and count every execution it spends.

    `prune_by_frames` restricts the root candidates to atoms whose measured effect moves a frame
    the goal is stated on. That is a prior over actions derived from the goal itself -- exactly the
    mechanism `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK` ranks first -- and the cost of computing the
    prior is counted in the same currency as the search, so a prior that does not pay for itself
    shows up as a loss.
    """
    executions = 0
    machine.reset()
    # the prior's own cost: one execution per atom to see which frames it moves. Paid by PRUNE and
    # ORDER alike, so a prior that does not pay for itself shows up as a loss in the same column.
    effects: dict[str, list[tuple[str, str]]] = {}
    if mode in ("prune", "order"):
        for atom in atoms:
            machine.reset()
            before = read(machine)
            execute(atom, machine, room.cell_args(list(before), "TARGET_ABSENT"))
            after = read(machine)
            executions += 1
            effects[atom.ident] = [f for f in ALL_FRAMES
                                   if any(cf.moved(before, after, f, s)
                                          for s in slots_of(before, f))]
        machine.reset()
    wanted_frames = {part[0] for part in goal.parts}
    if mode == "prune":
        candidates = [a for a in atoms
                      if wanted_frames & set(effects.get(a.ident, []))]
    elif mode == "order":
        candidates = sorted(atoms, key=lambda a: 0 if wanted_frames & set(
            effects.get(a.ident, [])) else 1)
    else:
        candidates = list(atoms)
    for sequence in itertools.product(candidates, repeat=depth):
        machine.reset()
        for atom in sequence:
            execute(atom, machine, room.cell_args(machine.read(), "TARGET_ABSENT"))
            executions += 1
        reached = goal.holds(read(machine))
        machine.reset()
        if reached:
            return {"verdict": "PLAN_FOUND", "sequence": [a.ident for a in sequence],
                    "executions": executions, "candidates_at_the_root": len(candidates),
                    "mode": mode}
    machine.reset()
    return {"verdict": "NO_PLAN_AT_THIS_DEPTH", "sequence": None, "executions": executions,
            "candidates_at_the_root": len(candidates), "mode": mode}


# =============================================================================================
# the blind spot
# =============================================================================================

def blind_spot(root: pathlib.Path) -> dict[str, Any]:
    room_dir = root / "BLIND"
    room_dir.mkdir(parents=True, exist_ok=True)
    path = room_dir / "seed"
    path.write_text(room.ALPHA, encoding="utf-8")
    subprocess.run(["chmod", "600", str(path)], check=False)
    before = ((path.name, path.read_text(encoding="utf-8")),)
    subprocess.run(["chmod", "755", str(path)], check=False)
    after = ((path.name, path.read_text(encoding="utf-8")),)
    mode = subprocess.run(["stat", "-c", "%a", str(path)], capture_output=True, text=True)
    moved = [f for f in ALL_FRAMES if any(cf.moved(before, after, f, s)
                                          for s in slots_of(before, f))]
    return {"reading_changed": before != after, "mode_after": mode.stdout.strip(),
            "frames_that_see_the_change": [list(f) for f in moved],
            "the_vocabulary_can_state_it": bool(moved),
            "note": "chmod 600 -> 755 is a real change to real state. Every frame here is blind "
                    "to it, and the instrument says so instead of guessing."}


# =============================================================================================
# main
# =============================================================================================

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="the frame crosses the machine")
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--pairs", type=int, default=30,
                        help="how many of a goal's judged pairs the identification may spend")
    parser.add_argument("--machines", nargs="*")
    parser.add_argument("--max-sequences", type=int, default=800,
                        help="a sequence budget, so an unreachable depth is reported as such")
    options = parser.parse_args(argv)
    started = time.time()

    builds = room.all_machines()
    names = options.machines or sorted(builds)
    builds = {k: v for k, v in builds.items() if k in names}

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in builds:
            (root / name).mkdir(parents=True, exist_ok=True)
        cells, notes = probe_cells(builds, root)

        machines: dict[str, Any] = {}
        atoms: dict[str, list[Any]] = {}
        shallow: dict[str, list[State]] = {}
        deep: dict[str, list[State]] = {}
        for name in sorted(builds):
            machine = builds[name](root / name)
            machine.reset()
            machines[name] = machine
            atoms[name] = list(machine.atoms)
            shallow[name] = run_pool(machine, 2)
            if options.depth > 2:
                deep[name] = run_pool(machine, options.depth)

        goals: dict[str, list[Goal]] = {
            name: goals_for_machine(name, machines[name], atoms[name], shallow[name])
            for name in sorted(builds)}

        # ---- L1 ------------------------------------------------------------------------------
        l1 = stateability(cells, notes)

        # ---- L2, per machine, with a leave-one-machine-out prior ------------------------------
        # The prior is built from what the OTHER machines' judged runs taught, and it is only
        # ever used to ORDER hypotheses. A prior cannot change how many labelled runs identify
        # the truth; it changes how right the agent is while it waits, and that is measured too.
        l2: dict[str, Any] = {}
        for name in sorted(builds):
            space = hypothesis_space(read(machines[name]))
            machines[name].reset()
            trained: list[tuple[str, str]] = []
            for other in sorted(builds):
                if other == name:
                    continue
                other_space = hypothesis_space(read(machines[other]))
                machines[other].reset()
                for goal in goals[other]:
                    evidence = labelled_runs(goal, shallow[other])
                    got = identify(canonical_order(other_space), goal, evidence,
                                   shallow[other], shallow[other])
                    if got.get("identified"):
                        trained.append(goal.frame)
            rows = []
            reachable: list[Goal] = []
            _seen_goal: set[tuple] = set()
            for goal in goals[name]:
                if goal.frame in _seen_goal:
                    continue
                _seen_goal.add(goal.frame)
                reachable.append(goal)
            for goal in reachable[:6]:
                evidence = labelled_runs(goal, shallow[name])
                rows.append({
                    "goal": goal.name, "frame": list(goal.frame), "slot": goal.slot,
                    "runs_available": len(evidence),
                    "without_prior": identify(canonical_order(space), goal, evidence,
                                              shallow[name], deep.get(name) or shallow[name]),
                    "with_prior": identify(prior_order(trained, space), goal, evidence,
                                           shallow[name], deep.get(name) or shallow[name]),
                    "prior_top_hypothesis": what_a_prior_buys(
                        prior_order(trained, space), goal, evidence,
                        deep.get(name) or shallow[name]),
                })
            l2[name] = {
                "goals": len(goals[name]),
                "distinct_frames_reachable": len(reachable),
                "identified_without_prior": sum(1 for r in rows
                                                if r["without_prior"]["identified"]),
                "identified_with_prior": sum(1 for r in rows
                                             if r["with_prior"]["identified"]),
                "top_correct_before_any_prior": sum(
                    1 for r in rows if r["prior_top_hypothesis"]["after_0"][
                        "top_behaves_like_the_goal"]),
                "top_correct_after_one_run_no_prior": sum(
                    1 for r in rows if r["without_prior"].get("names_the_goals_frame")),
                "rows": rows,
                "prior_frames_from_other_machines": [list(f) for f in trained],
            }

        # ---- L3, the crossing ----------------------------------------------------------------
        # A frame is learned on machine A from A's labelled runs. Only the frame crosses: no
        # atom identifier, no literal, no command, no value. On machine B the agent reads B,
        # executes each atom once (a counted cost), and answers. B's reader judges.
        l3: list[dict[str, Any]] = []
        excluded_already_true = 0
        for source in sorted(builds):
            if not goals[source]:
                continue
            sources_frames: list[tuple[str, str]] = []
            for goal in goals[source]:
                if goal.frame not in sources_frames:
                    sources_frames.append(goal.frame)
            for frame in sources_frames[:3]:
                exemplar_goal = next(g for g in goals[source] if g.frame == frame)
                learned = learn_frame(exemplar_goal, shallow[source],
                                      hypothesis_space(read(machines[source])))
                machines[source].reset()
                carried = learned["carried"]
                exemplar = next((s for s in shallow[source] if holds(exemplar_goal, s)), None)
                foreign_atom = exemplar_goal.atom
                for target in sorted(builds):
                    if target == source:
                        continue
                    target_goal, why = _target_goal(frame, target, machine=machines[target],
                                                    atoms=atoms[target])
                    if target_goal is None:
                        l3.append({"source_machine": source, "target_machine": target,
                                   "carried_frame": list(frame), "FRAME": f"NOT_A_TASK__{why}",
                                   "EXEMPLAR": "n/a", "REPLAY": "n/a"})
                        continue
                    machines[target].reset()
                    if target_goal.holds(read(machines[target])):
                        excluded_already_true += 1
                        l3.append({"source_machine": source, "target_machine": target,
                                   "carried_frame": list(frame),
                                   "FRAME": "EXCLUDED__GOAL_ALREADY_TRUE_AT_RESET",
                                   "EXEMPLAR": "n/a", "REPLAY": "n/a"})
                        continue
                    answer = answer_on_target(target_goal, carried, machines[target],
                                              atoms[target])
                    blind = answer_on_target(target_goal, carried, machines[target],
                                             atoms[target], blind=True)
                    control_exemplar = exemplar_control(exemplar or (), atoms[target],
                                                        machines[target])
                    control_replay = replay_control(foreign_atom, atoms[target])
                    l3.append({
                        "source_machine": source, "target_machine": target,
                        "carried_frame": list(frame),
                        "target_slot": target_goal.slot,
                        "frame_identified_exactly": learned["identification"]["identified"],
                        "FRAME": answer["verdict"], "frame_probes": answer.get("probes"),
                        "FRAME_picked_the_generating_atom":
                            answer.get("picked_the_atom_the_goal_was_generated_from"),
                        "BLIND": blind["verdict"],
                        "BLIND_picked_the_generating_atom":
                            blind.get("picked_the_atom_the_goal_was_generated_from"),
                        "EXEMPLAR": control_exemplar["verdict"],
                        "REPLAY": control_replay["verdict"],
                    })

        # ---- L4, depth ------------------------------------------------------------------------
        # A frame is chosen on the shallow pool and then asked the same question on the deeper
        # one. The failure mode is the one this tree measured as F5: sufficiency is relative to
        # the runs you could afford, and a deeper run is not a bigger sample -- it is a new case.
        l4: list[dict[str, Any]] = []
        if deep:
            for name in sorted(builds):
                for user_goal in user_goals(name, machines[name], atoms[name])[:8]:
                    shallow_runs = [(st, user_goal.holds(st)) for st in shallow[name]]
                    deep_runs = [(st, user_goal.holds(st)) for st in deep[name]]
                    chosen = sufficient_frame(user_goal, shallow[name])
                    row = {"machine": name, "goal": user_goal.name,
                           "chosen_on_depth2": chosen,
                           "runs_depth2": len(shallow_runs), "runs_deep": len(deep_runs),
                           "depth": options.depth}
                    if chosen.get("frame"):
                        frame = tuple(chosen["frame"])
                        row["collisions_at_depth2"] = collisions_of(frame, chosen.get("slot"),
                                                                    shallow_runs)
                        row["collisions_on_the_deeper_pool"] = collisions_of(
                            frame, chosen.get("slot"), deep_runs)
                        row["witness_on_the_deeper_pool"] = witness_pair(
                            frame, chosen.get("slot"), deep_runs)
                    l4.append(row)

        # ---- L5, composition -----------------------------------------------------------------
        # Two depths, because "cut the branching factor" is a claim about an EXPONENT and an
        # exponent cannot be read off one point. A budget cap is applied so a test that is
        # out of reach is reported as out of reach rather than run until the sun sets.
        l5: list[dict[str, Any]] = []
        for depth in (2, 3):
            for name in sorted(builds):
                goals_here = conjunction_goals(name, machines[name], atoms[name])[:2]
                for goal in goals_here:
                    row: dict[str, Any] = {"machine": name, "goal": goal.name, "depth": depth}
                    for mode in ("blind", "prune", "order"):
                        if len(atoms[name]) ** depth > options.max_sequences:
                            row[mode.upper()] = {"verdict": "OUT_OF_REACH__MORE_SEQUENCES_"
                                                            "THAN_THE_BUDGET_ALLOWS",
                                                 "executions": 0,
                                                 "candidates_at_the_root": len(atoms[name])}
                            continue
                        row[mode.upper()] = solve_sequence(goal, machines[name], atoms[name],
                                                           depth=depth, mode=mode)
                    l5.append(row)

        blind = blind_spot(root)

    def tally(rows: Sequence[dict[str, Any]], key: str) -> dict[str, int]:
        return dict(collections.Counter(row.get(key, "ABSENT") for row in rows))

    report = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "machines": notes,
        "L1_stateability": l1,
        "L2_identification": l2,
        "L3_crossing": {"rows": l3, "FRAME": tally(l3, "FRAME"),
                        "FRAME_picked_the_generating_atom": sum(
                            1 for r in l3 if r.get("FRAME_picked_the_generating_atom")),
                        "BLIND": tally(l3, "BLIND"),
                        "BLIND_picked_the_generating_atom": sum(
                            1 for r in l3 if r.get("BLIND_picked_the_generating_atom")),
                        "EXEMPLAR": tally(l3, "EXEMPLAR"), "REPLAY": tally(l3, "REPLAY")},
        "L4_depth": {"rows": l4,
                     "goals": len(l4),
                     "sufficient_on_the_shallow_pool": sum(
                         1 for r in l4 if r.get("chosen_on_depth2", {}).get("frame")),
                     "collided_on_the_deeper_pool": sum(
                         1 for r in l4 if r.get("collisions_on_the_deeper_pool", 0)),
                     "witnesses": sum(1 for r in l4 if r.get("witness_on_the_deeper_pool")),
                     "rows_examined": len(l4)},
        "L5_composition": {
            "goals": len(l5),
            **{f"by_depth_{d}": {mode: sum(
                    1 for r in l5 if r["depth"] == d and r[mode]["verdict"] == "PLAN_FOUND")
                    for mode in ("BLIND", "PRUNE", "ORDER")} for d in (2, 3)},
            **{f"executions_by_depth_{d}": {mode: sum(
                    r[mode]["executions"] for r in l5 if r["depth"] == d)
                    for mode in ("BLIND", "PRUNE", "ORDER")} for d in (2, 3)},
            **{f"{mode}_plans_found": sum(1 for r in l5 if r[mode]["verdict"] == "PLAN_FOUND")
               for mode in ("BLIND", "PRUNE", "ORDER")},
            **{f"{mode}_executions": sum(r[mode]["executions"] for r in l5)
               for mode in ("BLIND", "PRUNE", "ORDER")},
            "plans_lost_by_pruning": sum(1 for r in l5 if r["BLIND"]["verdict"] == "PLAN_FOUND"
                                         and r["PRUNE"]["verdict"] != "PLAN_FOUND"),
            "plans_lost_by_ordering": sum(1 for r in l5 if r["BLIND"]["verdict"] == "PLAN_FOUND"
                                          and r["ORDER"]["verdict"] != "PLAN_FOUND"),
            "rows": l5,
        },
        "blind_spot": blind,
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "cells_executed": len(cells),
                 "runs_executed": sum(len(v) for v in shallow.values())
                 + sum(len(v) for v in deep.values()),
                 "duration_s": round(time.time() - started, 2)},
    }
    text = json.dumps(report, indent=2, default=str)
    pathlib.Path(options.out).write_text(text, encoding="utf-8")
    if options.receipt:
        pathlib.Path(options.receipt).write_text(text, encoding="utf-8")
    summary = {
        "L1": {k: {"old_vocab_sees": v["effects_stateable_under_the_old_vocabulary"],
                   "old_vocab_cannot_name": v["effects_NOT_stateable_under_the_old_vocabulary"]}
               for k, v in l1.items()},
        "L2": {k: {"goals": v["goals"],
                   "identified_without_prior": v["identified_without_prior"],
                   "identified_with_prior": v["identified_with_prior"],
                   "top_correct_before_any_run": v["top_correct_before_any_prior"]}
               for k, v in l2.items()},
        "L3": report["L3_crossing"]["FRAME"], "L3_exemplar": report["L3_crossing"]["EXEMPLAR"],
        "L3_replay": report["L3_crossing"]["REPLAY"],
        "L4": {k: v for k, v in report["L4_depth"].items() if k != "rows"},
        "blind_spot_can_state_it": blind["the_vocabulary_can_state_it"],
        "cost": report["cost"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
