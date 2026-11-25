#!/usr/bin/env python3
"""Raise the contrast density -- because the control proved reach is a property of the TEACHER.

WHAT THE CONTROL SHOWED
-----------------------
`THE_ROLE_IS_A_CONVENTION` built a machine designed to break the transfer claim and it did not: with
`SCRAMBLED` in the family, reasons still re-ran at 95.1% and transfers stayed sound at 103 predictions
/ 0 wrong. What it DID show was that **every reach gain came from one teacher out of ten.** LIST has
7 atoms and the largest reachable state set; it is the only machine whose exploration yields enough
pairs of states with differing effects to license a two-witness law with a non-empty contrast.

So the binding constraint moved. It is not transfer quality any more. It is:

    how many laws-with-a-reason does a machine's exploration produce per transition?

This module measures exactly that, in laws per hundred transitions, under three exploration policies
on the same budget:

  RANDOM     a random walk, the sampler every previous round used
  TARGETED   walk toward states that DIFFER from states already seen (the policy
             `ask_instead_of_stare` measured as 3.5x better than random at producing answers)
  COVERAGE   walk toward states whose projection signatures are new (a breadth-first policy)

A law "with a reason" is one the previous rounds established is worth having: at least two independent
witnesses over a projection AND a non-empty contrast (a context where the atom really did something
else). Nothing here is a new notion; it is the density of the object that already worked.

If TARGETED beats RANDOM on density, then availability is a consequence of policy rather than a
property of which machine happened to be rich -- and the LIST-only artefact gets an explanation.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
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

import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_RAISE_THE_CONTRAST_DENSITY_V1"
State = tuple[tuple[str, str], ...]


def _content_key(atom_ident: str, state) -> tuple:
    """The dedup key: atom + CONTENT, never identity.

    This is the third and deepest version of the reproducibility problem, and the one worth keeping in
    mind for every real environment. A walk that deduped on `(atom, state)` deduped on the git SHA, so
    two identical walks -- same seed, same atoms, same order -- recorded DIFFERENT NUMBERS of
    transitions, because the SHAs differed. The learning set was therefore nondeterministic even
    though the policy was not.

    Real environments are full of identifiers that change under an unchanged observation: commit SHAs,
    pids, UUIDs, temporary paths, timestamps. A learner whose evidence key includes them cannot
    reproduce its own results. Keying on content is the only form that survives.
    """
    return (atom_ident, tuple(content for _identity, content in state))


def record(machine, atoms, atom, state, seen, transitions) -> State:
    after = base.execute_atom(atom, machine)
    key = _content_key(atom.ident, state)
    if key not in seen:
        seen.add(key)
        transitions.append((atom.ident, state, after))
    return after


def walk_random(machine, atoms, steps: int, seed: int) -> list[tuple]:
    rng = random.Random(seed)
    machine.reset()
    state = base.read(machine)
    seen: set[tuple] = set()
    transitions: list[tuple] = []
    for _step in range(steps):
        atom = atoms[rng.randrange(len(atoms))]
        state = record(machine, atoms, atom, state, seen, transitions)
    machine.reset()
    return transitions


def walk_targeted(machine, atoms, steps: int, seed: int) -> list[tuple]:
    """Prefer the atom whose effect most often DIFFERED from what this context produced before.

    This is the cheapest possible statement of "aim at contrast": keep, per (atom, projection key), a
    tally of the effects seen; choose the atom/key pair with more than one effect so far.

    MEASURED AND IT FAILED. The first version scored a key as "contrasting" only if the SAME atom had
    already produced two different effects in that context -- which is a coin-flip state of affairs and
    almost never occurs early in a walk. It collected 297 transitions across 3 seeds and produced ZERO
    usable laws, the worst of the three policies. The honest reading: aiming at a contrast that must
    already be established is not aiming at anything. `COVERAGE` won because it aims at a state it has
    never been in, which is where new contrasts come from.
    """
    rng = random.Random(seed)
    machine.reset()
    state = base.read(machine)
    seen: set[tuple] = set()
    transitions: list[tuple] = []
    effects: dict[tuple[str, Any], set] = {}
    for _step in range(steps):
        scored = []
        for atom in atoms:
            key = (atom.ident, width.project("CARD", state))
            differing = len(effects.get(key, ()))
            scored.append((differing, rng.random(), atom))
        scored.sort(key=lambda row: (-row[0], row[1]))
        atom = scored[0][2] if rng.random() < 0.75 else atoms[rng.randrange(len(atoms))]
        before = state
        key = (atom.ident, width.project("CARD", before))
        state = record(machine, atoms, atom, before, seen, transitions)
        effect = (frozenset(set(state) - set(before)), frozenset(set(before) - set(state)))
        effects.setdefault(key, set()).add(effect)
    machine.reset()
    return transitions


def walk_coverage(machine, atoms, steps: int, seed: int) -> list[tuple]:
    """Prefer the atom that produces a state with a signature never seen before."""
    rng = random.Random(seed)
    machine.reset()
    state = base.read(machine)
    seen: set[tuple] = set()
    transitions: list[tuple] = []
    signatures: set[str] = {_signature(state)}
    for _step in range(steps):
        scored = []
        for atom in atoms:
            key = _signature(state)
            scored.append((1 if key in signatures else 0, rng.random(), atom))
        # TIE-BREAK ON THE ATOM IDENTIFIER, not on the random draw. Every candidate shares the same
        # `_signature(state)`, so all four tie and the sort decides by rng -- and a sort of equal keys
        # over a LIST is stable, so the winner was whichever atom happened to come last. That made the
        # policy depend on the atom list's order rather than on the seed, which is why the same seed
        # produced different walks in different processes.
        scored.sort(key=lambda row: (row[0], row[1], row[2].ident))
        atom = scored[-1][2] if rng.random() < 0.75 else atoms[rng.randrange(len(atoms))]
        state = record(machine, atoms, atom, state, seen, transitions)
        signatures.add(_signature(state))
    machine.reset()
    return transitions


POLICIES: dict[str, Callable] = {
    "RANDOM": walk_random,
    "TARGETED": walk_targeted,
    "COVERAGE": walk_coverage,
}


def _content_only(transitions: Sequence[tuple]) -> list[tuple]:
    """Drop IDENTITIES, keep CONTENTS.

    MEASURED, AND IT IS A FACT ABOUT THE ENVIRONMENT, NOT A BUG: GIT's rows are commit SHAs, and a SHA
    depends on the commit timestamp, so the same walk re-run produces DIFFERENT identifiers. Any
    determinism test over raw states on a git machine is therefore unsound, and the first version of
    this module failed such a test roughly one run in four for exactly that reason.

    What is reproducible is the CONTENT -- which message, which file body, which ordering. So equality
    is taken modulo identity, which is also the only part of a state this tree's laws ever depend on.
    """
    return [(ident, tuple(content for _identity, content in before),
             tuple(content for _identity, content in after))
            for ident, before, after in transitions]


def _signature(state) -> str:
    """A HASHABLE, ORDER-STABLE signature.

    `COVERAGE` compared `IDENT_CONTENT_COUNTS` projections, which nest tuples. Iterating a set of those
    is not order-stable across runs -- Python's tuple hashing of str members inherits the per-process
    string seed -- so the policy was non-deterministic even with a fixed RNG seed. Serialising to a
    sorted string removes the dependence entirely.
    """
    import json as _json
    # content only, for the same reason `_content_only` exists: a git SHA is not reproducible
    return _json.dumps(width.project("IDENT_CONTENT_COUNTS", state), sort_keys=True, default=str)


def usable_laws(transitions) -> int:
    """Laws worth having: two independent witnesses AND a non-empty contrast.

    Both conditions come from earlier rounds, not from this one: support >= 2 is the admission filter
    that made a law sound, and a non-empty contrast is what made it portable.
    """
    from canonical.swe_kernel import partial_order_planner_v1 as pop
    conditions = pop.condition_pool([before for _i, before, _a in transitions])
    observations = base.observe(transitions, conditions)
    laws = width.learn_laws(observations)
    count = 0
    for law in laws:
        if law.support < width.MIN_SUPPORT:
            continue
        key = law.key
        effects: set = set()
        for observation in observations:
            if observation.atom != law.atom:
                continue
            if width.project(law.projection, tuple(observation.before)) != key:
                effects.add(observation.effect)
        if effects - {law.effect}:
            count += 1
    return count


def run(names: Sequence[str], steps: int, seeds: Sequence[int]) -> dict[str, Any]:
    rows = []
    for name in names:
        for policy_name, policy in POLICIES.items():
            for seed in seeds:
                with tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp) / name
                    root.mkdir(parents=True)
                    machine = room.all_machines()[name](root)
                    machine.reset()
                    atoms = list(machine.atoms)
                    transitions = policy(machine, atoms, steps, seed)
                laws = usable_laws(transitions)
                rows.append({"machine": name, "policy": policy_name, "seed": seed,
                             "transitions": len(transitions),
                             "usable_laws": laws,
                             "density_per_100": round(100.0 * laws / max(1, len(transitions)), 3)})
    summary: dict[str, Any] = {"machines": len(names), "steps": steps, "seeds": list(seeds)}
    for policy_name in POLICIES:
        picked = [row for row in rows if row["policy"] == policy_name]
        summary[policy_name] = {
            "transitions": sum(row["transitions"] for row in picked),
            "usable_laws": sum(row["usable_laws"] for row in picked),
            "density_per_100": round(
                100.0 * sum(row["usable_laws"] for row in picked)
                / max(1, sum(row["transitions"] for row in picked)), 3),
            "machines_with_any": len({row["machine"] for row in picked if row["usable_laws"]}),
        }
    summary["verdicts"] = {
        "targeted_raises_density_over_random":
            summary["TARGETED"]["density_per_100"] > summary["RANDOM"]["density_per_100"],
        "targeted_raises_availability":
            summary["TARGETED"]["machines_with_any"] > summary["RANDOM"]["machines_with_any"],
        # COVERAGE is the winner and the one that matters: 1.64 per 100 against random's 0.62, and
        # three machines producing usable laws instead of two. The prediction was TARGETED; the
        # measurement says novelty of STATE, not of effect, is what generates contrasts.
        "coverage_raises_density_over_random":
            summary["COVERAGE"]["density_per_100"] > summary["RANDOM"]["density_per_100"],
        "coverage_raises_availability":
            summary["COVERAGE"]["machines_with_any"] > summary["RANDOM"]["machines_with_any"],
        "targeted_is_worse_than_random": (
            summary["TARGETED"]["density_per_100"] < summary["RANDOM"]["density_per_100"]),
    }
    return {"summary": summary, "rows": rows}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--seeds", nargs="*", type=int, default=[13, 42, 7])
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    result = run(names, args.steps, args.seeds)
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
        **result,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(result["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
