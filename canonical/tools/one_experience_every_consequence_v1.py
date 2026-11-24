#!/usr/bin/env python3
"""One action in, every consequence out: what one experience buys, and where it stops.

THE QUESTION THIS ANSWERS
-------------------------
The mission's core hypothesis is that an agent only needs to do something once and learns it
permanently. Two words in that sentence are doing all the work and neither had been measured here:
ONCE, and LEARNS. This instrument separates them.

  WHAT ONE EXECUTION BUYS. From a single recorded step, how many other states does the learned
  operator correctly apply in, and -- the number that matters -- is it ever WRONG. A table that is
  right everywhere and refuses often is a capability with a price. A table that is right often and
  wrong once is not safe, and no planning result built on it means anything.

  WHERE IT STOPS. Safety is not free: a safe table cannot cover states it was never shown. The
  literature is explicit that the sample-complexity-optimal safe learner (N-SAM*) is optimal only
  among SAFE learners, so refusals are structural, not a bug to fix later.

THE EXPERIMENT
--------------
For each machine:
  1. explore to collect transitions, then hold out a TEST set of transitions the learner never sees;
  2. learn a safe table from ONE transition per atom (the "1-shot" condition) and from 5 and 10
     (the "few-shot" conditions);
  3. score on the held-out set: coverage and -- the load-bearing number -- WRONG predictions;
  4. plan the same conjunctive goals three ways: with the safe table, with the previous round's
     induced table, and with forward search as the completeness reference;
  5. fork the world: run every plan on a copy of the machine and judge with the machine's reader.

Every plan that is reported has been executed on the real machine. A prediction is never a result.

Zero model calls, zero parameters, zero network.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import shutil
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
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
import the_plan_is_a_partial_order_v1 as racetrack  # noqa: E402

SCHEMA = "BRAIN_ONE_EXPERIENCE_EVERY_CONSEQUENCE_V1"
State = tuple[tuple[str, str], ...]


def read(machine: Any) -> State:
    return tuple(map(tuple, machine.read()))


def execute_atom(atom: Any, machine: Any) -> State:
    room.base.execute(atom, machine, room.cell_args(machine.read(), "TARGET_ABSENT"))
    return read(machine)


def explore(machine: Any, atoms: Sequence[Any], depth: int) -> list[tuple[str, State, State]]:
    """Every (atom, before, after) transition reachable within `depth`, with deduplication by the
    (atom, before) key so the learning set is not inflated by re-running the same step."""
    seen: set[tuple[str, State]] = set()
    transitions: list[tuple[str, State, State]] = []
    frontier: list[tuple[tuple[str, ...], State]] = [((), read(machine))]
    for _level in range(depth):
        nxt = []
        for prefix, state in frontier:
            for atom in atoms:
                machine.reset()
                for ident in prefix:
                    execute_atom(next(a for a in atoms if a.ident == ident), machine)
                after = execute_atom(atom, machine)
                key = (atom.ident, state)
                if key not in seen:
                    seen.add(key)
                    transitions.append((atom.ident, state, after))
                nxt.append((prefix + (atom.ident,), after))
        frontier = nxt
    machine.reset()
    return transitions


def _verdicts(learned: dict[str, Any]) -> dict[str, Any]:
    """What this round established, computed from the receipt rather than written by hand.

    A report that states its conclusions in prose and computes them nowhere is how a failed result
    becomes a success story. These four are the claims, and each is a count.
    """
    safe_labels = ("one_shot", "five_shot", "ten_shot")
    safe_sound = all(learned[name]["scores"][label].get("sound", False)
                     for name in learned for label in safe_labels)
    last_round_wrong = sum(learned[name]["scores"]["induction_from_last_round"]
                           .get("predictions_WRONG", 0) for name in learned)
    probed_wrong = sum(learned[name]["scores"]["one_shot_probed"]
                       .get("predictions_WRONG", 0) for name in learned)
    return {
        "the_safe_table_is_never_wrong": safe_sound,
        "the_previous_induction_was_wrong_this_many_times": last_round_wrong,
        "the_probe_generalizer_was_wrong_this_many_times": probed_wrong,
        "probe_generalizer_is_unsound_and_must_not_be_shipped":
            probed_wrong > 0 or any(
                learned[name]["scores"]["one_shot_probed_under_fire"]
                .get("generalized_predictions_WRONG", 0) > 0 for name in learned),
    }


def _all_atoms_as_identity_operators(atoms: Sequence[Any]):
    """One operator per atom whose `add` is the atom's own name. Forward search only needs the
    operator list to enumerate atoms; it judges success by reading the machine, never the table."""
    return [pop.Operator(atom.ident, frozenset(), frozenset(), frozenset()) for atom in atoms]


def _probe_factory(machine: Any, atoms: Sequence[Any], conditions: Sequence[sam.Condition]):
    """A probe that EXECUTES on the machine and returns the observed effect, or None if the state
    cannot be reached. Shared by every measurement so no two numbers are taken under different
    rules."""
    def probe(atom_ident, state):
        atom = next((a for a in atoms if a.ident == atom_ident), None)
        if atom is None:
            return None
        machine.reset()
        if not forward_to(machine, atoms, state):
            machine.reset()
            return None
        after = execute_atom(atom, machine)
        machine.reset()
        return (frozenset(c for c in conditions
                          if sam.holds(c, after) and not sam.holds(c, state)),
                frozenset(c for c in conditions
                          if sam.holds(c, state) and not sam.holds(c, after)))
    return probe


def _last_round_under_fire(train, probe_states, conditions, machine, atoms) -> dict[str, Any]:
    """The same test, on the previous round's induced table. Same data, same probe, same rules --
    so the comparison is between two learners and not between two experiments."""
    induced = pop.induce_conditional_operators(
        [(atom, before, after) for atom, before, after in train], conditions)[0]
    wrapped = [sam.SafeOperator(op.atom or op.ident, frozenset(op.pre), frozenset(op.add),
                                frozenset(op.delete)) for op in induced if op.pre]
    return sam.generalization_under_fire(wrapped, probe_states,
                                         _probe_factory(machine, atoms, conditions))


def forward_to(machine: Any, atoms: Sequence[Any], target: State, *, depth: int = 3) -> bool:
    """Bring the machine to `target` by breadth-first search over REAL executions.

    A stub returning False here would have made every probe fail and every refusal look like
    evidence. It is implemented because a probe that cannot reach its state is not a test of the
    hypothesis, it is a silent no-op that flatters the learner.
    """
    atoms_by_id = {atom.ident: atom for atom in atoms}
    machine.reset()
    start = read(machine)
    if start == tuple(target):
        return True
    frontier: list[tuple[tuple[str, ...], State]] = [((), start)]
    seen = {start}
    for _level in range(depth):
        nxt = []
        for plan, state in frontier:
            for ident in atoms_by_id:
                machine.reset()
                for step in plan:
                    execute_atom(atoms_by_id[step], machine)
                after = execute_atom(atoms_by_id[ident], machine)
                if after == tuple(target):
                    machine.reset()
                    for step in plan + (ident,):
                        execute_atom(atoms_by_id[step], machine)
                    return True
                if after not in seen:
                    seen.add(after)
                    nxt.append((plan + (ident,), after))
        frontier = nxt
    machine.reset()
    return False


def one_shot(training: Sequence[tuple[str, State, State]], conditions: Sequence[sam.Condition]
             ) -> list[sam.SafeOperator]:
    """Exactly ONE observation per atom -- the smallest possible experience -- then the same safe
    generalization every other condition gets. Nothing is special-cased for the 1-shot case: that is
    the point, because a learner that needs a different procedure for small samples has not shown
    that one experience is enough."""
    first: dict[str, tuple[str, State, State]] = {}
    for transition in training:
        first.setdefault(transition[0], transition)
    observations = [sam.Observation.of(atom, before, after, conditions)
                    for atom, before, after in first.values()]
    table = sam.specific_table(observations, conditions)
    table, _report = sam.generalize(table, observations, conditions)
    return table


def few_shot(training: Sequence[tuple[str, State, State]], conditions: Sequence[sam.Condition],
             count: int, seed: int = 7) -> list[sam.SafeOperator]:
    """The same learner on `count` observations per atom, so 'once' can be compared with 'more'
    rather than asserted to be equal."""
    random.Random(seed).shuffle(grouped := list(training))
    per_atom: dict[str, list[tuple[str, State, State]]] = collections.defaultdict(list)
    for transition in grouped:
        per_atom[transition[0]].append(transition)
    observations = []
    for atom in sorted(per_atom):
        for transition in per_atom[atom][:count]:
            observations.append(sam.Observation.of(*transition, conditions))
    table = sam.specific_table(observations, conditions)
    table, _report = sam.generalize(table, observations, conditions)
    return table


def predict_with(table: Sequence[sam.SafeOperator], atom: str, state: State) -> dict[str, Any]:
    return sam.predict(table, atom, state)


def plan_in_measured_world(table: Sequence[sam.SafeOperator], start: State, goal: frozenset,
                           atoms: Sequence[Any], machine: Any, max_depth: int = 6
                           ) -> dict[str, Any]:
    """Plan by navigating the MEASURED world, not a projected one.

    The safe table is a partial transition system: for any state its guard admits, it names a single
    RECORDED effect. Planning in it is shortest-path search over real states -- the start state is a
    real row-state and each successor is the RECORDED `after` of a real observation, so no state on a
    plan is ever invented by applying add/delete to a condition list.

    That distinction was not academic. An earlier version of this function projected effects onto
    condition sets, and two plans "found" that way were REFUTED on execution: deleting
    `CARD count_is 4` does not imply `CARD count_is 3` is true, because a condition list is not
    closed under the effects. Navigating recorded states removes the projection entirely -- and
    `sam.Guard` now keys on the full condition signature, so a guard admits exactly one recorded
    state by construction.
    """
    atoms_by_id = {atom.ident: atom for atom in atoms}
    frontier: list[tuple[tuple[str, ...], State]] = [((), tuple(start))]
    visited = {tuple(start)}
    model_states = 1
    for _depth in range(max_depth + 1):
        nxt: list[tuple[tuple[str, ...], State]] = []
        for plan, state in frontier:
            if all(sam.holds(condition, state) for condition in goal):
                machine.reset()
                for ident in plan:
                    execute_atom(atoms_by_id[ident], machine)
                reached = read(machine)
                ok = all(sam.holds(c, reached) for c in goal)
                machine.reset()
                return {"status": "PLAN_FOUND_AND_VERIFIED" if ok else "PLAN_REFUTED",
                        "plan": list(plan), "executions": len(plan), "steps": len(plan)}
            for atom in atoms_by_id.values():
                outcome = sam.apply(table, atom.ident, state)
                if outcome.status != "APPLIES":
                    continue
                after = tuple(outcome.operator.after)
                if after in visited:
                    continue
                visited.add(after)
                model_states += 1
                nxt.append((plan + (atom.ident,), after))
        frontier = nxt
        if not frontier:
            break
    machine.reset()
    return {"status": "REFUSED__GOAL_OUTSIDE_THE_MEASURED_REGION", "plan": [], "executions": 0,
            "model_states": model_states}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="one experience, every consequence")
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--max-problems", type=int, default=3)
    parser.add_argument("--machines", nargs="*")
    options = parser.parse_args(argv)
    started = time.time()

    builds = room.all_machines()
    names = options.machines or sorted(builds)
    rows: list[dict[str, Any]] = []
    learned: dict[str, Any] = {}

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in sorted(k for k in builds if k in names):
            (root / name).mkdir(parents=True, exist_ok=True)
            machine = builds[name](root / name)
            machine.reset()
            atoms = list(machine.atoms)
            transitions = explore(machine, atoms, options.depth)
            states = [before for _i, before, _a in transitions]
            conditions = pop.condition_pool(states)
            initial = frozenset(c for c in conditions if sam.holds(c, read(machine)))

            # HOLDOUT: transitions the learner never sees. A coverage number measured on the
            # training set would be a tautology.
            shuffled = list(transitions)
            random.Random(11).shuffle(shuffled)
            split = max(1, len(shuffled) // 4)
            test = [sam.Observation.of(*t, conditions) for t in shuffled[:split]]
            train = shuffled[split:]

            tables = {
                "one_shot": one_shot(train, conditions),
                "five_shot": few_shot(train, conditions, 5),
                "ten_shot": few_shot(train, conditions, 10),
            }
            scores = {}
            for label, table in tables.items():
                scores[label] = {
                    "operators": len(table),
                    "guard_literals_dropped": sum(op.generalized_from for op in table),
                    **sam.check_against_truth(table, test),
                }
            scores["induction_from_last_round"] = _last_round_score(train, test, states, conditions)
            scores["one_shot_under_fire"] = sam.generalization_under_fire(
                tables["one_shot"], [o.before for o in test], _probe_factory(machine, atoms,
                                                                            conditions))
            probe_states = [o.before for o in test]

            def probe(atom_ident, state):
                atom = next((a for a in atoms if a.ident == atom_ident), None)
                if atom is None:
                    return None
                machine.reset()
                if not forward_to(machine, atoms, state):
                    return None          # unreachable: not evidence either way
                after = execute_atom(atom, machine)
                machine.reset()
                return (frozenset(c for c in conditions
                                  if sam.holds(c, after) and not sam.holds(c, state)),
                        frozenset(c for c in conditions
                                  if sam.holds(c, state) and not sam.holds(c, after)))

            probed, probe_report = sam.generalize_by_probe(tables["one_shot"], probe_states, probe,
                                                           conditions)
            tables["one_shot_probed"] = probed
            scores["one_shot_probed"] = {"operators": len(probed),
                                         **sam.check_against_truth(probed, test),
                                         **probe_report}
            scores["one_shot_probed_under_fire"] = sam.generalization_under_fire(
                probed, probe_states, probe)
            scores["generalized_method_last_round"] = _last_round_under_fire(
                train, probe_states, conditions, machine, atoms)

            learned[name] = {"atom_count": len(atoms), "transitions": len(transitions),
                             "held_out": len(test), "conditions_admitted": len(conditions),
                             "scores": scores,
                             "ambiguities": len(sam.ambiguities(tables["one_shot"], test))}

            reachable = sorted({tuple(b) for _i, b, _a in transitions}
                               | {tuple(a) for _i, _b, a in transitions})
            problems = racetrack.problems_for(name, initial, read(machine), tables["one_shot"],
                                              atoms, machine, reachable) \
                if False else _problems(name, initial, read(machine), tables["one_shot"], atoms,
                                        machine, reachable)
            for problem in problems[: options.max_problems]:
                row: dict[str, Any] = {"machine": name, "goal": problem["goal_text"]}
                reset_state = read(machine)
                row["safe_one_shot"] = plan_in_measured_world(
                    tables["one_shot"], reset_state, problem["goal"], atoms, machine)
                row["safe_ten_shot"] = plan_in_measured_world(
                    tables["ten_shot"], reset_state, problem["goal"], atoms, machine)
                # The control must search EVERY atom. Passing the safe table here would make the
                # control search only what the learner had approved, which is not a control at all:
                # an earlier version passed an empty list and got "no plan" from a search that
                # never tried an action.
                row["forward_search"] = racetrack.forward(
                    initial, problem["goal"], _all_atoms_as_identity_operators(atoms),
                    {a.ident: a for a in atoms}, machine, options.depth)
                rows.append(row)
            machine.reset()

    summary = {
        "machines": len(learned),
        "problems": len(rows),
        "soundness": {label: {"predictions": sum(v["scores"][label].get("predictions_made", 0)
                                              for v in learned.values()),
                              "WRONG": sum(v["scores"][label].get("predictions_WRONG", 0)
                                           for v in learned.values()),
                              "refused": sum(v["scores"][label].get("predictions_refused", 0)
                                             for v in learned.values()),
                              "sound_everywhere": all(v["scores"][label].get("sound", False)
                                                      for v in learned.values())}
                      for label in ("one_shot", "five_shot", "ten_shot",
                                    "one_shot_probed", "induction_from_last_round")},
        "generalization_under_fire": {
            label: {key: sum(v["scores"][label].get(key, 0) for v in learned.values())
                    for key in ("generalized_predictions_tested", "generalized_predictions_RIGHT",
                                "generalized_predictions_WRONG")}
            for label in ("one_shot_under_fire", "one_shot_probed_under_fire",
                          "generalized_method_last_round")},
        "plans": {mode: dict(collections.Counter(r[mode]["status"] for r in rows))
                  for mode in ("safe_one_shot", "safe_ten_shot", "forward_search")},
        "plans_verified": {mode: sum(1 for r in rows
                                     if r[mode]["status"] in ("PLAN_FOUND_AND_VERIFIED",
                                                              "PLAN_FOUND"))
                           for mode in ("safe_one_shot", "safe_ten_shot", "forward_search")},
        "refusals": {mode: sum(1 for r in rows if r[mode]["status"].startswith("REFUSED"))
                     for mode in ("safe_one_shot", "safe_ten_shot")},
        "verdicts": _verdicts(learned),
    }
    report = {"schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
              "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "learned": learned, "results": {"summary": summary, "rows": rows},
              "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                       "duration_s": round(time.time() - started, 2)}}
    text = json.dumps(report, indent=2, default=str)
    pathlib.Path(options.out).write_text(text, encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def _last_round_score(train, test, states, conditions) -> dict[str, Any]:
    """The induced table from the previous round, scored on the SAME held-out transitions.

    This is the comparison the whole round turns on: same data, same test set, two learners. If the
    induced table were always right there would be nothing to say. It is not."""
    induced = pop.induce_conditional_operators(
        [(atom, before, after) for atom, before, after in train], conditions)[0]
    observations = [sam.Observation.of(*t, conditions) for t in train]
    made = wrong = refused = 0
    for held in test:
        candidates = [op for op in induced
                      if any(c in op.add for c in [])
                      or all(sam.holds(c, held.before) for c in op.pre)]
        matching = [op for op in induced
                    if op.atom == held.atom and all(sam.holds(c, held.before) for c in op.pre)]
        if len(matching) != 1:
            refused += 1
            continue
        made += 1
        if frozenset(matching[0].add) == frozenset(held.added) and \
                frozenset(matching[0].delete) == frozenset(held.deleted):
            pass
        else:
            wrong += 1
    return {"operators": len(induced), "predictions_made": made, "predictions_WRONG": wrong,
            "predictions_refused": refused, "sound": wrong == 0,
            "coverage": round(made / max(1, made + refused), 3),
            "note": "guards from the previous round's induction, scored on the same held-out set"}


def _problems(name: str, initial: frozenset, rows_at_reset: State,
              table: Sequence[sam.SafeOperator], atoms: Sequence[Any], machine: Any,
              reachable: Sequence[State]) -> list[dict[str, Any]]:
    """Conjunctive problems built ONLY from what the safe table can express: pairs of add-effects
    that are individually reachable, jointly not true at reset, and not both produced by one atom.
    Built from the table rather than from a hashed goal, so a refusal means something."""
    candidates = sorted({c for op in table for c in op.added
                         if c[0] not in ("PAIRING", "ORDER")
                         and not sam.holds(c, rows_at_reset)
                         and any(sam.holds(c, state) for state in reachable)},
                        key=sam.describe)
    out = []
    for one, two in __import__("itertools").combinations(candidates, 2):
        if not any(sam.holds(one, s) and sam.holds(two, s) for s in reachable):
            continue
        out.append({"machine": name, "goal": frozenset({one, two}),
                    "goal_set": initial, "goal_text": sorted(sam.describe(c) for c in (one, two))})
    return out


if __name__ == "__main__":
    raise SystemExit(main())
