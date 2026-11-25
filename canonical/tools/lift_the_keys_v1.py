#!/usr/bin/env python3
"""Lift the keys and the effects, then re-run the transfer instrument unchanged.

THE BLOCKER, FROM THE LAST ROUND
--------------------------------
Laws learned on one machine do not apply to another, and the measurement said why: 10 of 16 source laws
had no counterpart KEY in the target, because a key is a projection value over GROUND names (`GIT_A1`,
`probe_seed_content`) and ground names are machine-local.

The fix has to be lifting, not mapping. `GIT_A1` in the source and `LS_A1` in the target are not the same
name and must not be renamed into each other -- the previous round tried renaming and it tied its own
shuffled null. What can cross is a law stated over STRUCTURE:

    "adding a row whose content already appears in the state"      (not: "adding GIT_A3")
    "deleting a row that holds the only copy of its content"       (not: "deleting GIT_A1")

THE LIFTING, AND WHY EACH TERM IS DERIVED
-----------------------------------------
Every predicate below is computed with the relation vocabulary already in the tree, over a state alone.
None of them names a machine, an atom, or a content literal.

  row content DUPLICATED?   content appears at least twice in the state
  content SHARED?           content appears at least twice
  row is UNIQUE?            content appears exactly once
  rows count               CARD

A lifted law is `(atom_rank, LIFTED_KEY, LIFTED_EFFECT)` where `atom_rank` is the atom's position in
sorted ident order -- the only cross-machine atom coordinate the vocabulary can compute without a table,
and it is derived by sorting, not written down.

WHAT WOULD MAKE THIS FAIL, AND HOW IT WILL SHOW
-----------------------------------------------
The null is the same instrument's shuffled-alignment arm. If lifted laws cross machine boundaries for a
real reason, arm B must beat arm B′; if they only cross because `CARD` and `CONTENT_COUNTS` are already
portable, B and B′ will be indistinguishable and this file says so.
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

SCHEMA = "BRAIN_LIFT_THE_KEYS_V1"
State = tuple[tuple[str, str], ...]

#: Lifted predicates. Each is a function of the STATE ALONE, built from the relation vocabulary.
#: The key is the pattern a state must match; the effect is the pattern of the change.
KEY_PATTERNS: Sequence[tuple[str, Any]] = (
    ("HAS_DUPLICATE_CONTENT",
     lambda state: any(state.count(row) > 0
                       and sum(1 for _i, c in state if c == row[1]) > 1 for row in state)),
    ("ALL_CONTENT_UNIQUE",
     lambda state: len({content for _ident, content in state}) == len(state)),
    ("ROWS_2", lambda state: len(state) == 2),
    ("ROWS_3", lambda state: len(state) == 3),
    ("ROWS_4", lambda state: len(state) == 4),
)

#: Lifted effects, as (added_rows, deleted_rows) described structurally.
EFFECT_PATTERNS: Sequence[tuple[str, Any]] = (
    ("NO_CHANGE", lambda added, deleted: not added and not deleted),
    ("ADD_DUPLICATE", lambda added, deleted: bool(added) and not deleted),
    ("ADD_AND_DELETE", lambda added, deleted: bool(added) and bool(deleted)),
    ("DELETE_ONLY", lambda added, deleted: not added and bool(deleted)),
)


def atom_rank(idents: Sequence[str], ident: str) -> int:
    """Cross-machine atom coordinate: position in sorted ident order. Derived by sorting."""
    return sorted(idents).index(ident)


def key_of(state: State) -> str:
    """The lifted key: every pattern the state satisfies, sorted and joined. Deterministic."""
    return "|".join(name for name, test in KEY_PATTERNS if test(state)) or "NO_PATTERN"


def effect_of(added: list, deleted: list, after: State) -> str:
    contents = {content for _ident, content in after}
    name = next((n for n, test in EFFECT_PATTERNS if test(added, deleted)), "OTHER")
    # the structural suffix: does the added content already exist somewhere in the target state?
    if added and any(content in contents for _ident, content in added):
        name += "+REUSES_CONTENT"
    return name


class Lifted:
    """An inspectable, removable law: `atom at rank R in a state matching KEY does EFFECT`."""

    __slots__ = ("rank", "key", "effect", "support", "idents")

    def __init__(self, rank: int, key: str, effect: str) -> None:
        self.rank = rank
        self.key = key
        self.effect = effect
        self.support = 0
        self.idents: tuple[str, ...] = ()

    def admits(self, rank: int, state: State) -> bool:
        return rank == self.rank and key_of(tuple(state)) == self.key

    def to_dict(self) -> dict[str, Any]:
        return {"rank": self.rank, "key": self.key, "effect": self.effect,
                "support": self.support}


def lift(transitions: list[tuple[str, State, State]], idents: Sequence[str]) -> list[Lifted]:
    table: dict[tuple[int, str], Lifted] = {}
    for ident, before, after in transitions:
        rank = atom_rank(idents, ident)
        added = [row for row in after if row not in before]
        deleted = [row for row in before if row not in after]
        key = key_of(tuple(before))
        lifted = Lifted(rank, key, effect_of(added, deleted, tuple(after)))
        bucket = table.setdefault((rank, key), lifted)
        bucket.support += 1
    return list(table.values())


def predict_lifted(laws: Sequence[Lifted], rank: int, state: State) -> dict[str, Any]:
    """Same admissibility rule as the unlifted learner: every admitting law must agree, else refuse."""
    candidates = [law for law in laws if law.admits(rank, tuple(state))]
    if not candidates:
        return {"status": "REFUSED__NO_LIFTED_LAW_ADMITS_THIS_STATE"}
    effects = {law.effect for law in candidates}
    if len(effects) > 1:
        return {"status": "REFUSED__LAWS_DISAGREE"}
    return {"status": "PREDICTS", "effect": next(iter(effects))}


def outcome_of(before: State, after: State) -> str:
    added = [row for row in after if row not in before]
    deleted = [row for row in before if row not in after]
    return effect_of(added, deleted, tuple(after))


def score(laws: Sequence[Lifted], idents: Sequence[str],
          held: list[tuple[str, State, State]]) -> dict[str, Any]:
    predictions = wrong = refused = 0
    for ident, before, after in held:
        rank = atom_rank(idents, ident)
        result = predict_lifted(laws, rank, tuple(before))
        if result["status"] != "PREDICTS":
            refused += 1
            continue
        predictions += 1
        if result["effect"] != outcome_of(tuple(before), tuple(after)):
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused,
            "accuracy": round(predictions / max(1, predictions + wrong), 4),
            "coverage": round(predictions / max(1, predictions + refused), 4)}


def run(target: str, source: str, walk_steps: int, budget: int, seed: int,
        shuffle: bool = False) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / target
        root.mkdir(parents=True)
        machine = room.all_machines()[target](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]

        walked = walker.budgeted_walk(machine, atoms, walk_steps, seed)
        full = base.explore(machine, atoms, 3)
        seen = {before for _i, before, _a in walked}
        held = [(ident, before, after) for ident, before, after in full if before not in seen]
        if not held:
            return {"target": target, "skipped": "walk covered every reachable state"}

        src_root = pathlib.Path(tmp) / source
        src_root.mkdir(parents=True)
        src_machine = room.all_machines()[source](src_root)
        src_machine.reset()
        src_atoms = list(src_machine.atoms)
        src_idents = [atom.ident for atom in src_atoms]
        src_walked = walker.budgeted_walk(src_machine, src_atoms, walk_steps, seed)

        # LIFTED laws from the source. No name is carried across; only rank + structural pattern.
        source_laws = lift(src_walked, src_idents)
        n_target_atoms = len(atoms)
        imported = [law for law in source_laws if law.rank < n_target_atoms]
        if shuffle:
            orders = list(range(n_target_atoms))
            random.Random(seed).shuffle(orders)
            for law in imported:
                law.rank = orders[law.rank]

        row: dict[str, Any] = {
            "target": target, "source": source,
            "source_laws": len(source_laws),
            "imported": len(imported),
            "target_atoms": n_target_atoms,
            "source_atoms": len(src_atoms),
            "held_out": len(held),
            "B": score(imported, idents, held),
        }

        # C: imported laws PLUS the target's own lifted laws -- the honest combined arm
        own = lift(walked, idents)
        combined = imported + [law for law in own
                               if not any(law.rank == other.rank and law.key == other.key
                                          for other in imported)]
        row["C"] = score(combined, idents, held)
        row["A"] = score(own, idents, held)
        row["probes"] = 0
        return row


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--budget", type=int, default=200)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--pairs", nargs="*",
                        default=["GIT:LIST", "GIT2:SCRAMBLED", "LIST:JOURNAL",
                                 "VAULT:ARCHIVE2", "GIT:SQLITE"])
    args = parser.parse_args(argv)

    started = time.time()
    rows: list[dict[str, Any]] = []
    for pair in args.pairs:
        source, target = pair.split(":")
        rows.append(run(target, source, args.walk_steps, args.budget, args.seed))
        rows.append(run(target, source, args.walk_steps, args.budget, args.seed, shuffle=True))

    real = [row for i, row in enumerate(rows) if i % 2 == 0 and "skipped" not in row]
    null = [row for i, row in enumerate(rows) if i % 2 == 1 and "skipped" not in row]

    def total(key: str, subset: list[dict[str, Any]]) -> dict[str, Any]:
        predictions = sum(row[key]["predictions"] for row in subset)
        wrong = sum(row[key]["wrong"] for row in subset)
        refused = sum(row[key]["refused"] for row in subset)
        return {"predictions": predictions, "wrong": wrong, "refused": refused,
                "accuracy": round(predictions / max(1, predictions + wrong), 4),
                "coverage": round(predictions / max(1, predictions + refused), 4)}

    summary = {
        "pairs": args.pairs,
        "skipped": [row["target"] for row in rows if "skipped" in row],
        "A_target_only": total("A", real),
        "B_lifted_transfer": total("B", real),
        "B_lifted_shuffled": total("B", null),
        "C_lifted_combined": total("C", real),
        "C_lifted_shuffled": total("C", null),
        "source_laws": sum(row["source_laws"] for row in real),
        "imported": sum(row["imported"] for row in real),
    }
    a, b, bs = summary["A_target_only"], summary["B_lifted_transfer"], summary["B_lifted_shuffled"]
    c = summary["C_lifted_combined"]
    summary["verdicts"] = {
        "lifting_lets_laws_cross": b["predictions"] > 0,
        "lifting_beats_its_own_shuffled_null":
            b["accuracy"] > bs["accuracy"] and b["predictions"] > bs["predictions"],
        "lifted_transfer_beats_target_learning_on_reach": b["predictions"] > a["predictions"],
        "lifted_transfer_matches_target_learning":
            abs(b["accuracy"] - a["accuracy"]) < 0.05 and b["predictions"] >= a["predictions"],
        "combined_beats_target_only": c["predictions"] > a["predictions"]
            and c["accuracy"] >= a["accuracy"] - 0.05,
        "lifting_removes_the_key_miss_problem": b["refused"] < 0.5 * (b["refused"] + b["predictions"]),
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
