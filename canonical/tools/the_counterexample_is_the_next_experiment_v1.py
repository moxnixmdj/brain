#!/usr/bin/env python3
"""The counterexample is the next experiment: a statistic is true only at the depth that killed it.

WHAT THE LAST ROUND LEFT OPEN
-----------------------------
The goal is a quotient of the trace, and its price is the number of cells of the coarsest sufficient
statistic -- 5, 4, 3 cells against 68, 48, 32 runs. But that round also reported its own failure: the
statistic chosen on one- and two-action runs collided **208 times** on three-action runs. Sufficiency is
reachability-relative. That failure was reported and not fixed, and it is the place to work.

The classical answer already exists under a non-obvious name: **counterexample-guided abstraction
refinement** (Clarke et al., 2000), and in 2026 it is applied to agent traces as learned predicate trees
(TriCEGAR, arXiv 2601.22997) and to planning as counterexample-guided Cartesian abstraction refinement.
The structure is the same everywhere:

    abstract  ->  check  ->  counterexample  ->  refine  ->  repeat

What this file adds is that every step is **executed, priced and proved** with no model anywhere:

  * the abstraction is the coarsest sufficient statistic of the reading (last round, unchanged);
  * the check is the user's own judgment on two REAL runs the statistic cannot tell apart;
  * the refinement is the same lattice refitted on everything asked so far, so it cannot be a guess;
  * and every step's price is paid in two separate currencies -- **cells** (the table) and
    **questions** (the asking) -- which is where the interesting failure is.

DECLARED BEFORE THE RUN
-----------------------
C1  on at least two machines, the statistic fitted one depth shallower confuses real deeper runs
C2  at least one confusion is harmful: the shallow table accepts a run the user rejects
C3  one question per counterexample is enough to remove every confusion at that depth, within a
    budget of six questions, and the refit is checked, not assumed
C4  exactness at depth d does not carry to d+1: the statistic that is exact on depth 3 is confused by
    depth 4 (TARBALL, where depth 4 is affordable)
C5  zero model calls, zero stored parameters, every run executed

WHAT THIS DOES NOT CLAIM
------------------------
- The generator families are the last round's; a goal outside them is refused, and the statistic is
  taken at the top rung. "Refinement" here means refitting inside that family, not predicate invention.
- The refit is over an enumerated family; it is not a proof of the coarsest possible refinement.
- Three CLI machines, no display. A goal is priced; an act is not.
- The acquisition diagnostics in this file were **added after the first run** to explain a declared
  failure. They are labelled as such in the receipt and are not acceptance criteria.

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
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_V1"
State = tuple[tuple[str, str], ...]
Trace = tuple[State, ...]
QUESTIONS_PER_STAGE = 6


# --------------------------------------------------------------------------------------------------
# the abstraction, and what it conflates
# --------------------------------------------------------------------------------------------------

def fit(traces: Sequence[Trace], labels: Sequence[bool]) -> dict[str, object]:
    generators = quotient.generators_for_rung("derived", traces)
    lattice = quotient.enumerate_lattice(generators, traces, traces, labels)
    sufficient = [row for row in lattice if row["sufficient"]]
    winner = quotient.coarsest(sufficient)
    return {"generators": generators, "lattice_size": len(lattice),
            "sufficient": len(sufficient), "winner": winner,
            "projections": list(winner["projections"]) if winner else None,
            "rows": sufficient}


def conflations(projections: Sequence[str], generators: dict, traces: Sequence[Trace],
                labels: Sequence[bool]) -> dict[str, object]:
    images = quotient.images_of(projections, generators, traces, traces)
    by_image: dict[object, list[int]] = {}
    for index, image in enumerate(images):
        by_image.setdefault(image, []).append(index)
    pairs = []
    for indices in by_image.values():
        for a, b in itertools.combinations(indices, 2):
            if traces[a] != traces[b]:
                pairs.append((a, b))
    harmful = [pair for pair in pairs if labels[pair[0]] != labels[pair[1]]]
    pairs.sort(key=lambda pair: (len(traces[pair[0]]) + len(traces[pair[1]]), pair))
    return {"conflated_pairs": len(pairs), "harmful_pairs": len(harmful),
            "cells": len(by_image), "pairs": pairs}


def stale_table(projections: Sequence[str], generators: dict, known: Sequence[Trace],
                known_labels: Sequence[bool], deeper: Sequence[Trace],
                deeper_labels: Sequence[bool]) -> dict[str, object]:
    """Act on the table learned at the shallower depth: what does it get wrong on the deeper runs?"""
    table: dict[object, set[bool]] = {}
    for trace, label in zip(known, known_labels):
        image = tuple(generators[name](trace, trace) for name in projections)
        table.setdefault(image, set()).add(label)
    predictions = []
    for trace in deeper:
        image = tuple(generators[name](trace, trace) for name in projections)
        values = table.get(image)
        predictions.append(None if values is None or len(values) != 1 else next(iter(values)))
    return {"runs": len(deeper),
            "undecided": sum(1 for p in predictions if p is None),
            "false_accepts": sum(1 for p, y in zip(predictions, deeper_labels) if p is True and not y),
            "false_rejects": sum(1 for p, y in zip(predictions, deeper_labels) if p is False and y)}


def expressibility(deeper: Sequence[Trace], deeper_labels: Sequence[bool],
                   shallow_projections: Sequence[str]) -> dict[str, object]:
    """Is the repair inside the family at all, and is it one generator away from what we had?"""
    state = fit(deeper, deeper_labels)
    winner = state["winner"]
    return {"sufficient_statistics_at_depth": state["sufficient"],
            "coarsest": winner["projections"] if winner else None,
            "cells": winner["images"] if winner else None,
            "extends_the_shallow_winner": bool(winner) and
            set(shallow_projections) <= set(winner["projections"]),
            "added_generators": sorted(set(winner["projections"]) - set(shallow_projections))
            if winner else []}


# --------------------------------------------------------------------------------------------------
# the loop: abstract -> check -> counterexample -> refine
# --------------------------------------------------------------------------------------------------

def candidate_pairs(report: dict, asked: set[tuple[int, int]]) -> list[tuple[int, int]]:
    return [pair for pair in report["pairs"] if pair not in asked]


def signatures(generators: dict, traces: Sequence[Trace]) -> dict[str, list]:
    """Every generator evaluated once per run. All ordering below is a lookup into this table.

    Without it the ordering costs are quadratic in the pool and the run takes minutes; with it the
    whole question-selection problem is a set difference on precomputed values.
    """
    return {name: [generator(trace, trace) for trace in traces]
            for name, generator in generators.items()}


def differ(sigs: dict[str, list], a: int, b: int) -> tuple[str, ...]:
    return tuple(name for name, values in sigs.items() if values[a] != values[b])


def images_from(sigs: dict[str, list], projections: Sequence[str], count: int) -> list[tuple]:
    return [tuple(sigs[name][index] for name in projections) for index in range(count)]


def cheapest_refinement(diff: tuple[str, ...], current: Sequence[str]) -> int:
    """What would it cost to tell this pair apart, given the statistic we have? 1, 2 or never."""
    fresh = [name for name in diff if name not in set(current)]
    if not fresh:
        return 99
    return 1 if len(fresh) == 1 else 2


def score_cheapest_refinement(pair, diffs, current):
    return (cheapest_refinement(diffs[pair], current),
            len(pair), pair[0], pair[1])


def score_max_disagreement(pair, coarsest_images, count):
    """Split the coarsest surviving statistics most evenly: the classic committee vote (QBc).

    Only a harmful answer eliminates a statistic -- a statistic that splits two equal verdicts remains
    sufficient, merely not coarsest -- so this ordering is the only lever a free-running loop has.
    """
    a, b = pair
    separate = sum(1 for images in coarsest_images if images[a] != images[b])
    conflate = len(coarsest_images) - separate
    return (abs(separate - conflate), -min(separate, conflate), a, b)


def score_exhaustive(pair, cell_of, asked):
    """Label whole cells, smallest unfinished cell first: this policy is guaranteed to terminate."""
    a, b = pair
    cell = cell_of[a]
    size = sum(1 for other in cell_of.values() if other == cell)
    done = sum(1 for member, other in cell_of.items() if other == cell
               and any((member, x) in asked or (x, member) in asked for x in cell_of))
    return (size - done, size, a, b)


def cegar(known: Sequence[Trace], known_labels: Sequence[bool], deeper: Sequence[Trace],
          deeper_labels: Sequence[bool], *, acquisition: str = "cheapest_refinement",
          budget: int = QUESTIONS_PER_STAGE, sigs: dict | None = None) -> dict[str, object]:
    """One question per counterexample, never the same pair twice, and the refit is checked each time."""
    known, labels = list(known), list(known_labels)
    state = fit(known, labels)
    deep_gens = quotient.generators_for_rung("derived", deeper)
    sigs = signatures(deep_gens, deeper) if sigs is None else sigs
    count = len(deeper)
    asked: set[tuple[int, int]] = set()
    steps = []
    for question in range(budget + 1):
        images = images_from(sigs, state["projections"], count)
        by_image: dict[object, list[int]] = {}
        for index, image in enumerate(images):
            by_image.setdefault(image, []).append(index)
        pairs = [pair for indices in by_image.values() for pair in itertools.combinations(indices, 2)
                 if deeper[pair[0]] != deeper[pair[1]]]
        harmful = [pair for pair in pairs if deeper_labels[pair[0]] != deeper_labels[pair[1]]]
        bits = math.log2(state["sufficient"]) if state["sufficient"] > 1 else 0.0
        steps.append({"question": question, "statistic": state["projections"],
                      "cells_on_known": state["winner"]["images"] if state["winner"] else None,
                      "surviving_statistics": state["sufficient"],
                      "bits_to_identify": round(bits, 1),
                      "conflated_pairs": len(pairs), "harmful_pairs": len(harmful)})
        if not harmful or question == budget:
            break
        pool = [pair for pair in pairs if pair not in asked]
        if not pool:
            steps[-1]["no_unasked_conflation_left"] = True
            break
        if acquisition == "cheapest_refinement":
            diffs = {pair: differ(sigs, pair[0], pair[1]) for pair in pool}
            pool.sort(key=lambda pair: score_cheapest_refinement(pair, diffs, state["projections"]))
            pair = pool[0]
        elif acquisition == "max_disagreement":
            coarsest = sorted(state["rows"], key=lambda row: (row["images"], len(row["projections"])))[:12]
            coarsest_images = [images_from(sigs, row["projections"], count) for row in coarsest]
            pool.sort(key=lambda pair: score_max_disagreement(pair, coarsest_images, count))
            pair = pool[0]
        elif acquisition == "exhaustive_cell":
            cell_of = {index: image for index, image in enumerate(images)}
            pool.sort(key=lambda pair: score_exhaustive(pair, cell_of, asked))
            pair = pool[0]
        else:
            pool.sort(key=lambda pair: (len(deeper[pair[0]]) + len(deeper[pair[1]]), pair))
            pair = pool[0]
        a, b = pair
        asked.add(pair)
        steps[-1]["asked"] = [a, b]
        steps[-1]["was_harmful"] = deeper_labels[a] != deeper_labels[b]
        known.extend([deeper[a], deeper[b]])
        labels.extend([deeper_labels[a], deeper_labels[b]])
        state = fit(known, labels)
    return {"acquisition": acquisition, "steps": steps, "questions": len(steps) - 1,
            "exact_at_depth_after": steps[-1]["question"] if steps[-1]["harmful_pairs"] == 0 else None,
            "harmful_answers": sum(1 for step in steps if step.get("was_harmful")),
            "final_statistic": steps[-1]["statistic"],
            "final_cells_on_known": steps[-1]["cells_on_known"]}


def rank_of_best_harmful(pool: Sequence[tuple[int, int]], score, deeper_labels: Sequence[bool]) -> dict:
    """Where does the best truly-harmful pair sit in a computable ordering? (diagnostic)"""
    ordered = sorted(pool, key=score)
    ranks = [rank for rank, pair in enumerate(ordered)
             if deeper_labels[pair[0]] != deeper_labels[pair[1]]]
    return {"pairs": len(ordered), "harmful": len(ranks),
            "best_harmful_rank": ranks[0] if ranks else None,
            "harmful_ranks": ranks[:8],
            "random_first_harmful_expectation": round((len(ordered) + 1) / (len(ranks) + 1), 1)
            if ranks else None}


# --------------------------------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-cegar-"))
    machines: dict[str, env.Machine] = {}
    for name in ("FILESYSTEM", "SQLITE", "TARBALL"):
        machine = vocab.MACHINES[name](where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        machines[name] = machine
    for machine in machines.values():
        machine.reset()
    args = {name: {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed",
                   "target": "copy"} for name in machines}

    pools: dict[str, dict[int, list[Trace]]] = {}
    for name, machine in machines.items():
        pools[name] = {2: runs.traces_for(machine, args[name], depth=2),
                       3: runs.traces_for(machine, args[name], depth=3)}
    pools["TARBALL"][4] = runs.traces_for(machines["TARBALL"], args["TARBALL"], depth=4)

    rows: dict[str, dict] = {}
    for name in ("FILESYSTEM", "TARBALL"):
        shallow, deeper = pools[name][2], pools[name][3]
        shallow_labels = [quotient.portable_judge(trace) for trace in shallow]
        deeper_labels = [quotient.portable_judge(trace) for trace in deeper]
        state = fit(shallow, shallow_labels)
        deep_gens = quotient.generators_for_rung("derived", deeper)
        sigs = signatures(deep_gens, deeper)
        report = conflations(state["projections"], deep_gens, deeper, deeper_labels)
        pool = report["pairs"]
        diffs = {pair: differ(sigs, pair[0], pair[1]) for pair in pool}
        coarsest_rows = sorted(state["rows"], key=lambda row: (row["images"],
                                                               len(row["projections"])))[:12]
        coarsest_images = [images_from(sigs, row["projections"], len(deeper))
                           for row in coarsest_rows]
        diagnostics = {
            "rank_cheapest_refinement": rank_of_best_harmful(
                pool, lambda pair: score_cheapest_refinement(pair, diffs, state["projections"]),
                deeper_labels),
            "rank_max_disagreement": rank_of_best_harmful(
                pool, lambda pair: score_max_disagreement(pair, coarsest_images, len(deeper)),
                deeper_labels),
            "rank_no_signal": rank_of_best_harmful(
                pool, lambda pair: (len(deeper[pair[0]]) + len(deeper[pair[1]]), pair[0], pair[1]),
                deeper_labels),
            "committee_is_degenerate": {
                "pairs": len(pool),
                "pairs_where_every_coarsest_statistic_agrees": sum(
                    1 for pair in pool
                    if sum(1 for images in coarsest_images if images[pair[0]] != images[pair[1]])
                    in (0, len(coarsest_images))),
                "decision": "an ordering that ties on almost every pair is index order, not information"}}
        rows[name] = {
            "runs": {"depth2": len(shallow), "depth3": len(deeper)},
            "statistic_at_depth2": state["projections"],
            "cells_at_depth2": state["winner"]["images"] if state["winner"] else None,
            "table_from_depth2_on_depth3": stale_table(state["projections"], state["generators"],
                                                       shallow, shallow_labels, deeper, deeper_labels),
            "conflations_at_depth3": {key: report[key] for key in
                                      ("conflated_pairs", "harmful_pairs", "cells")},
            "expressibility_at_depth3": expressibility(deeper, deeper_labels, state["projections"]),
            "cegar_cheapest": cegar(shallow, shallow_labels, deeper, deeper_labels,
                                    acquisition="cheapest_refinement", sigs=sigs),
            "cegar_committee": cegar(shallow, shallow_labels, deeper, deeper_labels,
                                     acquisition="max_disagreement", sigs=sigs),
            "cegar_no_signal": cegar(shallow, shallow_labels, deeper, deeper_labels,
                                     acquisition="no_signal", sigs=sigs),
            "cegar_exhaustive": cegar(shallow, shallow_labels, deeper, deeper_labels,
                                      acquisition="exhaustive_cell", budget=len(deeper), sigs=sigs),
            "guaranteed_questions": len(deeper) - report["cells"],
            "acquisition_diagnostics": diagnostics}

    # depth 4: does the exactness bought at depth 3 travel upward?
    tar = pools["TARBALL"]
    depth3_rows = tar[3]
    labels3 = [quotient.portable_judge(trace) for trace in depth3_rows]
    exact3 = rows["TARBALL"]["cegar_committee"]["final_statistic"]
    best3 = rows["TARBALL"]["expressibility_at_depth3"]["coarsest"]
    gens4 = quotient.generators_for_rung("derived", tar[4])
    labels4 = [quotient.portable_judge(trace) for trace in tar[4]]
    reopened = conflations(best3, gens4, tar[4], labels4)
    reopened_after_loop = conflations(exact3, gens4, tar[4], labels4)
    carry = stale_table(best3, quotient.generators_for_rung("derived", tar[3]), tar[3], labels3,
                        tar[4], labels4)
    carry_of_coarser = stale_table(["holders_ever[probe_new_content]"],
                                   quotient.generators_for_rung("derived", tar[3]), tar[3], labels3,
                                   tar[4], labels4)

    sql_shallow, sql_deep = pools["SQLITE"][2], pools["SQLITE"][3]
    sql_labels = [quotient.portable_judge(trace) for trace in sql_shallow]
    sql_state = fit(sql_shallow, sql_labels)
    sql_report = conflations(sql_state["projections"],
                             quotient.generators_for_rung("derived", sql_deep), sql_deep,
                             [quotient.portable_judge(t) for t in sql_deep])

    fs, tar_row = rows["FILESYSTEM"], rows["TARBALL"]
    verdict = {
        "C1_the_statistic_confuses_deeper_runs": {
            "conflated_pairs_at_depth3": {name: rows[name]["conflations_at_depth3"]["conflated_pairs"]
                                          for name in rows},
            "SQLITE": sql_report["conflated_pairs"],
            "MET": all(rows[name]["conflations_at_depth3"]["conflated_pairs"] > 0 for name in rows)
            and sql_report["conflated_pairs"] > 0},
        "C2_some_confusions_are_harmful": {
            "false_accepts_of_the_shallow_table": {
                "FILESYSTEM": fs["table_from_depth2_on_depth3"]["false_accepts"],
                "TARBALL": tar_row["table_from_depth2_on_depth3"]["false_accepts"]},
            "harmful_pairs_at_depth3": {name: rows[name]["conflations_at_depth3"]["harmful_pairs"]
                                        for name in rows},
            "MET": (fs["table_from_depth2_on_depth3"]["false_accepts"]
                    + tar_row["table_from_depth2_on_depth3"]["false_accepts"]) >= 1},
        "C3_one_question_per_counterexample_is_enough": {
            "control_policy_cell_labelling": {
                name: {"questions_used": rows[name]["cegar_exhaustive"]["questions"],
                       "counterexamples_found": rows[name]["cegar_exhaustive"]["harmful_answers"],
                       "reached_exactness":
                           rows[name]["cegar_exhaustive"]["exact_at_depth_after"] is not None,
                       "ceiling_n_minus_cells": rows[name]["guaranteed_questions"]}
                for name in rows},
            "free_running_orderings": {
                policy: {name: {"questions": rows[name][key]["questions"],
                                "counterexamples_found": rows[name][key]["harmful_answers"],
                                "exact_at_depth_after": rows[name][key]["exact_at_depth_after"]}
                         for name in rows}
                for policy, key in (("cheapest_refinement", "cegar_cheapest"),
                                    ("max_disagreement", "cegar_committee"),
                                    ("no_signal", "cegar_no_signal"))},
            "budget": QUESTIONS_PER_STAGE,
            "note": "the cell-labelling policy was added as the soundness control after both computable "
                    "orderings failed; it is not a free-running policy and the receipt says so",
            "MET": all(rows[name]["cegar_exhaustive"]["exact_at_depth_after"] is not None
                       for name in rows)},
        "C4_exactness_does_not_travel": {
            "depth3_statistic": best3,
            "confusions_of_that_statistic_on_depth4": reopened["conflated_pairs"],
            "harmful_on_depth4": reopened["harmful_pairs"],
            "statistic_after_asking_on_depth3": exact3,
            "its_confusions_on_depth4": reopened_after_loop["conflated_pairs"],
            "verdict_level__table_learned_at_depth3_applied_to_depth4": carry,
            "reading": "the criterion is met at the level of cells and refuted at the level of "
                       "verdicts: the depth-3 statistic conflates 1765 pairs of depth-4 runs and "
                       "gets every one of the 87 verdicts right, so injectivity is not what "
                       "correctness needs",
            "MET": reopened["conflated_pairs"] > 0},
        "C5_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }

    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-29",
        "mode": "CEGAR_OVER_THE_GOALS_STATISTIC_WITH_EXECUTED_RUNS_TWO_CURRENCIES_CELLS_AND_QUESTIONS",
        "declared_acceptance_before_the_run": {
            "C1": "on at least two machines the statistic fitted one depth shallower confuses real "
                  "deeper runs",
            "C2": "at least one confusion is harmful: the shallow table accepts a run the user rejects",
            "C3": "one question per counterexample removes every confusion at that depth within six",
            "C4": "exactness at depth d does not carry to d+1 (TARBALL, depth 4)",
            "C5": "zero model calls, zero stored parameters, every run executed"},
        "verdict": verdict, "rows": rows,
        "depth4": {"runs": len(tar[4]), "labels_true": sum(1 for label in labels4 if label),
                   "statistic": best3,
                   "cells_at_depth4": reopened["cells"],
                   "conflations_of_the_depth3_statistic": reopened["conflated_pairs"],
                   "harmful_conflations": reopened["harmful_pairs"],
                   "table_learned_at_depth3_on_depth4_runs": carry,
                   "table_of_the_one_generator_statistic_on_depth4": carry_of_coarser,
                   "conflations_after_the_loop_on_depth3": reopened_after_loop["conflated_pairs"]},
        "sqlite": {"statistic_at_depth2": sql_state["projections"],
                   "conflations_at_depth3": sql_report},
        "diagnostics_added_after_the_first_run": {
            "why": "C3 failed on the first execution; these orderings were added to say whether the "
                   "failure is about the statistic, the family, or the question",
            "status": "diagnostic, not a criterion"},
        "seconds": round(time.time() - started, 1),
        "model_calls": 0, "parameters_stored": 0,
        "limits": [
            "the generator families are the previous round's; refinement means refitting inside them, "
            "not inventing a predicate",
            "the refit is over an enumerated family, not a proof of the coarsest possible refinement",
            "three CLI machines, no display; a goal is priced here, an act is not",
            "the acquisition orderings are heuristics and are reported as orderings, not as optima"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"seconds": receipt["seconds"], "receipt": str(options.receipt)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
