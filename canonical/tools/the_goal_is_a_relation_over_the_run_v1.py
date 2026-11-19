#!/usr/bin/env python3
"""The goal is a relation over the run, not over the final state.

THE LAST CLAIM, AND WHAT IT IS STILL MISSING
--------------------------------------------
Four rounds took the goal apart and put it back together without a model: the effect vocabulary was
blind (round one), relations over the reader replaced it (round two), the goal was inferred from
judgments instead of being handed in (round three), and ambiguity was acted on by intersection rather
than by guessing (round four). Every one of those rounds read the goal off **one state**.

That is exactly where real computer use breaks. Two runs can end in the *same* state while one of them
is what the user wanted and the other is not:

    write the member, then delete it, then write it again   -> final state F, REJECTED
    write the member                                        -> final state F, accepted

    move the file away, then copy it back                   -> final state F, REJECTED
    copy it away, then move it                              -> final state F, accepted

A goal that is a function of the final state **cannot tell these apart, ever**. It is not imprecise
about them; the two runs are the same input to it. So it will accept the rejected run -- a false
accept, the accusation class -- and no amount of experience, vocabulary growth or extra questions can
fix that, because the observable it needs is not the state. It is the *run*.

WHAT IS BUILT HERE
------------------
The observable is a **trace**: the machine's own reading after every step. The goal is a conjunction of
terms over the trace, in a grammar that includes, but is not limited to, the final state:

    final:*              what the end state is (the entire vocabulary every previous round had)
    never_removed[c]     the content was present in every state
    at_least_once[c]     it appeared at some point
    created_once[c]      exactly one step increased its count and no step decreased it
    monotone[c]          its count never went down
    two_copies[c]        some state held it in two places at once
    never_together[a;b]  no state ever held both
    precedence[X;Y]      a state with X occurred strictly before one with Y
    present_then_absent[i]   an identity was there and is not now
    no_decrease          the machine never lost an entity at any step

Judgments come from running real sequences of real atoms on real machines and reading the machine
after each step. The user's goal is a behaviour over runs; the agent never sees it.

A CORRECTION TO THE PREVIOUS ROUND'S SOLVER, FOUND BY USING IT
-------------------------------------------------------------
`minimal_discriminators` returns only the **smallest** conjunctions consistent with the data. That is
right for asking "what is the shortest rule", and wrong for deciding whether the goal is identified:
treating the smallest set as if it were the whole version space makes a grammar look identified when a
larger consistent hypothesis disagrees. In the first run of this tool it produced exactly that: a
single surviving term rejected thirty-two runs the user accepted, and the stopping rule called it
identified. So here the version space is **every** consistent conjunction up to size two -- terms are
evaluated once into a bitmask over runs, conjunctions are bitwise ANDs, and a behavioural class is a
distinct mask. The previous round's file is untouched; this is a correction, not a quiet edit.

HOW IT IS SCORED (declared before the run)
------------------------------------------
Leave-one-run-out. For every run, both goals are fitted on the judgments of every *other* run and must
then judge the held-out run. A false accept is the accusation class: the user rejected the run and the
inferred goal accepted it. `undecided` means the grammar contained **no** hypothesis consistent with
the training judgments -- an incompleteness, reported as such, never counted as a rejection.

B1  REAL INDISTINGUISHABLE GROUPS: on at least two machines, a final state is reached by real runs
    with **opposite judgments**. Counted by execution, not constructed by hand.
B2  THE END-STATE VOCABULARY IS NOT MERELY WRONG, IT IS EMPTY: every term that may read only the final
    state takes the same value inside every such group (counted, must be 0 disagreements), so on any
    judgment set containing one such group it has **no** consistent hypothesis at all -- and where it
    does speak, leave-one-run-out produces at least one false accept.
B3  THE RUN VOCABULARY IS NOT EMPTY AND IS SOUND: every goal keeps a consistent hypothesis, every
    group is separated by some run-term, and leave-one-run-out has 0 false accepts and 0 false rejects.
B4  IDENTIFICATION IS A COUNT, AND AGREEMENT IS NOT TRUTH: asking the most even-splitting question,
    the run vocabulary reaches a single behavioural class in k judgments and the agreed goal is
    exactly right on every run; the end-state vocabulary also reaches agreement, on a goal that is
    wrong. Both counts are reported.
B5  ZERO: no model calls, no stored parameters, no network at run time; every run is an execution.

WHAT THIS DOES NOT CLAIM
------------------------
- The trace grammar is a grammar. A goal outside it is refused (`undecided`), not approximated. The
  end-state grammar is incomplete *by theorem*; the run grammar is incomplete only by construction,
  and that is a weaker statement.
- Three CLI machines, depth three, no display. On a screen the trace is longer and the same.
- Runs are deduplicated by trace: two action sequences that read identically after every step are one
  observable, and a goal over traces must judge them alike. How many sequences that collapses is
  reported per machine.
- Judgments are produced by real executions but by this tool's own predicates; a human's sense of
  "did it the right way" is the next study, not this one.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import itertools
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
import the_goal_is_a_discriminator_v1 as demand  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_THE_GOAL_IS_A_RELATION_OVER_THE_RUN_V1"
State = tuple[tuple[str, str], ...]
Trace = tuple[State, ...]                    # the reading after every step, initial state first
Judge = Callable[[Trace], bool]

FINAL_STATE_ONLY = "final_state_only"
OVER_THE_RUN = "over_the_run"


# --------------------------------------------------------------------------------------------------
# traces: real sequences, read after every step
# --------------------------------------------------------------------------------------------------

def traces_for(machine: env.Machine, args: dict[str, str], *, depth: int = 3) -> list[Trace]:
    """Every real run of up to `depth` actions, with the machine's own reading after each step."""
    traces: list[Trace] = []
    for length in range(1, depth + 1):
        for sequence in itertools.product(machine.atoms, repeat=length):
            machine.reset()
            states: list[State] = [tuple(machine.read())]
            for atom in sequence:
                env.execute(atom, machine, args)
                states.append(tuple(machine.read()))
            trace = tuple(states)
            if trace not in traces:
                traces.append(trace)
    machine.reset()
    return traces


# --------------------------------------------------------------------------------------------------
# the grammar: terms that read the run, and terms that may only read its last state
# --------------------------------------------------------------------------------------------------

def _count(state: State, content: str) -> int:
    return sum(1 for _ident, value in state if value == content)


def _increased_once(trace: Trace, content: str) -> bool:
    ups = sum(_count(trace[i + 1], content) > _count(trace[i], content)
              for i in range(len(trace) - 1))
    downs = any(_count(trace[i + 1], content) < _count(trace[i], content)
                for i in range(len(trace) - 1))
    return ups == 1 and not downs


def _precedence(trace: Trace, left: str, right: str) -> bool:
    first_left = next((i for i, state in enumerate(trace) if any(ident == left for ident, _v in state)),
                      None)
    first_right = next((i for i, state in enumerate(trace) if any(ident == right for ident, _v in state)),
                       None)
    return first_left is not None and first_right is not None and first_left < first_right


def _present_then_absent(trace: Trace, ident: str) -> bool:
    seen = [any(i == ident for i, _v in state) for state in trace]
    return any(seen) and not seen[-1]


def _never_together(trace: Trace, left: str, right: str) -> bool:
    return not any(_count(state, left) >= 1 and _count(state, right) >= 1 for state in trace)


def run_terms(traces: Sequence[Trace]) -> tuple[list[demand.Term], list[demand.Term]]:
    """(terms over the whole run, terms that may read only the final state).

    The second list is the entire vocabulary every previous round had. Keeping it separate is the
    measurement: anything expressible there is a function of the last state, so two runs that end
    identically are the same input to it -- and it cannot be right about both.
    """
    finals = [trace[-1] for trace in traces]
    contents = sorted({value for state in finals for _i, value in state})
    idents = sorted({ident for state in finals for ident, _v in state})

    end_only: list[demand.Term] = []
    for n in sorted({len(state) for state in finals}):
        end_only.append(demand.Term(f"final:card=={n}", lambda t, n=n: len(t[-1]) == n))
    for content in contents:
        for k in sorted({_count(state, content) for state in finals}):
            end_only.append(demand.Term(f"final:count[{content}]=={k}",
                                        lambda t, c=content, k=k: _count(t[-1], c) == k))
    for ident, content in sorted({(i, c) for state in finals for i, c in state}):
        end_only.append(demand.Term(f"final:has[{ident}]={content}",
                                    lambda t, i=ident, c=content: (i, c) in t[-1]))

    whole: list[demand.Term] = []
    for content in contents:
        whole.append(demand.Term(f"never_removed[{content}]",
                                 lambda t, c=content: all(_count(state, c) >= 1 for state in t)))
        whole.append(demand.Term(f"at_least_once[{content}]",
                                 lambda t, c=content: any(_count(state, c) >= 1 for state in t)))
        whole.append(demand.Term(f"created_once[{content}]",
                                 lambda t, c=content: _increased_once(t, c)))
        whole.append(demand.Term(f"monotone[{content}]",
                                 lambda t, c=content: all(_count(t[i + 1], c) >= _count(t[i], c)
                                                          for i in range(len(t) - 1))))
        whole.append(demand.Term(f"two_copies[{content}]",
                                 lambda t, c=content: any(_count(state, c) >= 2 for state in t)))
    whole.append(demand.Term("no_decrease",
                             lambda t: all(len(t[i + 1]) >= len(t[i]) for i in range(len(t) - 1))))
    for left, right in itertools.combinations(contents, 2):
        whole.append(demand.Term(f"never_together[{left};{right}]",
                                 lambda t, a=left, b=right: _never_together(t, a, b)))
    for ident in idents:
        whole.append(demand.Term(f"present_then_absent[{ident}]",
                                 lambda t, a=ident: _present_then_absent(t, a)))
    for left, right in itertools.permutations(idents, 2):
        whole.append(demand.Term(f"precedence[has {left}; has {right}]",
                                 lambda t, a=left, b=right: _precedence(t, a, b)))

    seen: dict[str, demand.Term] = {}
    for term in whole + end_only:
        seen.setdefault(term.text, term)
    return ([seen[text] for text in dict.fromkeys(term.text for term in whole)],
            [seen[text] for text in dict.fromkeys(term.text for term in end_only)])


# --------------------------------------------------------------------------------------------------
# the version space: every consistent conjunction, as a bitmask over runs
# --------------------------------------------------------------------------------------------------

class Space:
    """The grammar evaluated once. A hypothesis is a bitmask; a behavioural class is a mask."""

    def __init__(self, terms: Sequence[demand.Term], traces: Sequence[Trace]) -> None:
        self.terms = list(terms)
        self.traces = list(traces)
        self.masks = []
        for term in self.terms:
            mask = 0
            for index, trace in enumerate(self.traces):
                if term.holds(trace):
                    mask |= 1 << index
            self.masks.append(mask)
        self.combos = [(i,) for i in range(len(self.terms))]
        self.combos += [(i, j) for i in range(len(self.terms)) for j in range(i + 1, len(self.terms))]
        self.masks_of = {combo: self._and(combo) for combo in self.combos}

    def _and(self, combo: Sequence[int]) -> int:
        value = (1 << len(self.traces)) - 1
        for index in combo:
            value &= self.masks[index]
        return value

    def version_space(self, accepted: int, rejected: int) -> list[int]:
        return [mask for mask in (self.masks_of[combo] for combo in self.combos)
                if mask & accepted == accepted and mask & rejected == 0]

    def smallest(self, accepted_masks: Sequence[int], rejected_masks: Sequence[int]) -> list[str] | None:
        best: list[str] | None = None
        for combo, mask in self.masks_of.items():
            if best is not None and len(combo) > len(best):
                continue
            if all(mask & a == a for a in accepted_masks) and not any(mask & r for r in rejected_masks):
                best = [self.terms[i].text for i in combo]
        return best

    def judge(self, mask: int, index: int) -> bool:
        return bool(mask >> index & 1)


def score(predictions: Sequence[bool | None], labels: Sequence[bool]) -> dict[str, object]:
    false_accepts = [i for i, (p, y) in enumerate(zip(predictions, labels)) if p is True and not y]
    false_rejects = [i for i, (p, y) in enumerate(zip(predictions, labels)) if p is False and y]
    undecided = [i for i, p in enumerate(predictions) if p is None]
    decided = len(labels) - len(undecided)
    correct = sum(1 for p, y in zip(predictions, labels) if p is not None and p == y)
    return {"runs": len(labels), "decided": decided, "correct": correct,
            "accuracy_where_decided": round(correct / decided, 4) if decided else None,
            "false_accepts": len(false_accepts), "false_accept_indices": false_accepts[:5],
            "false_rejects": len(false_rejects), "false_reject_indices": false_rejects[:5],
            "undecided": len(undecided)}


def predict(space: Space, index: int, survivors: Sequence[int]) -> bool | None:
    """The intersection: accept only where every survivor accepts."""
    if not survivors:
        return None
    return all(space.judge(mask, index) for mask in survivors)


def leave_one_out(space: Space, labels: Sequence[bool]) -> dict[str, object]:
    """Fit on every run but one, judge the held-out run. The end-state goal cannot do this."""
    predictions = []
    for held_out in range(len(space.traces)):
        accepted = sum(1 << i for i in range(len(labels)) if i != held_out and labels[i])
        rejected = sum(1 << i for i in range(len(labels)) if i != held_out and not labels[i])
        predictions.append(predict(space, held_out, space.version_space(accepted, rejected)))
    return score(predictions, labels)


def identify(space: Space, labels: Sequence[bool]) -> dict[str, object]:
    """How many questions it takes for every survivor to agree, and whether the agreed goal is right.

    The agent starts with no judgments: every conjunction in the grammar is a survivor. While the
    survivors disagree about some run, it asks about the run that splits them most evenly -- the
    question carrying the most information -- and refits. Two different things can end the loop, and
    they are not the same thing: agreement (`identified_after`) and emptiness
    (`vocabulary_emptied_after`, no hypothesis at all). Agreement under an incomplete grammar can be
    wrong, so the agreed goal's accuracy is measured, never assumed.
    """
    revealed: list[int] = []
    survivors = space.version_space(0, 0)
    history: list[dict[str, object]] = []
    identified_at: int | None = None
    emptied_at: int | None = None
    while True:
        classes = len(set(survivors))
        predictions = [predict(space, index, survivors) for index in range(len(space.traces))]
        error = score(predictions, labels)
        history.append({"judgments": len(revealed), "survivors": len(survivors),
                        "behavioural_classes": classes,
                        "false_accepts": error["false_accepts"],
                        "false_rejects": error["false_rejects"],
                        "undecided": error["undecided"],
                        "accuracy_of_the_intersection": error["accuracy_where_decided"]})
        if survivors and classes == 1:
            identified_at = len(revealed)
            break
        if not survivors:
            emptied_at = len(revealed)
            break
        if len(revealed) == len(space.traces):
            break
        choice, best = None, None
        for index in range(len(space.traces)):
            if index in revealed:
                continue
            yes = sum(space.judge(mask, index) for mask in survivors)
            if yes in (0, len(survivors)):
                continue
            balance = abs(2 * yes - len(survivors))
            if best is None or balance < best:
                choice, best = index, balance
        if choice is None:
            break
        revealed.append(choice)
        survivors = space.version_space(
            sum(1 << i for i in revealed if labels[i]),
            sum(1 << i for i in revealed if not labels[i]))
    return {"identified_after": identified_at, "vocabulary_emptied_after": emptied_at,
            "agreeing_goal_accuracy": history[-1]["accuracy_of_the_intersection"],
            "agreeing_goal_false_accepts": history[-1]["false_accepts"],
            "judgments_asked": [[index, labels[index]] for index in revealed],
            "history": history}


def separation_is_structural(end_only: Space, whole: Space,
                             groups: Sequence[Sequence[int]]) -> dict[str, int]:
    """Two measurements that do not depend on any fitting.

    Every term that may read only the final state takes the SAME value on every run of a group, because
    a group is the set of runs with one final state. That is the proof, counted over every term and
    every group. The run vocabulary, on the same groups, has a term that splits each of them.
    """
    disagreements = sum(1 for group in groups for mask in end_only.masks
                        for run in group if end_only.judge(mask, run) != end_only.judge(mask, group[0]))
    separated = sum(1 for group in groups if any(
        whole.judge(mask, group[0]) != whole.judge(mask, run)
        for mask in whole.masks for run in group))
    return {"final_state_terms_that_disagree_inside_a_group": disagreements,
            "groups_separated_by_some_run_term": separated, "groups": len(groups)}


# --------------------------------------------------------------------------------------------------
# the goals a user actually means, and how their judgments are produced
# --------------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class RunGoal:
    machine: str
    name: str
    args: dict[str, str]
    judge: Judge


def run_goals(machines: dict[str, env.Machine]) -> list[RunGoal]:
    goals: list[RunGoal] = []
    if "FILESYSTEM" in machines:
        holder = next(ident for ident, content in machines["FILESYSTEM"].read()
                      if content == env.PROBE_OLD)
        goals.append(RunGoal(
            "FILESYSTEM", "copy it before you move it: the original existed in two places at once",
            {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": holder, "target": "backup"},
            lambda t, c=env.PROBE_OLD: any(_count(state, c) >= 2 for state in t)))
    if "SQLITE" in machines:
        goals.append(RunGoal(
            "SQLITE", "replace the row in place: the old value and the new value never coexisted",
            {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "moved"},
            lambda t, a=env.PROBE_OLD, b=env.PROBE_NEW: _never_together(t, a, b)
            and _count(t[-1], b) >= 1))
    if "TARBALL" in machines:
        goals.append(RunGoal(
            "TARBALL", "add the member once, keep it: exactly one write, never removed",
            {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "member", "target": "copy"},
            lambda t, c=env.PROBE_NEW: _increased_once(t, c) and _count(t[-1], c) == 1))
    return goals


# --------------------------------------------------------------------------------------------------
# the round
# --------------------------------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--depth", type=int, default=3)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-runs-"))
    machines: dict[str, env.Machine] = {}
    for name in ("FILESYSTEM", "SQLITE", "TARBALL"):
        machine = vocab.MACHINES[name](where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        machines[name] = machine
    for machine in machines.values():
        machine.reset()

    rows = []
    for goal in run_goals(machines):
        machine = machines[goal.machine]
        sequences = sum(len(machine.atoms) ** length for length in range(1, options.depth + 1))
        traces = traces_for(machine, goal.args, depth=options.depth)
        labels = [goal.judge(trace) for trace in traces]
        whole_terms, end_terms = run_terms(traces)
        whole, end_only = Space(whole_terms, traces), Space(end_terms, traces)

        grouped: dict[State, list[int]] = collections.defaultdict(list)
        for index, trace in enumerate(traces):
            grouped[trace[-1]].append(index)
        groups = [indices for indices in grouped.values() if len({labels[i] for i in indices}) > 1]

        accepted = sum(1 << i for i, label in enumerate(labels) if label)
        rejected = sum(1 << i for i, label in enumerate(labels) if not label)
        rows.append({
            "machine": goal.machine, "goal": goal.name,
            "sequences_executed": sequences, "runs": len(traces),
            "accepted_runs": sum(labels), "rejected_runs": len(labels) - sum(labels),
            "terms_over_the_run": len(whole_terms), "terms_over_the_final_state_only": len(end_terms),
            "indistinguishable_groups": len(groups),
            "indistinguishable_examples": [
                {"final_state": [list(pair) for pair in traces[indices[0]][-1]],
                 "runs": indices, "judgments": [labels[i] for i in indices]} for indices in groups[:3]],
            "structural": separation_is_structural(end_only, whole, groups),
            FINAL_STATE_ONLY: {
                "consistent_hypotheses_on_the_full_judgment_set":
                    len(end_only.version_space(accepted, rejected)),
                "smallest_hypothesis": end_only.smallest(
                    [1 << i for i, y in enumerate(labels) if y],
                    [1 << i for i, y in enumerate(labels) if not y]),
                "leave_one_out": leave_one_out(end_only, labels),
                "identification": identify(end_only, labels),
            },
            OVER_THE_RUN: {
                "consistent_hypotheses_on_the_full_judgment_set":
                    len(whole.version_space(accepted, rejected)),
                "smallest_hypothesis": whole.smallest(
                    [1 << i for i, y in enumerate(labels) if y],
                    [1 << i for i, y in enumerate(labels) if not y]),
                "leave_one_out": leave_one_out(whole, labels),
                "identification": identify(whole, labels),
            },
        })

    groups_total = sum(row["indistinguishable_groups"] for row in rows)
    machines_with_groups = sorted({row["machine"] for row in rows if row["indistinguishable_groups"]})
    with_groups = [row for row in rows if row["indistinguishable_groups"]]
    disagreements = sum(row["structural"]["final_state_terms_that_disagree_inside_a_group"]
                        for row in rows)
    separated = sum(row["structural"]["groups_separated_by_some_run_term"] for row in rows)
    end_empty = all(row[FINAL_STATE_ONLY]["consistent_hypotheses_on_the_full_judgment_set"] == 0
                    for row in with_groups)
    end_false = sum(row[FINAL_STATE_ONLY]["leave_one_out"]["false_accepts"] for row in rows)
    run_loo = [row[OVER_THE_RUN]["leave_one_out"] for row in rows]
    run_identified = [row[OVER_THE_RUN]["identification"] for row in rows]
    end_identified = [row[FINAL_STATE_ONLY]["identification"] for row in rows]

    verdict = {
        "B1_indistinguishable_groups_are_real": {
            "groups": groups_total, "machines": machines_with_groups,
            "MET": groups_total >= 2 and len(machines_with_groups) >= 2},
        "B2_the_end_state_goal_is_empty": {
            "final_state_terms_that_disagree_inside_a_group": disagreements,
            "every_goal_with_a_group_has_no_consistent_hypothesis": end_empty,
            "leave_one_out_false_accepts": end_false,
            "MET": disagreements == 0 and end_empty and end_false >= 1},
        "B3_the_run_goal_is_not_empty_and_sound": {
            "groups_separated_by_some_run_term": separated, "groups": groups_total,
            "every_goal_has_a_consistent_hypothesis":
                all(row[OVER_THE_RUN]["consistent_hypotheses_on_the_full_judgment_set"] > 0
                    for row in rows),
            "leave_one_out_false_accepts": sum(item["false_accepts"] for item in run_loo),
            "leave_one_out_false_rejects": sum(item["false_rejects"] for item in run_loo),
            "MET": separated == groups_total
            and all(row[OVER_THE_RUN]["consistent_hypotheses_on_the_full_judgment_set"] > 0
                    for row in rows)
            and all(item["false_accepts"] == 0 and item["false_rejects"] == 0 for item in run_loo)},
        "B4_identification_is_a_count": {
            "run_goal_identified_after": [item["identified_after"] for item in run_identified],
            "run_goal_accuracy_when_identified": [item["agreeing_goal_accuracy"]
                                                  for item in run_identified],
            "end_state_goal_identified_after": [item["identified_after"] for item in end_identified],
            "end_state_goal_accuracy_when_identified": [item["agreeing_goal_accuracy"]
                                                        for item in end_identified],
            "MET": all(item["identified_after"] is not None
                       and item["agreeing_goal_accuracy"] == 1.0 for item in run_identified)
            and any(item["agreeing_goal_accuracy"] is not None
                    and item["agreeing_goal_accuracy"] < 1.0 for item in end_identified)},
        "B5_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-27",
        "mode": "GOAL_INFERRED_FROM_JUDGMENTS_ON_REAL_RUNS",
        "declared_acceptance_before_the_run": {
            "B1": "on at least two machines, a final state is reached by real runs with opposite "
                  "judgments, counted rather than constructed",
            "B2": "no term that reads only the final state disagrees inside a group; on any judgment "
                  "set holding one such group the end-state grammar has no consistent hypothesis; "
                  "leave-one-run-out produces at least one false accept",
            "B3": "every group is separated by some run-term, every goal keeps a consistent "
                  "hypothesis, and leave-one-run-out has 0 false accepts and 0 false rejects",
            "B4": "the run grammar reaches agreement in k judgments with an exactly correct goal; the "
                  "end-state grammar reaches agreement on a goal that is wrong; both k are counted",
            "B5": "zero model calls, zero stored parameters, every run a real execution"},
        "verdict": verdict, "rows": rows, "depth": options.depth,
        "seconds": round(time.time() - started, 1),
        "model_calls": 0, "parameters_stored": 0,
        "limits": [
            "the trace grammar is a grammar: a goal outside it is refused (undecided), not approximated",
            "the end-state grammar is incomplete by theorem; the run grammar only by construction",
            "three CLI machines, no display: on a screen the trace is longer and the same",
            "GIT is not included: its reset is five git invocations per run, and the three machines "
            "present carry the same structure",
            "runs are deduplicated by trace, so action sequences that read identically are one run",
            "judgments come from real executions but from this tool's predicates; a human's sense of "
            "'the right way' is the next study"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"goals": len(rows), "seconds": receipt["seconds"],
                      "receipt": str(options.receipt)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
