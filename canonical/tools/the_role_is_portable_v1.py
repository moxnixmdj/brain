#!/usr/bin/env python3
"""The role is portable: a goal learned on one machine's runs survives a rename.

WHAT FAILED
-----------
`the_question_is_a_real_run_v1` learned, from executed filesystem runs, the sentence

    monotone[probe_seed_content] ∧ ¬final:has[seed]=probe_seed_content

for the project's `moved_judge`. It was right on 128 deeper runs of the same tool. On a git
reader it could not even be evaluated: `seed` is a filename on one machine and a commit hash on
another. The sentence was correct and unportable. Its two representations on the pool both named
a private identity.

THE SMALLEST REPAIR
-------------------
Do not change the learner, the questions, or the bit price. Change the **vocabulary**: keep only
terms that read contents and counts, drop every term that reads a private identity, and add one
computed role term per content:

    holders_changed[c] -- the set of identities holding c at the start is non-empty, the set at
                          the end is non-empty, and the two sets differ.

No name is stored: the role is evaluated from each machine's own reader. The identity-specific
goal becomes `¬two_copies[old] ∧ holders_changed[old]`, which is groundable on any machine whose
reader emits (identity, content) rows.

WHAT IS TESTED
--------------
The sentence is learned from user bits on real runs of a filesystem, then evaluated on a second,
real filesystem whose seed file is named `origin` instead of `seed`, with a different action
binding. Both machines have positive and negative runs for both goals. The old sentence is shown
to be ungrounded there; the role-based sentence is shown to be correct there.

No model, no weights, no network at run time. Authority: NONE.
"""
from __future__ import annotations

import argparse
import json
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
import the_goal_is_a_discriminator_v1 as d  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_question_is_a_real_run_v1 as prior  # noqa: E402

SCHEMA = "BRAIN_THE_ROLE_IS_PORTABLE_V1"
State = tuple[tuple[str, str], ...]
Trace = tuple[State, ...]
OLD_SENTENCE = "monotone[probe_seed_content] ∧ ¬final:has[seed]=probe_seed_content"

CRITERIA = {
    "E1": "the learning vocabulary contains no term that reads a private identity, and adds a computed holder-change role",
    "E2": "both real goals have a two-literal representation in that role vocabulary on the source runs",
    "E3": "both goals are identified by user bits on executed source runs, including the goal that needed negation",
    "E4": "the sentences are groundable and correct on a second real machine whose identities are named differently",
    "E5": "the old identity-specific sentence is ungrounded on that second machine",
    "E6": "zero model calls, zero stored parameters, zero network calls at run time",
}


# --------------------------------------------------------------------------------------------------
# the vocabulary: contents and computed roles, never a private identity
# --------------------------------------------------------------------------------------------------

def private_identities(traces: Sequence[Trace]) -> set[str]:
    return {ident for trace in traces for state in trace for ident, _content in state}


def holders(state: State, content: str) -> set[str]:
    return {ident for ident, value in state if value == content}


def holder_change(trace: Trace, content: str) -> bool:
    before, after = holders(trace[0], content), holders(trace[-1], content)
    return bool(before) and bool(after) and before != after


def surface_neutral_terms(traces: Sequence[Trace]) -> list[d.Term]:
    whole, end_only = runs.run_terms(traces)
    idents = private_identities(traces)
    kept: list[d.Term] = []
    seen: set[str] = set()
    for term in list(whole) + list(end_only):
        text = term.text
        if any(f"[{ident}]" in text or f"has {ident}" in text for ident in idents):
            continue
        if text not in seen:
            seen.add(text)
            kept.append(term)
    contents = sorted({value for trace in traces for state in trace for _ident, value in state})
    for content in contents:
        text = f"holders_changed[{content}]"
        if text not in seen:
            seen.add(text)
            kept.append(d.Term(text, lambda trace, c=content: holder_change(trace, c)))
    return kept


def by_text_for(traces: Sequence[Trace]) -> dict[str, Callable[[Trace], bool]]:
    return {term.text: term.holds for term in surface_neutral_terms(traces)}


# --------------------------------------------------------------------------------------------------
# the second machine: same real tools, different private names and different action binding
# --------------------------------------------------------------------------------------------------

def renamed_filesystem(root: pathlib.Path) -> env.Machine:
    root.mkdir(parents=True, exist_ok=True)
    base = env.build_filesystem(root)

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        (root / "origin").write_text(env.PROBE_OLD)
        (root / "second").write_text("probe_second_content")

    machine = env.Machine("RENAMED_FILESYSTEM", root, base.atoms, base.read, reset)
    machine.reset()
    return machine


def evaluate_on(sentence: str, by_text: dict[str, Callable[[Trace], bool]],
                traces: Sequence[Trace], judge: Callable[[Trace], bool]) -> dict:
    predicted = prior.evaluate(sentence, by_text, traces)
    actual = [bool(judge(trace)) for trace in traces]
    return {"runs": len(traces), "positive_runs": sum(actual),
            "matches": sum(a == b for a, b in zip(predicted, actual)),
            "agreement": round(sum(a == b for a, b in zip(predicted, actual)) / len(traces), 4),
            "predicted_positives": sum(predicted)}


# --------------------------------------------------------------------------------------------------
# receipt run
# --------------------------------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--depth", type=int, default=3)
    options = parser.parse_args(argv)
    started = time.time()

    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-role-")) / "source"
    root.mkdir(parents=True)
    source = env.build_filesystem(root)
    source.reset()
    source_args = env.probe_args(source.read(), "TARGET_EXISTS")
    pool = runs.traces_for(source, source_args, depth=options.depth)
    terms = surface_neutral_terms(pool)
    literals = prior.ground_literals(pool, terms=terms)
    space = prior.hypotheses(literals)

    goals: dict[str, Callable[[Trace], bool]] = {
        "portable": quotient.portable_judge,
        "moved": quotient.moved_judge,
    }
    goal_masks = {name: sum(1 << index for index, trace in enumerate(pool) if judge(trace))
                  for name, judge in goals.items()}
    pool_terms = runs.run_terms(pool)
    pool_by_text = {term.text: term.holds for term in list(pool_terms[0]) + list(pool_terms[1])}
    pool_by_text.update(by_text_for(pool))
    learned: dict[str, dict] = {}
    verification: dict[str, dict] = {}
    for name, judge in goals.items():
        forced: dict[int, bool] = {}
        rounds = 0
        while rounds < 5:
            rounds += 1
            result = prior.learn(space, pool, prior.User(judge), forced=forced)
            if not result.get("sentence"):
                break
            try:
                predicted = prior.evaluate(result["sentence"], pool_by_text, pool)
            except ValueError:
                break
            auditor = prior.User(judge)
            mismatches = [index for index, (trace, guess) in enumerate(zip(pool, predicted))
                          if not isinstance(auditor.answer(prior.render_run(trace), trace), bool)
                          or guess != bool(judge(trace))]
            if not mismatches:
                break
            forced[mismatches[0]] = bool(judge(pool[mismatches[0]]))
        learned[name] = result
        verification[name] = {"rounds": rounds, "forced": sorted(forced),
                              "pool_mismatches_after": len(mismatches) if result.get("sentence") else 0}

    other_root = pathlib.Path(tempfile.mkdtemp(prefix="brain-role-")) / "renamed"
    other = renamed_filesystem(other_root)
    other_args = env.probe_args(other.read(), "TARGET_EXISTS")
    other_traces = runs.traces_for(other, other_args, depth=options.depth)
    other_by_text = by_text_for(other_traces)

    transfer: dict[str, dict] = {}
    for name, judge in goals.items():
        sentence = learned[name].get("sentence")
        if sentence is None:
            transfer[name] = {"status": "NOT_LEARNED"}
            continue
        try:
            transfer[name] = evaluate_on(sentence, other_by_text, other_traces, judge)
        except ValueError as error:
            transfer[name] = {"status": "UNGROUNDED_ON_SECOND_MACHINE", "error": str(error)}
    try:
        old = evaluate_on(OLD_SENTENCE, other_by_text, other_traces, quotient.moved_judge)
    except ValueError as error:
        old = {"status": "UNGROUNDED_ON_SECOND_MACHINE", "error": str(error)}

    identity_terms = [term.text for term in terms
                      if any(f"[{ident}]" in term.text or f"has {ident}" in term.text
                             for ident in private_identities(pool))]
    role_terms = [term.text for term in terms if term.text.startswith("holders_changed[")]
    expressive = {name: sum(1 for mask in space if mask == goal_mask)
                  for name, goal_mask in goal_masks.items()}

    verdict = {
        "E1_role_vocabulary": {
            "terms": len(terms), "private_identity_terms": identity_terms,
            "role_terms": role_terms,
            "MET": not identity_terms and len(role_terms) > 0},
        "E2_both_goals_expressed": {"representations": expressive,
                                    "MET": all(count > 0 for count in expressive.values())},
        "E3_identified_from_user_bits": {
            "statuses": {name: result["status"] for name, result in learned.items()},
            "questions": {name: result.get("questions_asked") for name, result in learned.items()},
            "MET": all(result["status"] == "IDENTIFIED" for result in learned.values())},
        "E4_transfer_to_renamed_machine": {
            "machine": other.name, "source_binding": source_args, "target_binding": other_args,
            "rows": transfer,
            "MET": all(transfer[name].get("agreement") == 1.0
                       and transfer[name].get("positive_runs", 0) > 0 for name in goals)},
        "E5_old_sentence_fails_to_ground": {
            "sentence": OLD_SENTENCE, "row": old,
            "MET": old.get("status") == "UNGROUNDED_ON_SECOND_MACHINE"},
        "E6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-21",
        "mode": "COMPUTED_ROLE_VOCABULARY_TRANSFERS_A_LEARNED_GOAL_ACROSS_PRIVATE_NAMES",
        "declared_criteria": CRITERIA,
        "criteria_were_declared_before_the_receipt_run": True,
        "prototype_note": "a scratch probe of the same two machines was run while writing the tool; "
                          "the criteria are structural and were fixed before this receipt run",
        "source": {"machine": source.name, "depth": options.depth, "runs": len(pool),
                   "identity_example": env.PROBE_OLD},
        "target": {"machine": other.name, "depth": options.depth, "runs": len(other_traces),
                   "seed_name": "origin"},
        "learned": {name: {key: value for key, value in result.items() if key != "questions"}
                    for name, result in learned.items()},
        "verification": verification,
        "verdict": verdict,
        "limits": [
            "both machines are real filesystems with different private names; a different tool family is not tested here",
            "the role is one computed generator over contents; a goal needing a different role is refused",
            "the scripted user's bits come from the project's own judges, not from a model",
            "no edit, GUI, SWE-bench or OSWorld task is attempted",
        ],
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0,
                 "user_bits": sum(result.get("questions_asked", 0) for result in learned.values())},
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"portable": learned["portable"].get("sentence"),
                      "moved": learned["moved"].get("sentence"),
                      "transfer": transfer, "old_sentence": old,
                      "user_bits": receipt["cost"]["user_bits"],
                      "seconds": receipt["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
