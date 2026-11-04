#!/usr/bin/env python3
"""Measure whether the creature invents the distinctions it thinks with.

Log 16's question is not "can a module produce an expression". It is whether a system that was
handed a vocabulary can grow past it without a person adding a column. So every number below is
a before/after over the SAME world and the SAME seed, and the only thing that changes is whether
the creature is allowed to invent.

Two kinds of measurement, and the second is the one that counts:

  offline  the vocabulary is discovered from a training split, then handed to the belief tree
           and scored on a holdout. This isolates the mechanism.
  live     the real `organism_v1.tick` loop runs against a world whose rule is a product -- a
           rule no single sense can express. Nobody calls discovery; the creature examines its
           own experience and decides. This isolates whether it is alive.

Cost is reported as measurement spend (worlds, ticks), never as a solve rate, per AGENTS.md.

Measured 2026-11-04. Honest failure: `ratio` is still unsolved and inventing a vocabulary there
costs accuracy (0.883 -> 0.533) until the pay-for-itself guard refuses it.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief      # noqa: E402
from canonical.runtime import organism_v1 as organism  # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab   # noqa: E402

SCHEMA = "PROJECT_BRAIN_VOCABULARY_V1"
OUT = ROOT / "canonical" / "verification" / "VOCABULARY_V1.json"


# --------------------------------------------------------------------------- worlds
def offline_world(kind: str, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for index in range(n):
        a, b = rng.random(), rng.random()
        verdict = {
            "ratio": "BIG" if a / (b + 0.001) > 1 else "SMALL",
            "product": "HIGH" if a * b > 0.25 else "LOW",
            "sum": "HI" if a + b > 1 else "LO",
            "xor": "DIFF" if (a > 0.5) != (b > 0.5) else "SAME",
            "noise": rng.choice(["X", "Y"]),
        }[kind]
        out.append({"group": f"g{index}", "signals": {"a": a, "b": b}, "verdict": verdict})
    return out


def score_vocabulary(vocabulary: dict, train: list[dict], test: list[dict]) -> float:
    space = lambda rows: vocab.augment(rows, vocabulary)          # noqa: E731
    model = belief.blank()
    split = int(len(train) * 0.75)
    belief.fit(model, space(train[:split]), space(train[split:]))
    for example in space(train[:split]):
        belief.observe(model, example["signals"], example["verdict"])
    return round(belief.accuracy(model, space(test))[0], 4)


def measure_offline() -> dict:
    rows = {}
    invented_total = 0
    for kind in ("ratio", "product", "sum", "xor"):
        train, test = offline_world(kind, 90, 1), offline_world(kind, 60, 2)
        discovered = vocab.discover(train, belief.capability_folds(train))
        rows[kind] = {
            "fixed_vocabulary": score_vocabulary(vocab.blank(), train, test),
            "invented_vocabulary": score_vocabulary(discovered, train, test),
            "invented": [e["renders"] for e in discovered["entries"]],
            "proposed": discovered.get("proposed", 0),
            "person_enumerated_features": 0,
        }
    for trial in range(8):
        data = offline_world("noise", 90, trial * 7)
        invented_total += len(vocab.discover(data, belief.capability_folds(data))["entries"])
    rows["_noise"] = {"worlds": 8, "invented": invented_total}
    return rows


def measure_live(seeds: int = 30, ticks: int = 160) -> dict:
    def run(kind: str, seed: int, grow: bool) -> tuple[float, int, int]:
        rng = random.Random(seed)
        targets = []
        for index in range(ticks):
            a, b = rng.random(), rng.random()
            if kind == "product":
                verdict = "HIGH" if a * b > 0.25 else "LOW"
            else:
                verdict = rng.choice(["HIGH", "LOW"])
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

        state = organism.blank_state()
        organs = {"geometry": Geometry()}
        hits = predicted = 0
        for _ in range(ticks):
            if not grow:
                state["vocabulary_next_check"] = 10 ** 9
            row = organism.tick(state, organs)
            if row.get("predicted") is not None:
                predicted += 1
                hits += int(row["predicted"] == row["observed"])
        grown = len((state.get("vocabulary") or {}).get("entries") or [])
        return (hits / predicted if predicted else 0.0), predicted, grown

    product = {"frozen": [], "growing": [], "worlds_that_invented": 0}
    for seed in range(seeds):
        frozen, n_frozen, _ = run("product", seed, False)
        growing, n_growing, entries = run("product", seed, True)
        product["frozen"].append(round(frozen, 3))
        product["growing"].append(round(growing, 3))
        product["worlds_that_invented"] += int(entries > 0)
        product["predictions_frozen"] = product.get("predictions_frozen", 0) + n_frozen
        product["predictions_growing"] = product.get("predictions_growing", 0) + n_growing
    noise = {"worlds_that_invented": 0}
    for seed in range(seeds):
        _, _, entries = run("noise", seed, True)
        noise["worlds_that_invented"] += int(entries > 0)

    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "seeds": seeds, "ticks": ticks,
        "product": {
            "frozen_prediction_accuracy": mean(product["frozen"]),
            "growing_prediction_accuracy": mean(product["growing"]),
            "worlds_that_invented": product["worlds_that_invented"],
            "predictions_frozen": product.get("predictions_frozen", 0),
            "predictions_growing": product.get("predictions_growing", 0),
        },
        "noise": {"worlds_that_invented": noise["worlds_that_invented"],
                  "false_invention_rate": round(noise["worlds_that_invented"] / seeds, 4)},
    }


def measure(write: bool = False) -> dict:
    offline = measure_offline()
    live = measure_live()
    result = {
        "schema": SCHEMA,
        "generated_by": "canonical/tools/vocabulary_probe_v1.py",
        "what_this_is": (
            "Whether a running system can grow the set of distinctions it thinks in. The "
            "algebra is given; which compositions become permanent is decided against held-out "
            "experience by the system itself. No feature is enumerated by a person."
        ),
        "offline": offline,
        "live": live,
        "honest_failures": [
            "ratio is unsolved: 0.883 fixed -> 0.533 invented, because the tree that approximates "
            "the diagonal loses its ladder when composed columns are added",
            "the live loop predicts rarely, so the growing-vs-frozen contrast rests on a small "
            "number of predictions rather than on a large sample",
            "one live noise stream in thirty still invents a distinction",
            "the permutation gate has never fired in 52 measured offline worlds; the load-bearing "
            "guards are the per-fold rule and the pay-for-itself check",
        ],
        "person_enumerated_distinctions": 0,
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
    print(json.dumps({"offline": result["offline"], "live": result["live"]}, indent=2)[:2400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
