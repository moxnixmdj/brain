#!/usr/bin/env python3
"""Measure whether the creature choosing its own method is worth anything.

Seventeen logs, one learning procedure, every constant mine. `xor` failed in every one of them.
This probe answers the question underneath that: if the method itself is an object of measurement,
does the creature reach worlds its incumbent cannot?

Two kinds of number, and the second is the one that matters:

  offline  a method is chosen from the creature's experience, then scored on a world it never saw
  live     the real organism loop runs, and the only difference is whether it may use the method
           it adopted

Cost is reported as worlds and fits, never as a solve rate, per AGENTS.md.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief      # noqa: E402
from canonical.runtime import method_v1 as method      # noqa: E402
from canonical.runtime import organism_v1 as organism  # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab   # noqa: E402
from canonical.tools.worlds_v1 import world            # noqa: E402

SCHEMA = "PROJECT_BRAIN_METHOD_V1"
OUT = ROOT / "canonical" / "verification" / "METHOD_V1.json"
RULES = ("and", "or", "xor", "circles", "product", "sum", "stripe")


def offline(kind: str, seeds: int = 4) -> dict:
    scores, baselines, adopted = [], [], 0
    picks: collections.Counter = collections.Counter()
    for seed in range(1, seeds + 1):
        train, test = world(kind, 90, seed), world(kind, 90, seed + 1000)
        folds = belief.capability_folds(train, seed=belief.PERMUTATION_SEED)
        vocabulary = vocab.discover(train, folds)
        decision = method.choose(train, folds, vocabulary=vocabulary)
        chosen = decision["chosen"]
        if not isinstance(chosen, method.Method):
            chosen = next(m for m in method.method_space(True) if m.name == chosen)
        rows = method._prepare(chosen, train, vocabulary)
        predictor = method.make(chosen, method.names_of(rows))(rows)
        scored = method._prepare(chosen, test, vocabulary)
        scores.append(sum(1 for ex in scored
                          if predictor.predict(ex["signals"]) == ex["verdict"]) / len(scored))
        majority = collections.Counter(ex["verdict"] for ex in train).most_common(1)[0][0]
        baselines.append(sum(1 for ex in test if ex["verdict"] == majority) / len(test))
        adopted += int(decision["adopted"])
        picks[chosen.name] += 1
    mean = lambda xs: round(sum(xs) / len(xs), 4)                  # noqa: E731
    return {"heldout": mean(scores), "baseline": mean(baselines),
            "worlds_that_adopted": f"{adopted} of {seeds}", "methods_chosen": dict(picks)}


def live(kind: str, ticks: int = 200, seed: int = 7) -> dict:
    rng = random.Random(seed)
    targets = []
    for index in range(ticks):
        a, b = rng.random(), rng.random()
        if kind == "xor":
            verdict = "DIFF" if (a > 0.5) != (b > 0.5) else "SAME"
        else:
            verdict = rng.choice(["X", "Y"])
        targets.append({"id": f"t{index}", "a": a, "b": b, "verdict": verdict})

    class Geometry(organism.Organ):
        name = "geometry"

        def targets(self):
            return targets

        def senses(self, target):
            return {"a": target["a"], "b": target["b"]}

        def act(self, target):
            return {"applied": True}

        def observe(self, target, acted):
            return target["verdict"]

        def predict(self, target, record):
            return organism._expected(record)

    def run(use_methods: bool):
        real = organism.method_predictor
        if not use_methods:
            organism.method_predictor = lambda *a, **k: None
        state = organism.blank_state()
        hits = predicted = 0
        try:
            for _ in range(ticks):
                row = organism.tick(state, {"geometry": Geometry()})
                if row.get("predicted") is not None:
                    predicted += 1
                    hits += int(row["predicted"] == row["observed"])
        finally:
            organism.method_predictor = real
        return (round(hits / predicted, 4) if predicted else 0.0), predicted, \
            (state.get("method") or {}).get("method")

    inc, inc_n, _ = run(False)
    chosen, chosen_n, picked = run(True)
    return {"incumbent_only": inc, "predictions_incumbent": inc_n,
            "with_method_choice": chosen, "predictions_with_methods": chosen_n,
            "method_picked": picked}


def measure(write: bool = False) -> dict:
    result = {
        "schema": SCHEMA,
        "generated_by": "canonical/tools/method_probe_v1.py",
        "what_this_is": (
            "The learning method is chosen by measurement from a generated space of methods, "
            "instead of being fixed by whoever wrote the code. Whether that is worth anything is "
            "a number below."
        ),
        "offline": {kind: offline(kind) for kind in RULES},
        "noise": offline("noise", seeds=10),
        "live": {kind: live(kind) for kind in ("xor", "noise")},
        "honest_failures": [
            "the method PRIMITIVES are still mine: tree and nearest neighbour are a person's idea "
            "of what hypotheses are thinkable",
            "one structureless world in forty adopts a method; measured out of sample it did no "
            "harm, but the claim was not warranted",
            "a greedy axis-aligned tree still cannot learn xor (0.625 on its own training data) -- "
            "the world was reached by a different family, not by a deeper tree",
        ],
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
    print(json.dumps({"offline": result["offline"], "noise": result["noise"],
                      "live": result["live"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
