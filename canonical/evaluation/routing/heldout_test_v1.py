"""Run the held-out probes against FULL and NO_DICT.  This is the test that decides whether
last round's 84.4% was a method or a memory."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, ".")

import canonical.evaluation.routing.ablate_the_dictionary_v1 as A
import canonical.evaluation.routing.scale_experiment_v1 as E
from canonical.evaluation.routing.heldout_probes_v1 import HELDOUT


def rate_heldout(n: int, cond: str, seeds: int = 20) -> tuple[float, int]:
    A.set_condition(cond)
    right = total = 0
    for s in range(seeds):
        lib = E.build_library(n, random.Random(s))
        for key, probe in HELDOUT.items():
            if key not in lib:
                continue
            total += 1
            if E.structure_route(probe, lib) == key:
                right += 1
    A.set_condition("FULL")
    return (right / total if total else 0.0), total


if __name__ == "__main__":
    print(f"{'skills':>7} {'FULL':>8} {'NO_DICT':>9}   (held-out probes only)")
    for n in (10, 25, 50, 64):
        f, t = rate_heldout(n, "FULL")
        d, _ = rate_heldout(n, "NO_DICT")
        print(f"{n:>7} {f:>7.1%} {d:>8.1%}   n={t}")
