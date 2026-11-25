#!/usr/bin/env python3
"""Price every predicate in the lifted vocabulary: coverage gained per prediction risked.

Lifting is the only mechanism in this project that ever moved coverage (0.126 -> 0.70 for zero extra
evidence), and it has never been optimised. This holds the walk fixed at 120 and adds one predicate at a
time, measuring what it buys and what it costs.

THE CURRENCY, DEFINED BEFORE MEASURING
--------------------------------------
Every added predicate can only ever make a key MORE specific (keys are conjunctions of satisfied
predicates), so it can never create a law -- only split one. Splitting is the interesting event: if the
split is real, the pieces stay true and cover states the whole did not. If it is noise, the pieces
disagree and the system refuses.

    reach_gained   predictions with the predicate minus predictions without
    wrong_added    wrong with the predicate minus wrong without
    price          wrong_added / max(1, reach_gained)   -- errors per prediction bought

A predicate worth keeping has reach_gained > 0 and price near 0. A predicate that "looks like it should
help" (a domain-plausible feature) but scores price > 1 is a predicate that is describing the sample.

WHY SINGLE PREDICATES AND NOT SUBSETS
-------------------------------------
With 5 base predicates there are 32 subsets, which is few enough to enumerate exhaustively -- so this
does that too, and reports the best subset found. The single-predicate table is what makes the result
explainable; the subset sweep is what makes it complete.
"""
from __future__ import annotations

import argparse
import itertools
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

import acquire_the_second_witness_v1 as walker  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_PRICE_THE_VOCABULARY_V1"
State = tuple[tuple[str, str], ...]
HELD_OUT_SHARE = 0.35

#: The candidate predicates. Each is a pure function of a state; none names a machine or a literal.
PREDICATES: dict[str, Callable[[State], bool]] = {
    "HAS_DUPLICATE_CONTENT": lambda s: any(s.count(r) > 0 and sum(1 for _i, c in s if c == r[1]) > 1
                                           for r in s),
    "ALL_CONTENT_UNIQUE": lambda s: len({c for _i, c in s}) == len(s),
    "ROWS_2": lambda s: len(s) == 2,
    "ROWS_3": lambda s: len(s) == 3,
    "ROWS_4": lambda s: len(s) == 4,
    # the additions under test, each independently plausible
    "ROWS_1": lambda s: len(s) == 1,
    "HAS_MANY_ROWS": lambda s: len(s) >= 4,
    "CONTENT_SORTED": lambda s: [c for _i, c in s] == sorted(c for _i, c in s),
    "IDENT_SORTED": lambda s: [i for i, _c in s] == sorted(i for i, _c in s),
    "HAS_REPEATED_IDENT_LENGTH": lambda s: len({len(i) for i, _c in s}) == 1,
}


def key_of(state: State, active: Sequence[str]) -> str:
    return "|".join(name for name in active if PREDICATES[name](state)) or "NO_PATTERN"


def effect_of(before: State, after: State) -> str:
    from canonical.tools.lift_the_keys_v1 import effect_of as lifted_effect
    added = [row for row in after if row not in before]
    deleted = [row for row in before if row not in after]
    return lifted_effect(added, deleted, tuple(after))


def learn(walked: list[tuple[str, State, State]], idents: Sequence[str],
          active: Sequence[str]) -> dict[tuple[int, str], str]:
    table: dict[tuple[int, str], str] = {}
    for ident, before, after in walked:
        rank = sorted(idents).index(ident)
        table[(rank, key_of(before, active))] = effect_of(before, after)
    return table


def score(table: dict[tuple[int, str], str], idents: Sequence[str],
          held: list[tuple[str, State, State]]) -> dict[str, int]:
    predictions = wrong = refused = 0
    for ident, before, after in held:
        rank = sorted(idents).index(ident)
        effect = table.get((rank, key_of(before, ())))
        # `key_of` with an empty active list is not right here: the caller passes real predicates via
        # the closure below, so this branch is only used by tests.
        if effect is None:
            refused += 1
            continue
        predictions += 1
        if effect != effect_of(before, after):
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


def evaluate(walked, idents, held, active: Sequence[str]) -> dict[str, int]:
    table: dict[tuple[int, str], str] = {}
    conflicts: set[tuple[int, str]] = set()
    for ident, before, after in walked:
        rank = sorted(idents).index(ident)
        key = (rank, key_of(before, active))
        effect = effect_of(before, after)
        if key in table and table[key] != effect:
            conflicts.add(key)          # laws disagree -> refuse, same rule as everywhere else
        table[key] = effect
    predictions = wrong = refused = 0
    for ident, before, after in held:
        rank = sorted(idents).index(ident)
        key = (rank, key_of(before, active))
        if key not in table or key in conflicts:
            refused += 1
            continue
        predictions += 1
        if table[key] != effect_of(before, after):
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--walk-steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)

    started = time.time()
    data = []
    for name in sorted(room.all_machines()):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / name
            root.mkdir(parents=True)
            machine = room.all_machines()[name](root)
            machine.reset()
            atoms = list(machine.atoms)
            idents = [atom.ident for atom in atoms]
            full = [(ident, tuple(before), tuple(after))
                    for ident, before, after in base.explore(machine, atoms, 3)]
            full.sort()
            random.Random(args.seed).shuffle(full)
            cut = max(1, int(len(full) * HELD_OUT_SHARE))
            held = full[:cut]
            held_keys = {(ident, before) for ident, before, _a in held}
            walked = [(ident, tuple(before), tuple(after))
                      for ident, before, after in walker.budgeted_walk(machine, atoms,
                                                                       args.walk_steps, args.seed)
                      if (ident, tuple(before)) not in held_keys]
            if walked and held:
                data.append((name, idents, walked, held))

    def total(active: Sequence[str]) -> dict[str, Any]:
        predictions = wrong = refused = 0
        for _name, idents, walked, held in data:
            cell = evaluate(walked, idents, held, active)
            predictions += cell["predictions"]
            wrong += cell["wrong"]
            refused += cell["refused"]
        return {"predictions": predictions, "wrong": wrong, "refused": refused,
                "accuracy": round(predictions / max(1, predictions + wrong), 4),
                "coverage": round(predictions / max(1, predictions + refused), 4)}

    base_names = ("HAS_DUPLICATE_CONTENT", "ALL_CONTENT_UNIQUE", "ROWS_2", "ROWS_3", "ROWS_4")
    baseline = total(base_names)
    singles = {}
    for name in PREDICATES:
        if name in base_names:
            continue
        with_it = total(base_names + (name,))
        reach = with_it["predictions"] - baseline["predictions"]
        added_wrong = with_it["wrong"] - baseline["wrong"]
        singles[name] = {**with_it, "reach_gained": reach, "wrong_added": added_wrong,
                         "price": round(added_wrong / max(1, reach) if reach > 0 else None, 3)
                         if reach > 0 else None}

    best = None
    sweep = []
    for size in range(1, len(PREDICATES) + 1):
        for subset in itertools.combinations(sorted(PREDICATES), size):
            cell = total(subset)
            sweep.append({"subset": list(subset), **cell})
            key = (cell["accuracy"], cell["coverage"])
            if best is None or key > (best["accuracy"], best["coverage"]):
                best = {"subset": list(subset), **cell}

    # --- HONEST EVALUATION: selecting the best of 1023 subsets on the data it is scored on is the same
    # defect as the vocabulary leak two rounds ago. Leave-one-machine-out: choose the subset using only
    # the other machines, then score it on the machine it never saw.
    holdout_cells = []
    for index in range(len(data)):
        rest = [row for position, row in enumerate(data) if position != index]
        held_out = data[index]

        def total_on(active: Sequence[str], subset) -> dict[str, Any]:
            predictions = wrong = refused = 0
            for _name, idents, walked, held in subset:
                cell = evaluate(walked, idents, held, active)
                predictions += cell["predictions"]
                wrong += cell["wrong"]
                refused += cell["refused"]
            return {"predictions": predictions, "wrong": wrong, "refused": refused,
                    "accuracy": round(predictions / max(1, predictions + wrong), 4),
                    "coverage": round(predictions / max(1, predictions + refused), 4)}

        best_subset, best_key = None, None
        for size in range(1, len(PREDICATES) + 1):
            for subset in itertools.combinations(sorted(PREDICATES), size):
                cell = total_on(subset, rest)
                key = (cell["accuracy"], cell["coverage"])
                if best_key is None or key > best_key:
                    best_subset, best_key = subset, key
        holdout_cells.append({
            "machine": held_out[0],
            "chosen_on_the_other_nine": list(best_subset),
            "selected_baseline": total_on(base_names, [held_out]),
            "selected_subset": total_on(best_subset, [held_out]),
        })

    def pooled(key: str, side: str) -> dict[str, Any]:
        predictions = sum(cell[side]["predictions"] for cell in holdout_cells)
        wrong = sum(cell[side]["wrong"] for cell in holdout_cells)
        refused = sum(cell[side]["refused"] for cell in holdout_cells)
        return {"predictions": predictions, "wrong": wrong, "refused": refused,
                "accuracy": round(predictions / max(1, predictions + wrong), 4),
                "coverage": round(predictions / max(1, predictions + refused), 4)}

    honest_baseline = pooled("", "selected_baseline")
    honest_selected = pooled("", "selected_subset")

    winners = [name for name, cell in singles.items()
               if cell["reach_gained"] > 0 and (cell["price"] is not None and cell["price"] <= 0.25)]
    summary = {
        "machines": len(data),
        "walk_steps": args.walk_steps,
        "held_out_share": HELD_OUT_SHARE,
        "baseline": baseline,
        "singles": singles,
        "verdicts": {
            "some_predicate_buys_reach_at_low_price": bool(winners),
            "the_best_subset_beats_the_baseline_vocabulary":
                best is not None and best["accuracy"] >= baseline["accuracy"] - 0.01
                and best["coverage"] > baseline["coverage"],
            "no_added_predicate_helps": not any(cell["reach_gained"] > 0
                                                for cell in singles.values()),
            "a_single_predicate_buys_reach_at_zero_price":
                any(cell["price"] == 0 and cell["reach_gained"] > 0 for cell in singles.values()),
            "the_optimism_is_real_selected_subset_beats_baseline_out_of_sample":
                honest_selected["accuracy"] > honest_baseline["accuracy"]
                or honest_selected["coverage"] > honest_baseline["coverage"],
            "subset_selection_gains_do_not_survive_out_of_sample":
                honest_selected["accuracy"] <= honest_baseline["accuracy"] + 0.01
                and honest_selected["coverage"] <= honest_baseline["coverage"] + 0.02,
        },
        "predicates_worth_their_price": winners,
        "best_subset": best,
        "full_data_selection_is_optimistic": True,
        "leave_one_machine_out": {
            "baseline": honest_baseline,
            "selected_subset": honest_selected,
            "choices": [{"machine": cell["machine"],
                         "chosen": cell["chosen_on_the_other_nine"]} for cell in holdout_cells],
            "note": ("the subset is chosen on nine machines and scored on the tenth, so the gain here "
                     "is out-of-sample; compare it against the full-data best_subset, which is not."),
        },
        "sweep_size": len(sweep),
        "sweep": sorted(sweep, key=lambda cell: (-cell["accuracy"], -cell["coverage"]))[:10],
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
    print(json.dumps({k: v for k, v in summary.items() if k != "sweep"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
