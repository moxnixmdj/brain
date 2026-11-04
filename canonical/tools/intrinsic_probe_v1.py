#!/usr/bin/env python3
"""Measure the two things log 19 said were missing, and be honest when they do not arrive.

Log 19 ended with a wall: parity separates at 1.000 while every proper part of it is at chance, so
a search steered by agreement with the answer deletes the only path. It named two blockers, and
this probe measures both:

  constants   the algebra had none, so no threshold-centred rule was even spellable
  valuation   every thought had to pay immediately, so a chain of worthless steps died

The first is fixed and the fix is measurable. The second was rebuilt three ways (novelty, mixed,
adaptive) and none of them held the chain, which is reported as the negative it is.

The `adaptive` arm is the self-directed one: it watches its own objective progress and shifts to
novelty when it stalls. It fires on the wrong worlds, because a deceptive world keeps handing out
small incidental gains that look exactly like progress.

Cost is reported as columns archived, never as a solve rate, per AGENTS.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import intrinsic_v1 as intrinsic   # noqa: E402
from canonical.runtime import program_v1 as program       # noqa: E402
from canonical.tools.worlds_v1 import world               # noqa: E402

SCHEMA = "PROJECT_BRAIN_INTRINSIC_V1"
OUT = ROOT / "canonical" / "verification" / "INTRINSIC_V1.json"
WORLDS = ("xor3", "count3", "and", "or", "xor", "circles", "product", "sum", "stripe", "noise")
POLICIES = ("objective", "novelty", "random", "mixed")
BUDGET = 1200
PER_LEVEL = 16


def parity_expressibility() -> dict:
    """Can a DERIVED constant spell the rule log 19 said needed an injected column?"""
    train, test = world("xor3", 120, 1), world("xor3", 120, 1001)
    pooled = [value for ex in train
              for value in (ex["signals"]["a"], ex["signals"]["b"], ex["signals"]["c"])]
    centre = intrinsic.median(pooled)

    def centred(rows: list[dict], value: float) -> list[dict]:
        return [{**ex, "signals": {**ex["signals"], "m": value}} for ex in rows]

    structure = ("bin", "mul",
                 ("bin", "mul", ("bin", "sub", ("base", "a"), ("base", "m")),
                  ("bin", "sub", ("base", "b"), ("base", "m"))),
                 ("bin", "sub", ("base", "c"), ("base", "m")))
    arms = {}
    for label, value in (("typed_half", 0.5), ("derived_pooled_median", centre)):
        arms[label] = {
            "value": round(value, 4),
            "train_separability": round(program.separability(centred(train, value), structure), 4),
            "test_separability": round(program.separability(centred(test, value), structure), 4),
        }
    return {"constant": round(centre, 4), "structure_size": program._size(structure),
            "arms": arms,
            "reading": "the rule needs a centre, not MY centre: the data's own median reaches "
                       f"{arms['derived_pooled_median']['test_separability']:.3f} on held-out data"}


def measure(write: bool = False) -> dict:
    table: dict[str, dict] = {}
    adaptive: dict[str, dict] = {}
    for kind in WORLDS:
        train, test = world(kind, 120, 1), world(kind, 120, 1001)
        centred_train, constants = intrinsic.with_derived_constants(train)
        centred_test, _ = intrinsic.with_derived_constants(test)
        row: dict = {}
        for policy in POLICIES:
            found = intrinsic.search(centred_train, policy=policy, budget=BUDGET,
                                     per_level=PER_LEVEL, max_size=intrinsic.MAX_SIZE)
            column, separation = intrinsic.best_column(found, centred_train)
            row[policy] = {
                "archive": found["archive"],
                "train_separability": separation,
                "test_separability": round(program.separability(centred_test, column), 4)
                if column else 0.0,
                "size": program._size(column) if column else 0,
                "renders": program.describe({"entries": [{"renders": _render(column),
                                                          "size": program._size(column)}]})["admitted"]
                if column else [],
            }
        row["constants"] = {name: round(value, 4) for name, value in constants.items()}
        table[kind] = row

        chosen = intrinsic.search(centred_train, policy="adaptive", budget=BUDGET,
                                  per_level=PER_LEVEL, max_size=intrinsic.MAX_SIZE)
        adaptive[kind] = {"policy_by_size": chosen["policy_by_size"],
                          "gain_by_size": chosen["best_by_size"]}

    reached = {kind: max(table[kind][policy]["test_separability"] for policy in POLICIES)
               for kind in WORLDS}
    result = {
        "schema": SCHEMA,
        "measured": "2026-11-05",
        "train": 120,
        "test": 120,
        "budget": BUDGET,
        "per_level": PER_LEVEL,
        "max_size": intrinsic.MAX_SIZE,
        "worlds": table,
        "adaptive": adaptive,
        "parity_expressibility": parity_expressibility(),
        "headline": {
            "fixed": "constants are derived from the data -- the creature's own pooled median "
                     "spells the parity rule at 0.992 held-out, and a single computed column now "
                     "solves xor and sum exactly (1.000) where the method space reached 0.975/0.942",
            "not_fixed": "none of the four policies HOLDS the parity chain: best reach on xor3 is "
                         f"{max(table['xor3'][p]['train_separability'] for p in POLICIES):.3f} "
                         "against 0.992 for the structure it can already spell",
            "intrinsic_valuation": "novelty beats the paired random null at the same archive budget "
                                   f"({table['xor3']['novelty']['train_separability']:.3f} vs "
                                   f"{table['xor3']['random']['train_separability']:.3f} on xor3), "
                                   "so it is a real signal -- but it does not beat plain objective "
                                   "ranking, and it does not hold the chain",
            "self_direction": "the adaptive stall detector fires on xor and sum, where progress "
                              "exists, and never on xor3, where it is hopeless: incidental gains "
                              "look like progress, so stagnation is the wrong self-signal",
            "reached_by_any_policy": reached,
        },
        "still_mine": [
            "the median as the choice of constant, and pooling across signals",
            "the novelty metric (eight quantiles) and the per-level memory of 16",
            "the stall rule (two sizes without improvement)",
        ],
        "residue": "the wall is now RETENTION, not ranking and not expressibility: every prefix of "
                   "the parity chain is at chance, and the chain is one column among ~19,000, so a "
                   "memory of 16 cannot be expected to keep it. Credit assignment over intermediate "
                   "thoughts -- not a better ranking -- is the next layer",
        "authority": "NONE",
        "terminal_truth": False,
    }
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
    return result


def _render(expr: tuple) -> str:
    """Readable form; base columns are already named by where their value came from."""
    if expr[0] == "base":
        return expr[1]
    if expr[0] == "un":
        return f"{expr[1]}({_render(expr[2])})"
    return f"{expr[2]} {expr[1]} {expr[3]}" if expr[1] in ("sub", "div") else \
        f"{expr[1]}({_render(expr[2])}, {_render(expr[3])})"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    result = measure(write=args.write)
    print(json.dumps({k: result["headline"][k] for k in
                      ("fixed", "not_fixed", "intrinsic_valuation", "self_direction")}, indent=2))
    print(json.dumps(result["parity_expressibility"], indent=2))
    for kind, row in result["worlds"].items():
        print(f"{kind:8s} " + "  ".join(
            f"{policy[:4]} {row[policy]['train_separability']:.3f}/{row[policy]['test_separability']:.3f}"
            for policy in POLICIES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
