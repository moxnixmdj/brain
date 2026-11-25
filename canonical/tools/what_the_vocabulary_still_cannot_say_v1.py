#!/usr/bin/env python3
"""The learner is now wide enough that its REFUSALS are the interesting object.

Coverage 0.704 means 68 of 230 held-out transitions carry no lifted key at all. This file does not try
to cover them. It asks what a NEW predicate would have to distinguish, by measuring the structure the
refused states share with each other and with the states the vocabulary already handles.

THE QUESTION, MADE SHARP
------------------------
For each refused state, record the atoms applied and the effect produced. Two refused states with the
SAME atom and DIFFERENT effects are the load-bearing case: no predicate over the current feature set can
separate them, because the effects differ while the current vocabulary sees no difference. Those pairs
are the honest specification of what the vocabulary is missing.

  SAME_ATOM_SAME_EFFECT     one lifted law would cover both -- the vocabulary is merely too narrow
  SAME_ATOM_DIFFERENT_EFFECT the atom's effect depends on something unrepresented -- a real gap
  DIFFERENT_ATOM            not a vocabulary question

The output is a work order written by the learner: which atoms have context-dependent effects, and how
many distinct effects each shows across the states it currently refuses.
"""
from __future__ import annotations

import argparse
import collections
import json
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

import frames_that_cross_machines_v1 as room  # noqa: E402

import acquire_the_second_witness_v1 as walker  # noqa: E402
import lift_the_keys_v1 as lift  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_WHAT_THE_VOCABULARY_STILL_CANNOT_SAY_V1"


def examine(machine_name: str, walk_steps: int, seed: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        walked = walker.budgeted_walk(machine, atoms, walk_steps, seed)
        own = lift.lift(walked, idents)
        full = base.explore(machine, atoms, 3)
        seen = {before for _i, before, _a in walked}
        held = [(ident, before, after) for ident, before, after in full if before not in seen]
        if not held:
            return {"machine": machine_name, "skipped": "walk covered every reachable state"}

        refused: list[tuple[str, str, str]] = []       # (ident, key, effect)
        covered = 0
        for ident, before, after in held:
            rank = lift.atom_rank(idents, ident)
            result = lift.predict_lifted(own, rank, tuple(before))
            if result["status"] == "PREDICTS":
                covered += 1
                continue
            refused.append((ident, lift.key_of(tuple(before)),
                            lift.outcome_of(tuple(before), tuple(after))))

        # the taxonomy of refusals
        by_atom: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        for ident, key, effect in refused:
            by_atom[ident].append((key, effect))

        same_effect_coverable = 0
        context_dependent: dict[str, dict[str, Any]] = {}
        for ident, entries in sorted(by_atom.items()):
            effects = {effect for _key, effect in entries}
            if len(effects) == 1:
                same_effect_coverable += len(entries)
            else:
                context_dependent[ident] = {
                    "refused_states": len(entries),
                    "distinct_effects": len(effects),
                    "effects": sorted(effects),
                    "keys_seen": sorted({key for key, _e in entries}),
                }

        # SPLIT the context-dependent atoms by WHAT KIND of dependence it is. An atom whose effects
        # include NO_CHANGE is not content-dependent at all: it has a GUARD, and the "second effect" is
        # the atom declining to fire. A guard is a different missing object from a state predicate --
        # the vocabulary describes effects and has no way to state a precondition -- so the two must be
        # counted apart or the work order asks for the wrong thing.
        guards: dict[str, Any] = {}
        genuinely_dependent: dict[str, Any] = {}
        for ident, cell in context_dependent.items():
            if "NO_CHANGE" in cell["effects"]:
                other = [effect for effect in cell["effects"] if effect != "NO_CHANGE"]
                guards[ident] = {**cell, "fires_as": other,
                                 "reading": "the atom declines to fire unless a precondition holds"}
            else:
                genuinely_dependent[ident] = {
                    **cell, "reading": "two different effects, both firing"}

        # how much of the existing feature set already separates the context-dependent atoms?
        separable_by_current_keys = 0
        for ident, cell in context_dependent.items():
            pairs = by_atom[ident]
            conflict = any(
                key_a == key_b and effect_a != effect_b
                for i, (key_a, effect_a) in enumerate(pairs)
                for key_b, effect_b in pairs[i + 1:])
            if not conflict:
                separable_by_current_keys += 1

        return {
            "machine": machine_name,
            "held_out": len(held),
            "covered": covered,
            "refused": len(refused),
            "refusals_with_same_atom_and_single_effect": same_effect_coverable,
            "context_dependent_atoms": context_dependent,
            "guard_atoms": guards,
            "genuinely_dependent_atoms": genuinely_dependent,
            "context_dependent_count": len(context_dependent),
            "guard_count": len(guards),
            "genuinely_dependent_count": len(genuinely_dependent),
            "context_dependent_separable_by_current_keys": separable_by_current_keys,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)

    started = time.time()
    rows: list[dict[str, Any]] = []
    for name in sorted(room.all_machines()):
        rows.append(examine(name, args.walk_steps, args.seed))
    live = [row for row in rows if "skipped" not in row]

    held = sum(row["held_out"] for row in live)
    covered = sum(row["covered"] for row in live)
    refused = sum(row["refused"] for row in live)
    coverable = sum(row["refusals_with_same_atom_and_single_effect"] for row in live)
    dependent = sum(row["context_dependent_count"] for row in live)
    separable = sum(row["context_dependent_separable_by_current_keys"] for row in live)
    guard_count = sum(row["guard_count"] for row in live)
    genuinely = sum(row["genuinely_dependent_count"] for row in live)
    summary = {
        "machines": len(live),
        "skipped": [row["machine"] for row in rows if "skipped" in row],
        "held_out": held,
        "covered": covered,
        "refused": refused,
        "coverage": round(covered / max(1, held), 4),
        "refusals_a_narrower_law_would_already_cover": coverable,
        "context_dependent_atoms": dependent,
        "context_dependent_separable_by_current_keys": separable,
        "guard_atoms": guard_count,
        "genuinely_dependent_atoms_count": genuinely,
        "verdicts": {
            "most_refusals_are_a_narrow_vocabulary_not_a_missing_one":
                coverable > 0.5 * refused,
            "some_atom_effects_really_depend_on_unrepresented_context": dependent > 0,
            "the_current_keys_already_separate_some_of_them": separable > 0,
            # the real answer to "what is missing": mostly a GUARD, which the vocabulary cannot state
            "most_context_dependence_is_a_guard_not_a_predicate": guard_count > genuinely,
            "the_vocabulary_gap_is_small_and_named": dependent <= max(1, len(live)),
        },
        "work_order": {
            "guards": {row["machine"]: row["guard_atoms"]
                       for row in live if row["guard_count"]},
            "genuinely_dependent": {row["machine"]: row["genuinely_dependent_atoms"]
                                    for row in live if row["genuinely_dependent_count"]},
        },
    }
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
    print(json.dumps({k: v for k, v in summary.items() if k != "work_order"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
