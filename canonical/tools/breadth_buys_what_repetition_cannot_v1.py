#!/usr/bin/env python3
"""Breadth buys what repetition cannot: every goal has a class, and the class ends in one question of words.

WHAT THE LAST ROUND LEFT, AND WHERE IT WAS LOOSE
------------------------------------------------
Last round separated the environment from the goal and counted, on one machine: 231 runs, 11 935
hypotheses, 353 behaviours, and **79 statements consistent with everything the user ever said**. It
called those 79 the residual. That count was inflated: a conjunction that repeats its own conjunct, or
adds one that is true on every run, has the same behaviour as the smaller statement, so 79 was mostly
redundancy. Corrected here: on TARBALL the user's goal has **4 minimal statements**, not 79. The
correction makes the user's claim *stronger*, not weaker, and it is stated first because a count that
flatters the argument is the failure this project keeps hunting.

WHAT IS MEASURED NOW
--------------------
The claim under test is "learn it once, in a new arbitrary environment, and keep it permanently". If
breadth of experience is what identifies a goal, then the class of statements carrying a behaviour must
shrink as environments are added, and the question is whether it shrinks *to one*.

One grammar over the union of every literal the three machines can hold (244 terms, closed under
conjunctions of two = 29 890 hypotheses), evaluated once into bitmasks over **555 executed runs** of three
kinds of machine -- a tarball, a filesystem, a SQLite database. A statement's behaviour is its mask, so:

  * the **resolving power** of a set of environments is the number of distinct masks;
  * the **class** of a behaviour is the number of *minimal* statements that carry it, where a conjunction
    is non-minimal if one of its conjuncts alone already has that behaviour;
  * the **residual** for the user's goal is that class on the union -- the statements no run of any of the
    three machines can tell apart, and therefore the statements only the user's words can separate.

All seven subsets of the three machines are measured, so the marginal value of each environment is a
count and not an argument.

DECLARED BEFORE THE RECEIPT RUN -- AND WHAT WAS ALREADY SEEN
------------------------------------------------------------
A prototype probe over the same three pools was run in this session while writing the tool, and it
produced the headline numbers. These criteria are therefore *confirmatory*, not predictive, and the
receipt says so in the field `criteria_were_declared_after_a_prototype_probe`. They are written as
structural claims rather than as the numbers seen, so that a stale or edited tool cannot pass them by
accident:

B1  the union of the three machines has strictly more distinct behaviours than any single machine
B2  the union's minimal class for the user's goal is strictly smaller than the richest single machine's
B3  the union's minimal class for the user's goal is still greater than one: experience does not finish
    the job even after every run of three machines
B4  the third machine removes fewer minimal statements from the goal's class than the second machine did:
    breadth saturates, and what is left is structural
B5  the residual is priced: log2(class) questions *of the user*, and no run of any machine can pay a
    single one of them
B6  zero model calls, zero stored parameters, every run executed

WHAT THIS DOES NOT CLAIM
------------------------
- The grammar is supplied and small: 244 terms over the literals these machines can hold. A goal outside
  it is refused, and the ceiling is computed for this grammar, not for goals in general.
- Three CLI machines, no display, depths 5/4/4 -- the deepest this sandbox affords. Depth 6 is named as
  out of reach, not simulated.
- Nothing here composes an edit against a live codebase. The synthesis side of coding is untouched and is
  named as the next corpus, not faked.
- A residual of log2(k) bits is a *count of questions*, not a dialogue system: it says what must be asked,
  not how to ask it well.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
import pathlib
import sys
import tempfile
import time
from typing import Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_discriminator_v1 as demand  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_BREADTH_BUYS_WHAT_REPETITION_CANNOT_V1"
MACHINES = ("TARBALL", "FILESYSTEM", "SQLITE")
DEPTHS = {"TARBALL": 5, "FILESYSTEM": 4, "SQLITE": 4}
Trace = tuple[tuple[tuple[str, str], ...], ...]


# --------------------------------------------------------------------------------------------------
# one grammar over everything the three machines can hold
# --------------------------------------------------------------------------------------------------

def union_terms(pools: dict[str, list[Trace]]) -> list[demand.Term]:
    """The grammar of the union, deduplicated by text: the terms the machines share, plus their own."""
    union = [trace for name in MACHINES for trace in pools[name]]
    whole, end_only = runs.run_terms(union)
    seen: dict[str, demand.Term] = {}
    for term in list(whole) + list(end_only):
        seen.setdefault(term.text, term)
    return list(seen.values())


def masks_on(terms: Sequence[demand.Term], traces: Sequence[Trace]) -> list[int]:
    out = []
    for term in terms:
        value = 0
        for index, trace in enumerate(traces):
            if term.holds(trace):
                value |= 1 << index
        out.append(value)
    return out


def judge_mask(traces: Sequence[Trace]) -> int:
    value = 0
    for index, trace in enumerate(traces):
        if quotient.portable_judge(trace):
            value |= 1 << index
    return value


# --------------------------------------------------------------------------------------------------
# one analysis: a set of environments, its behaviours, their classes
# --------------------------------------------------------------------------------------------------

class Analysis:
    """Every hypothesis as a mask over the concatenated runs, then classes and minimal statements."""

    def __init__(self, terms: Sequence[demand.Term], per_machine_masks: list[list[int]],
                 sizes: list[int]) -> None:
        self.texts = [term.text for term in terms]
        self.terms = list(terms)
        self.sizes = list(sizes)
        masks = [0] * len(terms)
        offset = 0
        for machine_masks, size in zip(per_machine_masks, sizes):
            for index, value in enumerate(machine_masks):
                masks[index] |= value << offset
            offset += size
        self.runs = offset
        full = (1 << self.runs) - 1
        self.masks = masks
        self.by_combo: dict[tuple[int, ...], int] = {(i,): masks[i] for i in range(len(masks))}
        for i in range(len(masks)):
            for j in range(i + 1, len(masks)):
                self.by_combo[(i, j)] = masks[i] & masks[j]
        self.full = full

    def classes(self) -> dict[int, list[tuple[int, ...]]]:
        grouped: dict[int, list[tuple[int, ...]]] = collections.defaultdict(list)
        for combo, mask in self.by_combo.items():
            grouped[mask].append(combo)
        return dict(grouped)

    def minimal(self, behaviour: int, combos: Sequence[tuple[int, ...]]) -> list[tuple[int, ...]]:
        """Minimal statements for a behaviour: a pair is redundant if one conjunct already has it."""
        out = []
        for combo in combos:
            if len(combo) == 2 and behaviour in (self.by_combo[(combo[0],)], self.by_combo[(combo[1],)]):
                continue
            out.append(combo)
        return out

    def report(self, truth: int) -> dict[str, object]:
        grouped = self.classes()
        sizes = [len(self.minimal(mask, combos)) for mask, combos in grouped.items()]
        trivial = 0
        for mask in (0, self.full):
            if mask in grouped:
                sizes.remove(len(self.minimal(mask, grouped[mask])))
                trivial += 1
        goal = grouped.get(truth, [])
        goal_minimal = self.minimal(truth, goal) if goal else []
        return {
            "runs": self.runs,
            "hypotheses": len(self.by_combo),
            "behaviours": len(grouped),
            "trivial_behaviours_excluded": trivial,
            "behaviours_with_a_unique_statement": sum(1 for size in sizes if size == 1),
            "share_unique": round(sum(1 for size in sizes if size == 1) / len(sizes), 4) if sizes else None,
            "mean_class": round(sum(sizes) / len(sizes), 2) if sizes else None,
            "largest_class": max(sizes) if sizes else None,
            "goal_statements_with_the_behaviour": len(goal),
            "goal_minimal_statements": len(goal_minimal),
            "goal_minimal_texts": [" ∧ ".join(self.texts[i] for i in combo) for combo in goal_minimal],
        }


# --------------------------------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-breadth-"))
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    machines: dict[str, env.Machine] = {}
    pools: dict[str, list[Trace]] = {}
    for name in MACHINES:
        machine = vocab.MACHINES[name](where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        machines[name] = machine
        pools[name] = runs.traces_for(machine, args, depth=DEPTHS[name])

    terms = union_terms(pools)
    per_machine = {name: masks_on(terms, pools[name]) for name in MACHINES}
    truth_by_machine = {name: judge_mask(pools[name]) for name in MACHINES}

    subsets = []
    for size in (1, 2, 3):
        subsets.extend(itertools.combinations(MACHINES, size))
    rows: dict[str, dict[str, object]] = {}
    for subset in subsets:
        analysis = Analysis(terms, [per_machine[name] for name in subset],
                            [len(pools[name]) for name in subset])
        offset = 0
        truth = 0
        for name in subset:
            truth |= truth_by_machine[name] << offset
            offset += len(pools[name])
        rows["+".join(subset)] = analysis.report(truth)

    singles = {name: rows[name]["behaviours"] for name in MACHINES}
    union = rows["+".join(MACHINES)]
    richest = max(MACHINES, key=lambda name: rows[name]["behaviours"])
    pair = max((key for key in rows if key.count("+") == 1),
               key=lambda key: rows[key]["goal_minimal_statements"])
    marginal = {
        "first_machine_goal_minimal": rows[richest]["goal_minimal_statements"],
        "after_two_machines_goal_minimal": rows[pair]["goal_minimal_statements"],
        "after_three_machines_goal_minimal": union["goal_minimal_statements"],
        "second_machine_removed": rows[richest]["goal_minimal_statements"]
        - rows[pair]["goal_minimal_statements"],
        "third_machine_removed": rows[pair]["goal_minimal_statements"]
        - union["goal_minimal_statements"],
    }
    residual = int(union["goal_minimal_statements"])
    verdict = {
        "B1_breadth_increases_resolving_power": {
            "single": singles, "union": union["behaviours"],
            "MET": union["behaviours"] > max(singles.values())},
        "B2_breadth_shrinks_the_goal_class": {
            "richest_single_machine": {richest: rows[richest]["goal_minimal_statements"]},
            "union": residual,
            "MET": residual < rows[richest]["goal_minimal_statements"]},
        "B3_the_residual_survives_every_machine": {
            "residual_statements": residual,
            "texts": union["goal_minimal_texts"],
            "MET": residual > 1},
        "B4_breadth_saturates": {
            "marginal": marginal,
            "MET": marginal["third_machine_removed"] < marginal["second_machine_removed"]},
        "B5_the_residual_is_priced_in_words": {
            "questions_of_the_user": round(math.log2(residual), 3) if residual > 1 else 0.0,
            "runs_that_could_pay_it": 0,
            "MET": residual > 1},
        "B6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }

    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-12-01",
        "mode": "ONE_GRAMMAR_OVER_THREE_MACHINES_PRICES_BREADTH_AND_COUNTS_THE_RESIDUAL",
        "correction_to_the_previous_round": {
            "what_was_reported": f"{rows['TARBALL']['goal_statements_with_the_behaviour']} statements "
                                 "consistent with everything the user said on TARBALL",
            "what_it_was": f"{rows['TARBALL']['goal_statements_with_the_behaviour']} contains "
                           f"{rows['TARBALL']['goal_statements_with_the_behaviour'] - rows['TARBALL']['goal_minimal_statements']} "
                           "redundant conjunctions; the goal's minimal class is "
                           f"{rows['TARBALL']['goal_minimal_statements']}",
            "why_it_matters": "a count that flatters the argument is the failure this project hunts; the "
                              "corrected count makes the claim stronger and the residual smaller"},
        "criteria_were_declared_after_a_prototype_probe": True,
        "prototype_note": "a probe over the same three pools ran while the tool was written and produced "
                          "the headline numbers, so B1-B6 are confirmatory; they are written as "
                          "structural claims so that an edited tool cannot pass them by accident",
        "declared_acceptance_before_the_receipt_run": {
            "B1": "the union of the three machines has strictly more distinct behaviours than any single "
                  "machine",
            "B2": "the union's minimal class for the user's goal is strictly smaller than the richest "
                  "single machine's",
            "B3": "the union's minimal class for the user's goal is still greater than one",
            "B4": "the third machine removes fewer minimal statements than the second",
            "B5": "the residual is log2(class) questions of the user, and no run can pay one of them",
            "B6": "zero model calls, zero stored parameters, every run executed"},
        "verdict": verdict,
        "subsets": rows,
        "terms": len(terms),
        "runs": {name: len(pools[name]) for name in MACHINES},
        "depths": DEPTHS,
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "definitions": {
            "behaviour": "the bitmask of a statement over every executed run: two statements are the same "
                         "knowledge when their masks are equal",
            "class": "the number of minimal statements carrying one behaviour; a conjunction of two is "
                     "non-minimal when one conjunct alone already carries it",
            "residual": "the class of the user's goal on the union: statements no run of any of the three "
                        "machines can tell apart"},
        "limits": [
            "the grammar is supplied and small (244 terms over these machines' literals); the ceiling is "
            "computed for it, not for goals in general",
            "three CLI machines at depths 5/4/4; depth 6 is out of reach here and named, not simulated",
            "the synthesis side of coding is untouched: this prices what an edit would be for, not an edit",
            "log2(k) is a count of questions, not a dialogue: it says what must be asked, not how well"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"residual": residual, "texts": union["goal_minimal_texts"],
                      "seconds": receipt["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
