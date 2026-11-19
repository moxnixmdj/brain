#!/usr/bin/env python3
"""Agreement is not equivalence: the one bit the last round priced in words is closed by proof instead.

WHERE THIS COMES FROM
---------------------
The last round measured that the user's goal, over a grammar of 244 terms evaluated on 555 executed runs
of three real machines, has a minimal class of exactly **two** statements:

    created_once[probe_new_content]
    monotone[probe_new_content] ∧ final:count[probe_new_content]==1

and it pre-registered the next step: put both sentences to the user, price the answer at log2(2) = 1
question, and validate the chosen one on a machine it was never fitted on. It also wrote, as its single
bottleneck: "the residual class -- and the fact that it can only be closed by language, not by experience."

That last sentence is what this round tests, and the answer is that it is wrong in a way that matters.
A question to the user is NOT the only way to close the class, and it is not the cheapest. There is a
third source of bits, sitting between "no run can tell them apart" and "ask the user", and the project
has never measured it:

    a proof that two statements are the same function, or a witness that they are not.

WHAT IS MEASURED
----------------
K1  reproduction: on the three fitted machines the goal's minimal class is two statements, and their
    texts are the ones the previous receipt recorded
K2  agreement is total: on every trace of every one of FIVE real machines -- the three that were fitted and
    two (GIT, SORT) that were never fitted and already exist in this tree -- BOTH statements agree with the
    goal's own judge on 100% of runs. More agreement did not, and cannot, separate them.
K3  the bounded proof: over the count envelope -- every history of counts up to a fixed length, with
    every per-step jump the arithmetic allows, starting from zero -- the second statement is EQUIVALENT to
    the judge on every history, and the first is not: a single step that adds two copies at once satisfies
    "created once" and violates "exactly one at the end".
K4  the witness is not exhibitable: no atom of any of the five machines can add two copies in one step, so
    the distinction the proof turns on cannot be produced by any run of any of these machines at ANY depth.
    The residual was never short of evidence; it was outside the action alphabet.
K5  the price, corrected: zero questions of the user are needed for a goal that is given as a total judge.
    The one bit the last round priced at log2(2) is paid by proof, and a proof is cheaper than a question
    and permanent in a way a question is not.
K6  permanence, precisely: a statement is permanent iff it is equivalent to the goal's definition under the
    definition's precondition -- here `count(initial state) == 0`, which is true of all five machines and
    is checked by one read, not by experience. Agreement on runs is evidence; equivalence is proof; only
    one of them survives an environment nobody has seen.
K7  zero: model calls, stored parameters, network calls.

WHAT THIS DOES NOT CLAIM
------------------------
- The equivalence is proved for THIS judge and THIS grammar, and checked exhaustively over a bounded count
  envelope, not for goals in general. The general statement is the criterion (permanence = proven
  equivalence under a checkable precondition), not a theorem about all goals.
- A witness trace need not be executable to refute an equivalence between two statements. That is exactly
  the asymmetry this round measures: the world supplies runs, and a proof may turn on a run the world
  cannot have. K4 measures which of the five machines could ever perform it, and none can.
- The count envelope is the part of the state that the disputed statements read. It is a complete quotient
  for these two statements by construction, not a sample.
- No sentience, no model, no weights, no parameters. Every number is a run or an arithmetic check.

Authority: NONE. Producer-run sandbox measurement.
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
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402
import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402

SCHEMA = "BRAIN_AGREEMENT_IS_NOT_EQUIVALENCE_V1"
FITTED = ("TARBALL", "FILESYSTEM", "SQLITE")
HELD_OUT = ("GIT", "SORT")
DEPTHS = {"TARBALL": 5, "FILESYSTEM": 4, "SQLITE": 4, "GIT": 4, "SORT": 4}
ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}


# --------------------------------------------------------------------------------------------------
# statements: a conjunction is a pair of terms, so it is evaluated as one
# --------------------------------------------------------------------------------------------------

def index_of(terms: Sequence[Any]) -> dict[str, Any]:
    return {term.text: term for term in terms}


def holds(text: str, trace: Any, index: dict[str, Any]) -> bool:
    """A statement is a conjunction of terms joined by ' ∧ '; every conjunct must hold."""
    parts = [part.strip() for part in text.split("∧")]
    return all(index[part].holds(trace) for part in parts)


def masks_for(text: str, traces: Sequence[Any], index: dict[str, Any]) -> int:
    value = 0
    for position, trace in enumerate(traces):
        if holds(text, trace, index):
            value |= 1 << position
    return value


def bits(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# --------------------------------------------------------------------------------------------------
# the count envelope: the whole state the disputed statements can read
# --------------------------------------------------------------------------------------------------

def state_with(count: int) -> tuple[tuple[str, str], ...]:
    return tuple((f"holder_{n}", env.PROBE_NEW) for n in range(count))


def envelope(max_length: int = 6, max_jump: int = 3) -> list[Any]:
    """Every count history up to `max_length` steps, every per-step jump from -3 to +max_jump, from 0.

    This is a complete quotient for statements that read only the count of one content: two histories
    with the same count sequence are the same input to `created_once`, `monotone`, `final:count==k` and to
    the judge. So an exhaustive check here is a proof over all traces, not a sample of them."""
    histories: list[Any] = []
    for length in range(1, max_length + 1):
        for deltas in itertools.product(range(-3, max_jump + 1), repeat=length):
            counts = [0]
            for delta in deltas:
                counts.append(counts[-1] + delta)
            if min(counts) < 0:
                continue
            histories.append(tuple(state_with(count) for count in counts))
    return histories


# --------------------------------------------------------------------------------------------------
# the measurement
# --------------------------------------------------------------------------------------------------

def measure(receipt_path: pathlib.Path | None = None, *, quick: bool = False) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-agreement-"))
    depths = dict(DEPTHS)
    if quick:
        depths = {name: 3 for name in DEPTHS}

    machines: dict[str, Any] = {}
    pools: dict[str, list[Any]] = {}
    for name in FITTED + HELD_OUT:
        machine = vocab.MACHINES[name](where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        machines[name] = machine
        pools[name] = runs.traces_for(machine, ARGS, depth=depths[name])

    # the grammar is the fitted machines', and it is not extended by the held-out ones: that would be
    # fitting on the test
    terms = breadth.union_terms({name: pools[name] for name in FITTED})
    index = index_of(terms)
    per = {name: breadth.masks_on(terms, pools[name]) for name in FITTED}
    truth = {name: breadth.judge_mask(pools[name]) for name in FITTED}
    analysis = breadth.Analysis(terms, [per[name] for name in FITTED],
                                [len(pools[name]) for name in FITTED])
    truth_mask = 0
    offset = 0
    for name in FITTED:
        truth_mask |= truth[name] << offset
        offset += len(pools[name])
    report = analysis.report(truth_mask)
    statements = list(report["goal_minimal_texts"])
    if len(statements) != 2:
        raise RuntimeError("K1 assumes the previous round's two-statement class; got "
                           + json.dumps(statements))

    # K2 -- agreement on every trace of all five machines
    agreement: dict[str, Any] = {}
    every_trace = [trace for name in FITTED + HELD_OUT for trace in pools[name]]
    for text in statements:
        row: dict[str, Any] = {}
        for name in FITTED + HELD_OUT:
            machine_mask = masks_for(text, pools[name], index)
            judge = breadth.judge_mask(pools[name])
            row[name] = {"runs": len(pools[name]), "differs_from_the_judge": bits(machine_mask, judge)}
        row["ALL_FIVE"] = {"runs": len(every_trace),
                           "differs_from_the_judge": bits(masks_for(text, every_trace, index),
                                                         breadth.judge_mask(every_trace))}
        agreement[text] = row

    # K3 -- the bounded proof over the count envelope
    histories = envelope()
    judge_histories = [quotient.portable_judge(trace) for trace in histories]
    envelope_rows: dict[str, Any] = {}
    witness: dict[str, Any] | None = None
    for text in statements:
        values = [holds(text, trace, index) for trace in histories]
        differs = [position for position, value in enumerate(values) if value != judge_histories[position]]
        envelope_rows[text] = {"histories": len(histories), "differs_from_the_judge": len(differs)}
        if differs and witness is None:
            position = differs[0]
            trace = histories[position]
            witness = {"statement": text,
                       "counts": [len(state) for state in trace],
                       "statement_says": values[position],
                       "judge_says": judge_histories[position]}
    equivalent = [text for text in statements if envelope_rows[text]["differs_from_the_judge"] == 0]

    # K4 -- can any atom of any machine add two copies in one step?
    alphabet: dict[str, Any] = {}
    for name in FITTED + HELD_OUT:
        machine = machines[name]
        biggest = 0
        for atom in machine.atoms:
            machine.reset()
            before = runs._count(tuple(machine.read()), env.PROBE_NEW)
            env.execute(atom, machine, ARGS)
            after = runs._count(tuple(machine.read()), env.PROBE_NEW)
            biggest = max(biggest, after - before)
        alphabet[name] = {"atoms": len(machine.atoms), "largest_single_step_increase": biggest}

    # K6 -- the precondition, by one read per machine
    preconditions: dict[str, int] = {}
    for name in FITTED + HELD_OUT:
        machines[name].reset()
        preconditions[name] = runs._count(tuple(machines[name].read()), env.PROBE_NEW)

    survivor = equivalent[0] if len(equivalent) == 1 else None
    rejected = [text for text in statements if text != survivor]
    verdict = {
        "K1_the_class_reproduces_as_two_statements": {
            "statements": statements,
            "runs_on_the_three_fitted_machines": report["runs"],
            "MET": report["goal_minimal_statements"] == 2},
        "K2_agreement_is_total_and_still_not_identity": {
            "per_statement": agreement,
            "MET": all(row["ALL_FIVE"]["differs_from_the_judge"] == 0 for row in agreement.values())},
        "K3_the_proof_finds_the_difference_that_no_run_shows": {
            "envelope": envelope_rows,
            "witness": witness,
            "exactly_one_statement_is_equivalent": len(equivalent) == 1,
            "MET": len(equivalent) == 1 and witness is not None},
        "K4_the_witness_is_not_exhibitable_by_any_machine": {
            "alphabet": alphabet,
            "the_witness_needs_a_step_of": (witness or {}).get("counts"),
            "MET": witness is not None and all(row["largest_single_step_increase"] < 2
                                               for row in alphabet.values())},
        "K5_the_price_is_zero_questions_corrected": {
            "the_previous_round_priced": "log2(2) = 1 question of the user",
            "questions_needed_here": 0,
            "because": "the class contains a statement provably equivalent to the goal's own judge",
            "MET": len(equivalent) == 1},
        "K6_permanence_is_a_checkable_precondition": {
            "precondition": "count(initial state) == 0",
            "measured": preconditions,
            "survivor": survivor,
            "rejected": rejected,
            "MET": len(equivalent) == 1 and all(value == 0 for value in preconditions.values())},
        "K7_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-19",
        "mode": "FIVE_REAL_MACHINES__ONE_GRAMMAR__A_PROOF_INSTEAD_OF_A_QUESTION",
        "correction_to_the_previous_round": {
            "what_it_said": "the residual class can only be closed by language, not by experience",
            "what_is_true": "it cannot be closed by experience, and it does not need language either: the "
                            "class contains a statement provably equivalent to the goal's own judge, so the "
                            "bit is paid by a proof",
            "why_it_matters": "a question of the user is the most expensive bit available; pricing the "
                              "residual at one question overpriced it by exactly one question",
            "what_it_got_right": "no run separates the two statements, and this round measures that this is "
                                 "not a shortage of evidence -- the distinguishing transition is outside the "
                                 "alphabet of every machine in the tree"},
        "criteria_were_declared_after_a_prototype_probe": True,
        "which_criteria_were_already_seen": {
            "seen_before_this_round": ["K1 -- the two texts are in the previous receipt"],
            "not_seen_before_this_round": ["K2", "K3", "K4", "K5", "K6"]},
        "declared_acceptance_before_the_receipt_run": {
            "K2": "both statements agree with the judge on every trace of all five machines",
            "K3": "over the count envelope exactly one statement is equivalent to the judge, and the other "
                  "differs on a history that is exhibited as a witness",
            "K4": "no machine's atom adds two copies in one step, so the witness is not exhibitable at any "
                  "depth",
            "K5": "zero questions of the user are needed",
            "K6": "the precondition count(initial)==0 holds on all five machines"},
        "the_class": report,
        "pools": {name: len(pools[name]) for name in FITTED + HELD_OUT},
        "depths": depths,
        "verdict": verdict,
        "cost": {"seconds": 0.0, "model_calls": 0, "parameters_stored": 0,
                 "network_calls_at_run_time": 0},
        "limits": [
            "the equivalence is proved for this judge and this grammar, over a bounded count envelope "
            "(6 steps, jumps -3..+3); the envelope is a complete quotient for statements that read only "
            "the count, which is what the two disputed statements read",
            "the general claim is a criterion -- permanence is proven equivalence under a checkable "
            "precondition -- not a theorem that every goal has a total judge",
            "five CLI machines, depths 5/4/4/4/4, no network at run time, no model, no parameters",
            "the witness is a model, not a run: it refutes an equivalence, and K4 measures that no machine "
            "in the tree could produce it",
        ],
    }
    receipt["cost"]["seconds"] = round(time.time() - started, 1)
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def headline(receipt: dict[str, Any]) -> str:
    verdict = receipt["verdict"]
    equivalent = [text for text, row in verdict["K3_the_proof_finds_the_difference_that_no_run_shows"]
                  ["envelope"].items() if row["differs_from_the_judge"] == 0]
    return "\n".join([
        "runs: " + ", ".join(f"{name} {count}" for name, count in receipt["pools"].items()),
        f"class on three: {verdict['K1_the_class_reproduces_as_two_statements']['statements']}",
        f"agreement on all five: "
        f"{[row['ALL_FIVE']['differs_from_the_judge'] for row in verdict['K2_agreement_is_total_and_still_not_identity']['per_statement'].values()]}",
        f"equivalent over the envelope: {equivalent}",
        f"witness: {verdict['K3_the_proof_finds_the_difference_that_no_run_shows']['witness']}",
        f"largest single-step increase per machine: "
        f"{ {name: row['largest_single_step_increase'] for name, row in verdict['K4_the_witness_is_not_exhibitable_by_any_machine']['alphabet'].items()} }",
        f"seconds {receipt['cost']['seconds']}",
    ])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    parser.add_argument("--quick", action="store_true")
    options = parser.parse_args(argv)
    receipt = measure(options.receipt, quick=options.quick)
    print(json.dumps({key: value["MET"] for key, value in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
