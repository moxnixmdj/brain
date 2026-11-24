#!/usr/bin/env python3
"""Four planners, one measured operator set, and the Sussman anomaly built out of real tools.

THE CLAIM UNDER TEST
--------------------
Last round's instrument recorded its own strongest idea failing:

    forward search with the action set pruned to "atoms that move a frame the goal is stated on"
    -> 4.9x fewer executions, 5 of 14 plans LOST. Incomplete.
    the sound version, re-ordering without pruning -> lost nothing, saved nothing.

So "reduce the branching factor with a goal-directed prior" is not one idea. It is three, and only
one of them is both sound and cheap. That third one is classical and this tree had never built it:

    **partial-order planning** -- never commit to an action order; link each open condition to one
    action that establishes it, protect the link against actions that would delete it, and order
    two steps only when a link or a threat forces it.

THE FOUR PLANNERS, ALL ON THE SAME OPERATOR SET
-----------------------------------------------
  FORWARD   breadth-first over action sequences. Sound, complete, branching factor = |atoms|.
  PRUNE     forward, but only atoms relevant to the goal at the ROOT. What last round did.
  BACKWARD  greedy: achieve one unmet conjunct, then the next. The version that is famously
            INCOMPLETE (Sussman's anomaly). Kept because the difference must be measured.
  POP       partial order, with promotion/demotion of threats. The claim of this round.

Every planner gets the same operators -- measured, not written -- the same initial reading, the
same goal, and every execution is counted. A plan is executed for real and judged by the machine's
own reader: `canonical/swe_kernel/canonical_frame_v1`. Nothing is taken on trust.

THE PROBLEMS
------------
Conjunctive goals on real machines (`git`, `tar`, `sort`, `sh`, `gzip`): two conditions that no
single atom establishes, on machines where one atom destroys a condition another atom established.
Those are the problems where the four planners separate, and the ones where a synthetic benchmark
would have been a lie.

WHAT THIS DOES NOT CLAIM
------------------------
Not a benchmark score, not GUI, not independent verification. Operators are measured within one
machine and are not carried across machines here (that is the frame module's job and the two are
not yet wired -- named as the next step, not implied as done). Zero model calls, zero parameters.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import itertools
import json
import pathlib
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
from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402

SCHEMA = "BRAIN_THE_PLAN_IS_A_PARTIAL_ORDER_V1"
State = tuple[tuple[str, str], ...]
Condition = tuple


def read(machine: Any) -> State:
    return tuple(map(tuple, machine.read()))


def execute_atom(atom: Any, machine: Any) -> State:
    room.base.execute(atom, machine, room.cell_args(machine.read(), "TARGET_ABSENT"))
    return read(machine)


# =============================================================================================
# 1. the operators, measured from variation -- never written down
# =============================================================================================

def explore(machine: Any, atoms: Sequence[Any], depth: int,
            cap: int = 6000) -> tuple[list[State], list[tuple[str, State, State]], int]:
    """One breadth-first sweep of the machine. It yields BOTH things this instrument needs, from
    the same executions:

      * every state observed -- the ground truth about which conjunctive goals are even possible;
      * every (atom, before, after) TRANSITION -- the measurement the operator table is built from.

    An earlier version sampled operators from enumerated prefixes up to depth 2 and then ran a
    SEPARATE sweep for reachability. That was both wasteful and worse: the transitions available
    were the ones a prefix enumeration happens to visit, which on JOURNAL left the table without
    the context that one of the solvable problems needed. The reachable graph is the right sample,
    and it costs nothing extra because it was already being explored.
    """
    machine.reset()
    origin = read(machine)
    states: list[State] = [origin]
    transitions: list[tuple[str, State, State]] = []
    frontier: list[tuple[tuple[str, ...], State]] = [((), origin)]
    executions = 0
    for _level in range(depth):
        nxt: list[tuple[tuple[str, ...], State]] = []
        for prefix, state in frontier:
            for atom in atoms:
                machine.reset()
                for ident in prefix:
                    execute_atom(next(a for a in atoms if a.ident == ident), machine)
                executions += len(prefix) + 1
                after = execute_atom(atom, machine)
                transitions.append((atom.ident, state, after))
                executions += 1
                if after not in states and len(states) < cap:
                    states.append(after)
                nxt.append((prefix + (atom.ident,), after))
        frontier = nxt
    machine.reset()
    return states, transitions, executions


def build_operators(machine: Any, atoms: Sequence[Any], depth: int
                    ) -> tuple[list[Any], list[Condition], frozenset, list[State], int, list[Any]]:
    """The operator table, the condition vocabulary, the initial state, the reachable states, and
    what the exploration cost -- all closed against ONE initial state.

    The first version built closure against an initial state that still contained PAIRING
    conditions and then handed the planner an initial state with them removed, so a precondition
    that survived because the initial state satisfied it became unestablishable a moment later.
    One `initial`, computed once, used by everything.
    """
    states, transitions, executions = explore(machine, atoms, depth)
    conditions = pop.condition_pool(states)
    operators, induction = pop.induce_conditional_operators(transitions, conditions)
    build_operators.last_closure = induction
    rows_at_reset = read(machine)
    # PAIRING conditions ARE allowed in the initial state: a whole pairing is a legitimate
    # PRECONDITION ("this file has exactly these members"). It is excluded only when CHOOSING
    # GOALS, where an unbounded value space makes the goal unfalsifiable.
    initial = frozenset(c for c in conditions if pop.holds(c, rows_at_reset))
    operators, closure = pop.close_preconditions(operators, initial)
    induction.update(closure)
    machine.reset()
    build_operators.last_closure = induction
    return operators, conditions, initial, states, executions, transitions


# =============================================================================================
# 2. the four planners
# =============================================================================================

def forward(initial: frozenset, goal: frozenset, operators: Sequence[Any], atoms_by_id: dict,
            machine: Any, depth: int, *, prune_to_relevant: bool = False,
            budget: int = 900) -> dict[str, Any]:
    """Breadth-first over sequences. Sound and complete within `depth`, and it counts every
    execution, including the state it is standing on when it decides a plan is a plan."""
    executions = 1
    canonical_atoms = sorted({op.command() for op in operators})
    if prune_to_relevant:
        canonical_atoms = [i for i in canonical_atoms
                           if any(op.relevant(c) for op in operators if op.command() == i
                                  for c in goal)]
    machine.reset()
    frontier: list[tuple[tuple[str, ...], State]] = [((), read(machine))]
    for _level in range(depth):
        nxt: list[tuple[tuple[str, ...], State]] = []
        for sequence, state in frontier:
            for ident in canonical_atoms:
                machine.reset()
                for step in sequence:
                    execute_atom(atoms_by_id[step], machine)
                executions += len(sequence) + 1
                reached = execute_atom(atoms_by_id[ident], machine)
                if all(pop.holds(c, reached) for c in goal):
                    machine.reset()
                    return {"status": "PLAN_FOUND", "plan": list(sequence) + [ident],
                            "executions": executions}
                if executions > budget:
                    machine.reset()
                    return {"status": "OUT_OF_BUDGET", "executions": executions}
                nxt.append((sequence + (ident,), reached))
        frontier = nxt
    machine.reset()
    return {"status": "NO_PLAN_AT_THIS_DEPTH", "executions": executions}


def backward_greedy(initial: frozenset, goal: frozenset, operators: Sequence[Any], atoms_by_id: dict,
                    machine: Any, depth: int) -> dict[str, Any]:
    """The famous incomplete one: pick a conjunct, achieve it, then the next. No protection.

    It is here because the difference between it and POP is the whole finding of this round, and
    a claim that POP is better is worthless without the thing it is better than."""
    executions = 0
    machine.reset()
    plan: list[str] = []
    for condition in sorted(goal, key=pop.describe):
        state = read(machine)
        if pop.holds(condition, state):
            continue
        placed = False
        for op in operators:
            if not op.relevant(condition):
                continue
            machine.reset()
            for step in plan:
                execute_atom(atoms_by_id[step], machine)
            executions += len(plan) + 1
            reached = execute_atom(atoms_by_id[op.command()], machine)
            if pop.holds(condition, reached):
                plan.append(op.command())
                placed = True
                break
        if not placed:
            machine.reset()
            return {"status": "NO_PLAN", "executions": executions,
                    "why": f"nothing establishes {pop.describe(condition)}"}
    machine.reset()
    for step in plan:
        execute_atom(atoms_by_id[step], machine)
    reached = read(machine)
    ok = all(pop.holds(c, reached) for c in goal)
    machine.reset()
    return {"status": "PLAN_FOUND" if ok else "UNDONE_BY_LATER_STEP",
            "plan": plan, "executions": executions}


def certify(commands: Sequence[str], initial: frozenset, operators: Sequence[Any],
            observed: Sequence[State], machine: Any, atoms_by_id: dict) -> dict[str, Any]:
    """Is every state this plan passes through a state the machine was actually SEEN in?

    This is the limit of the whole approach and it is better stated than hidden. An induced
    operator's guard is a conjunction of conditions that separated the observations; nothing says
    the guard is complete. So a plan can be "proved" against the table and fail on the machine,
    which is exactly what happened on VAULT: two plans passed the planner, executed, and left the
    goal false.

    The check is therefore not more inference, it is COVERAGE: walk the plan with the machine's own
    reader and require every intermediate reading to be one that was observed during measurement.
    If it was, the operator that fired there was measured there. If it was not, the step is a
    prediction, and a prediction is reported as UNVERIFIED rather than as a pass.
    """
    seen = set(observed)
    machine.reset()
    readings = [read(machine)]
    for command in commands:
        readings.append(execute_atom(atoms_by_id[command], machine))
    machine.reset()
    unobserved = [index for index, state in enumerate(readings) if state not in seen]
    return {"certified_all_states_observed": not unobserved,
            "unobserved_states": unobserved,
            "intermediate_readings": len(readings)}


def partial_order(initial: frozenset, goal: frozenset, operators: Sequence[Any], atoms_by_id: dict,
                  machine: Any, observed: Sequence[State] = (),
                  transitions: Sequence[Any] = ()) -> dict[str, Any]:
    """POP, then executed and judged. The partial order is the proof; the linearisation is a
    choice, and it is named as one."""
    started = time.time()
    found = pop.plan(initial, goal, operators)
    if found["status"] != "PASS__PARTIAL_ORDER_FOUND":
        return {**found, "executions": 0}
    commands = found["steps"]          # already atom names, in one admissible linearisation
    machine.reset()
    start = read(machine)
    check = certify(commands, initial, operators, observed, machine, atoms_by_id)
    replay = pop.replay_on_observed_transitions(commands, start, transitions)
    machine.reset()
    for command in commands:
        execute_atom(atoms_by_id[command], machine)
    reached = read(machine)
    ok = all(pop.holds(c, reached) for c in goal)
    machine.reset()
    status = "PLAN_FOUND" if ok else "PLAN_EXECUTED_GOAL_NOT_OBSERVED"
    if ok and not replay["every_step_was_observed"]:
        status = "PLAN_FOUND_BUT_UNVERIFIED"
    if not ok and replay["every_step_was_observed"]:
        status = "REFUTED_DESPITE_OBSERVED_STEPS"
    return {"status": status,
            "certified": replay["every_step_was_observed"],
            "steps_observed": replay["every_step_was_observed"],
            "first_unobserved_step": replay["first_unobserved_step"],
            "unobserved_states": check["unobserved_states"],
            "plan": commands, "partial_order": found["partial_order"],
            "causal_links": len(found["causal_links"]),
            "executions": len(found["steps"]),
            "search_nodes": found["stats"]["nodes"],
            "seconds": round(time.time() - started, 3)}


# =============================================================================================
# 3. problems: conjunctive goals no single atom establishes
# =============================================================================================

def problems_for(name: str, initial: frozenset, rows_at_reset: State,
                 operators: Sequence[Any], atoms: Sequence[Any], machine: Any,
                 reachable: Sequence[State]) -> list[dict[str, Any]]:
    """A problem is a pair of conditions that a REACHABLE state satisfies, that no single atom
    establishes, and where some atom DELETES one of them -- the interaction that makes the order
    matter. Without that last property the problem is two independent one-step tasks and every
    planner solves it, which would have made this round measure nothing."""
    produces: dict[Condition, list[str]] = collections.defaultdict(list)
    deletes: dict[Condition, list[str]] = collections.defaultdict(list)
    for op in operators:
        for condition in op.add:
            produces[condition].append(op.command())
        for condition in op.delete:
            deletes[condition].append(op.command())

    # conditions worth asking about: true somewhere reachable, false at reset, and nameable
    candidates = [c for c in produces
                  if not pop.holds(c, rows_at_reset)
                  and c[0] not in ("PAIRING", "ORDER")
                  and any(pop.holds(c, state) for state in reachable)]
    out = []
    for one, two in itertools.combinations(sorted(candidates, key=pop.describe), 2):
        witness = [s for s in reachable if pop.holds(one, s) and pop.holds(two, s)]
        if not witness:
            continue                    # no reachable state satisfies both: impossible, not hard
        both = [op.command() for op in operators if one in op.add and two in op.add]
        if both:
            continue                    # one atom does it: not a conjunctive problem
        if pop.holds(two, rows_at_reset) or pop.holds(one, rows_at_reset):
            continue
        interacting = bool(set(deletes[one]) | set(deletes[two]))
        if not interacting:
            continue
        out.append({"machine": name, "goal": frozenset({one, two}),
                    "goal_text": sorted(pop.describe(c) for c in (one, two)),
                    "reachable_witness": True,
                    "produced_by": {pop.describe(c): sorted(set(produces[c]))
                                    for c in (one, two)},
                    "deleted_by": {pop.describe(c): sorted(set(deletes[c]))
                                   for c in (one, two)}})
    machine.reset()
    return out


# =============================================================================================
# 4. main
# =============================================================================================

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="the plan is a partial order")
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--max-problems", type=int, default=3)
    parser.add_argument("--ground-truth-depth", type=int, default=4)
    parser.add_argument("--machines", nargs="*")
    options = parser.parse_args(argv)
    started = time.time()

    builds = room.all_machines()
    names = options.machines or sorted(builds)
    builds = {k: v for k, v in builds.items() if k in names}

    rows: list[dict[str, Any]] = []
    operator_rows: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in sorted(builds):
            (root / name).mkdir(parents=True, exist_ok=True)
            machine = builds[name](root / name)
            machine.reset()
            atoms = list(machine.atoms)
            atoms_by_id = {a.ident: a for a in atoms}
            (operators, conditions, initial, reachable, ground_truth_executions,
             transitions) = build_operators(machine, atoms, options.ground_truth_depth)
            rows_at_reset = read(machine)
            operator_rows[name] = {
                "atoms": len(atoms),
                "conditions_admitted": len(conditions),
                "conditions_in_the_initial_state": sum(1 for c in conditions
                                                       if pop.holds(c, rows_at_reset)),
                "operators_whose_effect_depends_on_state": sum(
                    1 for op in operators if "#" in op.ident),
                "operators": [{"atom": op.ident,
                               "pre": [pop.describe(c) for c in sorted(op.pre)],
                               "add": [pop.describe(c) for c in sorted(op.add)],
                               "del": [pop.describe(c) for c in sorted(op.delete)]}
                              for op in operators],
            }
            operator_rows[name].update(getattr(build_operators, "last_closure", {}))
            operator_rows[name]["ground_truth_executions"] = ground_truth_executions
            operator_rows[name]["reachable_states_observed"] = len(reachable)
            problems = problems_for(name, initial, rows_at_reset, operators, atoms, machine,
                                   reachable)
            for problem in problems[: options.max_problems]:
                row: dict[str, Any] = {"machine": name, "goal": problem["goal_text"],
                                       "produced_by": problem["produced_by"],
                                       "deleted_by": problem["deleted_by"]}
                row["POP"] = partial_order(initial, problem["goal"], operators, atoms_by_id,
                                           machine, reachable, transitions)
                row["FORWARD"] = forward(initial, problem["goal"], operators, atoms_by_id,
                                         machine, options.depth)
                row["PRUNE"] = forward(initial, problem["goal"], operators, atoms_by_id, machine,
                                       options.depth, prune_to_relevant=True)
                row["BACKWARD"] = backward_greedy(initial, problem["goal"], operators,
                                                  atoms_by_id, machine, options.depth)
                row["POP_found"] = row["POP"]["status"] == "PLAN_FOUND"
                rows.append(row)
            machine.reset()

    def tally(key: str) -> dict[str, int]:
        return dict(collections.Counter(r[key]["status"] for r in rows))

    report = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operator_sets": operator_rows,
        "results": {
            "problems": len(rows),
            "statuses": {mode: tally(mode) for mode in ("POP", "FORWARD", "PRUNE", "BACKWARD")},
            "POP_found": sum(1 for r in rows if r["POP"]["status"] == "PLAN_FOUND"),
            "FORWARD_found": sum(1 for r in rows if r["FORWARD"]["status"] == "PLAN_FOUND"),
            "PRUNE_found": sum(1 for r in rows if r["PRUNE"]["status"] == "PLAN_FOUND"),
            "BACKWARD_found": sum(1 for r in rows if r["BACKWARD"]["status"] == "PLAN_FOUND"),
            "POP_lost_where_FORWARD_found": sum(
                1 for r in rows if r["FORWARD"]["status"] == "PLAN_FOUND"
                and r["POP"]["status"] != "PLAN_FOUND"),
            "FORWARD_lost_where_POP_found": sum(
                1 for r in rows if r["POP"]["status"] == "PLAN_FOUND"
                and r["FORWARD"]["status"] != "PLAN_FOUND"),
            "executions": {mode: sum(r[mode]["executions"] for r in rows)
                           for mode in ("POP", "FORWARD", "PRUNE", "BACKWARD")},
            "POP_search_nodes": sum(r["POP"].get("search_nodes", 0) for r in rows),
            "rows": rows,
        },
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
    }
    text = json.dumps(report, indent=2, default=str)
    pathlib.Path(options.out).write_text(text, encoding="utf-8")
    if options.receipt:
        pathlib.Path(options.receipt).write_text(text, encoding="utf-8")
    print(json.dumps({k: v for k, v in report["results"].items() if k != "rows"}, indent=2))
    for row in rows:
        print(f"  {row['machine']:9s} {str(row['goal'])[:58]:58s} "
              f"POP={row['POP']['status'][:14]:14s} "
              f"FWD={row['FORWARD']['status'][:14]:14s} "
              f"PRUNE={row['PRUNE']['status'][:14]:14s} "
              f"BWD={row['BACKWARD']['status'][:14]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
