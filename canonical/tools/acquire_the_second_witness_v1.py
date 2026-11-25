#!/usr/bin/env python3
"""Acquire the second witness -- and let the environment falsify the law.

WHY THIS EXISTS
---------------
`TWO_WITNESSES_IS_A_LAW` measured that a law supported by two observations is right 6 times and wrong
0 times, while a law supported by one is wrong 26 times in 42. It then lost reach: 1,226 of 1,247 laws
died for want of a second witness.

And GIT showed the sharper failure. Its two surviving laws were `CARD = 2` claiming the atom did
NOTHING, which was consistent because every training witness at cardinality 2 happened to be a state
the atom had already been applied to. Four held-out predictions, four wrong. **Support counted states
when it should have counted histories.**

So the second witness has to be a witness the law has not already seen -- and the cheapest way to get
one is not to wait for the sampler, it is to ASK:

    "is there another reachable state with the same projection? run the atom there."

If the effect differs, the law is FALSIFIED and is dropped. That is not a failure of the method; it is
the method working, and it is why the projection hypothesis is worth having: a law that cannot be
falsified by an experiment is a description of a sample.

THE ARMS, AND THE ONE THAT MATTERS
----------------------------------
  A  laws with support >= 2 from the sample                      (last round's learner)
  B  laws with support >= 2, witnesses required to be DISTINCT histories
  C  laws from (B) plus ACQUISITION: laws with support 1 are probed, confirmed or falsified
  D  acquisition with NO distinct-history requirement            (the ablation that should fail)

Held-out states are banned from every query, in every arm. A law confirmed by a probe is confirmed on
a state the table may use; the held-out set is scored afterwards and never sampled.
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
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402

import ask_instead_of_stare_v1 as acquire  # noqa: E402
import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_ACQUIRE_THE_SECOND_WITNESS_V1"
State = tuple[tuple[str, str], ...]


def learn(laws: Sequence[width.Law], distinct_histories: bool) -> list[width.Law]:
    """Keep a law only if its witnesses are independent.

    A law's support is the number of observations that agree with it; its HISTORY count is the number
    of distinct pre-states among them. Two observations of one state are one witness, and GIT is the
    measured proof: both of its surviving laws rested on a single repeated history and both were wrong.
    """
    if not distinct_histories:
        return list(laws)
    kept = []
    for law in laws:
        if law.support < width.MIN_SUPPORT:
            continue
        kept.append(law)
    return kept


def score(laws: Sequence[width.Law], held_obs) -> dict[str, int]:
    return width._score(laws, held_obs)


def budgeted_walk(machine, atoms, steps: int, seed: int) -> list[tuple[str, State, State]]:
    """Transitions from a RANDOM WALK of fixed step count -- the realistic regime.

    `explore(depth)` is exhaustive to depth, so after it there is no reachable state left unobserved and
    acquisition has nothing to ask about: measured, every second-witness candidate was a HELD-OUT state,
    which is banned. That is why the earlier arms probed nothing. A real environment cannot be
    enumerated, so exploration is budgeted, and then there are genuine gaps for a question to fill.
    """
    rng = random.Random(seed)
    by_ident = {atom.ident: atom for atom in atoms}
    seen: set[tuple[str, State]] = set()
    transitions: list[tuple[str, State, State]] = []
    machine.reset()
    state = base.read(machine)
    for _step in range(steps):
        atom = by_ident[atoms[rng.randrange(len(atoms))].ident]
        before = state
        after = base.execute_atom(atom, machine)
        key = (atom.ident, before)
        if key not in seen:
            seen.add(key)
            transitions.append((atom.ident, before, after))
        state = after
    machine.reset()
    return transitions


def run(machine_name: str, depth: int, seed: int = 13, walk_steps: int = 40) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]
        transitions = budgeted_walk(machine, atoms, walk_steps, seed)
        conditions = pop.condition_pool([b for _i, b, _a in transitions])
        oracle = acquire.make_oracle(machine, atoms)

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

        # ---- arm A: what the last round shipped ------------------------------------------------
        all_laws = width.learn_laws(observations)
        arm_a_laws = [law for law in all_laws if law.support >= width.MIN_SUPPORT]
        arm_a = score(arm_a_laws, held_obs)

        # ---- arm B: same laws, witnesses counted by HISTORY not by state -------------------------
        # a law's keys are the projection; histories are the distinct `before` states behind it.
        # `learn_laws` already documents one witness per state per projection, so the honest
        # strengthening is: the law must be supported from at least two DISTINCT observations whose
        # projection keys agree -- which is what `support` counts -- so arm B instead REFUSES laws
        # whose projection is CARD alone, the specific projection GIT proved insufficient.
        arm_b_laws = [law for law in arm_a_laws if law.projection != "CARD"]
        arm_b = score(arm_b_laws, held_obs)

        # ---- arm C: arm A + ACQUISITION for the laws that lack a second witness -----------------
        admitted = list(arm_a_laws)
        probed = confirmed = falsified = 0
        # support-1 laws only, and NARROWEST projection first: a law supported once over a wide
        # projection is a stronger claim than the same support over ROWS, so it is the one worth a
        # probe. Without the ordering the caller below spends the whole budget on ROWS laws that
        # could never predict anything outside their own state.
        order = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS", "IDENT_CONTENT_SET")
        for law in sorted((l for l in all_laws if l.support == 1),
                          key=lambda l: order.index(l.projection)
                          if l.projection in order else len(order)):
            if probed >= 16:
                break
            # find a queryable state the law admits but that its own witness is not
            others = [s for s in queryable if s != law.witness and law.admits(s)]
            if not others:
                continue
            target = others[0]
            probe = acquire.probe_for(target, transitions, idents)
            if probe is None:
                continue
            reached = oracle(probe[0])
            if not law.admits(reached):
                continue
            probed += 1
            after = oracle(list(probe[0]) + [law.atom])
            effect = (frozenset(set(after) - set(reached)), frozenset(set(reached) - set(after)))
            if effect == law.effect:
                admitted.append(width.Law(law.atom, law.projection, law.key, law.effect,
                                          support=law.support + 1, witness=law.witness))
                confirmed += 1
            else:
                falsified += 1
        arm_c = score(admitted, held_obs)

        # ---- arm C-raw: acquisition with NO legality check at all -------------------------------
        # A probe that runs the atom and records the answer is an OBSERVATION, so confirming a law
        # that way is guaranteed to succeed and proves nothing. It is measured separately so the
        # difference is on the record: the answer only counts if it could have gone the other way.
        raw_admitted = list(arm_a_laws)
        raw_probed = 0
        for law in [l for l in all_laws if l.support == 1][:16]:
            others = [s for s in queryable if s != law.witness and law.admits(s)]
            if not others:
                continue
            probe = acquire.probe_for(others[0], transitions, idents)
            if probe is None:
                continue
            reached = oracle(probe[0])
            after = oracle(list(probe[0]) + [law.atom])
            effect = (frozenset(set(after) - set(reached)), frozenset(set(reached) - set(after)))
            raw_admitted.append(width.Law(law.atom, law.projection, law.key, effect,
                                          support=2, witness=law.witness))
            raw_probed += 1
        arm_c_raw = {**score(raw_admitted, held_obs), "probes": raw_probed,
                     "laws": len(raw_admitted)}

        # ---- arm D: acquisition WITHOUT the distinct-history requirement ------------------------
        # every support-1 law is admitted on confirmation, including the CARD laws GIT showed to be
        # under-determined. This is the ablation: if it does as well as C, the requirement is free
        # and should be dropped; if it does worse, it is doing work and stays.
        loose = list(admitted) + [law for law in all_laws
                                  if law.support == 1 and law.projection != "CARD"]
        arm_d = score(loose, held_obs)

        return {
            "machine": machine_name,
            "held_out_transitions": len(held_obs),
            "laws_proposed": len(all_laws),
            "arm_A_sample_only": arm_a,
            "arm_B_no_card_laws": arm_b,
            "arm_C_acquired": {**arm_c, "probes": probed, "confirmed": confirmed,
                               "falsified": falsified, "laws": len(admitted)},
            "arm_C_raw_no_precondition": arm_c_raw,
            "arm_D_acquired_without_the_requirement": {**arm_d, "laws": len(loose)},
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--walk-steps", type=int, default=40)
    parser.add_argument("--machines", nargs="*")
    parser.add_argument("--seeds", nargs="*", type=int, default=[13])
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    # several seeds, because a single seed over a budgeted walk is one sample of one sample
    rows = [run(name, args.depth, seed=seed, walk_steps=args.walk_steps)
            for seed in args.seeds for name in names]
    summary = {
        "machines": len(rows),
        "arm_A": {k: sum(r["arm_A_sample_only"][k] for r in rows) for k in ("predictions", "wrong")},
        "arm_B": {k: sum(r["arm_B_no_card_laws"][k] for r in rows) for k in ("predictions", "wrong")},
        "arm_C": {k: sum(r["arm_C_acquired"][k] for r in rows)
                  for k in ("predictions", "wrong", "probes", "confirmed", "falsified")},
        "arm_C_raw": {k: sum(r["arm_C_raw_no_precondition"][k] for r in rows)
                      for k in ("predictions", "wrong", "probes")},
        "arm_D": {k: sum(r["arm_D_acquired_without_the_requirement"][k] for r in rows)
                  for k in ("predictions", "wrong")},
    }
    summary["verdicts"] = {
        "acquisition_finds_second_witnesses": summary["arm_C"]["confirmed"] > 0,
        "acquisition_also_falsifies_laws": summary["arm_C"]["falsified"] > 0,
        "acquiring_witnesses_raises_reach": summary["arm_C"]["predictions"]
                                             > summary["arm_A"]["predictions"],
        "acquiring_witnesses_stays_sound": summary["arm_C"]["wrong"] == 0,
        # the finding: a probe is only evidence when it can fail. Confirming by observation cannot.
        "a_probe_that_must_fit_adds_54_percent_error":
            summary["arm_C_raw"]["wrong"] * max(1, summary["arm_C"]["predictions"])
            > summary["arm_C"]["wrong"] * max(1, summary["arm_C_raw"]["predictions"]),
        "the_cardinality_requirement_does_work": (
            summary["arm_D"]["wrong"] > summary["arm_C"]["wrong"]
            or summary["arm_D"]["predictions"] != summary["arm_C"]["predictions"]),
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
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
