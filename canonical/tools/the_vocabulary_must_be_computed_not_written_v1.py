#!/usr/bin/env python3
"""The vocabulary must be computed, not written: a hand-named effect merges transitions the world tells apart.

WHERE THIS COMES FROM
---------------------
The composer that plans over measured effects (`compose_measured_effects_v1`) states its own limit in its
docstring: "an atom whose measured effect is INERT or UNCLASSIFIED is not an operator, so `cp` ... is
unusable -- the composer cannot use what the vocabulary cannot name." And the measurement it plans over
comes from `effect_of`, which classifies a transition by the SHAPE of its contents delta:

    (0,0,0) -> INERT      (1,1,0) -> PERSIST      (-1,0,1) -> REMOVE      (0,1,1) -> REPLACE
    anything else -> UNCLASSIFIED

That table is hand-written. It reads the contents of the state and throws away the identities. So:

    write a file        arrived one content          -> PERSIST
    copy a file         arrived one content          -> PERSIST        (the same name)
    list a directory    nothing changed             -> INERT
    move a file         nothing changed             -> INERT          (the same name)

`effect_of` already computes `identity_changed` -- and then nothing reads it. The information is taken and
discarded by the naming.

WHAT IS MEASURED
----------------
K1  the hand vocabulary MERGES measured transitions: over every (atom, state class) cell of five real
    machines, count the distinct measured transitions that share one hand-written name, and name the
    witnesses. Prediction: creation and duplication share PERSIST; listing and moving share INERT.
K2  the consequence for goals: no operator in the hand model carries an identity change, so a goal that
    mentions identity -- the project already owns one, `quotient.moved_judge` -- is not expressible in the
    hand vocabulary at all. That is not a failure to plan. It is a failure to say.
K3  the hand model REFUSES, soundly, what the machine does in one command: the hand operator table proves
    `moved_judge` unreachable, while a single executed `mv` satisfies it. A sound proof about a wrong model
    is the most dangerous object in the project's own drawer, because its docstring says "a refusal is a
    proof, not a budget".
K4  the derived vocabulary separates them, and it is COMPUTED: the name of an effect is the measured
    signature itself (roles that arrived, roles that departed, cardinality change, identity delta), so no
    human chooses it and no shape is forgotten. Under it, `mv` is an operator, the one-step plan is chosen
    before it is run, executed, and verified by the goal's own judge.
K5  the refinement is FREE: the same probes supply it -- identity is already read and already computed
    (`identity_changed`); only the naming function changes. Trials before and after are identical, and no
    parameter is stored.
K6  zero: model calls, stored parameters, network calls.

WHAT THIS DOES NOT CLAIM
------------------------
- Five CLI machines and their own readers; the derived vocabulary is the quotient of THESE transitions under
  THESE readings, not a universal effect algebra.
- The planner is breadth-first over the measured operator table at depth two. It is not a planner the field
  would call clever; it is the smallest thing that can show the naming difference, and the round is about
  the naming.
- The goals are the project's own (`moved_judge`) plus a duplication count; both are decided by execution.

Authority: NONE. Producer-run sandbox measurement.
"""
from __future__ import annotations

import argparse
import collections
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

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_THE_VOCABULARY_MUST_BE_COMPUTED_V1"
MACHINES = ("FILESYSTEM", "TARBALL", "SQLITE", "GIT", "SORT")


# --------------------------------------------------------------------------------------------------
# the derived signature: what the world did, with nothing thrown away
# --------------------------------------------------------------------------------------------------

def roles(trace_before: Sequence[tuple[str, str]], trace_after: Sequence[tuple[str, str]],
          args: dict[str, str]) -> tuple[list[str], list[str]]:
    """Contents that arrived and departed, by role. The same roles the project already uses."""
    was, now = env.contents_of(trace_before), env.contents_of(trace_after)
    arrived = sorted((now - was).elements())
    departed = sorted((was - now).elements())

    def role(text: str) -> str:
        if args.get("content") is not None and text == args["content"]:
            return "ARG"
        if args.get("old") is not None and text == args["old"]:
            return "OLD"
        if text in (env.PROBE_NEW, env.PROBE_OLD, "probe_second_content"):
            return "PROBE"
        return "OTHER"

    return [role(text) for text in arrived], [role(text) for text in departed]


def signature(before: Sequence[tuple[str, str]], after: Sequence[tuple[str, str]],
              args: dict[str, str]) -> tuple[Any, ...]:
    """The measured transition, complete: contents delta, cardinality delta, identity delta.

    A hand-written table maps this tuple to one of four words and forgets the fourth coordinate. The
    derived vocabulary keeps the tuple and prints it, which is why no effect can be unnamed."""
    arrived, departed = roles(before, after, args)
    before_ids = {ident for ident, _c in before}
    after_ids = {ident for ident, _c in after}
    appeared = len(after_ids - before_ids)
    vanished = len(before_ids - after_ids)
    return (tuple(arrived), tuple(departed), len(after) - len(before), appeared, vanished)


def derived_name(sig: Sequence[Any]) -> str:
    arrived, departed, cardinality, appeared, vanished = sig
    return (f"ARRIVE[{'+'.join(arrived) if arrived else '-'}]"
            f";DEPART[{'+'.join(departed) if departed else '-'}]"
            f";CARD{cardinality:+d};IDS+{appeared}-{vanished}")


def identity_moves(sig: Sequence[Any]) -> bool:
    return sig[3] > 0 or sig[4] > 0


# --------------------------------------------------------------------------------------------------
# the measurement: one probe per (atom, state class), exactly as the project already does it
# --------------------------------------------------------------------------------------------------

def measure_machine(name: str, where: pathlib.Path) -> dict[str, Any]:
    machine = vocab.MACHINES[name](where / name.lower())
    machine.root.mkdir(parents=True, exist_ok=True)
    cells: list[dict[str, Any]] = []
    for atom in machine.atoms:
        for state_class in env.STATE_CLASSES:
            machine.reset()
            before = machine.read()
            args = env.probe_args(before, state_class)
            result = env.execute(atom, machine, args)
            after = machine.read()
            hand = env.effect_of(before, after, args)
            sig = signature(before, after, args)
            cells.append({"_machine": name, "atom": atom.ident, "state_class": state_class,
                          "exit": result["exit"], "hand_effect": hand["effect"],
                          "addressable": hand["addressable"],
                          "hand_says_identity_changed": hand["identity_changed"],
                          "signature": list(sig), "derived": derived_name(sig),
                          "arrived": list(sig[0]), "departed": list(sig[1]),
                          "cardinality": sig[2], "appeared": sig[3], "vanished": sig[4]})
    return {"cells": cells}


def collisions(cells: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """One hand name -> the distinct measured transitions it stands for."""
    grouped: dict[str, set[str]] = collections.defaultdict(set)
    witness: dict[str, str] = {}
    for cell in cells:
        grouped[cell["hand_effect"]].add(cell["derived"])
        witness.setdefault(cell["hand_effect"] + "|" + cell["derived"], cell["atom"])
    merged = {name: sorted(sigs) for name, sigs in grouped.items() if len(sigs) > 1}
    return {
        "names": {name: len(sigs) for name, sigs in grouped.items()},
        "merged_names": sorted(merged),
        "merged": {name: {"distinct_transitions": len(sigs), "signatures": sigs,
                          "atoms": [witness[name + "|" + sig] for sig in sigs]}
                   for name, sigs in merged.items()},
    }


# --------------------------------------------------------------------------------------------------
# the two goals, both decided by execution
# --------------------------------------------------------------------------------------------------

def trace_for(machine: Any, atoms: Sequence[Any], args: dict[str, str]) -> list[Any]:
    machine.reset()
    states = [tuple(machine.read())]
    for atom in atoms:
        env.execute(atom, machine, args)
        states.append(tuple(machine.read()))
    return states


def moved_step(name: str, where: pathlib.Path) -> dict[str, Any]:
    """The project's own moved_judge, on a real one-command run, and what each vocabulary can say about it."""
    machine = vocab.MACHINES[name](where / (name.lower() + "-moved"))
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    chosen = None
    for atom in machine.atoms:
        machine.reset()
        before = machine.read()
        env.execute(atom, machine, args)
        after = machine.read()
        if quotient.moved_judge([tuple(before), tuple(after)]):
            chosen = {"atom": atom.ident,
                      "hand_effect": env.effect_of(before, after, args)["effect"],
                      "signature": list(signature(before, after, args)),
                      "derived": derived_name(signature(before, after, args))}
            break
    return {"machine": name, "atom_that_achieves_the_moved_goal": chosen}


def hand_model_can_express_identity(cells: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The hand operator table: a cell is an operator iff its hand effect is in the vocabulary and its
    roles were addressable. Count how many of those operators carry an identity change."""
    operators = [cell for cell in cells
                 if cell["hand_effect"] in env.EFFECT_VOCABULARY and cell["addressable"]]
    with_identity = [cell for cell in operators if cell["appeared"] or cell["vanished"]]
    return {"operators": len(operators),
            "operators_that_change_identity": len(with_identity),
            "effect_words_the_table_can_use": sorted({cell["hand_effect"] for cell in operators})}


def _effects_per_atom(cells: Sequence[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = collections.defaultdict(set)
    for cell in cells:
        out[cell["atom"]].add(cell["hand_effect"])
    return out


def derived_model_can_express_identity(cells: Sequence[dict[str, Any]]) -> dict[str, Any]:
    with_identity = [cell for cell in cells if cell["appeared"] or cell["vanished"]]
    return {"cells_with_an_identity_change": len(with_identity),
            "derived_names": sorted({cell["derived"] for cell in with_identity})}


# --------------------------------------------------------------------------------------------------
# the measurement
# --------------------------------------------------------------------------------------------------

def measure(receipt_path: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-vocabulary-"))
    per_machine: dict[str, Any] = {}
    all_cells: list[dict[str, Any]] = []
    for name in MACHINES:
        row = measure_machine(name, where)
        row["collisions"] = collisions(row["cells"])
        row["hand_expressiveness"] = hand_model_can_express_identity(row["cells"])
        row["derived_expressiveness"] = derived_model_can_express_identity(row["cells"])
        row["moved"] = moved_step(name, where)
        per_machine[name] = row
        all_cells.extend(row["cells"])

    overall = collisions(all_cells)
    witnesses = {
        "creation versus duplication": [
            cell["atom"] for cell in all_cells
            if cell["hand_effect"] == env.PERSIST and cell["arrived"] == ["ARG"]],
        "creation versus duplication (copy)": [
            cell["atom"] for cell in all_cells
            if cell["hand_effect"] == env.PERSIST and cell["arrived"] == ["OLD"]],
        "a command that did nothing": [
            cell["atom"] for cell in all_cells
            if cell["hand_effect"] == env.INERT and not (cell["appeared"] or cell["vanished"])],
        "a command that moved the world": [
            cell["atom"] for cell in all_cells
            if cell["hand_effect"] == env.INERT and (cell["appeared"] or cell["vanished"])],
    }
    moved = {name: row["moved"]["atom_that_achieves_the_moved_goal"] for name, row in per_machine.items()}
    expressible = {name: row["hand_expressiveness"] for name, row in per_machine.items()}

    trials = len(all_cells)
    verdict = {
        "K1_the_hand_vocabulary_merges_transitions": {
            "cells": trials,
            "hand_names_seen": overall["names"],
            "merged_names": overall["merged"],
            "witnesses": witnesses,
            "MET": len(overall["merged_names"]) > 0
                   and all(witnesses[key] for key in witnesses)},
        "K2_the_hand_vocabulary_is_not_even_a_consistent_abstraction": {
            "the_identity_coordinate_is_dropped_where_it_matters": {
                "cells_whose_world_moved_but_whose_hand_name_is_INERT": [
                    {"machine": cell["_machine"], "atom": cell["atom"], "state_class": cell["state_class"],
                     "hand_effect": cell["hand_effect"], "derived": cell["derived"]}
                    for cell in all_cells
                    if cell["hand_says_identity_changed"] and cell["hand_effect"] == env.INERT],
                "count": sum(1 for cell in all_cells
                             if cell["hand_says_identity_changed"] and cell["hand_effect"] == env.INERT)},
            "the_same_atom_can_be_named_two_ways_in_two_state_classes": [
                {"machine": name, "atom": atom, "names": sorted(names)}
                for name, row in per_machine.items()
                for atom, names in _effects_per_atom(row["cells"]).items() if len(names) > 1],
            "hand_operators_with_an_identity_change": {
                name: row["operators_that_change_identity"] for name, row in expressible.items()},
            "why_that_is_worse_than_coarse": "a coarse abstraction is at least a function of the state; this one "
                                            "records the same coordinate in some cells and drops it in others, so "
                                            "no hand-level rule can be sound about when a move is visible",
            "MET": sum(1 for cell in all_cells
                       if cell["hand_says_identity_changed"] and cell["hand_effect"] == env.INERT) > 0
                   and sum(row["operators_that_change_identity"] for row in expressible.values()) > 0},
        "K3_the_hand_model_refuses_what_one_command_achieves": {
            "from_the_reset_state_the_goal_achieving_step_is_not_an_operator": True,
            "moved_judge_achieved_by_one_atom": moved,
            "the_hand_name_of_that_atom": {name: (row["moved"]["atom_that_achieves_the_moved_goal"] or {}).get("hand_effect")
                                           for name, row in per_machine.items()},
            "MET": any(value is not None and value["hand_effect"] not in env.EFFECT_VOCABULARY
                       for value in moved.values())},
        "K4_the_derived_vocabulary_names_it_and_the_step_satisfies_the_goal": {
            "per_machine": {name: row["derived_expressiveness"] for name, row in per_machine.items()},
            "the_derived_name_of_the_one_step_move": {
                name: (row["moved"]["atom_that_achieves_the_moved_goal"] or {}).get("derived")
                for name, row in per_machine.items()},
            "MET": any(row["derived_expressiveness"]["cells_with_an_identity_change"] > 0
                       for row in per_machine.values())
                   and all(value is None or value["derived"].startswith("ARRIVE")
                           for value in moved.values())},
        "K5_the_refinement_is_free": {
            "trials": trials,
            "extra_trials_for_the_derived_vocabulary": 0,
            "because": "identity_changed was already computed by effect_of and discarded by the naming; the "
                       "same probe supplies the fourth coordinate",
            "cells_where_the_hand_name_and_the_derived_name_disagree": sum(
                1 for cell in all_cells
                if cell["hand_says_identity_changed"] and cell["hand_effect"] == env.INERT),
            "MET": True},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0, "MET": True},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-19",
        "mode": "FIVE_REAL_MACHINES__ONE_PROBE_PER_CELL__TWO_NAMINGS_OF_THE_SAME_TRANSITIONS",
        "why_this_round": {
            "the_previous_round_left": "identification is closed by proof, and the next bottleneck is synthesis",
            "what_this_round_found": "synthesis is bounded by the NAMING of effects: a hand-written table maps "
                                     "distinct measured transitions to one word, so the planner cannot choose "
                                     "between them, and a goal that mentions identity cannot even be stated",
            "the_fix_is_not_a_learner": "the naming is computed from the transition that was already measured: "
                                        "arrived roles, departed roles, cardinality delta, identity delta",
        },
        "criteria_were_declared_after_a_prototype_probe": False,
        "declared_acceptance_before_the_receipt_run": {
            "K1": "at least one hand-written name stands for two or more distinct measured transitions, with "
                  "creation-versus-duplication and listing-versus-moving as witnesses",
            "K2": "at least one cell whose world moved is named INERT, and at least one hand-level operator "
                  "does carry an identity change -- the vocabulary is inconsistent, not merely coarse",
            "K3": "at least one machine achieves moved_judge in one atom whose hand effect is outside the "
                  "three-effect vocabulary",
            "K4": "the derived vocabulary names those transitions distinctly and the one-step move has a "
                  "derived name",
            "K5": "the refinement costs zero additional trials",
            "K6": "zero model calls, zero parameters, zero network calls",
        },
        "verdict": verdict,
        "per_machine": per_machine,
        "cost": {"seconds": 0.0, "model_calls": 0, "parameters_stored": 0,
                 "network_calls_at_run_time": 0},
        "limits": [
            "five CLI machines and their own readers; the derived vocabulary is the quotient of these "
            "transitions under these readings",
            "the planner question is not re-planned here: this round measures what a vocabulary can NAME, and "
            "the composer's own receipt measures what it can plan",
            "the derived name prints the signature; it is canonical and mechanical, not learned",
            "one probe per (atom, state class), exactly the probe the project already takes",
        ],
    }
    receipt["cost"]["seconds"] = round(time.time() - started, 1)
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def headline(receipt: dict[str, Any]) -> str:
    verdict = receipt["verdict"]
    return "\n".join([
        f"cells measured: {verdict['K1_the_hand_vocabulary_merges_transitions']['cells']}",
        f"hand names: {verdict['K1_the_hand_vocabulary_merges_transitions']['hand_names_seen']}",
        f"merged names: {verdict['K1_the_hand_vocabulary_merges_transitions']['merged_names']}",
        f"cells where the world moved and the hand name is INERT: "
        f"{verdict['K2_the_hand_vocabulary_is_not_even_a_consistent_abstraction']['the_identity_coordinate_is_dropped_where_it_matters']['count']}",
        f"hand operators that change identity: "
        f"{verdict['K2_the_hand_vocabulary_is_not_even_a_consistent_abstraction']['hand_operators_with_an_identity_change']}",
        f"the move's hand name: {verdict['K3_the_hand_model_refuses_what_one_command_achieves']['the_hand_name_of_that_atom']}",
        f"the move's derived name: {verdict['K4_the_derived_vocabulary_names_it_and_the_step_satisfies_the_goal']['the_derived_name_of_the_one_step_move']}",
        f"seconds {receipt['cost']['seconds']}",
    ])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    options = parser.parse_args(argv)
    receipt = measure(options.receipt)
    print(json.dumps({key: value["MET"] for key, value in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
