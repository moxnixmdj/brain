#!/usr/bin/env python3
"""Ask the question you will be tested on -- representative probing instead of adjacent probing.

THE TRADE THIS TRIES TO BREAK
-----------------------------
`BUY_REACH_WITH_QUESTIONS` measured, across 507 probes and two seeds:

    reach         166 -> 512 predictions   (3.1x)
    error rate    3.6% -> 13.3%            (3.7x worse)
    price         346 predictions bought for 507 probes  (below break-even)

The mechanism is simple and it is not a bug: a probe is chosen as a state the learner's current
boundary is *near*, so acquisition moves the boundary into the region under test. A question buys
coverage of the states you asked about and no others.

That suggests the defect is the OBJECTIVE, not the mechanism. Adjacency is the wrong selection rule.
What should be selected is a probe that is representative of the states the system will actually meet
-- i.e. disagreement with the *held-out distribution*, not with the *current boundary*.

THREE SELECTION RULES, ONE BUDGET
---------------------------------
  ADJACENT      the state nearest the current boundary that a support-1 law admits (last round's rule)
  REPRESENTATIVE  the state that maximises disagreement with what the law set already says about the
                 states the learner has NOT seen -- chosen by coverage of the law's own projection
                 keys, so the probe lands in a region where the table is silent rather than torn
  RANDOM        a uniformly chosen unobserved state (the control that stops either rule claiming credit
                for merely asking more)

Every arm spends the same budget, is scored on the same held-out transitions, and the honest metric is
**correct predictions**, because reach alone flatters whichever arm asks most aggressively.
"""
from __future__ import annotations

import argparse
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

import acquire_the_second_witness_v1 as walker  # noqa: E402
import ask_instead_of_stare_v1 as oracle_module  # noqa: E402
import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_ASK_WHAT_YOU_WILL_BE_TESTED_ON_V1"
PROJECTION_ORDER = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS")


def select_adjacent(candidates, unknown_states, observations):
    """Last round's rule: any unobserved state a support-1 law admits, widest projection first."""
    for law in candidates:
        for state in unknown_states:
            if law.admits(state):
                return law, state
    return None


def select_representative(candidates, unknown_states, observations):
    """Ask where the table is SILENT, not where it is torn.

    Score each unobserved state by how many support-1 laws admit it: a state admitted by many weak
    laws is one the table is about to make a claim about without evidence, so it is representative of
    the region the system will be wrong in. Ties break on the widest law, i.e. the biggest unsupported
    claim first.
    """
    scored = []
    for state in unknown_states:
        admitting = [law for law in candidates if law.admits(state)]
        if not admitting:
            continue
        widest = min(admitting, key=lambda law: PROJECTION_ORDER.index(law.projection)
                     if law.projection in PROJECTION_ORDER else len(PROJECTION_ORDER))
        scored.append((-len(admitting), PROJECTION_ORDER.index(widest.projection)
                       if widest.projection in PROJECTION_ORDER else len(PROJECTION_ORDER),
                       widest, state))
    if not scored:
        return None
    scored.sort(key=lambda row: (row[0], row[1]))
    return scored[0][2], scored[0][3]


def select_random(candidates, unknown_states, observations, index=[0]):
    """The control. Deterministic across runs by stepping a fixed stride through a sorted list."""
    if not unknown_states or not candidates:
        return None
    state = unknown_states[index[0] % len(unknown_states)]
    admitting = [law for law in candidates if law.admits(state)]
    index[0] += 7
    if not admitting:
        return None
    return admitting[0], state


RULES: dict[str, Callable] = {
    "ADJACENT": select_adjacent,
    "REPRESENTATIVE": select_representative,
    "RANDOM": select_random,
}


def run_arm(rule_name: str, machine, atoms, idents, observed, full, held_obs, budget: int):
    conditions = pop.condition_pool([b for _i, b, _a in observed])
    oracle = oracle_module.make_oracle(machine, atoms)
    seen = {before for _i, before, _a in observed}
    unknown = sorted(before for _i, before, _a in full if before not in seen)
    observations = list(base.observe(observed, conditions))
    probes = confirmed = falsified = 0
    rule = RULES[rule_name]
    for _round in range(budget):
        candidates = sorted(
            (law for law in width.learn_laws(observations)
             if law.support == 1 and law.projection in PROJECTION_ORDER),
            key=lambda law: PROJECTION_ORDER.index(law.projection))
        picked = rule(candidates, unknown, observations)
        if picked is None:
            break
        law, target = picked
        prefix = oracle_module.probe_for(target, full, idents)
        if prefix is None:
            unknown = [state for state in unknown if state != target]
            continue
        reached = oracle(prefix[0])
        after = oracle(list(prefix[0]) + [law.atom])
        probes += 1
        effect = (frozenset(set(after) - set(reached)), frozenset(set(reached) - set(after)))
        observations.append(sam.Observation.of(law.atom, reached, after, conditions))
        if effect == law.effect:
            confirmed += 1
        else:
            falsified += 1
        if reached in unknown:
            unknown = [state for state in unknown if state != reached]
    table = [law for law in width.learn_laws(observations) if law.support >= width.MIN_SUPPORT]
    score = width._score(table, held_obs)
    return {**score, "probes": probes, "confirmed": confirmed, "falsified": falsified}


def run(names: Sequence[str], walk_steps: int, budget: int, seed: int) -> dict[str, Any]:
    rows = []
    for name in names:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / name
            root.mkdir(parents=True)
            machine = room.all_machines()[name](root)
            machine.reset()
            atoms = list(machine.atoms)
            idents = [atom.ident for atom in atoms]
            observed = walker.budgeted_walk(machine, atoms, walk_steps, seed)
            full = base.explore(machine, atoms, 3)
            seen = {before for _i, before, _a in observed}
            held = [(ident, before, after) for ident, before, after in full if before not in seen]
            if not held:
                continue
            conditions = pop.condition_pool([b for _i, b, _a in observed])
            held_obs = base.observe(held, conditions)
            baseline = [law for law in width.learn_laws(base.observe(observed, conditions))
                        if law.support >= width.MIN_SUPPORT]
            row = {"machine": name,
                   "A_walk_only": width._score(baseline, held_obs)}
            for rule_name in RULES:
                row[rule_name] = run_arm(rule_name, machine, atoms, idents, observed, full,
                                         held_obs, budget)
            rows.append(row)

    summary: dict[str, Any] = {"machines": len(rows), "budget": budget, "walk_steps": walk_steps}
    for key in ("A_walk_only", *RULES):
        summary[key] = {
            "predictions": sum(row[key]["predictions"] for row in rows),
            "wrong": sum(row[key]["wrong"] for row in rows),
            "probes": sum(row[key].get("probes", 0) for row in rows),
        }
        preds = summary[key]["predictions"]
        summary[key]["correct"] = preds - summary[key]["wrong"]
        summary[key]["accuracy"] = round((preds - summary[key]["wrong"]) / preds, 3) if preds else 0.0
    summary["verdicts"] = {
        "representative_beats_adjacent_on_correct":
            summary["REPRESENTATIVE"]["correct"] > summary["ADJACENT"]["correct"],
        "representative_beats_random_on_correct":
            summary["REPRESENTATIVE"]["correct"] > summary["RANDOM"]["correct"],
        "representative_keeps_a_better_accuracy_than_adjacent":
            summary["REPRESENTATIVE"]["accuracy"] > summary["ADJACENT"]["accuracy"],
        # the objective change is only worth having if it beats the honest baseline too
        "representative_beats_asking_nothing_on_correct":
            summary["REPRESENTATIVE"]["correct"] > summary["A_walk_only"]["correct"],
    }
    return {"summary": summary, "rows": rows}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--budget", type=int, default=40)
    parser.add_argument("--seeds", nargs="*", type=int, default=[13, 42])
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    combined: dict[str, Any] | None = None
    all_rows: list[dict[str, Any]] = []
    for seed in args.seeds:
        result = run(names, args.walk_steps, args.budget, seed)
        all_rows.extend(result["rows"])
        if combined is None:
            combined = result["summary"]
        else:
            for key in ("A_walk_only", *RULES):
                for field in ("predictions", "wrong", "probes", "correct"):
                    combined[key][field] += result["summary"][key][field]
            for key in ("A_walk_only", *RULES):
                preds = combined[key]["predictions"]
                combined[key]["accuracy"] = (
                    round((preds - combined[key]["wrong"]) / preds, 3) if preds else 0.0)
            combined["machines"] += result["summary"]["machines"]
    assert combined is not None
    combined["verdicts"] = {
        "representative_beats_adjacent_on_correct":
            combined["REPRESENTATIVE"]["correct"] > combined["ADJACENT"]["correct"],
        "representative_beats_random_on_correct":
            combined["REPRESENTATIVE"]["correct"] > combined["RANDOM"]["correct"],
        "representative_keeps_a_better_accuracy_than_adjacent":
            combined["REPRESENTATIVE"]["accuracy"] > combined["ADJACENT"]["accuracy"],
        "representative_beats_asking_nothing_on_correct":
            combined["REPRESENTATIVE"]["correct"] > combined["A_walk_only"]["correct"],
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "seeds": args.seeds,
        "rows": all_rows,
        "summary": combined,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(combined, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
