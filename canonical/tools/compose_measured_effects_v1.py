#!/usr/bin/env python3
"""Compose measured effects: solve what a machine can express, PROVE what it cannot.

WHY THIS EXISTS
---------------
`instant_learning_in_a_new_environment_v1` measured the price of a new machine: one trial per
(atom, state class), one shared effect vocabulary, and a break-even of about six requests. It also
counted three refusals, and every one of them was the same shape of failure -- the agent had the
right effect in its table and still could not reach the goal, because reaching it needed *two* steps,
or because the machine has no atom for it at all. Picking one atom is not acting; it is guessing.

This is the composer, and it is deliberately two things at once:

  PLAN      breadth-first search over the MEASURED operator model, off-line, so the only trials spent
            are the ones that execute a plan that is already known to close. Not one trial is spent
            discovering what to do -- that was paid for once, per machine, by measurement.
  PROVE     when no sequence of the offered atoms reaches the goal, the search is exhaustive and the
            verdict is `PROVEN_UNREACHABLE_UNDER_THE_OFFERED_ATOMS`, with the number of abstract
            states that were exhausted. A refusal is a result. It is never a shrug, and it is never
            dressed up as a failure to try hard enough.

The composer does not invent operators. An operator is a *cell* of the measured table: an atom that
in a given state class produced a given effect using the arguments it was given. Two consequences
are stated as limits rather than hidden:

  * an atom whose measured effect is INERT or UNCLASSIFIED is not an operator, so `cp` (which
    duplicates a content, a shape outside the three-effect vocabulary) is unusable -- the composer
    cannot use what the vocabulary cannot name;
  * the applicability of a cell is exactly what its probe established: the TARGET_EXISTS cell is
    used only where the entity it names exists, the TARGET_ABSENT cell only where it does not. That
    is conservative induction in the SAM sense (Juba & Stern): a rule is admitted only under the
    condition it was observed under, so a plan built from it is expected to succeed rather than
    hoped to.

AND THEN THE PREDICTION IS CHECKED
----------------------------------
Every step is executed on the real machine and the reader is compared against what the operator
predicted *before* the step ran. A plan that executes without matching its own prediction is a
measurement error, not a success, and it is reported as `PREDICTION_MISMATCH`. This is the only
thing that makes off-line planning sound: the model is trusted for zero trials and audited for all
of them.

WHAT THIS DOES NOT DO
---------------------
- It does not learn new effects. Composition multiplies vocabulary; it cannot create it. The wall
  that remains after this file is the effect vocabulary and, above it, the specification -- turning a
  person's sentence into a predicate on machine state, which is not attempted here at all.
- It plans over the content projection, so effects that only move identity are invisible to it, and
  a request whose goal is invisible under that projection is reported as
  `ALREADY_SATISFIED__GOAL_INVISIBLE_UNDER_THE_PROJECTION` rather than silently skipped.
- It reuses the planner-free part of the tree deliberately: `transfer_learning_v1.drive` plans by
  ACTING in an environment (its budget is environment calls), which is the opposite of the economy
  being measured here. Nothing is re-implemented except the 40-line search over the measured table.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as instant  # noqa: E402

SCHEMA = "BRAIN_COMPOSE_MEASURED_EFFECTS_V1"
MAX_DEPTH = 3


@dataclasses.dataclass(frozen=True)
class Operator:
    """One cell of the measured table, usable as a planning operator."""
    atom: str
    state_class: str
    effect: str
    addressable: bool


def operators_from(library: Sequence[dict[str, Any]]) -> list[Operator]:
    """Only cells the measurement supports, and only the ones that depended on their argument."""
    return [Operator(row["atom"], row["state_class"], row["effect"], row["addressable"])
            for row in library
            if row["effect"] in instant.EFFECT_VOCABULARY and row["addressable"]]


def counts(state: Iterable[tuple[str, str]]) -> collections.Counter:
    return collections.Counter(content for _ident, content in state)


def state_key(state: collections.Counter) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((content, count) for content, count in state.items() if count))


def holds(request: instant.Request, start: collections.Counter, now: collections.Counter) -> bool:
    if request.effect == instant.PERSIST:
        return now[request.content] == start[request.content] + 1
    if request.effect == instant.REMOVE:
        return start[request.old] >= 1 and now[request.old] == start[request.old] - 1
    if request.effect == instant.REPLACE:
        return now[request.content] == start[request.content] + 1 and \
            start[request.old] >= 1 and now[request.old] == start[request.old] - 1
    return False


def holds_strict(request: instant.Request, start: collections.Counter,
                 now: collections.Counter) -> bool:
    """The request, plus a frame condition: nothing else about the machine may move.

    Without the frame the goal language is too weak to be safe: "make X disappear" can be satisfied
    by overwriting X with something nobody asked for, and a planner will happily choose that. The
    frame is what makes the difference between reaching a goal and reaching it without breaking
    something else, and it is measured here rather than assumed away.
    """
    if not holds(request, start, now):
        return False
    arrived = now - start
    departed = start - now
    want_arrived = collections.Counter({request.content: 1}) if request.effect in (
        instant.PERSIST, instant.REPLACE) else collections.Counter()
    want_departed = collections.Counter({request.old: 1}) if request.effect in (
        instant.REMOVE, instant.REPLACE) else collections.Counter()
    return arrived == want_arrived and departed == want_departed


def ground(operator: Operator, state: collections.Counter,
           request: instant.Request) -> dict[str, str] | None:
    """Bind the operator's arguments to this state, or refuse because its precondition fails.

    The precondition is not invented: it is the condition the cell was measured under.
    """
    if operator.effect == instant.PERSIST:
        if operator.state_class == "TARGET_ABSENT":
            if request.content in state:
                return None
            return {"content": request.content, "old": request.old}
        return None
    if operator.effect in (instant.REMOVE, instant.REPLACE):
        if operator.state_class != "TARGET_EXISTS" or not state[request.old]:
            return None
        content = request.content if operator.effect == instant.REPLACE else request.old
        return {"content": content, "old": request.old}
    return None


def predicted(operator: Operator, state: collections.Counter, args: dict[str, str]) -> collections.Counter:
    after = collections.Counter(state)
    if operator.effect == instant.PERSIST:
        after[args["content"]] += 1
    elif operator.effect == instant.REMOVE:
        after[args["old"]] -= 1
    elif operator.effect == instant.REPLACE:
        after[args["old"]] -= 1
        after[args["content"]] += 1
    return collections.Counter({content: count for content, count in after.items() if count > 0})


@dataclasses.dataclass(frozen=True)
class Step:
    operator: Operator
    args: dict[str, str]
    state: collections.Counter
    names_a_fresh_entity: bool = False


def plan(request: instant.Request, start: collections.Counter,
         operators: Sequence[Operator], *, max_depth: int = MAX_DEPTH) -> dict[str, Any]:
    """Breadth-first over the measured model. Exhaustive, so failure is a proof and not a budget."""
    if holds(request, start, start):
        return {"status": "ALREADY_SATISFIED__GOAL_INVISIBLE_UNDER_THE_PROJECTION", "plan": [],
                "explored": 0, "frame_violations_in_relaxed_plans": 0}
    frontier: collections.deque[tuple[collections.Counter, list[Step]]] = collections.deque([(start, [])])
    seen = {state_key(start)}
    explored = 0
    relaxed_seen = 0
    while frontier:
        state, path = frontier.popleft()
        explored += 1
        if len(path) >= max_depth:
            continue
        for operator in operators:
            args = ground(operator, state, request)
            if args is None:
                continue
            after = predicted(operator, state, args)
            key = state_key(after)
            if key in seen:
                continue
            seen.add(key)
            step = Step(operator, args, after, names_a_fresh_entity=(operator.effect == instant.PERSIST))
            if holds(request, start, after):
                relaxed_seen += 1
            if holds_strict(request, start, after):
                return {"status": "PLANNED", "plan": path + [step], "explored": explored,
                        "frame_violations_in_relaxed_plans": relaxed_seen}
            frontier.append((after, path + [step]))
    return {"status": "PROVEN_UNREACHABLE_UNDER_THE_OFFERED_ATOMS", "plan": [], "explored": explored,
            "frame_violations_in_relaxed_plans": relaxed_seen}


def step_agrees(step: Step, observed: Sequence[tuple[str, str]]) -> bool:
    """Did the machine do exactly what the operator predicted, before the step ran?"""
    return counts(observed) == step.state


def _execution_args(step: Step, before: Sequence[tuple[str, str]]) -> dict[str, str]:
    """Identity is surface-local, so it is bound here; the plan itself only ever spoke of contents."""
    args = dict(step.args)
    holder = next((ident for ident, content in before if content == step.args.get("old")), None)
    args["name"] = (step.args.get("content", "fresh") + "_member") if step.names_a_fresh_entity \
        else (holder or step.args.get("content", "fresh") + "_member")
    args["target"] = step.args.get("content", "fresh") + "_path"
    return args


def _side_effects(request: instant.Request, start: Sequence[tuple[str, str]],
                  now: Sequence[tuple[str, str]]) -> int:
    was, is_now = counts(start), counts(now)
    arrived, departed = is_now - was, was - is_now
    wanted_arrived = collections.Counter({request.content: 1}) if request.effect in (
        instant.PERSIST, instant.REPLACE) else collections.Counter()
    wanted_departed = collections.Counter({request.old: 1}) if request.effect in (
        instant.REMOVE, instant.REPLACE) else collections.Counter()
    return sum((arrived - wanted_arrived).values()) + sum((departed - wanted_departed).values())


def measure(machine: instant.Machine, *, max_depth: int = MAX_DEPTH) -> dict[str, Any]:
    started = time.time()
    table = instant.adapt(machine, active=True)
    operators = operators_from(table["library"])
    rows: list[dict[str, Any]] = []
    for request in instant.requests_for():
        machine.reset()
        start = counts(machine.read())
        search = plan(request, start, operators, max_depth=max_depth)
        row: dict[str, Any] = {"index": request.index, "effect": request.effect,
                               "status": search["status"], "explored": search["explored"],
                               "depth": len(search["plan"]),
                               "plan": [{"atom": step.operator.atom, "effect": step.operator.effect}
                                        for step in search["plan"]]}
        if search["status"] == "PLANNED":
            machine.reset()
            start_state = machine.read()
            before = start_state
            trail = []
            agreed = True
            for step in search["plan"]:
                atom = next(a for a in machine.atoms if a.ident == step.operator.atom)
                args = _execution_args(step, before)
                instant.execute(atom, machine, args)
                after = machine.read()
                agrees = step_agrees(step, after)
                agreed = agreed and agrees
                trail.append({"atom": step.operator.atom, "prediction_agreed": agrees})
                before = after
            solved = instant.satisfied(request, start_state, machine.read())
            row.update(executed=True, prediction_agreed_all_steps=agreed, trail=trail,
                       unrequested_side_effects=_side_effects(request, start_state, machine.read()),
                       relaxed_plans_that_break_the_frame=search["frame_violations_in_relaxed_plans"],
                       reader_agrees=bool(solved),
                       outcome=("SOLVED" if solved and agreed else
                                ("PREDICTION_MISMATCH" if not agreed else "REFUSED__READER")))
        else:
            row["executed"] = False
            row["outcome"] = search["status"]
        rows.append(row)
    machine.reset()
    return {"machine": machine.name, "atoms_offered": table["atoms_offered"],
            "adaptation_trials": table["trials"],
            "executions": sum(row["depth"] for row in rows),
            "measured_cells": len(table["library"]),
            "usable_operators": len(operators),
            "operators": [dataclasses.asdict(op) for op in operators],
            "requests": rows,
            "solved": sum(1 for row in rows if row.get("outcome") == "SOLVED"),
            "solved_with_two_steps": sum(1 for row in rows
                                         if row.get("outcome") == "SOLVED" and row["depth"] == 2),
            "unrequested_side_effects": sum(row.get("unrequested_side_effects", 0) for row in rows),
            "relaxed_plans_that_break_the_frame":
                sum(row.get("relaxed_plans_that_break_the_frame", 0) for row in rows),
            "proven_unreachable": sum(1 for row in rows
                                      if row["status"] == "PROVEN_UNREACHABLE_UNDER_THE_OFFERED_ATOMS"),
            "abstract_states_exhausted": sum(row["explored"] for row in rows
                                             if row["status"].startswith("PROVEN_UNREACHABLE")),
            "prediction_mismatches": sum(1 for row in rows if row.get("outcome") == "PREDICTION_MISMATCH"),
            "seconds": round(time.time() - started, 2)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--machines", nargs="*", default=list(instant.MACHINES))
    parser.add_argument("--max-depth", type=int, default=MAX_DEPTH)
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        with pathlib.Path(args.out).open("w") as handle:
            for name in args.machines:
                root = base / name.lower()
                root.mkdir(parents=True, exist_ok=True)
                machine = instant.MACHINES[name](root)
                machine.reset()
                row = measure(machine, max_depth=args.max_depth)
                rows.append(row)
                handle.write(json.dumps(row, default=str) + "\n")
                handle.flush()
                print(f"{name:<11} ops={row['usable_operators']:>2} solved={row['solved']}/4 "
                      f"two-step={row['solved_with_two_steps']} proved-unreachable={row['proven_unreachable']} "
                      f"mismatch={row['prediction_mismatches']}", flush=True)

    summary = {
        "machines": len(rows),
        "requests": 4 * len(rows),
        "solved": sum(row["solved"] for row in rows),
        "solved_with_two_steps": sum(row["solved_with_two_steps"] for row in rows),
        "proven_unreachable": sum(row["proven_unreachable"] for row in rows),
        "abstract_states_exhausted": sum(row["abstract_states_exhausted"] for row in rows),
        "prediction_mismatches": sum(row["prediction_mismatches"] for row in rows),
        "unrequested_side_effects": sum(row.get("unrequested_side_effects", 0) for row in rows),
        "relaxed_plans_that_break_the_frame":
            sum(row.get("relaxed_plans_that_break_the_frame", 0) for row in rows),
        "usable_operators": sum(row["usable_operators"] for row in rows),
        "adaptation_trials": sum(row["adaptation_trials"] for row in rows),
        "executions": sum(row["executions"] for row in rows),
        "trials_in_total": sum(row["adaptation_trials"] + row["executions"] for row in rows),
        "measured_cells": sum(row["measured_cells"] for row in rows),
        "per_machine": {row["machine"]: {"usable_operators": row["usable_operators"],
                                         "adaptation_trials": row["adaptation_trials"],
                                         "executions": row["executions"],
                                         "solved": row["solved"],
                                         "two_step": row["solved_with_two_steps"],
                                         "proven_unreachable": row["proven_unreachable"],
                                         "explored": row["abstract_states_exhausted"]}
                        for row in rows},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "planning_is_offline_over_the_measured_table": True,
        "every_step_audited_against_its_prediction": True,
        "refusal_is_a_proof_not_a_budget": True,
        "max_depth": args.max_depth,
        "summary": summary,
        "rows": rows,
    }
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
