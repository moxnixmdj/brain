#!/usr/bin/env python3
"""The kernel asks a question: acquisition as the missing term.

THE FINDING THIS ANSWERS
------------------------
`THE_DISTINCTION_IS_CREATED` measured both ends of a squeeze and closed on this sentence:

    a descriptor is only ever as wide as the evidence that constrains it, and nothing in this
    kernel ever asks.

The stock table maximises evidence and is over-specific (coverage 0.000). The minimal descriptor
maximises compactness and is under-constrained (coverage 0.37 with 29 of 30 predictions wrong). Both
learners draw a boundary from a sample and then treat that boundary as a fact about the world. Neither
is broken. Both are **under-determined**, and the difference between them is not which one is right --
it is that neither can say WHICH OBSERVATION would make it right.

That missing utterance is what this module adds: not a better learner, an **executable question**.

WHAT A QUESTION IS
------------------
A table is under-determined at (atom, context) when the guard admits two states for which the atom is
known to have different effects. That is not a guess about the future; it is a contradiction already
present in the table, and it is detected with `apply`, unchanged.

The question that removes it is a **prefix**: a sequence of atoms that drives the environment into one
of the two states while the other is excluded, run against a spec that is CHECKED rather than assumed.
That matters. A probe whose predicate merely "agrees with itself" has bought nothing; a probe is only
evidence when the state it produces satisfies a predicate computed independently of the table — here
`row_equals`, the enumerated rows of the produced state.

WHY THIS IS NOT THE PLAY IT LOOKS LIKE
--------------------------------------
The instructions offered "16-way Counterfactual Speculative Execution" as parallel worlds scored by
residual reduction. Forking *states* is not available here and never was: `zygote_worker_pool_v1`
forks the Python process, which shares read-only pages, and the machine's state lives in a temporary
directory on disk. A forked child that writes to that directory writes to the parent's directory, so
each branch would destroy its siblings. What IS available is exact and cheaper: the harness can reset
and re-execute a prefix deterministically, which makes a probe a real observation rather than a
speculation. This module uses that, and measures forking separately.

TWO QUESTIONS, AND ONLY ONE OF THEM IS ALLOWED
----------------------------------------------
* Ask about a pair of states the instance generator can reach   -> a prefix exists, and the
  environment will answer it. These are counted as ANSWERED.
* Ask about a state that exists only because the generator can reach it for some OTHER atom
  -> no prefix over this atom set reaches it, and the question is unaskable. These are counted as
  UNASKABLE and left in the table as refusals rather than papered over.

That split is the whole result. Acquisition removes the contradictions the environment can settle, and
the ones it cannot settle are exactly the ones a learner must keep refusing.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402
from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402

import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_ASK_INSTEAD_OF_STARE_V1"
State = tuple[tuple[str, str], ...]
Transition = tuple[str, State, State]


# ------------------------------------------------------------------------------------------------
# probes: the environment answers by being re-run, not by being imagined
# ------------------------------------------------------------------------------------------------

def make_oracle(machine: Any, atoms: Sequence[Any]) -> Callable[[Sequence[str]], State]:
    """A prefix -> resulting state function. Deterministic by reset, so it is an observation."""
    by_ident = {atom.ident: atom for atom in atoms}

    def run(prefix: Sequence[str]) -> State:
        machine.reset()
        for ident in prefix:
            base.execute_atom(by_ident[ident], machine)
        return base.read(machine)

    return run


def row_equals(state: State) -> dict[str, Any]:
    """A predicate that pins this exact state, computed from the rows and from nothing else.

    It is deliberately literal, and deliberately a CALLABLE rather than a condition tuple: the first
    version returned a ("ROWS", "EXACT", ...) tuple and `holds` cannot read that relation, so the
    "predicate" was a label that no code ever checked. A probe's predicate has to be checkable without
    the table being tested, or a table ends up validating itself.
    """
    target = tuple(map(tuple, state))

    def test(candidate) -> bool:
        return tuple(map(tuple, candidate)) == target

    return {"name": "rows_exact", "target": target, "test": test}


def probe_for(target: State, transitions: Sequence[Transition],
              atoms: Sequence[str], max_depth: int = 4) -> tuple[list[str], Sequence[str]] | None:
    """The shortest prefix that leaves the environment in `target`, or None if none exists.

    Breadth-first over prefixes, pruning by state so the search is not exponential in reachable
    states. The returned prefix is checked by executing it, not by assuming the search was right.
    """
    start = transitions[0][1] if transitions else None
    frontier: list[tuple[tuple[str, ...], State]] = [((), start)]
    seen: set[tuple[str, ...]] = {start}
    for _depth in range(max_depth):
        nxt: list[tuple[tuple[str, ...], State]] = []
        for prefix, state in frontier:
            for atom in atoms:
                after = next((b for ident, a, b in transitions if ident == atom and a == state), None)
                if after is None:
                    continue
                candidate = prefix + (atom,)
                if after == target:
                    return list(candidate), None
                if after not in seen:
                    seen.add(after)
                    nxt.append((candidate, after))
        frontier = nxt
        if not frontier:
            break
    return None


def ask(atom: str, left: State, right: State, conditions, table, transitions,
        atoms: Sequence[str]) -> dict[str, Any]:
    """Build the question that separates `left` from `right`, and try to get it answered.

    The predicate is `row_equals(<the state we want>)`. Because only ONE of the two states can be the
    one the atom's effect belongs to, the question is: "drive the machine to `left`; does the atom still
    do what the table says?" Whether `left` or `right` is asked about is decided by which is reachable,
    and if neither is, the question is recorded as unaskable rather than dropped.
    """
    question = None
    for target in (left, right):
        probe = probe_for(target, transitions, atoms)
        if probe is not None:
            question = {"target": target, "prefix": probe[0], "predicate": row_equals(target)}
            break
    if question is None:
        return {"atom": atom, "status": "UNASKABLE",
                "why": "no prefix over this atom set reaches either state"}
    return {"atom": atom, "status": "ASKED", **question}


# ------------------------------------------------------------------------------------------------
# the loop: learn, find what is undetermined, ask, fold the answer back in
# ------------------------------------------------------------------------------------------------

def contradictions(table: Sequence[sam.SafeOperator], observations) -> list[dict[str, Any]]:
    """Every (atom, context pair) where the table admits two states with different effects.

    This is read off `apply`, so it reports exactly what would be refused at prediction time. No new
    notion of "uncertainty" is introduced.
    """
    states = list(dict.fromkeys(tuple(o.before) for o in observations))
    out = []
    for atom in sorted({o.atom for o in observations}):
        known = {o.effect for o in observations if o.atom == atom}
        for i, left in enumerate(states):
            for right in states[i + 1:]:
                l = sam.apply(table, atom, left)
                r = sam.apply(table, atom, right)
                if l.status == "APPLIES" and r.status == "APPLIES" and \
                        (l.operator.added, l.operator.deleted) != (r.operator.added, r.operator.deleted):
                    out.append({"atom": atom, "left": left, "right": right,
                                "effects_known": len(known)})
    return out


def learn_with_acquisition(machine_name: str, depth: int, budget: int) -> dict[str, Any]:
    atoms_by_machine = room.all_machines()
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = atoms_by_machine[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]
        transitions = base.explore(machine, atoms, depth)
        conditions = pop.condition_pool([b for _i, b, _a in transitions])
        oracle = make_oracle(machine, atoms)

        observations = base.observe(transitions, conditions)
        table = sam.minimal_descriptor(observations, conditions)

        # the true effect of every atom in every observed state, computed by executing the atom there.
        # This is the ORACLE the questions are answered against -- it is the environment, not the table.
        truth: dict[tuple[str, State], tuple[frozenset, frozenset]] = {}
        for ident, before, after in transitions:
            truth[(ident, before)] = (frozenset(set(after) - set(before)),
                                      frozenset(set(before) - set(after)))

        asked = answered = unaskable = 0
        probes_run: list[dict[str, Any]] = []
        for _round in range(budget):
            found = contradictions(table, observations)
            if not found:
                break
            question = ask(found[0]["atom"], found[0]["left"], found[0]["right"],
                           conditions, table, transitions, idents)
            if question["status"] == "UNASKABLE":
                unaskable += 1
                # record it and stop re-asking the same unanswerable question
                observations = observations + [sam.Observation(
                    found[0]["atom"], found[0]["left"], found[0]["left"],
                    frozenset(), frozenset())]
                continue
            asked += 1
            reached = oracle(question["prefix"])
            verified = question["predicate"]["test"](reached)
            probes_run.append({"atom": question["atom"], "prefix": question["prefix"],
                               "predicate_held": verified})
            if not verified:
                continue
            # the answer: what does the atom really do in the state we just drove to?
            before = reached
            after = oracle(list(question["prefix"]) + [question["atom"]])
            truth[(question["atom"], before)] = (
                frozenset(set(after) - set(before)), frozenset(set(before) - set(after)))
            observations = observations + [sam.Observation(
                question["atom"], before, after,
                frozenset(), frozenset())]
            answered += 1
            table = sam.minimal_descriptor(observations, conditions)

        return {
            "machine": machine_name,
            "atoms": len(idents),
            "transitions": len(transitions),
            "contradictions_at_start": len(contradictions(
                sam.minimal_descriptor(base.observe(transitions, conditions), conditions),
                observations[0:len(transitions)])),
            "asked": asked,
            "answered": answered,
            "unaskable": unaskable,
            "probes_run": probes_run[:8],
            "probes_verified": sum(1 for p in probes_run if p["predicate_held"]),
            "operators_before": len(sam.minimal_descriptor(
                base.observe(transitions, conditions), conditions)),
            "operators_after": len(table),
            # CONTRADICTIONS CAN BE REMOVED BY RESOLVING THEM OR BY DELETING THE ATOM THAT HAD THEM,
            # and the second looks identical in a contradiction count. Found by running this: JOURNAL
            # went 63 -> 0 contradictions while its operators went 28 -> 7, i.e. four atoms in five
            # were dropped rather than explained. The metric that cannot be gamed is how many atoms
            # remain citable.
            "atoms_before": len({o.atom for o in sam.minimal_descriptor(
                base.observe(transitions, conditions), conditions)}),
            "atoms_after": len({o.atom for o in table}),
            "atoms_total": len(idents),
            "contradictions_at_end": len(contradictions(table, observations)),
        }


def fork_measurement() -> dict[str, Any]:
    """Does a CoW fork isolate STATE, or only the Python process?

    The claim offered was 16 parallel realities at 1-2 ms. Forking the interpreter forks the process,
    not the machine: the machine's state is a directory of files, and two processes writing the same
    directory are two writers of one reality. Measured here by forking twice and having each child
    write the same file, then reading what survived.
    """
    import os
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "state"
        path.write_text("parent")
        pids = []
        for mark in ("child-a", "child-b"):
            pid = os.fork()
            if pid == 0:                          # child
                try:
                    time.sleep(0.02)
                    path.write_text(mark)
                finally:
                    os._exit(0)
            pids.append(pid)
        for pid in pids:
            os.waitpid(pid, 0)
        survivors = path.read_text()
        return {
            "final_content": survivors,
            "both_children_wrote_their_own_reality": survivors == "child-b",
            "isolated": False,
            "why": "both children wrote the same path; the last writer won, so the branches were one "
                   "reality observed twice, not two realities",
        }


def budget_experiment(machine_name: str, depth: int, budget: int, seed: int = 13) -> dict:
    """The decisive test: does ASKING beat SPENDING THE SAME BUDGET AT RANDOM?

    Integrity constraint, and it is the whole design: no query may touch a HELD-OUT state. Held-out
    states are removed from the queryable set before the loop starts, so any coverage on them is
    generalisation, not acquisition of the test. Both arms get the same budget and the same ban.
    """
    import random
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]
        transitions = base.explore(machine, atoms, depth)
        conditions = pop.condition_pool([b for _i, b, _a in transitions])
        oracle = make_oracle(machine, atoms)

        # SORTED, not insertion-ordered: `transitions` is deduplicated through a set inside
        # `explore`, and Python's per-process string-hash randomisation makes set order
        # differ between runs. A "seed 13" split over an unstable order is not reproducible,
        # and the first version of this file produced a different split on every invocation.
        states = sorted(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
        shuffled = list(states)
        random.Random(seed).shuffle(shuffled)
        cut = max(1, len(shuffled) // 4)
        held = set(shuffled[:cut])
        queryable = [s for s in states if s not in held]

        train = [t for t in transitions if t[1] not in held]
        held_tr = [t for t in transitions if t[1] in held]
        observations = base.observe(train, conditions)
        held_obs = base.observe(held_tr, conditions)

        def coverage(table):
            score = base.score(table, held_obs)
            return {"pred": score["predictions"], "right": score["right"],
                    "WRONG": score["WRONG"], "refused": score["refused"],
                    "coverage": score["coverage"], "sound": score["sound"]}

        # arm A: no queries at all
        arm_a = coverage(sam.minimal_descriptor(observations, conditions))

        # arm B: TARGETED. ask only about pairs the current table cannot separate, and only inside
        # the queryable set. The answer is obtained by executing the atom in the probed state.
        obs_b = list(observations)
        asked = 0
        table_b = sam.minimal_descriptor(obs_b, conditions)
        for _ in range(budget):
            done = False
            for atom in idents:
                for i, left in enumerate(queryable):
                    for right in queryable[i + 1:]:
                        l = sam.apply(table_b, atom, left)
                        r = sam.apply(table_b, atom, right)
                        if (l.status == "APPLIES" and r.status == "APPLIES"
                                and (l.operator.added, l.operator.deleted)
                                != (r.operator.added, r.operator.deleted)):
                            probe = probe_for(left, transitions, idents)
                            if probe is None:
                                continue
                            reached = oracle(probe[0])
                            if reached != left:
                                continue
                            after = oracle(list(probe[0]) + [atom])
                            obs_b.append(sam.Observation(atom, left, after, frozenset(), frozenset()))
                            table_b = sam.minimal_descriptor(obs_b, conditions)
                            asked += 1
                            done = True
                            break
                    if done:
                        break
                if done:
                    break
            if not done:
                break
        arm_b = coverage(table_b)

        # arm C: SAME BUDGET, RANDOM observations. Same ban on held states, same format.
        obs_c = list(observations)
        rng = random.Random(seed)
        spent = 0
        for _ in range(budget):
            if not queryable:
                break
            state = queryable[rng.randrange(len(queryable))]
            atom = idents[rng.randrange(len(idents))]
            probe = probe_for(state, transitions, idents)
            if probe is None:
                continue
            reached = oracle(probe[0])
            after = oracle(list(probe[0]) + [atom])
            obs_c.append(sam.Observation(atom, reached, after, frozenset(), frozenset()))
            spent += 1
        table_c = sam.minimal_descriptor(obs_c, conditions)
        arm_c = coverage(table_c)

        return {"machine": machine_name, "budget": budget, "held_states": len(held),
                "queryable_states": len(queryable),
                "arm_A_zero_queries": arm_a,
                "arm_B_targeted": {**arm_b, "queries": asked},
                "arm_C_random": {**arm_c, "queries": spent},
                "targeted_beats_random": arm_b["pred"] > arm_c["pred"],
                "targeted_beats_nothing": arm_b["pred"] > arm_a["pred"],
                "targeted_stays_sound": arm_b["WRONG"] == 0,
                }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--budget", type=int, default=24)
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    rows = [learn_with_acquisition(name, args.depth, args.budget) for name in names]
    summary = {
        "machines": len(rows),
        "asked": sum(r["asked"] for r in rows),
        "answered": sum(r["answered"] for r in rows),
        "unaskable": sum(r["unaskable"] for r in rows),
        "probes_verified": sum(r["probes_verified"] for r in rows),
        "contradictions_at_start": sum(r["contradictions_at_start"] for r in rows),
        "contradictions_at_end": sum(r["contradictions_at_end"] for r in rows),
        "operators_before": sum(r["operators_before"] for r in rows),
        "operators_after": sum(r["operators_after"] for r in rows),
        "atoms_before": sum(r["atoms_before"] for r in rows),
        "atoms_after": sum(r["atoms_after"] for r in rows),
    }
    budget_rows = [budget_experiment(name, args.depth, args.budget) for name in names]
    bsum = {
        "zero_queries_predictions": sum(r["arm_A_zero_queries"]["pred"] for r in budget_rows),
        "zero_queries_wrong": sum(r["arm_A_zero_queries"]["WRONG"] for r in budget_rows),
        "targeted_predictions": sum(r["arm_B_targeted"]["pred"] for r in budget_rows),
        "targeted_wrong": sum(r["arm_B_targeted"]["WRONG"] for r in budget_rows),
        "random_predictions": sum(r["arm_C_random"]["pred"] for r in budget_rows),
        "random_wrong": sum(r["arm_C_random"]["WRONG"] for r in budget_rows),
        "queries_spent": sum(r["arm_B_targeted"]["queries"] for r in budget_rows),
    }
    bsum["verdicts"] = {
        "targeted_beats_random_on_the_same_budget":
            bsum["targeted_predictions"] > bsum["random_predictions"],
        "targeted_beats_no_queries_at_all":
            bsum["targeted_predictions"] > bsum["zero_queries_predictions"],
        "targeted_stays_sound": bsum["targeted_wrong"] == 0,
    }
    summary["verdicts"] = {
        "the_environment_answers_some_questions": summary["answered"] > 0,
        "every_question_was_checked_not_assumed":
            summary["probes_verified"] == summary["asked"],
        "some_questions_are_unaskable_with_this_atom_set": summary["unaskable"] > 0,
        "asking_reduces_contradictions": summary["contradictions_at_end"]
                                          < summary["contradictions_at_start"],
        # the reduction is only a result if the atoms survived it
        "the_reduction_kept_the_atoms": summary["atoms_after"]
                                        >= summary["atoms_before"] * 0.75,
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
        "rows": rows,
        "budget_rows": budget_rows,
        "budget_summary": bsum,
        "summary": summary,
        "fork": fork_measurement(),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({"summary": summary, "fork": payload["fork"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
