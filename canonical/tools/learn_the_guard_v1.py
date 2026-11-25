#!/usr/bin/env python3
"""A no-op is a NEGATIVE WITNESS, and the learner has been throwing it away.

THE ARGUMENT
------------
Last round's work order: four of six context-dependent atoms are an atom declining to fire. An atom that
fires sometimes and not others has a precondition, and the current learner records only what an atom
does. Worse, `walker.budgeted_walk` keeps `(atom, before)` pairs and drops repeated observations of the
same pair -- so a state where the atom did nothing is retained only if it was the FIRST time that pair
was seen.

A guard is learned from the same evidence, read the other way:

    PASSED  (atom, state) -> the effect happened      positive witness for the effect
    BLOCKED (atom, state) -> nothing changed          negative witness, and it is free

    guard = (atom_rank, blocked-key) : in states matching this key, the atom does not fire

Prediction with guards: if the state matches a blocked key, predict NO_CHANGE -- a real prediction, so it
can be WRONG, which is what makes it a claim rather than a default. Otherwise fall back to the lifted
effect law as before.

WHY THIS IS THE CHEAPEST AVAILABLE IMPROVEMENT
----------------------------------------------
The evidence is already in the walk. No new probes, no new exploration, no new vocabulary over states.
If guards pay, they pay from data the learner was discarding.

WHAT WOULD MAKE THIS FAIL
-------------------------
Guards may simply re-label refusals as `NO_CHANGE` and get them wrong, which would raise COVERAGE and
destroy ACCURACY -- the exact trade this project refuses to make silently. Both numbers are reported, and
the verdict `guards_do_not_trade_coverage_for_accuracy` requires both to move the right way.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402

import acquire_the_second_witness_v1 as walker  # noqa: E402
import lift_the_keys_v1 as lift  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_LEARN_THE_GUARD_V1"


def raw_walk(machine, atoms, steps: int, seed: int) -> list[tuple[str, lift.State, lift.State]]:
    """The walk WITHOUT deduplication.

    `walker.budgeted_walk` keeps only the first observation of each `(atom, before)` pair. That is
    correct when a repeat carries no new information about the EFFECT -- and fatal here, because the
    second observation of a pair is the only place a blocked witness can appear when the first was
    positive. Measurement and evidence collection are not the same job, so this file collects its own.
    """
    rng = random.Random(seed)
    by_ident = {atom.ident: atom for atom in atoms}
    transitions: list[tuple[str, lift.State, lift.State]] = []
    machine.reset()
    state = base.read(machine)
    for _step in range(steps):
        atom = by_ident[atoms[rng.randrange(len(atoms))].ident]
        before = state
        after = base.execute_atom(atom, machine)
        transitions.append((atom.ident, tuple(before), tuple(after)))
        state = after
    machine.reset()
    return transitions


def guard_key(before: lift.State) -> str:
    """The blocked-key: the same lifted vocabulary, so a guard is stated in the same language as a law."""
    return lift.key_of(tuple(before))


def learn_guards(walked: list[tuple[str, lift.State, lift.State]],
                 idents: Sequence[str]) -> dict[tuple[int, str], int]:
    """BLOCKED witnesses -> guards. Support counts how often the atom was seen not firing in this key."""
    guards: dict[tuple[int, str], int] = {}
    for ident, before, after in walked:
        if tuple(before) != tuple(after):
            continue
        key = (lift.atom_rank(idents, ident), guard_key(before))
        guards[key] = guards.get(key, 0) + 1
    return guards


def predict_with_guards(laws: Sequence[lift.Lifted], guards: dict[tuple[int, str], int],
                        rank: int, state: lift.State, min_guard_support: int = 1,
                        fallback_only: bool = False) -> dict[str, Any]:
    """A guard says "this atom does nothing in states matching this key".

    `fallback_only=False` lets the guard OVERRIDE an existing law. That is the version that sounds right
    -- the guard is evidence about this exact key -- and it is the version that destroys accuracy, because
    the guard and the law are conditioned on the same key and the key does not determine firing.
    `fallback_only=True` uses a guard only where no law admits, i.e. purely to fill refusals.
    """
    outcome = lift.predict_lifted(laws, rank, state)
    if fallback_only and outcome["status"] == "PREDICTS":
        return outcome
    key = guard_key(state)
    support = guards.get((rank, key), 0)
    if support >= min_guard_support:
        return {"status": "PREDICTS", "effect": "NO_CHANGE", "by": "GUARD"}
    return outcome


def score(laws: Sequence[lift.Lifted], guards: dict[tuple[int, str], int] | None,
          idents: Sequence[str], held: list[tuple[str, lift.State, lift.State]],
          min_guard_support: int = 1, fallback_only: bool = False) -> dict[str, Any]:
    predictions = wrong = refused = 0
    for ident, before, after in held:
        rank = lift.atom_rank(idents, ident)
        if guards is None:
            result = lift.predict_lifted(laws, rank, tuple(before))
        else:
            result = predict_with_guards(laws, guards, rank, tuple(before), min_guard_support,
                                         fallback_only)
        if result["status"] != "PREDICTS":
            refused += 1
            continue
        predictions += 1
        if result["effect"] != lift.outcome_of(tuple(before), tuple(after)):
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused,
            "accuracy": round(predictions / max(1, predictions + wrong), 4),
            "coverage": round(predictions / max(1, predictions + refused), 4)}


def examine(machine_name: str, walk_steps: int, seed: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        # RAW walk: no dedup, because dedup is what discards the second observation of a pair, and the
        # second observation is the negative witness when the first was positive.
        walked = raw_walk(machine, atoms, walk_steps, seed)
        # the evidence set is the DEDUPLICATED view (what the learner may claim from), while guards are
        # learned from the full sequence -- a no-op observed twice is two witnesses, not one.
        deduped: list[tuple[str, lift.State, lift.State]] = []
        seen_pairs: set[tuple[str, lift.State]] = set()
        for ident, before, after in walked:
            if (ident, before) in seen_pairs:
                continue
            seen_pairs.add((ident, before))
            deduped.append((ident, before, after))
        own = lift.lift(deduped, idents)
        guards = learn_guards(walked, idents)

        full = base.explore(machine, atoms, 3)
        seen = {before for _i, before, _a in deduped}
        # held out: states the walk never visited, exactly as in every previous round
        held = [(ident, tuple(before), tuple(after)) for ident, before, after in full
                if tuple(before) not in seen]
        if not held:
            return {"machine": machine_name, "skipped": "walk covered every reachable state"}

        no_guards = score(own, None, idents, held)
        with_guards = score(own, guards, idents, held, min_guard_support=1)
        strict_guards = score(own, guards, idents, held, min_guard_support=2)
        fallback_two = score(own, guards, idents, held, min_guard_support=2, fallback_only=True)

        blocked_witnesses = sum(1 for _i, before, after in walked if tuple(before) == tuple(after))
        return {
            "machine": machine_name,
            "walk_transitions": len(walked),
            "blocked_witnesses": blocked_witnesses,
            "guards_learned": len(guards),
            "guards_with_two_witnesses": sum(1 for n in guards.values() if n >= 2),
            "held_out": len(held),
            "A_no_guards": no_guards,
            "B_guards": with_guards,
            "C_guards_strict": strict_guards,
            "D_guards_fallback_only": fallback_two,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)

    started = time.time()
    rows = [examine(name, args.walk_steps, args.seed) for name in sorted(room.all_machines())]
    live = [row for row in rows if "skipped" not in row]

    def total(key: str) -> dict[str, Any]:
        predictions = sum(row[key]["predictions"] for row in live)
        wrong = sum(row[key]["wrong"] for row in live)
        refused = sum(row[key]["refused"] for row in live)
        return {"predictions": predictions, "wrong": wrong, "refused": refused,
                "accuracy": round(predictions / max(1, predictions + wrong), 4),
                "coverage": round(predictions / max(1, predictions + refused), 4)}

    a, b, c = total("A_no_guards"), total("B_guards"), total("C_guards_strict")
    d = total("D_guards_fallback_only")
    summary = {
        "machines": len(live),
        "skipped": [row["machine"] for row in rows if "skipped" in row],
        "blocked_witnesses": sum(row["blocked_witnesses"] for row in live),
        "guards_learned": sum(row["guards_learned"] for row in live),
        "guards_with_two_witnesses": sum(row["guards_with_two_witnesses"] for row in live),
        "held_out": sum(row["held_out"] for row in live),
        "A_no_guards": a,
        "B_guards": b,
        "C_guards_strict": c,
        "D_guards_fallback_only": d,
        "verdicts": {
            "guards_raise_coverage": b["coverage"] > a["coverage"],
            "guards_cost_no_accuracy": b["accuracy"] >= a["accuracy"] - 0.01,
            "guards_do_not_trade_coverage_for_accuracy":
                b["coverage"] > a["coverage"] and b["accuracy"] >= a["accuracy"] - 0.01,
            "a_guard_needs_two_witnesses": c["accuracy"] >= b["accuracy"],
            "guards_used_only_as_a_fallback_cover_refusals": d["coverage"] > a["coverage"],
            "guards_used_only_as_a_fallback_cost_nothing": d["accuracy"] >= a["accuracy"] - 0.01,
            "the_guard_and_the_law_cannot_share_a_key": b["accuracy"] < a["accuracy"],
        },
        "note": ("B uses every blocked witness as a guard; C requires two. If C is much better than B, "
                 "a single no-op is noise; if they are equal, one blocked observation is enough."),
    }
    summary["verdicts"]["the_walk_contains_blocked_witnesses"] = summary["blocked_witnesses"] > 0
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "rows": rows,
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "note"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
