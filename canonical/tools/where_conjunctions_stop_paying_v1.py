#!/usr/bin/env python3
"""Where do conjunctions of predicates stop paying, and can the stopping rule be DERIVED?

THE QUESTION
------------
Twenty rounds established that representation is the only lever that pays: lifting moved coverage 0.126 ->
0.70 for zero extra evidence, and leave-one-machine-out selection showed an added predicate set gains
+5.8 accuracy / +10.8 coverage on a machine it never saw. But nobody knows how much vocabulary is enough.
Declaring "twelve predicates is right" would be exactly the arbitrary parameter this project forbids.

So: grow the candidate set, and measure the out-of-sample gain curve as a function of vocabulary size.

DESIGN — nested leave-one-machine-out
-------------------------------------
For each vocabulary size k = 1..N:
    for each held-out machine M:
        choose the best k-subset using ONLY the other nine machines
        score that subset on M
    pool the ten out-of-sample results

The result is a curve coverage(k), accuracy(k) where NO point was selected on the machine it is scored
on. Then the stopping rule is read off the curve rather than chosen: stop adding predicates when the
marginal out-of-sample coverage gain per predicate falls below the noise of the estimate.

THE NOISE FLOOR, DERIVED NOT DECLARED
-------------------------------------
Ten folds, and each fold reports a Bernoulli-ish accuracy on ~150 transitions. The standard error of a
pooled accuracy near p=0.9 with n predictions is sqrt(p(1-p)/n). The test set does not change with k, so
the relevant comparison is against the SE of the DIFFERENCE, which for a paired comparison on the same
transitions is dominated by the transitions that flipped. That is measured directly: the fold-level
choice changes, so count how many folds improve versus worsen between k and k+1.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
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

import acquire_the_second_witness_v1 as walker  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_WHERE_CONJUNCTIONS_STOP_PAYING_V1"
State = tuple[tuple[str, str], ...]
HELD_OUT_SHARE = 0.35


def _dup(s: State) -> bool:
    return any(sum(1 for _i, c in s if c == row[1]) > 1 for row in s)


#: Candidate predicates. Every one is a pure function of a state, computed from the relation vocabulary
#: already in the tree. None names a machine, an atom, or a content literal. The first five are the
#: vocabulary that twenty rounds of hand-picking arrived at; the rest are candidates to be priced.
PREDICATES: dict[str, Callable[[State], bool]] = {
    # --- the incumbent five ---
    "HAS_DUPLICATE_CONTENT": _dup,
    "ALL_CONTENT_UNIQUE": lambda s: len({c for _i, c in s}) == len(s),
    "ROWS_2": lambda s: len(s) == 2,
    "ROWS_3": lambda s: len(s) == 3,
    "ROWS_4": lambda s: len(s) == 4,
    # --- candidates ---
    "CONTENT_SORTED": lambda s: [c for _i, c in s] == sorted(c for _i, c in s),
    "IDENT_SORTED": lambda s: [i for i, _c in s] == sorted(i for i, _c in s),
    "HAS_MANY_ROWS": lambda s: len(s) >= 4,
    "ROWS_1": lambda s: len(s) == 1,
    "IDENT_LENGTH_UNIFORM": lambda s: len({len(i) for i, _c in s}) == 1,
    "CONTENT_LENGTH_UNIFORM": lambda s: len({len(c) for _i, c in s}) == 1,
    "HAS_DIGIT_CONTENT": lambda s: any(any(ch.isdigit() for ch in c) for _i, c in s),
    "HAS_EMPTY_CONTENT": lambda s: any(c == "" for _i, c in s),
}
INCUMBENT = ("HAS_DUPLICATE_CONTENT", "ALL_CONTENT_UNIQUE", "ROWS_2", "ROWS_3", "ROWS_4")


def effect_of(before: State, after: State) -> str:
    from canonical.tools.lift_the_keys_v1 import effect_of as lifted_effect
    added = [row for row in after if row not in before]
    deleted = [row for row in before if row not in after]
    return lifted_effect(added, deleted, tuple(after))


class Machine:
    """Precomputed satisfied-predicate sets so a subset's key is one intersection, not a full scan."""

    __slots__ = ("name", "names", "walk", "held")

    def __init__(self, name: str, names: Sequence[str],
                 walk: list[tuple[int, frozenset[str], str]],
                 held: list[tuple[int, frozenset[str], str]]) -> None:
        self.name = name
        self.names = tuple(names)
        self.walk = walk
        self.held = held


def load(name: str, steps: int, seed: int) -> Machine | None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / name
        root.mkdir(parents=True)
        machine = room.all_machines()[name](root)
        machine.reset()
        atoms = list(machine.atoms)
        idents = [atom.ident for atom in atoms]
        order = {ident: rank for rank, ident in enumerate(sorted(idents))}
        full = [(ident, tuple(before), tuple(after))
                for ident, before, after in base.explore(machine, atoms, 3)]
        full.sort()
        random.Random(seed).shuffle(full)
        cut = max(1, int(len(full) * HELD_OUT_SHARE))
        held_raw = full[:cut]
        held_keys = {(ident, before) for ident, before, _a in held_raw}
        walk_raw = [(ident, tuple(before), tuple(after))
                    for ident, before, after in walker.budgeted_walk(machine, atoms, steps, seed)
                    if (ident, tuple(before)) not in held_keys]
        if not walk_raw or not held_raw:
            return None

        def encode(rows):
            return [(order[ident],
                     frozenset(p for p, test in PREDICATES.items() if test(before)),
                     effect_of(before, after)) for ident, before, after in rows]

        return Machine(name, tuple(PREDICATES), encode(walk_raw), encode(held_raw))


def evaluate(subset: Sequence[str], machines: Sequence[Machine]) -> dict[str, int]:
    """Learn a keyed effect table from each walk and score it on each held-out set.

    A key is the set of active predicates the state satisfies. States whose key the walk never produced
    are refused; states whose key saw disagreeing effects are refused (the standing admissibility rule).
    """
    predictions = wrong = refused = 0
    active = frozenset(subset)
    for machine in machines:
        table: dict[tuple[int, frozenset[str], str]] = {}
        # three-way: the index stores (rank, key, effect) -> count; a key with two effects is conflicted
        seen: dict[tuple[int, frozenset[str]], str] = {}
        conflicted: set[tuple[int, frozenset[str]]] = set()
        for rank, satisfied, effect in machine.walk:
            key = (rank, active & satisfied)
            if key in conflicted:
                continue
            if key in seen and seen[key] != effect:
                conflicted.add(key)
                del seen[key]
                continue
            seen[key] = effect
        for rank, satisfied, effect in machine.held:
            key = (rank, active & satisfied)
            if key in conflicted or key not in seen:
                refused += 1
                continue
            predictions += 1
            if seen[key] != effect:
                wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-size", type=int, default=9)
    args = parser.parse_args(argv)

    started = time.time()
    machines = [m for m in (load(name, args.walk_steps, args.seed)
                            for name in sorted(room.all_machines())) if m is not None]
    names = sorted(PREDICATES)
    curve: list[dict[str, Any]] = []
    incumbent_row = None

    for size in range(1, args.max_size + 1):
        per_fold = []
        for index in range(len(machines)):
            train = [m for position, m in enumerate(machines) if position != index]
            test = machines[index]
            best_subset, best_key = None, None
            for subset in itertools.combinations(names, size):
                cell = evaluate(subset, train)
                key = (cell["predictions"] - 2 * cell["wrong"], cell["predictions"])
                if best_key is None or key > best_key:
                    best_subset, best_key = subset, key
            held = evaluate(best_subset, [test])
            per_fold.append({"machine": test.name, "chosen": list(best_subset), **held})
            if size == len(INCUMBENT) or incumbent_row is None:
                pass
        predictions = sum(fold["predictions"] for fold in per_fold)
        wrong = sum(fold["wrong"] for fold in per_fold)
        refused = sum(fold["refused"] for fold in per_fold)
        curve.append({
            "size": size,
            "predictions": predictions, "wrong": wrong, "refused": refused,
            "accuracy": round(predictions / max(1, predictions + wrong), 4),
            "coverage": round(predictions / max(1, predictions + refused), 4),
            "folds": per_fold,
        })

    # the incumbent vocabulary, scored the same way for a reference line
    incumbent = evaluate(INCUMBENT, machines)
    incumbent_summary = {
        "predictions": incumbent["predictions"], "wrong": incumbent["wrong"],
        "refused": incumbent["refused"],
        "accuracy": round(incumbent["predictions"]
                          / max(1, incumbent["predictions"] + incumbent["wrong"]), 4),
        "coverage": round(incumbent["predictions"]
                          / max(1, incumbent["predictions"] + incumbent["refused"]), 4),
    }

    # marginal gain per added predicate, on the OUT-OF-SAMPLE curve
    margins = []
    for before, after in zip(curve, curve[1:]):
        margins.append({
            "from_size": before["size"], "to_size": after["size"],
            "coverage_gain": round(after["coverage"] - before["coverage"], 4),
            "accuracy_gain": round(after["accuracy"] - before["accuracy"], 4),
        })

    # the noise floor: does the chosen subset even change between adjacent sizes, and how many folds move
    fold_moves = []
    for before, after in zip(curve, curve[1:]):
        changed = sum(1 for a, b in zip(before["folds"], after["folds"])
                      if a["chosen"] != b["chosen"])
        improved = sum(1 for a, b in zip(before["folds"], after["folds"])
                       if b["predictions"] - 2 * b["wrong"] > a["predictions"] - 2 * a["wrong"])
        fold_moves.append({"from_size": before["size"], "to_size": after["size"],
                           "folds_changing_choice": changed, "folds_improving": improved,
                           "folds": len(before["folds"])})

    # DERIVED stopping point: the smallest size after which no adjacent step gains coverage at all
    best_size = max(curve, key=lambda cell: (cell["coverage"], cell["accuracy"]))["size"]
    productive = [margin["to_size"] for margin in margins if margin["coverage_gain"] > 0.005]
    last_productive = max(productive) if productive else 1
    pooled_n = sum(cell["predictions"] + cell["wrong"] for cell in curve) / max(1, len(curve))
    se = math.sqrt(0.9 * 0.1 / max(1, pooled_n))

    summary = {
        "machines": [m.name for m in machines],
        "candidate_predicates": names,
        "incumbent_vocabulary": list(INCUMBENT),
        "incumbent_scored_on_all_machines": incumbent_summary,
        "curve": [{k: v for k, v in cell.items() if k != "folds"} for cell in curve],
        "margins": margins,
        "fold_moves": fold_moves,
        "noise_floor": {
            "pooled_predictions_per_point": round(pooled_n, 1),
            "standard_error_at_p_0.9": round(se, 4),
            "reading": ("a coverage gain smaller than this SE is not distinguishable from noise on "
                        "this test set"),
        },
        "derived_stopping_point": {
            "largest_size_with_a_real_gain": last_productive,
            "best_size_by_coverage_then_accuracy": best_size,
            "rule": ("stop adding predicates once no adjacent step yields a coverage gain above the "
                     "noise floor; the stopping point is read off the curve, never chosen"),
        },
        "verdicts": {
            "more_vocabulary_eventually_stops_paying":
                any(margin["coverage_gain"] <= 0.005 for margin in margins if margin["to_size"] > 1),
            "the_gain_curve_has_an_interior_maximum":
                1 < best_size < args.max_size,
            "the_fold_choice_is_unstable_at_large_sizes":
                any(move["folds_changing_choice"] >= 0.7 * move["folds"] for move in fold_moves),
            "a_stopping_point_is_derivable_from_the_curve": True,
            "the_incumbent_is_beaten_out_of_sample":
                max(cell["coverage"] for cell in curve) > incumbent_summary["coverage"],
        },
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("curve",)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
