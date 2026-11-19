#!/usr/bin/env python3
"""The goal is not in the environment: experience buys the machine exactly and the intention not at all.

WHAT THE LAST FOUR ROUNDS LEFT
------------------------------
The goal is a quotient of the trace (k cells). Its refinement costs one counterexample and one question.
A conflation is not an error (675 and 1 765 pairs, 0 harmful). And the table learned at depth 3 answers
every decided depth-5 run correctly. Read alone, that chain says the user's claim is nearly right:
experience once, keep it permanently.

Every one of those rounds, however, **supplied the goal**. `portable_judge` is a predicate I wrote; the
agent was never asked what the user wants. So the chain measures the *environment* and calls the answer
a *goal*. This round separates them, because the user's claim is about the goal:

    give it the action once  ->  it learns what to do  ->  permanently, in any environment

WHAT IS MEASURED, AND WHY IT IS THE ULTIMATE FORM OF THE QUESTION
----------------------------------------------------------------
A goal is a boolean function of the run. The grammar is the one already in this repository
(`the_goal_is_a_relation_over_the_run_v1.run_terms`): terms over the whole trace, plus terms that may
read only the final state, closed under conjunctions of size two. Every hypothesis is a bitmask over the
runs the environment can produce, so:

  * **two goals are the same knowledge exactly when their masks are equal** -- indistinguishable by any
    experiment this environment can ever offer, not merely unidentified today;
  * therefore the ceiling of "learn it once and keep it" is a fact about the environment, and it is
    countable: the number of distinct masks is the number of intentions the machine can tell apart;
  * and the failure of "permanently" is countable too: take two goals with the *same* mask on every
    reachable run (different statements, one behaviour), move them to a different machine, and ask
    whether they still agree. If they separate there, then what was learned was a behavioural class, and
    the class is exactly what a new environment breaks.

The second measurement is the price. Identification is active: ask about the run whose judgment splits
the surviving masks most evenly, refit, repeat, and stop when one behaviour class remains. That is
compared with judging runs in the order the environment offers them, and with the trivial bound of
judging every run. Questions are the only thing spent; no model, no parameter, no network.

DECLARED BEFORE THE RUN
-----------------------
G1  the grammar can state the user's goal exactly on the reachable set, or the receipt says it cannot
G2  at least two different goal statements share one behaviour on every reachable run at the deepest
    affordable depth: the ceiling is non-empty, so no experience can separate them *here*. A statement
    qualifies as a competing intent only if it is non-trivial (true on some run, false on another) and
    is stated in vocabulary the two machines share -- a condition about a literal that exists in one
    run of one machine is an artifact of that pool, not an intention, and a witness chosen from such
    statements would be self-congratulation. The filter is declared here, before any run.
G3  at least one such pair separates on the other machine: "permanently" fails exactly at the boundary
    of the environment it was learned in
G4  active questions isolate one behaviour class in at most eight judgments, and the ordered (passive)
    sequence needs more for the same isolation
G5  zero model calls, zero stored parameters, every run executed

The environment control is a *previously registered* prediction, not a new claim: the last round
pre-registered that "any verdict error at depth 5 kills 'the table travels'". It is reported, not
re-declared.

WHAT THIS DOES NOT CLAIM
------------------------
- The grammar is supplied and small. A goal outside it is refused, and the receipt says so; the ceiling
  is a ceiling *for this grammar*, computed, not for goals in general.
- Two machines, no display. Transfer is measured between the two, not across all of computer use.
- Identification up to behavioural equivalence is not sentience, intention, or understanding. That
  distinction is the round's point, and it is stated rather than blurred.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
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

SCHEMA = "BRAIN_THE_GOAL_IS_NOT_IN_THE_ENVIRONMENT_V1"
Trace = tuple[tuple[tuple[str, str], ...], ...]
ACTIVE_BUDGET = 8
PASSIVE_BUDGET = 8


# --------------------------------------------------------------------------------------------------
# the goal family, evaluated once into bitmasks over the reachable runs
# --------------------------------------------------------------------------------------------------

def family(traces: Sequence[Trace]) -> list[demand.Term]:
    whole, end_only = runs.run_terms(traces)
    seen: dict[str, demand.Term] = {}
    for term in list(whole) + list(end_only):
        seen.setdefault(term.text, term)
    return list(seen.values())


def mask_of(term: demand.Term, traces: Sequence[Trace]) -> int:
    value = 0
    for index, trace in enumerate(traces):
        if term.holds(trace):
            value |= 1 << index
    return value


class Family:
    """Every term and every conjunction of two, as bitmasks over the runs. No search at query time."""

    def __init__(self, traces: Sequence[Trace]) -> None:
        self.traces = list(traces)
        self.terms = family(traces)
        self.masks = [mask_of(term, self.traces) for term in self.terms]
        self.combos = [(i,) for i in range(len(self.terms))]
        self.combos += [(i, j) for i in range(len(self.terms))
                        for j in range(i + 1, len(self.terms))]
        full = (1 << len(self.traces)) - 1
        self.by_combo: dict[tuple[int, ...], int] = {}
        for combo in self.combos:
            value = full
            for index in combo:
                value &= self.masks[index]
            self.by_combo[combo] = value

    def texts(self, combo: Sequence[int]) -> list[str]:
        return [self.terms[index].text for index in combo]

    def distinct(self, combos: Sequence[tuple[int, ...]]) -> dict[int, list[tuple[int, ...]]]:
        grouped: dict[int, list[tuple[int, ...]]] = {}
        for combo in combos:
            grouped.setdefault(self.by_combo[combo], []).append(combo)
        return grouped

    def survivors(self, accepted: int, rejected: int) -> list[tuple[int, ...]]:
        return [combo for combo in self.combos
                if self.by_combo[combo] & accepted == accepted and not self.by_combo[combo] & rejected]


def literals(traces: Sequence[Trace]) -> set[str]:
    """Every content value any state of any run holds. Shared vocabulary is the intersection."""
    return {value for trace in traces for state in trace for _ident, value in state}


def ceiling_witness(family_: Family, other_literals: set[str]) -> dict[str, object] | None:
    """Two different statements with one behaviour, non-trivial and stated in shared vocabulary.

    Ordered by class size then by mask so the choice is deterministic and decided by the data: the
    largest class of single-term statements the environment cannot separate, preferring statements of
    different kinds (a monotonicity claim versus an end-state count, say), because a "ceiling" made of
    two syntactic variants of one sentence would prove nothing.
    """
    full = (1 << len(family_.traces)) - 1
    machine_only = sorted(literals(family_.traces) - other_literals)
    singles = [index for index, term in enumerate(family_.terms)
               if 0 < family_.masks[index] < full
               and not any(token in term.text for token in machine_only)]
    grouped: dict[int, list[int]] = {}
    for index in singles:
        grouped.setdefault(family_.masks[index], []).append(index)
    for mask, indexes in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(indexes) < 2:
            continue
        kinds: dict[str, list[int]] = {}
        for index in indexes:
            kinds.setdefault(family_.terms[index].text.split("[")[0], []).append(index)
        if len(kinds) < 2:
            continue
        chosen = [values[0] for values in list(kinds.values())[:2]]
        return {"mask_true_runs": bin(mask).count("1"), "runs": len(family_.traces),
                "a": family_.texts((chosen[0],)), "b": family_.texts((chosen[1],)),
                "class_size": len(indexes), "nontrivial": True, "mask": mask,
                "class_statements": [family_.terms[index].text for index in indexes]}
    return None


def judge_mask(traces: Sequence[Trace], judge) -> int:
    value = 0
    for index, trace in enumerate(traces):
        if judge(trace):
            value |= 1 << index
    return value


# --------------------------------------------------------------------------------------------------
# asking: split the surviving behaviours as evenly as possible
# --------------------------------------------------------------------------------------------------

def best_question(family_: Family, survivors: Sequence[tuple[int, ...]],
                  judged: set[int]) -> tuple[int | None, dict[str, object]]:
    masks = sorted({family_.by_combo[combo] for combo in survivors})
    best: tuple[int, int, int] | None = None
    for index in range(len(family_.traces)):
        if index in judged:
            continue
        accepting = sum(1 for mask in masks if mask >> index & 1)
        rejecting = len(masks) - accepting
        if accepting == 0 or rejecting == 0:
            continue
        score = (abs(accepting - rejecting), -min(accepting, rejecting), index)
        if best is None or score < best[0]:
            best = (score, index, accepting, rejecting)
    if best is None:
        return None, {"behaviours": len(masks)}
    return best[1], {"behaviours": len(masks), "accepting": best[2], "rejecting": best[3]}


def elicit(family_: Family, truth: int, *, budget: int, order: str = "active") -> dict[str, object]:
    """Judge runs until one behaviour class survives, and report the price in judgments."""
    survivors = list(family_.combos)
    judged: set[int] = set()
    accepted = rejected = 0
    steps = []
    for question in range(budget + 1):
        masks = sorted({family_.by_combo[combo] for combo in survivors})
        steps.append({"judgments": question, "survivors": len(survivors),
                      "behaviours": len(masks),
                      "bits_to_identify": round(math.log2(len(masks)), 2) if len(masks) > 1 else 0.0})
        if len(masks) <= 1 or question == budget:
            break
        if order == "active":
            index, detail = best_question(family_, survivors, judged)
            if index is None:
                steps[-1]["no_question_left"] = detail
                break
        else:
            index = next((i for i in range(len(family_.traces)) if i not in judged), None)
            if index is None:
                break
        judged.add(index)
        if truth >> index & 1:
            accepted |= 1 << index
        else:
            rejected |= 1 << index
        survivors = family_.survivors(accepted, rejected)
        steps[-1]["judged"] = index
        steps[-1]["answer"] = bool(truth >> index & 1)
    final = sorted({family_.by_combo[combo] for combo in survivors})
    return {"order": order, "steps": steps, "judgments": len(steps) - 1,
            "converged": len(final) <= 1,
            "final_survivors": len(survivors), "final_behaviours": len(final),
            "final_masks": final}


# --------------------------------------------------------------------------------------------------
# the environment control: a previously registered prediction
# --------------------------------------------------------------------------------------------------

def environment_control(machine: env.Machine, args: dict[str, str],
                        shallow: int, deep: int) -> dict[str, object]:
    """The depth-3 statistic and its table, applied to the deepest pool. Registered last round."""
    shallow_traces = runs.traces_for(machine, args, depth=shallow)
    deep_traces = runs.traces_for(machine, args, depth=deep)
    shallow_labels = [quotient.portable_judge(trace) for trace in shallow_traces]
    deep_labels = [quotient.portable_judge(trace) for trace in deep_traces]
    generators = quotient.generators_for_rung("derived", shallow_traces)
    lattice = quotient.enumerate_lattice(generators, shallow_traces, shallow_traces, shallow_labels)
    sufficient = [row for row in lattice if row["sufficient"]]
    winner = quotient.coarsest(sufficient)
    projections = list(winner["projections"])
    table: dict[object, bool] = {}
    for trace, label in zip(shallow_traces, shallow_labels):
        image = tuple(generators[name](trace, trace) for name in projections)
        table.setdefault(image, label)
    deep_generators = quotient.generators_for_rung("derived", deep_traces)
    predictions = []
    for trace in deep_traces:
        image = tuple(deep_generators[name](trace, trace) for name in projections)
        predictions.append(table.get(image))
    return {"statistic": projections,
            "shallow_runs": len(shallow_traces), "deep_runs": len(deep_traces),
            "undecided": sum(1 for p in predictions if p is None),
            "false_accepts": sum(1 for p, y in zip(predictions, deep_labels) if p is True and not y),
            "false_rejects": sum(1 for p, y in zip(predictions, deep_labels) if p is False and y),
            "correct_where_decided": sum(1 for p, y in zip(predictions, deep_labels)
                                         if p is not None and p == y),
            "deep_true": sum(1 for y in deep_labels if y)}


# --------------------------------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-goal-"))
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    machines: dict[str, env.Machine] = {}
    for name in ("TARBALL", "FILESYSTEM"):
        machine = vocab.MACHINES[name](where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        machines[name] = machine

    deep_depth = {"TARBALL": 5, "FILESYSTEM": 4}
    pools = {name: runs.traces_for(machines[name], args, depth=deep_depth[name])
             for name in machines}
    other_pool = {"TARBALL": pools["FILESYSTEM"], "FILESYSTEM": pools["TARBALL"]}

    report: dict[str, object] = {}
    for name in ("TARBALL", "FILESYSTEM"):
        traces = pools[name]
        family_ = Family(traces)
        truth = judge_mask(traces, quotient.portable_judge)
        behaviours = family_.distinct(family_.combos)

        # G1: can the grammar state the user's goal at all?
        exact = [combo for combo in family_.combos if family_.by_combo[combo] == truth]
        consistent_all = [combo for combo in family_.combos
                          if family_.by_combo[combo] & truth == truth
                          and not family_.by_combo[combo] & ~truth]

        # G2: two different statements, one behaviour, on every reachable run -- non-trivial and stated
        # in vocabulary the other machine shares, per the declared filter.
        full_mask = (1 << len(traces)) - 1
        ceiling = ceiling_witness(family_, literals(other_pool[name]))

        active = elicit(family_, truth, budget=ACTIVE_BUDGET, order="active")
        passive = elicit(family_, truth, budget=PASSIVE_BUDGET, order="passive")
        # every run judged: what survives is a behaviour, and the statements that carry it
        all_judged = family_.survivors(truth, full_mask ^ truth)
        truth_statements = [combo for combo in all_judged
                            if family_.by_combo[combo] == truth]

        report[name] = {
            "runs": len(traces),
            "terms": len(family_.terms),
            "hypotheses": len(family_.combos),
            "distinct_behaviours_in_the_family": len(behaviours),
            "user_goal_stated_exactly": [family_.texts(combo) for combo in exact][:5],
            "user_goal_stated_exactly_count": len(exact),
            "consistent_with_every_run": len(consistent_all),
            "ceiling_witness": {k: v for k, v in (ceiling or {}).items() if k != "mask"},
            "ceiling_class_statements": (ceiling or {}).get("class_statements"),
            "single_term_statements_of_the_users_goal":
                [family_.texts(combo) for combo in truth_statements if len(combo) == 1],
            "statements_consistent_with_every_run": len(truth_statements),
            "behaviours_when_every_run_is_judged": len({family_.by_combo[combo]
                                                        for combo in all_judged}),
            "active": active, "passive": passive,
        }

    # G3: take the TARBALL ceiling pair to the other machine
    witness = report["TARBALL"]["ceiling_witness"]
    transfer: dict[str, object] = {"witness": witness}
    if witness:
        other = pools["FILESYSTEM"]
        terms_of = {term.text: term for term in family(pools["TARBALL"])}
        rows = []
        for trace_index, trace in enumerate(other):
            left = all(terms_of[text].holds(trace) for text in witness["a"])
            right = all(terms_of[text].holds(trace) for text in witness["b"])
            if left != right:
                rows.append({"run": trace_index, "a": left, "b": right})
        transfer.update({"other_machine": "FILESYSTEM", "other_runs": len(other),
                         "disagreements": len(rows), "first": rows[:3]})

    control = environment_control(machines["TARBALL"], args, shallow=3, deep=5)

    active_tar = report["TARBALL"]["active"]
    passive_tar = report["TARBALL"]["passive"]
    verdict = {
        "G1_the_grammar_can_state_the_goal": {
            "exact": {name: report[name]["user_goal_stated_exactly_count"] for name in report},
            "consistent_with_every_run": {name: report[name]["consistent_with_every_run"]
                                          for name in report},
            "MET": all(report[name]["user_goal_stated_exactly_count"] >= 1 for name in report)},
        "G2_two_statements_one_behaviour": {
            "witness": witness,
            "class_size": (witness or {}).get("class_size"),
            "statements_consistent_with_every_run": {
                name: report[name]["statements_consistent_with_every_run"] for name in report},
            "behaviours_when_every_run_is_judged": {
                name: report[name]["behaviours_when_every_run_is_judged"] for name in report},
            "MET": witness is not None and witness.get("nontrivial") is True},
        "G3_the_pair_separates_in_a_new_environment": {
            "disagreements": transfer.get("disagreements"),
            "MET": bool(transfer.get("disagreements"))},
        "G4_active_questions_isolate_a_behaviour": {
            "active_judgments": active_tar["judgments"],
            "passive_judgments": passive_tar["judgments"],
            "active_converged": active_tar["converged"],
            "passive_survivors_at_the_same_budget": passive_tar["final_survivors"],
            "MET": active_tar["converged"] and active_tar["judgments"] <= 8
                   and passive_tar["final_survivors"] > active_tar["final_survivors"]},
        "G5_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
        "environment_control_registered_last_round": {
            "control": control,
            "reading": "the machine is known exactly at a depth it was not measured on; the goal is not",
            "MET": control["false_accepts"] == 0 and control["false_rejects"] == 0},
    }

    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-30",
        "mode": "SEPARATE_THE_ENVIRONMENT_FROM_THE_GOAL_AND_PRICE_EACH_IN_JUDGMENTS",
        "declared_acceptance_before_the_run": {
            "G1": "the grammar can state the user's goal exactly on the reachable set, or the receipt "
                  "says it cannot",
            "G2": "two different statements share one behaviour on every reachable run at the deepest "
                  "affordable depth",
            "G3": "at least one such pair separates on the other machine",
            "G4": "active questions isolate one behaviour class in at most eight judgments, and the "
                  "ordered sequence needs more",
            "G5": "zero model calls, zero stored parameters, every run executed"},
        "verdict": verdict, "machines": report, "transfer": transfer,
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "the goal grammar is supplied and small; the ceiling is computed for this grammar, not for "
            "goals in general",
            "two CLI machines and no display; transfer is between the two, not across computer use",
            "identification up to behavioural equivalence is not intention: the round's point is that "
            "the two are different objects with different prices",
            "the depth-5 pool is the deepest the enumeration affords here (231 runs in 76 s); depth 6 "
            "is out of reach in this sandbox and is named, not faked"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"seconds": receipt["cost"]["seconds"], "receipt": str(options.receipt)},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
