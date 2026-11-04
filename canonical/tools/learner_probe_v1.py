#!/usr/bin/env python3
"""Measure what the model can and cannot learn, against the rule it claims to be learning.

Log 16 gave the creature a vocabulary. This probe answers the question underneath: can the model
it feeds use a distinction that is not additive? Before 2026-11-04 the answer was measured NO --
on `a > 0.5 AND b > 0.5` it refused to split at all and scored 0.700 against a base rate of 0.750.

Everything below is out-of-group: the model is fitted on one slice and scored on worlds it has
never seen. Noise is measured at the same sizes, because a learner that finds structure in noise
is not a learner. Cost is world count, per AGENTS.md -- not a solve rate.
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

from canonical.runtime import belief_v1 as belief  # noqa: E402
from canonical.tools.worlds_v1 import world           # noqa: E402

SCHEMA = "PROJECT_BRAIN_LEARNER_V1"
OUT = ROOT / "canonical" / "verification" / "LEARNER_V1.json"
RULES = ("and", "or", "product", "xor")   # names must exist in tools/worlds_v1.py


def measure_rule(kind: str, seeds: int = 6) -> dict:
    scores, baselines, accepted = [], [], 0
    for seed in range(1, seeds + 1):
        train, test = world(kind, 90, seed), world(kind, 60, seed + 50)
        split = int(len(train) * 0.75)
        model = belief.blank()
        belief.fit(model, train[:split], train[split:])
        scores.append(belief.accuracy(model, test)[0])
        baselines.append(belief.majority_baseline(test))
        accepted += int(model["splits_accepted"] > 0)
    mean = lambda xs: round(sum(xs) / len(xs), 4)                   # noqa: E731
    return {"model": mean(scores), "majority_baseline": mean(baselines),
            "worlds_with_structure": f"{accepted} of {seeds}"}


def measure_noise(sizes=(60, 90, 140), trials=20) -> dict:
    out = {}
    for size in sizes:
        splits = 0
        for trial in range(trials):
            model = belief.blank()
            belief.fit(model, world("noise", size, trial * 7))
            splits += model["splits_accepted"]
        out[str(size)] = {"worlds": trials, "distinctions_invented": splits}
    return out


def measure(write: bool = False) -> dict:
    result = {
        "schema": SCHEMA,
        "generated_by": "canonical/tools/learner_probe_v1.py",
        "what_this_is": (
            "Whether the model can learn a rule that is not one cut at a time. A conjunction gains "
            "nothing from either of its cuts alone; a model judged cut-by-cut cannot see it."
        ),
        "rules": {kind: measure_rule(kind) for kind in RULES},
        "noise": measure_noise(),
        "honest_failures": [
            "xor is not learned: a two-cut tree applies the same two cuts everywhere, and xor "
            "needs a different cut in each branch",
            "the whole-tree search is bounded at two cuts; deeper interactions are out of reach",
            "two earlier attempts were measured and discarded: pair lookahead admitted splits in "
            "6-7 of 20 structureless worlds, log-loss judging in 57 across 10",
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
    print(json.dumps({"rules": result["rules"], "noise": result["noise"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
