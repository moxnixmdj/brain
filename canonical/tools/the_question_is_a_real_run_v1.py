#!/usr/bin/env python3
"""The question is a real run: negation costs a bit, not a model.

WHAT THIS CONTINUES
-------------------
`the_witness_is_the_question_v1` asked about hypothetical situations, repaired a conjunction from
user bits, and was falsified by a real machine: the one-bit sentence accepted four runs the user
rejected. Its pre-registered bottleneck was the hypothesis class and the reach of the situations
used to ask.

This round changes exactly two things, and nothing else:

1. The questions are **executed runs** of a machine, rendered as situations. Nothing hypothetical
   is asked; a run in the pool really happened.
2. The hypothesis class is a conjunction of at most two **literals** -- a grounded run term or its
   negation -- instead of a conjunction of positive terms only.

WHY THE SECOND CHANGE IS NECESSARY, NOT PREFERENCE
--------------------------------------------------
On 68 executed filesystem runs, the project's own `moved_judge` ("the original was moved, not
copied and deleted") has **zero** representations as a conjunction of two positive terms, and two
representations once negation is admitted. A learner restricted to the old class cannot say the
user's sentence at all; more questions cannot fix a grammar that lacks the sentence.

WHAT IS MEASURED
----------------
For each of two real goals, a version space of conjunctions of literals is maintained as bitmasks
over the executed pool. The next question is the pool run that most evenly splits the surviving
behaviours -- selected from unlabelled runs only. A scripted user (the project's own judge)
answers one bit per question. The surviving sentence is then checked on 128 *deeper* executed runs
that were never in the pool. A third goal, computed as the first XOR of two grounded masks absent
from the class, must fail closed with a named cause instead of producing a guess.

NOT CLAIMED
-----------
No edit is composed, no GUI is driven, no SWE-bench instance is solved. The terms are the
project's existing run-term vocabulary; the learner is not a general boolean learner and refuses
goals needing more than two literals. The scripted user's bits come from the project's judge; a
human would supply them. No model, no weights, no network at run time.

Authority: NONE. Producer-run measurement. Zero model calls, zero stored parameters.
"""
from __future__ import annotations

import argparse
import dataclasses
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
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402

SCHEMA = "BRAIN_THE_QUESTION_IS_A_REAL_RUN_V1"
CONJUNCTION = " ∧ "
NEGATION = "¬"
State = tuple[tuple[str, str], ...]
Trace = tuple[State, ...]

CRITERIA = {
    "D1": "the question pool is made of real executed runs and both real goals have positive and negative runs",
    "D2": "the moved goal has no positive-term conjunction of two literals but does have a literal conjunction",
    "D3": "both goals are identified from user bits on real runs within ceil(log2(class)) questions",
    "D4": "both identified sentences agree with every verdict on 128 deeper runs never used in the pool",
    "D5": "a goal outside the class fails closed with a named cause and no chosen sentence",
    "D6": "zero model calls, zero stored parameters, zero network calls at run time",
}


# --------------------------------------------------------------------------------------------------
# grounded literals: a term the machine emitted, or its negation
# --------------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Literal:
    text: str
    mask: int
    base: str
    negated: bool


def ground_literals(traces: Sequence[Trace]) -> list[Literal]:
    whole, end_only = runs.run_terms(traces)
    full = (1 << len(traces)) - 1
    out: list[Literal] = []
    for term in list(whole) + list(end_only):
        mask = sum(1 << index for index, trace in enumerate(traces) if bool(term.holds(trace)))
        if mask in (0, full):
            continue  # a term constant over the pool cannot answer a question
        out.append(Literal(term.text, mask, term.text, False))
        out.append(Literal(NEGATION + term.text, full ^ mask, term.text, True))
    return out


def hypotheses(literals: Sequence[Literal], *, max_terms: int = 2) -> dict[int, str]:
    """One behaviour per mask; when several spellings fit, keep the shortest, then the first."""
    out: dict[int, str] = {}
    for size in range(1, max_terms + 1):
        for combo in itertools.combinations(literals, size):
            mask = combo[0].mask
            for literal in combo[1:]:
                mask &= literal.mask
            if mask in out:
                continue
            text = CONJUNCTION.join(literal.text for literal in combo)
            out[mask] = text
    # shortest spelling wins within a behaviour, with lexicographic tie-break
    by_behaviour: dict[int, str] = {}
    for mask, text in out.items():
        if mask not in by_behaviour or (text.count(CONJUNCTION), text) < (
                by_behaviour[mask].count(CONJUNCTION), by_behaviour[mask]):
            by_behaviour[mask] = text
    return by_behaviour


def positive_only(literals: Sequence[Literal]) -> dict[int, str]:
    return hypotheses([literal for literal in literals if not literal.negated])


# --------------------------------------------------------------------------------------------------
# a real run, rendered as a situation a user can judge
# --------------------------------------------------------------------------------------------------

def _describe_step(before: State, after: State) -> str:
    def counts(state: State) -> dict[str, int]:
        result: dict[str, int] = {}
        for _ident, value in state:
            result[value] = result.get(value, 0) + 1
        return result
    was, now = counts(before), counts(after)
    changes = []
    for content in sorted(set(was) | set(now)):
        if was.get(content, 0) != now.get(content, 0):
            changes.append(f"{content} {was.get(content, 0)}→{now.get(content, 0)}")
    holders_before = sorted((ident, value) for ident, value in before)
    holders_after = sorted((ident, value) for ident, value in after)
    moved = sorted(set(holders_after) - set(holders_before))
    gone = sorted(set(holders_before) - set(holders_after))
    parts = changes[:]
    if moved:
        parts.append("appeared at " + ", ".join(f"{ident}={value}" for ident, value in moved[:3]))
    if gone:
        parts.append("disappeared from " + ", ".join(f"{ident}={value}" for ident, value in gone[:3]))
    return ", ".join(parts) if parts else "nothing changed"


def render_run(trace: Trace) -> str:
    first = "start: " + (", ".join(f"{ident} holds {value}" for ident, value in sorted(trace[0]))
                         or "nothing is present")
    steps = [f"step {index}: {_describe_step(before, after)}"
             for index, (before, after) in enumerate(zip(trace, trace[1:]), start=1)]
    return first + "; " + "; ".join(steps) + ". Is the goal already achieved in this situation?"


class User:
    def __init__(self, judge: Callable[[Trace], bool]) -> None:
        self.judge = judge
        self.bits_asked = 0

    def answer(self, question: str, trace: Trace) -> object:
        self.bits_asked += 1
        return self.judge(trace)


# --------------------------------------------------------------------------------------------------
# exact learning by maximum-split membership questions on real runs
# --------------------------------------------------------------------------------------------------

def learn(space: dict[int, str], traces: Sequence[Trace], user: User) -> dict:
    surviving = set(space)
    if not surviving:
        return {"status": "EMPTY_CLASS", "questions": []}
    budget = math.ceil(math.log2(len(surviving))) if len(surviving) > 1 else 0
    questions: list[dict] = []
    while len(surviving) > 1:
        best: tuple[int, int] | None = None
        for index in range(len(traces)):
            ones = sum(1 for mask in surviving if (mask >> index) & 1)
            balance = min(ones, len(surviving) - ones)
            if balance == 0:
                continue
            if best is None or balance > best[0]:
                best = (balance, index)
        if best is None:
            return {"status": "NO_QUESTION_SEPARATES", "questions": questions,
                    "survivors": len(surviving)}
        index = best[1]
        answer = user.answer(render_run(traces[index]), traces[index])
        if not isinstance(answer, bool):
            return {"status": "INVALID_ANSWER", "questions": questions}
        questions.append({"run": index, "question": render_run(traces[index]), "answer": answer,
                          "survivors_before": len(surviving)})
        surviving = {mask for mask in surviving if bool((mask >> index) & 1) == answer}
        if not surviving:
            return {"status": "GOAL_OUTSIDE_CLASS", "questions": questions}
        if len(questions) > budget:
            return {"status": "QUESTION_BUDGET_EXCEEDED", "budget": budget, "questions": questions}
    mask = next(iter(surviving))
    return {"status": "IDENTIFIED", "sentence": space[mask], "behaviour": mask,
            "questions": questions, "questions_asked": len(questions), "budget": budget}


def evaluate(sentence: str, by_text: dict[str, Callable[[Trace], bool]],
             traces: Sequence[Trace]) -> list[bool]:
    parts = [part.strip() for part in sentence.split(CONJUNCTION) if part.strip()]
    out: list[bool] = []
    for trace in traces:
        value = True
        for part in parts:
            negated = part.startswith(NEGATION)
            base = part[1:] if negated else part
            if base not in by_text:
                raise ValueError(f"UNGROUNDED_LITERAL: {base}")
            truth = bool(by_text[base](trace))
            value = value and (not truth if negated else truth)
        out.append(value)
    return out


# --------------------------------------------------------------------------------------------------
# receipt run
# --------------------------------------------------------------------------------------------------

def _unavailable_receipt(options: argparse.Namespace, reason: str, seconds: float) -> int:
    receipt = {"schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "status": reason,
               "cost": {"seconds": round(seconds, 1), "model_calls": 0,
                        "parameters_stored": 0, "network_calls_at_run_time": 0}}
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(reason)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--depth", type=int, default=3)
    options = parser.parse_args(argv)
    started = time.time()

    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-real-run-")) / "filesystem"
    root.mkdir(parents=True)
    machine = env.build_filesystem(root)
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "backup"}
    pool = runs.traces_for(machine, args, depth=options.depth)
    literals = ground_literals(pool)
    full_space = hypotheses(literals)
    pos_space = positive_only(literals)

    # The fail-closed control is computed, not hand-picked: the first XOR of two grounded
    # literal masks that the class cannot represent. A hand-picked "impossible" goal previously
    # turned out to be expressible, which is exactly why it is now searched for mechanically.
    full = (1 << len(pool)) - 1
    control_mask = None
    for first, second in itertools.combinations(literals, 2):
        candidate = first.mask ^ second.mask
        if 0 < candidate < full and candidate not in full_space:
            control_mask = candidate
            break
    if control_mask is None:
        return _unavailable_receipt(options, "NO_OUT_OF_CLASS_GOAL_IN_THIS_POOL", time.time() - started)
    index_of = {trace: index for index, trace in enumerate(pool)}

    goals = {
        "portable": quotient.portable_judge,
        "moved": quotient.moved_judge,
        "outside_class": lambda trace: bool((control_mask >> index_of[trace]) & 1),
    }
    goal_masks = {name: sum(1 << index for index, trace in enumerate(pool) if judge(trace))
                  for name, judge in goals.items()}
    results: dict[str, dict] = {}
    for name, judge in goals.items():
        results[name] = learn(full_space, pool, User(judge))

    # Verification by more user answers: a sentence that survives log2(class) questions can still
    # disagree on a run never asked about. The user is asked about every pool run; a disagreement
    # is a falsification, not a reason to edit the sentence until it happens to fit.
    pool_terms = runs.run_terms(pool)
    pool_by_text = {term.text: term.holds for term in list(pool_terms[0]) + list(pool_terms[1])}
    for name, judge in goals.items():
        result = results[name]
        if not result.get("sentence"):
            continue
        auditor = User(judge)
        predicted = evaluate(result["sentence"], pool_by_text, pool)
        mismatches = []
        for index, (trace, guess) in enumerate(zip(pool, predicted)):
            verdict = auditor.answer(render_run(trace), trace)
            if not isinstance(verdict, bool) or guess != verdict:
                mismatches.append(index)
        result["audit_bits"] = auditor.bits_asked
        result["pool_audit_mismatches"] = len(mismatches)
        if mismatches:
            result["status"] = "GOAL_OUTSIDE_CLASS"
            result["reason"] = "POOL_AUDIT_MISMATCH"
            result["mismatch_runs"] = mismatches[:8]
            del result["sentence"]

    held = [trace for trace in runs.traces_for(machine, args, depth=options.depth + 1)
            if trace not in pool]
    whole, end_only = runs.run_terms(held + pool)
    by_text = {term.text: term.holds for term in list(whole) + list(end_only)}
    predictions: dict[str, dict] = {}
    for name, judge in goals.items():
        sentence = results[name].get("sentence")
        if sentence is None:
            predictions[name] = {"status": results[name]["status"], "chosen": None}
            continue
        predicted = evaluate(sentence, by_text, held)
        actual = [bool(judge(trace)) for trace in held]
        predictions[name] = {"chosen": sentence, "runs": len(held),
                             "positive_runs": sum(actual),
                             "matches": sum(a == b for a, b in zip(predicted, actual)),
                             "agreement": round(sum(a == b for a, b in zip(predicted, actual))
                                                / len(held), 4) if held else None}

    moved_mask = goal_masks["moved"]
    verdict = {
        "D1_real_pool": {
            "runs": len(pool), "literals": len(literals), "hypotheses": len(full_space),
            "goal_positives": {name: bin(mask).count("1") for name, mask in goal_masks.items()},
            "MET": all(0 < bin(mask).count("1") < len(pool) for mask in goal_masks.values())},
        "D2_negation_is_necessary": {
            "positive_representations": sum(1 for mask in pos_space if mask == moved_mask),
            "literal_representations": sum(1 for mask in full_space if mask == moved_mask),
            "MET": moved_mask not in pos_space and moved_mask in full_space},
        "D3_identified_from_user_bits": {
            "statuses": {name: result["status"] for name, result in results.items()},
            "questions": {name: result.get("questions_asked") for name, result in results.items()},
            "budgets": {name: result.get("budget") for name, result in results.items()},
            "MET": results["portable"]["status"] == "IDENTIFIED"
                   and results["moved"]["status"] == "IDENTIFIED"
                   and all(result.get("questions_asked", 99) <= result.get("budget", 0)
                           for name, result in results.items() if name != "outside_class")},
        "D4_deeper_held_out": {
            "rows": predictions,
            "MET": predictions["portable"].get("agreement") == 1.0
                   and predictions["moved"].get("agreement") == 1.0},
        "D5_out_of_class_refuses": {
            "status": results["outside_class"]["status"],
            "questions": len(results["outside_class"]["questions"]),
            "chosen": results["outside_class"].get("sentence"),
            "MET": results["outside_class"]["status"] == "GOAL_OUTSIDE_CLASS"
                   and results["outside_class"].get("sentence") is None},
        "D6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-21",
        "mode": "MEMBERSHIP_QUESTIONS_ON_REAL_RUNS_WITH_NEGATED_GROUNDED_LITERALS",
        "declared_criteria": CRITERIA,
        "criteria_were_declared_before_the_receipt_run": True,
        "prototype_note": "a scratch probe over the same pool was run while writing the tool to "
                          "check that the moved goal needed negation; the criteria above are "
                          "structural and were fixed before this receipt run",
        "pool": {"machine": machine.name, "depth": options.depth, "runs": len(pool),
                 "questions_are_real_runs": True},
        "held_out": {"machine": machine.name, "depth": options.depth + 1,
                     "runs": len(held), "used_by_learner": False},
        "results": {name: {key: value for key, value in result.items() if key != "questions"}
                    for name, result in results.items()},
        "first_questions": {name: (result["questions"][0]["question"]
                                  if result.get("questions") else None)
                            for name, result in results.items()},
        "verdict": verdict,
        "limits": [
            "the pool and the held-out runs are the same real tool at different depths; a different tool is not tested here",
            "conjunctions of at most two literals are a stated class; a goal outside it refuses",
            "the scripted user's bits come from the project's own judges, not from a model",
            "no edit, no GUI, no SWE-bench or OSWorld task is attempted",
        ],
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0,
                 "user_bits": sum(result.get("questions_asked", len(result["questions"]))
                                  + result.get("audit_bits", 0)
                                  for result in results.values())},
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"portable": results["portable"].get("sentence"),
                      "moved": results["moved"].get("sentence"),
                      "outside_class": results["outside_class"]["status"],
                      "user_bits": receipt["cost"]["user_bits"],
                      "seconds": receipt["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
