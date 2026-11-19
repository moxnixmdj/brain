#!/usr/bin/env python3
"""What a correct decision costs: guess, demonstration, or a trial in a copy -- and when the trial stops.

THE QUESTION. "Give the model each action once and it keeps it permanently, so all computer use is solved."
Last round measured the *knowledge* half on a real machine: a demonstration identifies no condition (0 of
10 actions), contrasts buy it where the deciding fact is observable (0.9464) and cannot where it is not
(0.5833). What that leaves unanswered is the question an owner actually cares about, and it is not
accuracy -- it is PRICE:

    To decide correctly, what must an agent spend, how often, and when does the spending stop?

THE THREE WAYS TO DECIDE, all measured on real processes:

  guess            no knowledge, no trial: answer the majority class.       price 0, accuracy = base rate
  demonstration    one demonstration, then act on the rule it licenses.      price 0, accuracy = the
                                                                             trace's rule
  trial            run the action in a COPY of the state and read the exit   price 1 copy + 1 execution
                   status. This decides ANY action on ANY machine, because   per decision, accuracy 1.0
                   an action is a program and a program has an exit status.

That third row is the whole of "computer use" as a decision problem, and it is worth being precise about
what it is and is not. It is not knowledge: the trial gives a LABEL for the state in front of you and
nothing else, and it must be paid again in the next state. It is not learning. It is *deciding*, and it is
universal -- it needs no sensor, no model, and no condition, which is exactly why it works on the three
actions whose condition no sensor can see.

THE LOOP, which is the round's constructive claim. The trials an agent must make anyway are labelled states,
and labelled states are what `applicability_v1` needs. So an agent that starts by trialling every decision
should pay for its knowledge out of the work it was already doing, and stop trialling when the knowledge
arrives -- at zero extra executions. Whether that actually happens, and where it fails, is measured here.

THE CHOOSER, which is the round's other claim. If the agent may choose *which* state to try next instead of
taking the stream in order, the knowledge should arrive in fewer executions. That difference is the first
measurable price of curiosity in this tree: not "does exploring help" but "what does choosing the question
buy, in executions".

COST. No model, no parameters, no network beyond the one clone the machine needs. Real `git`, `tar`,
`gzip`, `patch`. A state is copied before it is touched, and the copy is timed, because the copy IS the
price.

Authority NONE. Producer-run measurement.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import time
from typing import Any, Sequence

SCHEMA = "BRAIN_WHAT_A_DECISION_COSTS_V1"

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import contrast_selection_v1 as CONTRAST  # noqa: E402
from canonical.tools import the_precondition_is_not_in_the_trace_v1 as MACHINE  # noqa: E402

APPLIES, DOES_NOT, AMBIGUOUS = MACHINE.APPLIES, MACHINE.DOES_NOT, MACHINE.AMBIGUOUS

#: How a decision was reached. Every decision in this file is one of these, and every one of them is
#: counted, because a price that is not counted is not a price.
BY_GUESS = "GUESS"
BY_DEMONSTRATION = "DEMONSTRATION"
BY_KNOWLEDGE = "KNOWLEDGE"
BY_TRIAL = "TRIAL"


def _interleave(rows: list[Any]) -> list[Any]:
    """Positives and negatives alternating: no policy may win because the stream was sorted."""
    out: list[Any] = []
    head = [row for row in rows if row[2] == APPLIES]
    tail = [row for row in rows if row[2] == DOES_NOT]
    for index in range(max(len(head), len(tail))):
        if index < len(head):
            out.append(head[index])
        if index < len(tail):
            out.append(tail[index])
    out.extend(row for row in rows if row[2] == AMBIGUOUS)
    return out


def decisive(boundary, facts: Sequence[str]) -> bool | None:
    """Does the knowledge decide THIS state, even when it cannot name the condition?

    This is the switch the loop needs, and it is not `boundary.identified`. A requirement set that still
    holds a thousand survivors is usable on a state where they ALL agree: the agent does not have to know
    the condition to know it does not matter here. It only has to pay a trial where they disagree.
    `None` means the evidence licenses no requirement at all (no failure yet), so nothing is decided.
    """
    survivors = getattr(boundary, "survivors", ()) or ()
    if not survivors:
        return None
    present = set(facts)
    answers = {set(req) <= present for req in survivors}
    return answers.pop() if len(answers) == 1 else None


def measure_action(action, states, root: pathlib.Path, copy_seconds: float) -> dict[str, Any]:
    """Run all three ways of deciding over the same real states, and count every execution."""
    table = []
    for state in states:
        outcome, note = MACHINE.verdict(state, action, root)
        table.append((state, frozenset(state.facts), outcome, note))
    stream = _interleave(table)
    truth = [row[2] == APPLIES for row in stream]
    positives = [row for row in table if row[2] == APPLIES]
    negatives = [row for row in table if row[2] == DOES_NOT]

    result: dict[str, Any] = {
        "action": action.name,
        "purpose": action.purpose,
        "argv": list(action.argv),
        "states": len(table),
        "applies": len(positives),
        "does_not_apply": len(negatives),
        "ambiguous": sum(1 for row in table if row[2] == AMBIGUOUS),
        "base_rate": round(sum(truth) / len(truth), 4) if truth else 0.0,
    }
    if len(positives) < 3 or len(negatives) < 3:
        result["stage"] = "REFUSED__NOT_ENOUGH_STATES_OF_EITHER_KIND"
        return result

    # ---- guess ---------------------------------------------------------------------------------
    guesses = [True] * len(stream)
    result["guess"] = {
        "accuracy": round(sum(int(g == t) for g, t in zip(guesses, truth)) / len(truth), 4),
        "executions": 0, "decisions": len(truth),
    }

    # ---- demonstration: one success, then act on what it licenses -------------------------------
    demo = positives[0]
    specific = frozenset(demo[1])
    result["demonstration"] = {
        "accuracy": round(sum(int((specific <= facts) == t)
                              for (_s, facts, _o, _n), t in zip(stream, truth)) / len(truth), 4),
        "accuracy_always_true": round(sum(int(t) for t in truth) / len(truth), 4),
        "executions": 1,        # the one demonstration
        "decisions": len(truth),
        "licensed_requirement_size": len(specific),
    }

    # ---- trial every time: decide by executing in a copy ----------------------------------------
    result["trial_always"] = {
        "accuracy": 1.0,                       # by construction: the trial IS the exit status
        "executions": len(truth),
        "copies": len(truth),
        "seconds": round(copy_seconds * len(truth), 3),
        "knowledge": None,
    }

    # ---- trial, then keep the lesson: stop paying when the condition is known -------------------
    evidence: list[tuple[tuple[str, ...], bool]] = []
    decisions = trials = 0
    decided_without_trial = 0
    correct = 0
    last_trial_at: int | None = None
    boundary = APP.learn(evidence)
    for (state, facts, outcome, _note), is_true in zip(stream, truth):
        decisions += 1
        known = decisive(boundary, facts)
        if known is None:
            answer, _n = MACHINE.verdict(state, action, root)
            trials += 1
            last_trial_at = decisions
            evidence.append((sorted(facts), answer == APPLIES))
            boundary = APP.learn(evidence)
            answer = answer == APPLIES
        else:
            answer = known
            decided_without_trial += 1
        correct += int(answer == is_true)
    result["trial_then_know"] = {
        "accuracy": round(correct / decisions, 4),
        "executions": trials,
        "decisions": decisions,
        "decided_without_trial": decided_without_trial,
        "last_trial_at_decision": last_trial_at,
        "requirement": sorted(boundary.required or ()) if boundary.identified else None,
        "survivors_after_stream": boundary.survivor_count,
        "status_after_stream": boundary.status,
        # Precise, because "knowledge arrived" would be false: the requirement is never NAMED here.
        # What happens is that the surviving requirements become decisive on some states.
        "trials_stopped_somewhere": decided_without_trial > 0,
        "decided_without_trial_fraction": round(decided_without_trial / decisions, 4),
    }

    # ---- trial, but choosing which state to try next (the chooser) -----------------------------
    available = {facts: (state, outcome == APPLIES) for state, facts, outcome, _n in table}
    used: set[frozenset[str]] = set()
    evidence = []
    boundary = APP.learn(evidence)
    chosen_trials = 0
    order: list[str] = []

    def covered() -> bool:
        """Can every state of this action now be decided without a trial?"""
        if not (getattr(boundary, "survivors", ()) or ()):
            return False
        return all(decisive(boundary, facts) is not None for facts in available)

    # The chooser cannot choose without a first observation: `select_contrast` has no space to split
    # until a failure exists. The first trial is therefore taken from the stream (an arbitrary but real
    # state), and every trial after it is CHOSEN.
    if not covered() and available:
        first_key = frozenset(stream[0][1])
        entry = available.get(first_key)
        if entry is not None:
            used.add(first_key)
            outcome, _note = MACHINE.verdict(entry[0], action, root)
            chosen_trials += 1
            order.append(entry[0].name)
            evidence.append((sorted(first_key), outcome == APPLIES))
            boundary = APP.learn(evidence)

    while not covered() and chosen_trials < 12:
        remaining = {k: v for k, v in available.items() if k not in used}
        if not remaining:
            break
        contrast = CONTRAST.select_contrast(evidence, [sorted(k) for k in remaining])
        if not contrast.informative:
            break
        key = frozenset(contrast.state)
        entry = remaining.get(key)
        if entry is None:
            break
        used.add(key)
        state, _is_true = entry
        outcome, _note = MACHINE.verdict(state, action, root)
        chosen_trials += 1
        order.append(state.name)
        evidence.append((sorted(key), outcome == APPLIES))
        boundary = APP.learn(evidence)
    chosen_accuracy = 0
    chosen_decisions = 0
    for facts, (_state, is_true) in available.items():
        known = decisive(boundary, facts)
        if known is None:
            chosen_accuracy += int(is_true)          # would have to trial: credit the truth
        else:
            chosen_accuracy += int(known == is_true)
        chosen_decisions += 1
    result["trial_choose"] = {
        "executions_to_knowledge": chosen_trials,
        "decisions": chosen_decisions or len(truth),
        "accuracy": round(chosen_accuracy / (chosen_decisions or 1), 4),
        "covers_every_state": covered(),
        "requirement": sorted(boundary.required or ()) if boundary.identified else None,
        "survivors_after_choice": boundary.survivor_count,
        "order": order,
    }

    # ---- the exchange rate ---------------------------------------------------------------------
    always = result["trial_always"]["executions"]
    learned = result["trial_then_know"]["executions"]
    result["exchange_rate"] = {
        "executions_trial_always": always,
        "executions_trial_then_know": learned,
        "saved": always - learned,
        "saved_fraction": round((always - learned) / always, 4) if always else 0.0,
        "chooser_saved_vs_stream": learned - chosen_trials,
    }
    result["stage"] = "MEASURED"
    return result


def measure(root: pathlib.Path, repo: str, commit: str | None, per_class: int = 8,
            receipt_path: pathlib.Path | None = None, seed: int = 7) -> dict[str, Any]:
    started = time.time()
    root.mkdir(parents=True, exist_ok=True)
    base = MACHINE.build_base(root, repo, commit)
    families = MACHINE.build_states(root, base, per_class=per_class, seed=seed)

    # What one copy of a state costs -- the price that trial pays and knowledge does not.
    probe_state = next(iter(families.values()))[0].path
    samples = []
    for index in range(3):
        destination = root / f"copy-timing-{index}"
        begin = time.perf_counter()
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(probe_state, destination, symlinks=True)
        samples.append(time.perf_counter() - begin)
        shutil.rmtree(destination, ignore_errors=True)
    copy_seconds = round(sum(samples) / len(samples), 4)

    rows: list[dict[str, Any]] = []
    for action in MACHINE.ACTIONS:
        row = measure_action(action, families[action.name], root, copy_seconds)
        rows.append(row)
        if receipt_path is not None:
            if row["stage"] != "MEASURED":
                print(f"[{action.name}] {row['stage']}", flush=True)
            else:
                print(f"[{action.name}] guess={row['guess']['accuracy']} "
                      f"demo={row['demonstration']['accuracy']} "
                      f"trial_then_know={row['trial_then_know']['accuracy']} "
                      f"exec {row['exchange_rate']['executions_trial_always']} -> "
                      f"{row['exchange_rate']['executions_trial_then_know']} "
                      f"({row['trial_then_know']['decided_without_trial_fraction']:.0%} decided "
                      f"without a trial)", flush=True)

    measured = [r for r in rows if r["stage"] == "MEASURED"]
    def mean(key: str, field: str) -> float:
        values = [r[key][field] for r in measured if isinstance(r.get(key), dict)]
        return round(sum(values) / len(values), 4) if values else 0.0

    summary = {
        "actions": len(measured),
        "refused": len(rows) - len(measured),
        "states": sum(r["states"] for r in measured),
        "copy_seconds_per_state": copy_seconds,
        "accuracy_guess": mean("guess", "accuracy"),
        "accuracy_demonstration": mean("demonstration", "accuracy"),
        "accuracy_trial_always": 1.0,
        "accuracy_trial_then_know": mean("trial_then_know", "accuracy"),
        "executions_trial_always": sum(r["trial_always"]["executions"] for r in measured),
        "executions_trial_then_know": sum(r["trial_then_know"]["executions"] for r in measured),
        "actions_where_the_trial_stopped": sum(
            1 for r in measured if r["trial_then_know"]["trials_stopped_somewhere"]),
        "requirements_named": sum(1 for r in measured
                                  if r["trial_then_know"]["requirement"] is not None),
        "decisions_decided_without_trial": sum(r["trial_then_know"]["decided_without_trial"]
                                               for r in measured),
        "actions_covered_by_chooser": sum(1 for r in measured
                                          if r["trial_choose"]["covers_every_state"]),
        "actions_never_stopping_the_trial": [r["action"] for r in measured
                                             if not r["trial_then_know"]["trials_stopped_somewhere"]],
        "executions_with_chooser": sum(r["trial_choose"]["executions_to_knowledge"] for r in measured),
        "chooser_saved_executions": sum(r["exchange_rate"]["chooser_saved_vs_stream"] for r in measured),
        "seconds": round(time.time() - started, 1),
        "parameters_stored": 0,
        "model_calls": 0,
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-27",
        "environment": {"kind": "real machine: git, tar, gzip, patch", "base_repo": repo,
                        "commit": commit, "states": summary["states"]},
        "oracle": "each program's own exit status, read in a copy; the copy is deleted",
        "summary": summary,
        "rows": rows,
    }
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def headline(receipt: dict[str, Any]) -> str:
    s = receipt["summary"]
    return (f"{s['actions']} real actions, {s['states']} real states, copy costs "
            f"{s['copy_seconds_per_state']*1000:.0f} ms. Accuracy: guess {s['accuracy_guess']}, "
            f"demonstration {s['accuracy_demonstration']}, trial-then-know {s['accuracy_trial_then_know']} "
            f"(trial alone is 1.0 by construction). Executions: {s['executions_trial_always']} to trial "
            f"every decision, {s['executions_trial_then_know']} with the lesson kept; the trial stops "
            f"somewhere on {s['actions_where_the_trial_stopped']} of {s['actions']} actions while the "
            f"requirement is NAMED on {s['requirements_named']}; choosing the question instead of taking "
            f"the stream saved {s['chooser_saved_executions']} executions.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/decision-cost")
    parser.add_argument("--repo", default="https://github.com/pypa/packaging.git")
    parser.add_argument("--commit", default=None)
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args(argv)
    receipt = measure(pathlib.Path(args.root), args.repo, args.commit, per_class=args.per_class,
                      receipt_path=pathlib.Path(args.receipt) if args.receipt else None,
                      seed=args.seed)
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
