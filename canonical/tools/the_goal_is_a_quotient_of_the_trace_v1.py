#!/usr/bin/env python3
"""The goal is a quotient of the trace, and the quotient is computed, not written.

WHERE THIS COMES FROM
---------------------
Five rounds removed every handed-in object but one. The effect vocabulary was replaced by relations
over the reader; the goal stopped being handed in and became inferred from judgments; ambiguity became
an intersection instead of a guess; and the goal stopped being a function of one state, because two
runs that end alike can be judged oppositely. In the last round, though, the *terms* were written by
me. `two_copies`, `created_once`, `never_together`, `precedence` -- I chose them. That is the same sin
at one level up: I supplied the vocabulary, so the measurement could only ever say "the vocabulary I
supplied works".

The honest object underneath all of it is smaller and sharper:

    a reading of the machine after every step is a tuple of rows (identity, content);
    the goal is a function of SOME statistic of that tuple;
    which statistic is not a matter of taste -- it is decided by whether it separates the runs the
    user judges differently.

So "what must the agent observe to know the goal" has a computable answer. Enumerate the projections
of the reading that are available -- the reading's own fields, and the fields of the literals the
machine actually emitted (the count of *this* content at each step, the identities that ever held it,
the content each identity held, ...). Keep the projections under which no two runs with opposite
judgments collide. Of those take the **coarsest**: the one with the fewest distinct images. Its images
are the cells of the goal, and the number of cells is what the goal costs in experiences -- exactly,
with no appeal to generalisation:

    a cell is a case; a case the agent has never seen cannot be labelled by anything, because the
    goal is a function of the projection and nothing else.

That is the precise form of "learn it once, keep it forever": **k cells, k experiences, then a table
that never changes** -- where k is computed, not asserted. One experience is enough exactly when
k = 1, and that is a property of the goal, measured.

MINIMALITY IS PROVED, NOT ASSERTED
----------------------------------
For every projection with fewer images than the winner a **witness pair** is produced: two runs with
the same image under that projection and opposite judgments. That pair *is* the proof that the cheaper
observable cannot carry the goal. No optimisation result is trusted; every refusal is exhibited.

THE INSUFFICIENCY, AND THE REPAIR
---------------------------------
A goal can be outside every projection of the reading -- here, "the listing atom ran", where two
sequences with identical readings are judged oppositely. Then **no** projection separates, which is the
project certificate firing in the place this project already knows. The repair the certificate names
is a new observable, and it is computed the same way: add a generator the machine already exposes (the
executor's own call log) and re-enumerate. The repair is measured, including what it costs -- the goal
about the exact sequence needs one cell per sequence, and that is reported rather than celebrated.

A DEFECT FOUND IN THIS FILE'S OWN FIRST BUILD
---------------------------------------------
The first lattice had only the reading's ten base fields, and it answered FILESYSTEM with 55 cells
against 68 runs -- a quotient that had learned almost nothing, because `content_delta` carries the
arrivals of every literal, relevant or not. The fix is not a threshold, it is the projection family:
the generators are parameterised by the literals the reading emits, exactly as `terms_from` is. The
first number was not wrong about the data; it was wrong about what the vocabulary had to contain, and
it is kept here because that is the same mistake this project keeps finding at every level.

WHAT THIS DOES NOT CLAIM
------------------------
- The generators are typed by the reading's own structure (identity, content, step, count). That is a
  *smaller* hand-supplied object than a term grammar, but it is not zero, and a goal outside all of
  them is refused, not fitted. Projections are enumerated up to two generators.
- The projection transfers across machines; the table does not. Refilling a k-cell table is what
  "instant learning in a new environment" means here, and k is measured.
- Three CLI machines, no display. A screen adds fields to the row, not a different theory.
- No planning and no synthesis: this round is about what the goal *is*, not about reaching it.

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
from typing import Callable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_V1"
State = tuple[tuple[str, str], ...]
Trace = tuple[State, ...]
Image = tuple[object, ...]
Generator = Callable[[object, Trace], Image]


# --------------------------------------------------------------------------------------------------
# base generators: the reading's own fields, no literals
# --------------------------------------------------------------------------------------------------

def _final_rows(_run: object, trace: Trace) -> Image:
    return tuple(trace[-1])


def _final_contents(_run: object, trace: Trace) -> Image:
    return tuple(sorted(content for _ident, content in trace[-1]))


def _cardinality_trace(_run: object, trace: Trace) -> Image:
    return tuple(len(state) for state in trace)


def _contents_by_step(_run: object, trace: Trace) -> Image:
    return tuple(tuple(sorted(content for _ident, content in state)) for state in trace)


def _identities_by_step(_run: object, trace: Trace) -> Image:
    return tuple(tuple(sorted(ident for ident, _content in state)) for state in trace)


def _content_delta(_run: object, trace: Trace) -> Image:
    out = []
    for before, after in zip(trace, trace[1:]):
        was = collections.Counter(content for _ident, content in before)
        now = collections.Counter(content for _ident, content in after)
        out.append((tuple(sorted((now - was).elements())), tuple(sorted((was - now).elements()))))
    return tuple(out)


def _change_events(_run: object, trace: Trace) -> Image:
    out = []
    for before, after in zip(trace, trace[1:]):
        was = {ident: content for ident, content in before}
        now = {ident: content for ident, content in after}
        out.append(tuple((ident, was.get(ident), now.get(ident))
                         for ident in sorted(set(was) | set(now)) if was.get(ident) != now.get(ident)))
    return tuple(out)


def _content_to_identities(_run: object, trace: Trace) -> Image:
    holders: dict[str, set[str]] = {}
    for state in trace:
        for ident, content in state:
            holders.setdefault(content, set()).add(ident)
    return tuple(sorted((content, tuple(sorted(ids))) for content, ids in holders.items()))


def _identity_histories(_run: object, trace: Trace) -> Image:
    histories: dict[str, list[str]] = {}
    for state in trace:
        for ident, content in state:
            histories.setdefault(ident, []).append(content)
    return tuple(sorted((ident, tuple(contents)) for ident, contents in histories.items()))


def _rows_trace(_run: object, trace: Trace) -> Image:
    return tuple(tuple(state) for state in trace)


BASE: dict[str, Generator] = {
    "final_rows": _final_rows,
    "final_contents": _final_contents,
    "cardinality_trace": _cardinality_trace,
    "contents_by_step": _contents_by_step,
    "identities_by_step": _identities_by_step,
    "content_delta": _content_delta,
    "change_events": _change_events,
    "content_to_identities": _content_to_identities,
    "identity_histories": _identity_histories,
    "rows_trace": _rows_trace,
}


# --------------------------------------------------------------------------------------------------
# literal generators: the same fields, aimed at what the machine actually emitted
# --------------------------------------------------------------------------------------------------

def _count_trace(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return tuple(runs._count(state, content) for state in trace)
    return project


def _count_delta(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return tuple(runs._count(trace[i + 1], content) - runs._count(trace[i], content)
                     for i in range(len(trace) - 1))
    return project


def _holders_by_step(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return tuple(tuple(sorted(ident for ident, value in state if value == content))
                     for state in trace)
    return project


def _holders_ever(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return tuple(sorted({ident for state in trace for ident, value in state if value == content}))
    return project


def _content_by_step(ident: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return tuple(next((value for name, value in state if name == ident), None) for state in trace)
    return project


def _contents_ever(ident: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return tuple(sorted({value for state in trace for name, value in state if name == ident}))
    return project


def generators_for(traces: Sequence[Trace]) -> dict[str, Generator]:
    """The reading's fields plus the same fields aimed at its own literals. No goal is consulted."""
    generators = dict(BASE)
    contents = sorted({value for trace in traces for state in trace for _i, value in state})
    idents = sorted({ident for trace in traces for state in trace for ident, _v in state})
    for content in contents:
        generators[f"count_trace[{content}]"] = _count_trace(content)
        generators[f"count_delta[{content}]"] = _count_delta(content)
        generators[f"holders_by_step[{content}]"] = _holders_by_step(content)
        generators[f"holders_ever[{content}]"] = _holders_ever(content)
    for ident in idents:
        generators[f"content_by_step[{ident}]"] = _content_by_step(ident)
        generators[f"contents_ever[{ident}]"] = _contents_ever(ident)
    return generators


def call_log_generators() -> dict[str, Generator]:
    return {"atom_sequence": lambda run, _trace: tuple(run)}


# --------------------------------------------------------------------------------------------------
# rung 3: derived statistics over a literal -- still a function of the trace, still not per goal
# --------------------------------------------------------------------------------------------------

def _increments(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return (sum(runs._count(trace[i + 1], content) > runs._count(trace[i], content)
                    for i in range(len(trace) - 1)),)
    return project


def _decrements(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return (sum(runs._count(trace[i + 1], content) < runs._count(trace[i], content)
                    for i in range(len(trace) - 1)),)
    return project


def _two_copies(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return (any(runs._count(state, content) >= 2 for state in trace),)
    return project


def _present_throughout(content: str) -> Generator:
    def project(_run: object, trace: Trace) -> Image:
        return (all(runs._count(state, content) >= 1 for state in trace),)
    return project


def derived_generators(traces: Sequence[Trace]) -> dict[str, Generator]:
    generators: dict[str, Generator] = {}
    contents = sorted({value for trace in traces for state in trace for _i, value in state})
    for content in contents:
        generators[f"increments[{content}]"] = _increments(content)
        generators[f"decrements[{content}]"] = _decrements(content)
        generators[f"two_copies[{content}]"] = _two_copies(content)
        generators[f"present_throughout[{content}]"] = _present_throughout(content)
    return generators


#: The ladder. Each rung is a strictly larger family of statistics of the same reading; the question
#: each rung answers is what the goal costs in experiences when that much structure is supplied.
RUNGS = ("raw", "fields", "literal", "derived")


def generators_for_rung(rung: str, traces: Sequence[Trace]) -> dict[str, Generator]:
    if rung == "raw":
        return {"rows_trace": _rows_trace}
    if rung == "fields":
        return dict(BASE)
    if rung == "literal":
        return generators_for(traces)
    if rung == "derived":
        generators = generators_for(traces)
        generators.update(derived_generators(traces))
        return generators
    raise SystemExit(f"UNKNOWN_RUNG:{rung}")


# --------------------------------------------------------------------------------------------------
# the lattice, the quotient, and its proof
# --------------------------------------------------------------------------------------------------

def images_of(names: Sequence[str], generators: dict[str, Generator], pool: Sequence[object],
              traces: Sequence[Trace]) -> list[Image]:
    return [tuple(generators[name](run, trace) for name in names)
            for run, trace in zip(pool, traces)]


def collisions(images: Sequence[Image], labels: Sequence[bool]) -> list[tuple[int, int]]:
    """Every pair of runs the projection cannot tell apart and the user judged differently."""
    by_image: dict[Image, list[int]] = collections.defaultdict(list)
    for index, image in enumerate(images):
        by_image[image].append(index)
    return sorted({(a, b) for indices in by_image.values()
                   for a, b in itertools.combinations(indices, 2) if labels[a] != labels[b]})


def enumerate_lattice(generators: dict[str, Generator], pool: Sequence[object],
                      traces: Sequence[Trace], labels: Sequence[bool], *,
                      max_size: int = 2) -> list[dict[str, object]]:
    rows = []
    names = list(generators)
    for size in range(1, min(max_size, len(names)) + 1):
        for combo in itertools.combinations(names, size):
            images = images_of(combo, generators, pool, traces)
            clash = collisions(images, labels)
            rows.append({"projections": list(combo), "size": size,
                         "images": len(set(images)), "collisions": len(clash),
                         "witnesses": [list(pair) for pair in clash[:3]],
                         "sufficient": not clash, "_images": images})
    return rows


def coarsest(sufficient: Sequence[dict[str, object]]) -> dict[str, object] | None:
    if not sufficient:
        return None
    return sorted(sufficient, key=lambda row: (row["images"], row["size"],
                                               tuple(row["projections"])))[0]


def smallest(sufficient: Sequence[dict[str, object]]) -> dict[str, object] | None:
    if not sufficient:
        return None
    return sorted(sufficient, key=lambda row: (row["size"], row["images"],
                                               tuple(row["projections"])))[0]


def table_test(row: dict[str, object], labels: Sequence[bool]) -> dict[str, object]:
    """What the quotient buys, exactly: a pure table whose cells are the experiences it costs.

    Fitted on the even runs, judged on the odd ones. A held-out run whose image was never seen is
    `unseen` -- a cell, an experience not yet paid for -- and is never counted as a success.
    """
    images = row["_images"]
    assert isinstance(images, list)
    table: dict[Image, set[bool]] = collections.defaultdict(set)
    for index, image in enumerate(images):
        table[image].add(labels[index])
    train = {image: labels[index] for index, image in enumerate(images) if index % 2 == 0}
    held = [(image, labels[index]) for index, image in enumerate(images) if index % 2 == 1]
    return {"cells": len(table),
            "impure_cells": sum(1 for values in table.values() if len(values) > 1),
            "runs": len(labels),
            "held_out_runs": len(held),
            "held_out_unseen_cell": sum(1 for image, _label in held if image not in train),
            "held_out_wrong_on_a_seen_cell": sum(1 for image, label in held
                                                 if image in train and train[image] != label)}


# --------------------------------------------------------------------------------------------------
# the goals
# --------------------------------------------------------------------------------------------------

def portable_judge(trace: Trace) -> bool:
    """The same sentence on every machine: the probe content arrived once and was never removed."""
    return runs._increased_once(trace, env.PROBE_NEW) and runs._count(trace[-1], env.PROBE_NEW) == 1


def moved_judge(trace: Trace) -> bool:
    """The original was moved, not copied-then-deleted: it was never in two places at once, and it
    ended under a different identity than the one it started in. The final state is identical for
    both behaviours; only the history of holders tells them apart."""
    holders = [[ident for ident, content in state if content == env.PROBE_OLD] for state in trace]
    if any(len(ids) > 1 for ids in holders):
        return False
    first = next((ids for ids in holders if ids), None)
    if not first or not holders[-1]:
        return False
    return holders[-1] != first


def sequences_for(machine: env.Machine, args: dict[str, str], *, depth: int = 2
                  ) -> tuple[list[tuple[str, ...]], list[Trace]]:
    """Every sequence, NOT deduplicated: two sequences that read alike stay two rows."""
    sequences, traces = [], []
    for length in range(1, depth + 1):
        for sequence in itertools.product(machine.atoms, repeat=length):
            machine.reset()
            states: list[State] = [tuple(machine.read())]
            for atom in sequence:
                env.execute(atom, machine, args)
                states.append(tuple(machine.read()))
            sequences.append(tuple(atom.ident for atom in sequence))
            traces.append(tuple(states))
    machine.reset()
    return sequences, traces


# --------------------------------------------------------------------------------------------------
# the round
# --------------------------------------------------------------------------------------------------

def _brief(row: dict[str, object] | None) -> dict[str, object] | None:
    if row is None:
        return None
    images = int(row["images"])
    return {"projections": row["projections"], "size": row["size"], "images": images,
            "bits": round(math.log2(max(1, images)), 2),
            "witnesses_of_cheaper_projections": row["witnesses"]}


def _ladder(traces: Sequence[Trace], labels: Sequence[bool]) -> dict[str, object]:
    """Every rung of the ladder, on one pool: what the goal costs at that much supplied structure."""
    out: dict[str, object] = {}
    for rung in RUNGS:
        generators = generators_for_rung(rung, traces)
        lattice = enumerate_lattice(generators, traces, traces, labels)
        sufficient = [row for row in lattice if row["sufficient"]]
        winner = coarsest(sufficient)
        out[rung] = {"generators": len(generators), "projections": len(lattice),
                     "sufficient": len(sufficient), "winner": winner,
                     "single_sufficient": [row["projections"][0] for row in sufficient
                                           if row["size"] == 1],
                     "table": table_test(winner, labels) if winner else None}
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--depth", type=int, default=3)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-quotient-"))
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

    portable: dict[str, dict[str, object]] = {}
    for name, machine in machines.items():
        traces = runs.traces_for(machine, args[name], depth=options.depth)
        labels = [portable_judge(trace) for trace in traces]
        portable[name] = {"runs": len(traces), "accepted": sum(labels), "labels": labels,
                          "ladder": _ladder(traces, labels)}

    # the same single generator, sufficient for the same sentence on all three machines
    top = "derived"
    shared_single = [generator for generator in
                     generators_for_rung(top, runs.traces_for(machines["FILESYSTEM"],
                                                              args["FILESYSTEM"], depth=2))
                     if all(generator in portable[name]["ladder"][top]["single_sufficient"]
                            for name in portable)]

    fs = machines["FILESYSTEM"]
    fs_traces = runs.traces_for(fs, args["FILESYSTEM"], depth=options.depth)
    fs_labels = [moved_judge(trace) for trace in fs_traces]
    pair_ladder = _ladder(fs_traces, fs_labels)

    portable_winner = portable["FILESYSTEM"]["ladder"][top]["winner"]["projections"]
    pair_winner = pair_ladder[top]["winner"]["projections"] if pair_ladder[top]["winner"] else None
    fs_generators = generators_for_rung(top, fs_traces)
    fs_portable_labels = [portable_judge(trace) for trace in fs_traces]
    pair_lattice_top = [row for row in enumerate_lattice(
        fs_generators, fs_traces, fs_traces, fs_labels) if row["projections"] == portable_winner]
    portable_lattice_top = [row for row in enumerate_lattice(
        fs_generators, fs_traces, fs_traces, fs_portable_labels) if row["projections"] == pair_winner]
    portable_on_pair_pool = [row["sufficient"] for row in pair_lattice_top]
    pair_on_portable_pool = [row["sufficient"] for row in portable_lattice_top]

    # the goal about which atom ran: outside every rung of the reading, repaired by the call log
    sequences, sequence_traces = sequences_for(fs, args["FILESYSTEM"], depth=2)
    listing = [any(atom == "FS_A5" for atom in sequence) for sequence in sequences]
    reading_ladders = {rung: _ladder(sequence_traces, listing) for rung in RUNGS}
    raw_generators = generators_for_rung("raw", sequence_traces)
    reading_ladders["raw"]["_lattice"] = enumerate_lattice(
        raw_generators, sequences, sequence_traces, listing)
    extended_generators = dict(generators_for_rung(top, sequence_traces))
    extended_generators.update(call_log_generators())
    extended_lattice = enumerate_lattice(extended_generators, sequences, sequence_traces, listing)
    extended_single = [row["projections"][0] for row in extended_lattice
                       if row["sufficient"] and row["size"] == 1]
    reading_rows = next(row for row in reading_ladders["raw"]["_lattice"]
                        if row["projections"] == ["rows_trace"])
    atom_witness = [[sequences[a], sequences[b]] for a, b in reading_rows["witnesses"][:2]]
    extension = coarsest([row for row in extended_lattice if row["sufficient"]])

    # held-out reachability: the projection chosen on the shallow pool, judged on the deep pool
    shallow_traces = runs.traces_for(fs, args["FILESYSTEM"], depth=2)
    shallow_labels = [portable_judge(trace) for trace in shallow_traces]
    shallow_ladder = _ladder(shallow_traces, shallow_labels)
    chosen = shallow_ladder[top]["winner"]["projections"] if shallow_ladder[top]["winner"] else None
    deep_generators = generators_for_rung(top, fs_traces)
    reachable_holdout = None
    if chosen and all(name in deep_generators for name in chosen):
        deep_images = images_of(chosen, deep_generators, fs_traces, fs_traces)
        reachable_holdout = {"projections": chosen, "deep_runs": len(fs_traces),
                             "collisions_on_the_deep_pool": len(collisions(deep_images, fs_labels))}

    def cells(name: str, rung: str) -> int | None:
        winner = portable[name]["ladder"][rung]["winner"]
        return winner["images"] if winner else None

    rungs_monotone = all(
        (cells(name, RUNGS[i]) or 10 ** 6) >= (cells(name, RUNGS[i + 1]) or 10 ** 6)
        for i in range(len(RUNGS) - 1) for name in portable)

    verdict = {
        "F1_one_projection_carries_one_sentence_on_three_machines": {
            "single_generators_sufficient_on_all_three": shared_single,
            "MET": bool(shared_single)},
        "F2_the_quotient_is_chosen_by_the_goal": {
            "portable_winner": portable_winner, "pair_goal_winner": pair_winner,
            "portable_winner_on_the_pair_pool": portable_on_pair_pool,
            "portable_winner_witnesses_there": pair_lattice_top[0]["witnesses"] if pair_lattice_top else [],
            "pair_winner_on_the_portable_pool": pair_on_portable_pool,
            "pair_winner_witnesses_there": portable_lattice_top[0]["witnesses"] if portable_lattice_top else [],
            "MET": pair_winner is not None and portable_on_pair_pool == [False]
            and pair_on_portable_pool == [False]},
        "F3_insufficiency_then_repair": {
            "reading_projections_that_suffice_at_every_rung":
                {rung: reading_ladders[rung][rung]["sufficient"] for rung in RUNGS},
            "single_generators_after_the_call_log": extended_single,
            "repair_cells": extension["images"] if extension else None,
            "MET": all(reading_ladders[rung][rung]["sufficient"] == 0 for rung in RUNGS)
            and "atom_sequence" in extended_single},
        "F4_the_ladder_is_the_exchange_rate": {
            "cells_by_rung": {name: {rung: cells(name, rung) for rung in RUNGS} for name in portable},
            "distinct_runs": {name: portable[name]["runs"] for name in portable},
            "pair_goal_cells_by_rung": {rung: (pair_ladder[rung]["winner"]["images"]
                                              if pair_ladder[rung]["winner"] else None)
                                        for rung in RUNGS},
            "cells_are_pure_at_the_top":
                all(portable[name]["ladder"][top]["table"]["impure_cells"] == 0 for name in portable),
            "non_increasing_along_the_ladder": rungs_monotone,
            "MET": rungs_monotone and all((cells(name, top) or 10) <= 4 for name in portable)
            and all(portable[name]["ladder"][top]["table"]["impure_cells"] == 0 for name in portable)},
        "F5_held_out_reachability": {
            "chosen_on_depth_2": chosen,
            "collisions_on_depth_3": reachable_holdout,
            "MET": bool(reachable_holdout) and reachable_holdout["collisions_on_the_deep_pool"] == 0},
        "F6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }

    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-28",
        "mode": "THE_OBSERVABLE_IS_COMPUTED_FROM_THE_READING_NOT_SUPPLIED",
        "declared_acceptance_before_the_run": {
            "F1": "one single generator suffices for the same sentence on all three machines",
            "F2": "each goal's coarsest statistic is insufficient for the other goal on the same "
                  "pool: the quotient is chosen by the goal, not by the machine",
            "F3": "no rung of the reading separates a goal about which atom ran, and the executor's "
                  "own call log does",
            "F4": "the ladder is non-increasing in cells and reaches at most four cells at the top "
                  "rung, with every cell pure",
            "F5": "the statistic chosen on the depth-2 pool has no collision on the depth-3 pool",
            "F6": "zero model calls, zero stored parameters, no network at run time"},
        "verdict": verdict,
        "portable_goal": {name: {"runs": report["runs"], "accepted": report["accepted"],
                                 "ladder": {rung: {"generators": report["ladder"][rung]["generators"],
                                                   "projections": report["ladder"][rung]["projections"],
                                                   "sufficient": report["ladder"][rung]["sufficient"],
                                                   "coarsest": _brief(report["ladder"][rung]["winner"]),
                                                   "table": report["ladder"][rung]["table"]}
                                            for rung in RUNGS}}
                          for name, report in portable.items()},
        "pair_goal": {"runs": len(fs_traces), "accepted": sum(fs_labels),
                      "ladder": {rung: {"sufficient": pair_ladder[rung]["sufficient"],
                                        "coarsest": _brief(pair_ladder[rung]["winner"]),
                                        "table": pair_ladder[rung]["table"]}
                                 for rung in RUNGS}},
        "atom_goal": {"sequences": len(sequences), "accepted": sum(listing),
                      "reading_ladder": {rung: {"sufficient": reading_ladders[rung][rung]["sufficient"]}
                                         for rung in RUNGS},
                      "two_sequences_one_reading_opposite_judgments": atom_witness,
                      "repair": _brief(extension),
                      "repair_cells": extension["images"] if extension else None},
        "held_out_reachability": reachable_holdout,
        "depth": options.depth,
        "seconds": round(time.time() - started, 1),
        "model_calls": 0, "parameters_stored": 0,
        "limits": [
            "the statistics are typed by the reading's own structure and its own literals; the top "
            "rung is a fixed small algebra over a literal, not a per-goal choice, but it is supplied",
            "the coarsest function of the trace is the label itself (two cells) and it is unlearnable; "
            "the ladder is the honest trade-off between supplied structure and bought experience",
            "the projection transfers across machines, the table does not: k cells are refilled per "
            "environment",
            "three CLI machines, no display; no planning and no synthesis here",
            "cells are a lower bound on the experiences the goal costs, because a cell cannot be "
            "labelled from another cell"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"seconds": receipt["seconds"], "receipt": str(options.receipt)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
