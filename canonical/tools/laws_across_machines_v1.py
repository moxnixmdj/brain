#!/usr/bin/env python3
"""Do laws learned on one machine predict a DIFFERENT machine, when the naming is aligned by behaviour?

THE PROBLEM THAT MAKES NAIVE TRANSFER TRIVIAL AND POINTLESS
-----------------------------------------------------------
Every machine names its atoms differently (`GIT_A1`, `LS_A1`, `JN_A1`, `VAULT_A2`). A law learned on GIT
therefore cannot apply to LIST at all, and a literal mapping between the two would be a hand-written
table of world facts -- the exact parameter this project forbids. So the alignment must be DERIVED.

HOW THE ALIGNMENT IS DERIVED (no hand-written pairs, nothing stored)
-------------------------------------------------------------------
Each atom gets a fingerprint from a few observations on its own machine, built only from quantities the
relation vocabulary can compute:

    (rows_added, rows_deleted, rows_after, copies_existing_content)

`copies_existing_content` is the load-bearing term: it is true when an added row's content already
appears in the state, which is what distinguishes "write a literal" from "duplicate a sibling" -- and it
is computed from the relation vocabulary rather than from knowledge of the machine.

Atoms are then matched by fingerprint agreement, greedily, widest-agreement first. Two machines that
share a structure will share fingerprints; two that do not will not align, and the transfer will be
scored as what it is.

ARMS
----
  A  target only          walk the target machine, learn there
  B  transfer             learn on the SOURCE, map its laws through the derived alignment, score on target
  C  transfer + refine    B, then keep asking questions on the target until its supply runs out
  D  shuffled alignment   B with the alignment randomly permuted -- the null that says whether the
                          alignment, rather than the mere act of importing laws, carries the result

HONESTY
-------
The target's held-out transitions are the ones its own walk never visited. The source machine is explored
freely in B and C, because the source is a machine the system has already lived in -- that is the regime
the architecture actually claims (a store of laws that is removable and reusable).
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
from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402

import acquire_the_second_witness_v1 as walker  # noqa: E402
import ask_instead_of_stare_v1 as oracle_module  # noqa: E402
import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_LAWS_ACROSS_MACHINES_V1"
PROJECTION_ORDER = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS")


class Prints:
    """Modal fingerprint per atom, computed from observations only."""

    def __init__(self, transitions: list[tuple[str, Any, Any]]) -> None:
        counts: dict[str, dict[tuple, int]] = {}
        for ident, before, after in transitions:
            contents = {content for _ident, content in before}
            added = [row for row in after if row not in before]
            deleted = [row for row in before if row not in after]
            key = (len(added), len(deleted), len(after),
                   any(content in contents for _ident, content in added))
            counts.setdefault(ident, {}).setdefault(key, 0)
            counts[ident][key] += 1
        self.table = {ident: max(sorted(sigs), key=lambda k: sigs[k])
                      for ident, sigs in counts.items()}


def align(source: Prints, target: Prints) -> dict[str, str]:
    """Greedy maximum-agreement matching, derived. No hand-written pair, no stored table."""
    pairs = []
    for src, src_sig in source.table.items():
        for dst, dst_sig in target.table.items():
            agreement = sum(1 for a, b in zip(src_sig, dst_sig) if a == b)
            pairs.append((-agreement, src, dst))
    pairs.sort()
    used_src: set[str] = set()
    used_dst: set[str] = set()
    mapping: dict[str, str] = {}
    for _neg, src, dst in pairs:
        if src in used_src or dst in used_dst:
            continue
        mapping[src] = dst
        used_src.add(src)
        used_dst.add(dst)
    return mapping


def translate(laws: Sequence[width.Law], mapping: dict[str, str]) -> list[width.Law]:
    """Re-point every law at the target machine's atom names. Keys stay as they are: the projections
    are computed by the same vocabulary on both machines, which is why they can cross at all."""
    out = []
    for law in laws:
        if law.atom not in mapping:
            continue
        out.append(width.Law(mapping[law.atom], law.projection, law.key, law.effect,
                             law.support, law.witness))
    return out


def acquire(machine_name: str, walk_steps: int, budget: int, seed: int,
            source_name: str | None = None, shuffle: bool = False,
            refine: bool = False) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        walked = walker.budgeted_walk(machine, atoms, walk_steps, seed)
        # vocabulary from the WALK only -- the leak from the previous round is not repeated here
        conditions = pop.condition_pool([b for _i, b, _a in walked])
        full = base.explore(machine, atoms, 3)
        seen = {before for _i, before, _a in walked}
        held = [(ident, before, after) for ident, before, after in full if before not in seen]
        held_obs = base.observe(held, conditions) if held else []
        if not held_obs:
            return {"target": machine_name, "skipped": "walk covered every reachable state"}

        observations = list(base.observe(walked, conditions))
        table_a = [law for law in width.learn_laws(observations)
                   if law.support >= width.MIN_SUPPORT]
        score_a = width._score(table_a, held_obs)

        row: dict[str, Any] = {"target": machine_name, "source": source_name,
                               "arm_A": score_a, "probes": 0,
                               "alignment": {}, "laws_imported": 0}

        imported: list[width.Law] = []
        if source_name is not None:
            src_root = pathlib.Path(tmp) / source_name
            src_root.mkdir(parents=True)
            src_machine = room.all_machines()[source_name](src_root)
            src_machine.reset()
            src_atoms = list(src_machine.atoms)
            src_walked = walker.budgeted_walk(src_machine, src_atoms, walk_steps, seed)
            src_conditions = pop.condition_pool([b for _i, b, _a in src_walked])
            src_observations = list(base.observe(src_walked, src_conditions))
            src_table = [law for law in width.learn_laws(src_observations)
                         if law.support >= width.MIN_SUPPORT]

            mapping = align(Prints(src_walked), Prints(walked))
            if shuffle and len(mapping) > 1:
                keys = sorted(mapping)
                values = [mapping[key] for key in keys]
                random.Random(seed).shuffle(values)
                mapping = dict(zip(keys, values))
            # THE DIAGNOSTIC THAT EXPLAINS THE RESULT: a law crosses only if its KEY is a projection
            # value the target actually takes AND its EFFECT names rows the target could produce.
            # Both halves are ground (un-lifted), so a name that encodes content cannot cross.
            target_keys: dict[str, set] = {}
            for _ident, before, _after in full:
                for projection_name in PROJECTION_ORDER:
                    target_keys.setdefault(projection_name, set()).add(
                        width.project(projection_name, tuple(before)))
            target_contents = {content for _i, state, _a in full
                               for _ident, content in state}
            crossable = 0
            for law in src_table:
                if law.atom not in mapping:
                    continue
                if law.key not in target_keys.get(law.projection, set()):
                    continue
                added, _deleted = law.effect
                if any(content not in target_contents for _ident, content in added):
                    continue
                crossable += 1
            row["crossable_laws"] = crossable
            row["source_laws"] = len(src_table)
            row["key_misses"] = sum(1 for law in src_table
                                    if law.atom in mapping
                                    and law.key not in target_keys.get(law.projection, set()))
            row["alignment"] = mapping
            imported = translate(src_table, mapping)
            row["laws_imported"] = len(imported)
            row["score_B"] = width._score(imported, held_obs)

        table_c = list(imported)
        opened = list(observations) if not imported else []
        # in arms A/C the target's own observations are available; in B nothing from the target's
        # walk is used for the imported laws, so B is scored on imported laws alone.
        if refine:
            opened = list(observations)
            probes = 0
            oracle = oracle_module.make_oracle(machine, atoms)
            unknown = sorted({before for _i, before, _a in full} - seen)
            while probes < budget:
                candidates = sorted((law for law in width.learn_laws(opened)
                                     if law.support == 1 and law.projection in PROJECTION_ORDER),
                                    key=lambda law: PROJECTION_ORDER.index(law.projection))
                picked = None
                for law in candidates:
                    for state in unknown:
                        if law.admits(state):
                            picked = (law, state)
                            break
                    if picked:
                        break
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
                opened.append(sam.Observation.of(law.atom, reached, after, conditions))
                if reached in unknown:
                    unknown = [state for state in unknown if state != reached]
            row["probes"] = probes
            table_c = [law for law in width.learn_laws(opened)
                       if law.support >= width.MIN_SUPPORT]
        row["score_C"] = width._score(table_c, held_obs)
        row["held_out"] = len(held_obs)
        return row


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--budget", type=int, default=200)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--pairs", nargs="*",
                        default=["GIT:LIST", "LIST:SQLITE", "VAULT:TARBALL", "GIT2:SCRAMBLED"])
    args = parser.parse_args(argv)

    started = time.time()
    rows: list[dict[str, Any]] = []
    for pair in args.pairs:
        source, target = pair.split(":")
        rows.append(acquire(target, args.walk_steps, args.budget, args.seed,
                            source_name=source, refine=True))
        rows.append(acquire(target, args.walk_steps, args.budget, args.seed,
                            source_name=source, refine=True, shuffle=True))

    def total(key: str, rows_in: list[dict[str, Any]]) -> dict[str, Any]:
        rows_in = [row for row in rows_in if key in row]
        predictions = sum(row.get(key, {}).get("predictions", 0) for row in rows_in)
        wrong = sum(row.get(key, {}).get("wrong", 0) for row in rows_in)
        refused = sum(row.get(key, {}).get("refused", 0) for row in rows_in)
        return {"predictions": predictions, "wrong": wrong, "refused": refused,
                "accuracy": round(predictions / max(1, predictions + wrong), 4),
                "coverage": round(predictions / max(1, predictions + refused), 4)}

    real = [row for i, row in enumerate(rows) if i % 2 == 0]
    shuffled = [row for i, row in enumerate(rows) if i % 2 == 1]
    summary = {
        "pairs": args.pairs,
        "A_target_only": total("arm_A", rows),
        "B_transferred": total("score_B", real),
        "B_shuffled_alignment": total("score_B", shuffled),
        "C_transferred_then_refined": total("score_C", real),
        "C_shuffled_then_refined": total("score_C", shuffled),
        "laws_imported": sum(row.get("laws_imported", 0) for row in real),
        "crossable_laws": sum(row.get("crossable_laws", 0) for row in real),
        "source_laws": sum(row.get("source_laws", 0) for row in real),
        "key_misses": sum(row.get("key_misses", 0) for row in real),
        "probes": sum(row.get("probes", 0) for row in rows),
        "alignments": {row["target"]: row.get("alignment", {}) for row in real},
        "skipped": [row["target"] for row in real if "skipped" in row],
    }
    b, bs = summary["B_transferred"], summary["B_shuffled_alignment"]
    c, a = summary["C_transferred_then_refined"], summary["A_target_only"]
    summary["verdicts"] = {
        "laws_cross_machines_at_all": b["predictions"] > 0,
        "transferred_laws_are_more_accurate_than_target_only":
            b["accuracy"] > a["accuracy"],
        "the_derived_alignment_beats_a_shuffled_one":
            b["accuracy"] > bs["accuracy"] and b["predictions"] >= bs["predictions"],
        "transfer_plus_refinement_beats_target_only_on_reach":
            c["predictions"] > a["predictions"],
        "transfer_keeps_accuracy_above_nine_tenths": b["accuracy"] > 0.90,
        # the explanation, measured rather than asserted
        "most_source_laws_have_no_counterpart_key_in_the_target":
            summary["key_misses"] > 0.5 * summary["source_laws"],
        "the_blocks_is_naming_not_evidence":
            summary["key_misses"] > 0.5 * summary["source_laws"] and b["predictions"] < 0.1 * a["predictions"],
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
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
