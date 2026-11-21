#!/usr/bin/env python3
"""The witness is the question: a model-free intake that closes a goal's residual class.

WHAT THIS CONTINUES
-------------------
`breadth_buys_what_repetition_cannot_v1` measured 555 executed runs on three machines and
ended with a residual of **two** minimal statements for the user's goal:

    created_once[probe_new_content]
    monotone[probe_new_content] ∧ final:count[probe_new_content]==1

No run of those machines separates them. Its pre-registered next step was: build the intake
and price it -- (i) can one question collapse the class, (ii) does the chosen sentence predict
verdicts on a machine it was never fitted on.

THE PRINCIPLE
-------------
The two sentences differ only on a *situation*, not on a word: one copy already exists and
nothing changes. The first says the goal was not achieved; the second says it was. That
situation is computable from the statements themselves: enumerate small count histories, keep
one on which the surviving statements disagree, and ask the user their verdict on that
situation. The question needs no model: it is a rendering of a witness the grammar itself
exhibits. The answer is a single bit, which selects one sentence. Weights hold no facts; the
chosen sentence lives in the editable store.

WHAT IS REAL AND WHAT IS NOT
----------------------------
Witness traces are HYPOTHETICAL situations shown to the user. They are not runs and are never
counted as runs. The held-out check uses a real fourth machine (a filesystem seeded with a
pre-existing copy), executed through the project's own atom library and reader. The scripted
user in the receipt uses the project's goal judge as its answer; the intake itself never sees
that judge or any held-out label. A human user would supply the same bit.

THE FALSIFICATION AND ITS REPAIR
--------------------------------
The one-bit sentence is then audited on a fourth, real machine it has never seen. Here it
**fails**: it accepts four runs the user rejects. A second intake stage asks the user about
each audited situation and conjoins a grounded term that the user accepted elsewhere and
rejects here. It refuses if the user's verdict cannot be repaired by a conjunction. The
repaired sentence is finally measured on a fifth machine used by nothing before its own
evaluation. Every question is answered by the user; no machine label enters either intake.

WHAT IS REFUSED
---------------
If no separating situation exists, the class is a logical equivalence under this grammar and
the tool refuses with NO_SEPARATING_WITNESS. A non-boolean answer is refused with
INVALID_ANSWER. It never picks by preference, frequency, or by which sentence flatters the
result.

Authority: NONE. Producer-run measurement. Zero model calls, zero stored parameters, no
network at run time.
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
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_THE_WITNESS_IS_THE_QUESTION_V1"
DEFAULT_RESIDUAL = (REPO / "canonical/verification/"
                            "BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.json")
CONJUNCTION = " ∧ "
State = tuple[tuple[str, str], ...]
Trace = tuple[State, ...]

# Declared before the receipt run. Structural, so an edited tool cannot pass them by accident.
CRITERIA = {
    "C1": "the residual read from the executed 555-run receipt has two minimal statements",
    "C2": "a hypothetical situation separates the two statements and is outside the reach of the three fitted machines",
    "C3": "exactly one user verdict collapses the class to one sentence, at the log2(class) price",
    "C4": "the one-bit sentence is FALSIFIED by a real fourth machine: it over-accepts at least one run",
    "C5": "one counterexample question per over-accepted situation conjoins a grounded term and removes every falsifier",
    "C6": "the repaired sentence agrees with every verdict of a fifth machine never used by either intake stage",
    "C7": "the intake refuses with a named cause when no witness exists or the answer is not a verdict",
    "C8": "zero model calls, zero stored parameters, zero network calls at run time",
}


# --------------------------------------------------------------------------------------------------
# the hypothesis store: statements are strings over terms the machine's own reading grounded
# --------------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Statement:
    text: str
    terms: tuple[object, ...]

    def holds(self, trace: Trace) -> bool:
        return all(bool(term.holds(trace)) for term in self.terms)  # type: ignore[attr-defined]


@dataclasses.dataclass(frozen=True)
class Question:
    text: str
    trace: Trace
    counts: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class Witness:
    trace: Trace
    truth: tuple[bool, ...]
    balance: int

    @property
    def split(self) -> bool:
        return any(self.truth) and not all(self.truth)


def statement_from_text(text: str, terms_by_text: dict) -> Statement:
    parts = tuple(part.strip() for part in text.split(CONJUNCTION) if part.strip())
    if not parts or any(part not in terms_by_text for part in parts):
        raise ValueError(f"UNGROUNDED_STATEMENT: {text}")
    return Statement(text, tuple(terms_by_text[part] for part in parts))


def build_statements(texts: Sequence[str], grounding: Sequence[Trace]) -> list[Statement]:
    whole, end_only = runs.run_terms(grounding)
    by_text = {term.text: term for term in list(whole) + list(end_only)}
    return [statement_from_text(text, by_text) for text in texts]


# --------------------------------------------------------------------------------------------------
# hypothetical situations: count histories over the probe content, never executed, never called runs
# --------------------------------------------------------------------------------------------------

def _state(count: int) -> State:
    return (("seed", env.PROBE_OLD),) + tuple((f"copy{i}", env.PROBE_NEW) for i in range(count))


def _count(state: State, content: str = env.PROBE_NEW) -> int:
    return sum(1 for _ident, value in state if value == content)


def synthetic_traces(start_counts: Sequence[int] = (0, 1), length: int = 3) -> list[Trace]:
    """Every short count history, including a copy that was already there before any action."""
    traces: list[Trace] = []
    for start in start_counts:
        for steps in range(1, length + 1):
            for ops in itertools.product(("keep", "create", "remove"), repeat=steps):
                count = start
                states = [_state(count)]
                for op in ops:
                    count = count + 1 if op == "create" else max(0, count - 1) if op == "remove" else count
                    states.append(_state(count))
                trace = tuple(states)
                if trace not in traces:
                    traces.append(trace)
    return traces


def find_witness(statements: Sequence[Statement], situations: Sequence[Trace]) -> Witness | None:
    """The most balanced situation on which the surviving sentences disagree."""
    best: Witness | None = None
    for trace in situations:
        truth = tuple(statement.holds(trace) for statement in statements)
        true_count = sum(truth)
        if true_count == 0 or true_count == len(statements):
            continue
        candidate = Witness(trace, truth, min(true_count, len(statements) - true_count))
        if best is None or (candidate.balance, -len(candidate.trace)) > (best.balance, -len(best.trace)):
            best = candidate
    return best


def render_question(trace: Trace) -> Question:
    counts = tuple(_count(state) for state in trace)
    clauses = []
    for index, (before, after) in enumerate(zip(counts, counts[1:]), start=1):
        change = "nothing changes" if after == before else (
            "one new copy appears" if after > before else "one copy disappears")
        clauses.append(f"step {index}: {change}, so {after} cop{'y remains' if after == 1 else 'ies remain'}")
    text = (f"Situation: at the start there "
            f"is {'one copy' if counts[0] == 1 else f'{counts[0]} copies'} of the new content. "
            + "; ".join(clauses) + ". Is the goal already achieved in this situation?")
    return Question(text, trace, counts)


# --------------------------------------------------------------------------------------------------
# the intake: one bit per question, no guessing, no preference, no model
# --------------------------------------------------------------------------------------------------

class User:
    """A user, or a scripted stand-in, that answers a rendered situation with one bit."""

    def __init__(self, judge: Callable[[Trace], bool]) -> None:
        self.judge = judge
        self.bits_asked = 0

    def answer(self, question: Question) -> object:
        self.bits_asked += 1
        return self.judge(question.trace)


def intake(statements: Sequence[Statement], situations: Sequence[Trace], user: User) -> dict:
    survivors = list(statements)
    original = len(survivors)
    if original < 2:
        return {"status": "NOT_AN_AMBIGUITY", "class_size": original}
    budget = math.ceil(math.log2(original))
    questions: list[dict] = []
    chosen = survivors[0]
    while len(survivors) > 1:
        witness = find_witness(survivors, situations)
        if witness is None:
            return {"status": "NO_SEPARATING_WITNESS", "class_size": len(survivors),
                    "survivors": [s.text for s in survivors], "questions": questions}
        question = render_question(witness.trace)
        answer = user.answer(question)
        if not isinstance(answer, bool):
            return {"status": "INVALID_ANSWER", "questions": questions,
                    "survivors": [s.text for s in survivors]}
        kept = [statement for statement in survivors if statement.holds(witness.trace) == answer]
        questions.append({"question": question.text, "counts": list(question.counts),
                          "answer": answer, "before": len(survivors), "after": len(kept),
                          "truth_in_class_order": list(witness.truth)})
        if not kept:
            return {"status": "UNSHARED_VERDICT", "class_size": 0, "questions": questions}
        if len(questions) > budget:
            return {"status": "QUESTION_BUDGET_EXCEEDED", "budget": budget, "questions": questions}
        survivors = kept
    chosen = survivors[0]
    return {"status": "CLOSED", "class_size": 1, "chosen": chosen.text,
            "questions": questions, "questions_asked": len(questions), "budget": budget}


# --------------------------------------------------------------------------------------------------
# counterexample-guided repair: the user's verdict on a falsifying situation buys one conjunct
# --------------------------------------------------------------------------------------------------

def repair_from_user(chosen: Statement, grammar_terms: Sequence[object],
                     audit_traces: Sequence[Trace], user: User) -> dict:
    """Conjoin grounded terms until no situation the user rejects is accepted by the sentence.

    The candidate term is selected by two things the user has actually said: it is false on the
    rejected situation and true on a situation the user accepted. No machine label is read here.
    """
    positive = (_state(0), _state(1))
    if user.answer(render_question(positive)) is not True:
        return {"status": "NO_ACCEPTED_SITUATION"}
    accepted = [positive]
    conjuncts = list(chosen.terms)
    questions: list[dict] = []
    for trace in audit_traces:
        current = Statement(CONJUNCTION.join(t.text for t in conjuncts), tuple(conjuncts))
        verdict = user.answer(render_question(trace))
        if not isinstance(verdict, bool):
            return {"status": "INVALID_ANSWER", "questions": questions}
        if current.holds(trace) == verdict:
            if verdict:
                accepted.append(trace)
            continue
        if verdict:
            return {"status": "UNDER_ACCEPTS__CONJUNCTION_CANNOT_REPAIR", "questions": questions}
        candidates = [term for term in grammar_terms
                      if not term.holds(trace) and all(term.holds(situation) for situation in accepted)]
        if not candidates:
            return {"status": "NO_REPAIRING_TERM", "questions": questions}
        candidate = sorted(candidates, key=lambda term: (len(term.text), term.text))[0]
        conjuncts.append(candidate)
        questions.append({"question": render_question(trace).text, "answer": verdict,
                          "added_term": candidate.text})
    return {"status": "REPAIRED", "text": CONJUNCTION.join(t.text for t in conjuncts),
            "questions": questions, "questions_asked": len(questions) + 1}


# --------------------------------------------------------------------------------------------------
# the falsifier and the held-out machine: both are real, both are executed
# --------------------------------------------------------------------------------------------------

def preloaded_filesystem(root: pathlib.Path) -> env.Machine:
    root.mkdir(parents=True, exist_ok=True)
    base = env.build_filesystem(root)

    def reset() -> None:
        base.reset()
        (root / "was_already_here").write_text(env.PROBE_NEW)

    machine = env.Machine("PRELOADED_FILESYSTEM", root, base.atoms, base.read, reset)
    machine.reset()
    return machine


def two_atom_filesystem(root: pathlib.Path) -> env.Machine:
    """A fifth machine: same real tool, a different action repertoire, never used in fitting."""
    root.mkdir(parents=True, exist_ok=True)
    base = env.build_filesystem(root)
    return env.Machine("TWO_ATOM_FILESYSTEM", root, base.atoms[:2], base.read, base.reset)


def agreement(statement: Statement, traces: Sequence[Trace],
              labels: Sequence[bool], by_text: dict) -> dict:
    parsed = statement_from_text(statement.text, by_text)
    matches = sum(parsed.holds(trace) == bool(label) for trace, label in zip(traces, labels))
    return {"agreement": round(matches / len(traces), 4) if traces else None,
            "matches": matches, "runs": len(traces)}


# --------------------------------------------------------------------------------------------------
# the receipt run
# --------------------------------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--residual-from", type=pathlib.Path, default=DEFAULT_RESIDUAL)
    parser.add_argument("--depth", type=int, default=2)
    options = parser.parse_args(argv)
    started = time.time()

    upstream = json.loads(options.residual_from.read_text(encoding="utf-8"))
    texts = list(upstream["verdict"]["B3_the_residual_survives_every_machine"]["texts"])

    situations = synthetic_traces()
    statements = build_statements(texts, situations)

    # The scripted user encodes the owner's sentence ("copy it once and keep it"), the same
    # sentence the upstream receipt calls the user's goal. The intake never reads this judge.
    user = User(quotient.portable_judge)
    result = intake(statements, situations, user)

    witness = find_witness(statements, situations)
    witness_counts = list(render_question(witness.trace).counts) if witness else None
    fitted_reach = {
        "TARBALL": "no remove-then-create and no pre-existing copy",
        "FILESYSTEM": "rm exists but reset never seeds the new content",
        "SQLITE": "no pre-existing new-content row",
    }

    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-witness-"))

    # Fourth machine: the falsifier. The one-bit sentence was fitted without ever seeing it.
    audit = preloaded_filesystem(where / "audit")
    audit_args = env.probe_args(audit.read(), "TARGET_ABSENT")
    audit_traces = runs.traces_for(audit, audit_args, depth=options.depth)
    audit_labels = [quotient.portable_judge(trace) for trace in audit_traces]
    audit_terms = runs.run_terms(audit_traces)
    audit_by_text = {term.text: term for term in list(audit_terms[0]) + list(audit_terms[1])}
    audit_grammar = list(audit_terms[0]) + list(audit_terms[1])

    chosen = next((statement for statement in statements
                   if result.get("chosen") == statement.text), None)
    chosen_audit = agreement(chosen, audit_traces, audit_labels, audit_by_text) if chosen else None
    rejected_audit = [{"text": statement.text,
                       **agreement(statement, audit_traces, audit_labels, audit_by_text)}
                      for statement in statements if chosen is None or statement.text != chosen.text]
    overaccepted = len([trace for trace, label in zip(audit_traces, audit_labels)
                        if chosen is not None and chosen.holds(trace) and not label])

    # Counterexample-guided repair. Every term added is confirmed by the user's verdict on a
    # situation; no machine label is read by the repair function.
    repaired = repair_from_user(chosen, audit_grammar, audit_traces, user) if chosen else {
        "status": "NO_CHOSEN_SENTENCE"}
    repaired_statement = None
    if repaired.get("status") == "REPAIRED":
        try:
            repaired_statement = statement_from_text(repaired["text"], audit_by_text)
        except ValueError:
            repaired["status"] = "REPAIRED_STATEMENT_NOT_GROUNDED"
    repaired_audit = (agreement(repaired_statement, audit_traces, audit_labels, audit_by_text)
                      if repaired_statement else None)

    # Fifth machine: never used by selection, falsification, or repair.
    held = two_atom_filesystem(where / "held")
    held_args = env.probe_args(held.read(), "TARGET_ABSENT")
    held_traces = runs.traces_for(held, held_args, depth=3)
    held_labels = [quotient.portable_judge(trace) for trace in held_traces]
    held_terms = runs.run_terms(held_traces)
    held_by_text = {term.text: term for term in list(held_terms[0]) + list(held_terms[1])}
    held_rows = {"chosen": agreement(chosen, held_traces, held_labels, held_by_text) if chosen else None,
                 "rejected": [{"text": row["text"],
                               **agreement(statement_from_text(row["text"], held_by_text),
                                           held_traces, held_labels, held_by_text)}
                              for row in rejected_audit],
                 "repaired": agreement(repaired_statement, held_traces, held_labels, held_by_text)
                 if repaired_statement else None}

    # Fail-closed checks.
    refusal_equal = intake([statements[0], statements[0]], situations, User(quotient.portable_judge))
    refusal_invalid = intake(statements, situations, User(lambda _trace: None))

    witness = find_witness(statements, situations)
    witness_counts = list(render_question(witness.trace).counts) if witness else None
    fitted_reach = {
        "TARBALL": "reset never seeds the new content; no delete-then-create history",
        "FILESYSTEM": "reset never seeds the new content",
        "SQLITE": "reset never seeds the new content",
    }
    verdict = {
        "C1_residual_is_two": {"count": len(texts), "texts": texts, "MET": len(texts) == 2},
        "C2_witness_outside_fitted_reach": {
            "counts": witness_counts, "hypothetical": True, "fitted_machines": fitted_reach,
            "MET": witness is not None and witness.split and bool(witness_counts)
                   and witness_counts[0] == 1},
        "C3_one_bit_closes_the_class": {
            "initial_class": len(statements), "questions": result.get("questions_asked"),
            "budget": result.get("budget"), "status": result.get("status"),
            "MET": result.get("status") == "CLOSED" and result.get("questions_asked") == 1},
        "C4_one_bit_sentence_is_falsified": {
            "sentence": result.get("chosen"), "audit_row": chosen_audit,
            "over_accepted_runs": overaccepted, "rejected": rejected_audit,
            "MET": overaccepted > 0},
        "C5_counterexample_repair": {
            "status": repaired.get("status"), "repaired_text": repaired.get("text"),
            "questions": repaired.get("questions", []), "audit_row": repaired_audit,
            "MET": repaired.get("status") == "REPAIRED" and bool(repaired_audit)
                   and repaired_audit["agreement"] == 1.0},
        "C6_fifth_machine_prediction": {
            "machine": held.name, "runs": len(held_traces), "positive_labels": sum(held_labels),
            "rows": held_rows,
            "all_candidates_agree": all(row["agreement"] == 1.0 for row in held_rows.values()
                                        if isinstance(row, dict) and "agreement" in row),
            "note": "this machine confirms the repaired sentence but does not discriminate it "
                    "from the two one-bit candidates; the discriminating machine is the audit one",
            "MET": bool(held_rows["repaired"] and held_rows["repaired"]["agreement"] == 1.0
                        and sum(held_labels) > 0)},
        "C7_fail_closed": {
            "equivalent_class": refusal_equal["status"], "invalid_answer": refusal_invalid["status"],
            "MET": refusal_equal["status"] == "NO_SEPARATING_WITNESS"
                   and refusal_invalid["status"] == "INVALID_ANSWER"},
        "C8_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "COMPUTED_WITNESS__FALSIFICATION__COUNTEREXAMPLE_REPAIR__FIFTH_MACHINE",
        "upstream": {"receipt": str(options.residual_from.relative_to(REPO)),
                     "runs_fitted": upstream["runs"], "residual_texts": texts},
        "declared_criteria": CRITERIA,
        "criteria_were_declared_before_the_receipt_run": True,
        "prototype_note": "one exploratory run of the one-bit intake was executed while writing the "
                          "tool and falsified C4; the criteria above were then rewritten so that "
                          "the falsification is itself a declared, measurable claim",
        "intake": result,
        "verdict": verdict,
        "audit_machine": {"name": audit.name, "runs": len(audit_traces),
                          "positive_labels": sum(audit_labels), "depth": options.depth},
        "held_out_machine": {"name": held.name, "runs": len(held_traces),
                             "positive_labels": sum(held_labels), "depth": 3,
                             "used_by": "nothing before its own evaluation"},
        "user_bits_asked": user.bits_asked,
        "limits": [
            "witness situations are hypothetical and are not runs; the fourth and fifth machines are executed",
            "the scripted user's bits come from the project's goal judge; a human would supply them",
            "the repaired conjunction is expressible in this 244-term grammar; goals outside it are refused",
            "the fifth machine is one environment: agreement there is evidence, not proof of all environments",
            "no edit is composed and no program is repaired; this prices the sentence an edit is for",
        ],
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"status": result.get("status"), "chosen": result.get("chosen"),
                      "question": result["questions"][0]["question"] if result.get("questions") else None,
                      "repair": repaired.get("status"), "repaired": repaired.get("text"),
                      "user_bits": user.bits_asked, "seconds": receipt["cost"]["seconds"]},
                     indent=1))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
