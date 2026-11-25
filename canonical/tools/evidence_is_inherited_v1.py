#!/usr/bin/env python3
"""Evidence is inherited, not rediscovered -- a projection confirmed once licenses many laws.

THE BOTTLENECK THIS ATTACKS
---------------------------
Three rounds moved the error rate down: 83% wrong (minimal descriptor) -> 42% (one witness) -> 0% at
support 2. Reach never exceeded 6 held-out predictions out of 99, and last round the verdict was blunt:

    the bottleneck is no longer accuracy. It is that a two-witness law is too rare to be useful.

Because support was counted PER ATOM. A law about `GIT_A4` needed two independent observations of
`GIT_A4`. But what a confirmed law actually establishes is not a fact about one atom -- it is that a
PROJECTION is sufficient on this machine. If `IDENT` determines the effect of four different atoms
across three states, the fifth atom's single witness is no longer standing alone: the projection has
been validated, and the single witness inherits that validation.

That is composition of evidence rather than accumulation of examples, and it is a strictly stronger
hypothesis than anything tested in this tree so far, so it is stated as one and can be falsified:

    H: if a projection P is confirmed for at least MIN_SUPPORT_ATOMS distinct atoms (each law having
       at least one witness), then a P-law with a single witness is ADMISSIBLE.

THE ARMS
--------
  A  per-atom support >= 2, any projection                     (last round)
  B  A, plus inherited support: P-laws with one witness where P is confirmed on >= 2 atoms
  C  B, but inheritance only from MATCHED effects: a single-witness law may inherit only from laws
     with the identical effect. Narrower hypothesis: the projection must be doing the same work.
  D  the ablation: inherit from a projection confirmed on ONE atom (i.e. no requirement at all)

Held-out states are banned from the evidence in every arm. Every number is produced by execution.
"""
from __future__ import annotations

import argparse
import collections
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
from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402

import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_EVIDENCE_IS_INHERITED_V1"

#: how many distinct atoms must confirm a projection before a single-witness law may inherit it
MIN_SUPPORT_ATOMS = 2


def inherited_laws(laws: Sequence[width.Law], *, atoms: int = MIN_SUPPORT_ATOMS,
                   matched_effect_only: bool = False) -> list[width.Law]:
    """Return the laws admissible once projection-level evidence is allowed to propagate."""
    # which projections are confirmed, and by how many distinct atoms
    confirmation: dict[str, set[str]] = collections.defaultdict(set)
    for law in laws:
        if law.support >= width.MIN_SUPPORT:
            confirmation[law.projection].add(law.atom)
    confirmed = {p for p, atom_set in confirmation.items() if len(atom_set) >= atoms}

    kept: list[width.Law] = []
    for law in laws:
        if law.support >= width.MIN_SUPPORT:
            kept.append(law)
            continue
        if law.projection not in confirmed:
            continue
        if matched_effect_only:
            # the projection must already be doing this exact work for another atom
            same = any(other.projection == law.projection and other.effect == law.effect
                       and other.support >= width.MIN_SUPPORT and other.atom != law.atom
                       for other in laws)
            if not same:
                continue
        kept.append(law)
    return kept


def cross_machine(observations_by_machine: dict[str, tuple]) -> dict[str, Any]:
    """Does a projection confirmed on machine X license laws on machine Y?

    This is the strongest form of the hypothesis, and the one worth testing: if evidence composes, the
    expensive confirmation is paid ONCE for a projection and the whole store benefits. It is measured
    on every ordered pair of machines, with each machine's own held-out split.
    """
    names = sorted(observations_by_machine)
    pairs = 0
    own = {"predictions": 0, "wrong": 0}
    inherited = {"predictions": 0, "wrong": 0}
    reach_rose = errors_rose = 0
    for teacher in names:
        teacher_obs, _held = observations_by_machine[teacher]
        confirmed = {law.projection for law in width.learn_laws(teacher_obs)
                     if law.support >= width.MIN_SUPPORT}
        for student in names:
            if student == teacher:
                continue
            student_obs, student_held = observations_by_machine[student]
            student_laws = width.learn_laws(student_obs)
            arm_own = [law for law in student_laws if law.support >= width.MIN_SUPPORT]
            arm_inh = arm_own + [law for law in student_laws
                                 if law.support == 1 and law.projection in confirmed]
            a = width._score(arm_own, student_held)
            b = width._score(arm_inh, student_held)
            pairs += 1
            for key in ("predictions", "wrong"):
                own[key] += a[key]
                inherited[key] += b[key]
            if b["predictions"] > a["predictions"]:
                reach_rose += 1
            if b["wrong"] > a["wrong"]:
                errors_rose += 1
    return {"pairs": pairs, "arm_own": own, "arm_inherited": inherited,
            "pairs_where_reach_rose": reach_rose, "pairs_where_errors_rose": errors_rose}


def run(machine_name: str, depth: int, seed: int = 13) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        transitions = base.explore(machine, atoms, depth)
        conditions = pop.condition_pool([b for _i, b, _a in transitions])

        states = sorted(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
        shuffled = list(states)
        random.Random(seed).shuffle(shuffled)
        cut = max(1, len(shuffled) // 4)
        held = set(shuffled[:cut])
        train = [t for t in transitions if t[1] not in held]
        held_tr = [t for t in transitions if t[1] in held]
        if not held_tr:
            return {"machine": machine_name, "skipped": "no held-out transitions"}

        observations = base.observe(train, conditions)
        held_obs = base.observe(held_tr, conditions)
        laws = width.learn_laws(observations)

        arm_a = [law for law in laws if law.support >= width.MIN_SUPPORT]
        arm_b = inherited_laws(laws)
        arm_c = inherited_laws(laws, matched_effect_only=True)
        arm_d = inherited_laws(laws, atoms=1)

        return {
            "machine": machine_name,
            "held_out_transitions": len(held_obs),
            "laws_total": len(laws),
            "laws_by_projection": dict(collections.Counter(law.projection for law in laws
                                                           if law.support >= width.MIN_SUPPORT)),
            "arm_A_per_atom": {**width._score(arm_a, held_obs), "laws": len(arm_a)},
            "arm_B_inherited": {**width._score(arm_b, held_obs), "laws": len(arm_b)},
            "arm_C_matched_effect": {**width._score(arm_c, held_obs), "laws": len(arm_c)},
            "arm_D_inherit_from_one": {**width._score(arm_d, held_obs), "laws": len(arm_d)},
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    rows = [run(name, args.depth) for name in names]
    rows = [row for row in rows if "skipped" not in row]

    # the cross-machine arm needs each machine's observations and held-out set at once
    corpus: dict[str, tuple] = {}
    for name in names:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / name
            root.mkdir(parents=True)
            machine = room.all_machines()[name](root)
            machine.reset()
            atoms = list(machine.atoms)
            transitions = base.explore(machine, atoms, args.depth)
            conditions = pop.condition_pool([b for _i, b, _a in transitions])
            states = sorted(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
            shuffled = list(states)
            random.Random(13).shuffle(shuffled)
            cut = max(1, len(shuffled) // 4)
            held = set(shuffled[:cut])
            corpus[name] = (base.observe([t for t in transitions if t[1] not in held], conditions),
                            base.observe([t for t in transitions if t[1] in held], conditions))
    cross = cross_machine(corpus)
    keys = ("predictions", "wrong", "refused", "laws")
    summary = {"machines": len(rows)}
    for label, field in (("arm_A", "arm_A_per_atom"), ("arm_B", "arm_B_inherited"),
                         ("arm_C", "arm_C_matched_effect"), ("arm_D", "arm_D_inherit_from_one")):
        summary[label] = {k: sum(row[field][k] for row in rows) for k in keys}
    summary["verdicts"] = {
        "inheritance_raises_reach": summary["arm_B"]["predictions"]
                                    > summary["arm_A"]["predictions"],
        "inheritance_stays_sound": summary["arm_B"]["wrong"] == 0,
        "requiring_the_same_effect_is_better_than_inheriting_freely": (
            summary["arm_C"]["wrong"] * max(1, summary["arm_B"]["predictions"])
            <= summary["arm_B"]["wrong"] * max(1, summary["arm_C"]["predictions"])),
        "inheritance_needs_a_real_confirmation": (
            summary["arm_D"]["wrong"] > summary["arm_B"]["wrong"]
            or summary["arm_D"]["predictions"] != summary["arm_B"]["predictions"]),
        # the strongest form, and the one that decides whether a store of laws can compound
        "cross_machine_inheritance_is_sound": cross["arm_inherited"]["wrong"] == 0,
        "cross_machine_inheritance_raises_reach":
            cross["arm_inherited"]["predictions"] > cross["arm_own"]["predictions"],
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
        "hypothesis": "a projection confirmed on >= 2 atoms licenses single-witness laws over it",
        "cross_machine": cross,
        "rows": rows,
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
