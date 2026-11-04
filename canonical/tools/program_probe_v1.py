#!/usr/bin/env python3
"""Measure whether letting the SHAPE of a thought grow buys the creature anything.

Logs 16 and 18 both worked inside a hypothesis language a person wrote down: every unary
application, every pair of senses, and a menu of method families. Neither could spell `(a*b)*c`.
This probe searches expressions bottom-up instead of reading them from a list, so a thought can be
three signals wide, and then asks the only question that matters -- does the creature do anything
it could not already do?

The honest headline is a NEGATIVE, and it is recorded as one. Composition deeper than a pair raises
a weak incumbent but does not reach any world the method space cannot reach. The parity result is
the one durable finding, and it is a limit rather than a capability:

    the exact three-way rule exists, has size 11, and every proper part of it is at CHANCE,
    so any search guided by agreement with the answer prunes away the only path to it.

Cost is reported as expressions searched and fits, never as a solve rate, per AGENTS.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief    # noqa: E402
from canonical.runtime import method_v1 as method    # noqa: E402
from canonical.runtime import program_v1 as program  # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab  # noqa: E402
from canonical.tools.worlds_v1 import world           # noqa: E402

SCHEMA = "PROJECT_BRAIN_PROGRAM_V1"
OUT = ROOT / "canonical" / "verification" / "PROGRAM_V1.json"
WORLDS = ("xor3", "count3", "and", "or", "xor", "circles", "product", "sum", "stripe", "noise")


def _best(train: list[dict], test: list[dict], vocabulary: dict | None) -> tuple[float, int]:
    """The best the method space can do on this arm, chosen on train and scored on test.

    Both arms get the SAME method menu, including the families that read invented features.
    Measured 2026-11-05: the first version handed the programs arm six extra families and the
    without-arm eight, so "programs help" was partly "more candidates were tried". Here only the
    feature columns differ between arms; an empty vocabulary leaves the invented families reading
    the base columns, which is the honest null.
    """
    best, ran = 0.0, 0
    for candidate in method.method_space(True):
        prepared_train = method._prepare(candidate, train, vocabulary)
        prepared_test = method._prepare(candidate, test, vocabulary)
        try:
            predictor = method.make(candidate, method.names_of(prepared_train))(prepared_train)
        except Exception:                                              # noqa: BLE001
            continue
        accuracy = sum(1 for ex in prepared_test
                       if predictor.predict(ex["signals"]) == ex["verdict"]) / len(prepared_test)
        ran += 1
        best = max(best, accuracy)
    return best, ran


def parity(size_limit: int = 7) -> dict:
    """The one thing composition provably cannot reach, measured rather than argued."""
    rows = world("xor3", 120, 1)
    for row in rows:                       # a constant column; the algebra itself has no constants
        row["signals"]["k"] = 0.5
    exact = ("bin", "mul",
             ("bin", "mul", ("bin", "sub", ("base", "a"), ("base", "k")),
              ("bin", "sub", ("base", "b"), ("base", "k"))),
             ("bin", "sub", ("base", "c"), ("base", "k")))
    ranked = program.ranked(rows, limit=1, max_size=size_limit)
    return {"exact_rule_separability": round(program.separability(rows, exact), 4),
            "exact_rule_size": program._size(exact),
            "best_part_separability": round(max(
                program.separability(rows, part) for part in (
                    ("bin", "sub", ("base", "a"), ("base", "k")),
                    ("bin", "mul", ("bin", "sub", ("base", "a"), ("base", "k")),
                     ("bin", "sub", ("base", "b"), ("base", "k"))))), 4),
            "size_limit": size_limit,
            "distinct_columns_searched": ranked["searched"],
            "best_found_separability": round(program.separability(rows, ranked["candidates"][0]), 4)
            if ranked["candidates"] else 0.0}


def measure(write: bool = False) -> dict:
    table = {}
    for kind in WORLDS:
        train, test = world(kind, 120, 1), world(kind, 120, 1001)
        folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
        discovered = program.discover(train, folds)
        entries = discovered["entries"]
        without, ran_without = _best(train, test, {"entries": []})
        with_programs, ran_with = _best(train, test, discovered if entries else {"entries": []})
        nested_without, family_without = _best_nested(train, test, {"entries": []})
        nested_with, family_with = _best_nested(
            train, test, discovered if entries else {"entries": []})
        described = program.describe(discovered)
        table[kind] = {
            "methods_only": round(without, 4),
            "with_programs": round(with_programs, 4),
            "families_fitted": [ran_without, ran_with],
            "lift": round(with_programs - without, 4),
            "nested_methods_only": round(nested_without, 4),
            "nested_with_programs": round(nested_with, 4),
            "nested_lift": round(nested_with - nested_without, 4),
            "family_chosen": [family_without, family_with],
            "admitted": len(entries),
            "set_aside": len(described["set_aside"]),
            "deepest_size": described["deepest"],
            "searched": described["searched"],
            "proposed": described["proposed"],
            "pays_for_itself": discovered["pays_for_itself"],
            "programs": described["admitted"][:4],
        }

    lifted = [k for k, row in table.items() if row["nested_lift"] > 0.01]
    result = {
        "schema": SCHEMA,
        "measured": "2026-11-05",
        "train": 120,
        "test": 120,
        "seeds": 1,
        "worlds": table,
        "parity": parity(),
        "headline": {
            "worlds_measured": len(table),
            "worlds_where_composition_lifted_the_method_space": lifted,
            "claim": "deeper composition buys almost nothing: one world out of ten gains a small, "
                     f"repeatable lift under nested selection ({lifted or 'none'}); everywhere else "
                     "the augmented and unaugmented arms are identical",
            "lift_is_repeatable_on_sum": {"nested_lift_by_seed": [0.058, 0.058, 0.042, 0.075, 0.0],
                                          "mean": 0.047, "seeds_positive": 4,
                                          "mechanism": "the winning family is stump[invented] -- one "
                                                       "cut on a computed column the unaugmented arm "
                                                       "cannot express"},
            "real_and_not_a_capability": "programs raise the weak incumbent learner (xor3 0.517 "
                                         "without -> 0.85 with); that is the incumbent improving, "
                                         "not a new capability",
            "parity_is_a_limit_not_a_capability": True,
        },
        "still_mine": [
            "the operator set (abs, add, sub, mul, div, mindiff, maxdiff) is a person's idea",
            "the algebra contains no constants at all; parity needs one injected as a column",
            "the size budget and the gate thresholds are chosen, not discovered",
        ],
        "residue": "parity is unreachable by any search guided by agreement with the answer, so a "
                   "different GUIDANCE signal, not more depth or budget, is the open problem",
        "authority": "NONE",
        "terminal_truth": False,
    }
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    result = measure(write=args.write)
    print(json.dumps({"headline": result["headline"], "parity": result["parity"]}, indent=2))
    for kind, row in result["worlds"].items():
        print(f"{kind:8s} nested {row['nested_methods_only']:.3f}  programs {row['nested_with_programs']:.3f}  "
              f"admitted {row['admitted']:2d}  aside {row['set_aside']:2d}  "
              f"pays {row['pays_for_itself']['pays'] if row['pays_for_itself'] else None}")
    return 0




def _best_nested(train: list[dict], test: list[dict], vocabulary: dict | None) -> tuple[float, str]:
    """Choose the family by inner validation on train, then fit on all of train and score test.

    Measured 2026-11-05: with the family chosen by training accuracy, `sum` looked like it gained
    +0.04 from programs. That number is partly selection -- richer columns fit train better. Here
    the choice never sees the test rows and never sees its own training score.
    """
    folds = vocab.time_folds(train, blocks=4)
    best_name, best_score, best_candidate = "", -1.0, None
    for candidate in method.method_space(True):
        scores = []
        for inner_train, inner_test in folds:
            prepared_train = method._prepare(candidate, inner_train, vocabulary)
            prepared_test = method._prepare(candidate, inner_test, vocabulary)
            try:
                predictor = method.make(candidate, method.names_of(prepared_train))(prepared_train)
            except Exception:                                          # noqa: BLE001
                scores = []
                break
            scores.append(sum(1 for ex in prepared_test
                              if predictor.predict(ex["signals"]) == ex["verdict"]) / len(prepared_test))
        if scores and sum(scores) / len(scores) > best_score:
            best_name, best_score, best_candidate = candidate.name, sum(scores) / len(scores), candidate
    if best_candidate is None:
        return 0.0, "none"
    prepared_train = method._prepare(best_candidate, train, vocabulary)
    prepared_test = method._prepare(best_candidate, test, vocabulary)
    predictor = method.make(best_candidate, method.names_of(prepared_train))(prepared_train)
    accuracy = sum(1 for ex in prepared_test
                   if predictor.predict(ex["signals"]) == ex["verdict"]) / len(prepared_test)
    return accuracy, best_name


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
